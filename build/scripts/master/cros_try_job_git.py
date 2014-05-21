# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import shutil

from StringIO import StringIO

try:
  # Create a block to work around evil sys.modules manipulation in
  # email/__init__.py that triggers pylint false positives.
  # pylint: disable=E0611,F0401
  from email.Message import Message
  from email.Utils import formatdate
except ImportError:
  raise

from buildbot.process.properties import Properties
from buildbot.schedulers.trysched import TryBase

from twisted.internet import defer, reactor, utils
from twisted.mail.smtp import SMTPSenderFactory
from twisted.python import log

from master.try_job_base import BadJobfile


def validate_job(parsed_job):
  # A list of field description tuples of the format:
  # (name, type, required).
  fields = [('name', basestring, True),
            ('user', basestring, True),
            ('email', list, True),
            ('bot', list, True),
            ('extra_args', list, False),
            ('version', int, True),
            ('slaves_request', list, False)]

  error_msgs = []
  for name, f_type, required in fields:
    val = parsed_job.get(name)
    if val is None:
      if required:
        error_msgs.append('Option %s missing!' % name)
    elif not isinstance(val, f_type):
      error_msgs.append('Option %s of wrong type!' % name)

  if error_msgs:
    raise BadJobfile('\n'.join(error_msgs))


def get_file_contents(poller, branch, file_path):
  """Returns a Deferred to returns the file's content."""
  return utils.getProcessOutput(
      poller.gitbin,
      ['show', 'origin/%s:%s' % (branch, file_path)],
      path=poller.workdir,
      )


def translate_v1_to_v2(parsed_job):
  """Translate tryjob desc from V1 to V2."""
  parsed_job['extra_args'].append('--remote-trybot')
  parsed_job['version'] = 2


def translate_v2_to_v3(parsed_job):
  """Translate tryjob desc from V2 to V3."""
  # V3 --remote-patches format is not backwards compatible.
  if any(a.startswith('--remote-patches') for a in parsed_job['extra_args']):
    raise BadJobfile('Cannot translate --remote-patches from tryjob v.2 to '
                     'v.3.  Please run repo sync.')

  parsed_job['version'] = 3


class CrOSTryJobGit(TryBase):
  """Poll a Git server to grab patches to try."""

  _PROPERTY_SOURCE = 'Try Job'
  # The version of tryjob that the master is expecting.
  _TRYJOB_FORMAT_VERSION = 3

  # Functions that translate from one tryjob version to another.
  _TRANSLATION_FUNCS = {
      1 : translate_v1_to_v2,
      2 : translate_v2_to_v3,
  }

  @classmethod
  def updateJobDesc(cls, parsed_job):
    """Ensure job description is in the format we expect."""
    while parsed_job['version'] < cls._TRYJOB_FORMAT_VERSION:
      prev_ver = parsed_job['version']
      translation_func = cls._TRANSLATION_FUNCS[parsed_job['version']]
      translation_func(parsed_job)
      if parsed_job['version'] <= prev_ver:
        raise AssertionError('translation function %s not incrementing version!'
                             % str(translation_func))

  def __init__(self, name, pollers, smtp_host, from_addr, reply_to,
               email_footer, properties=None):
    """Initialize the class.

    Arguments:
      name: See TryBase.__init__().
      pollers: A list of job repo git pit pollers.
      smtp_host: The smtp host for sending out error emails.
      from_addr: The email address to display as being sent from.
      reply_to: The email address to put in the 'Reply-To' email header field.
      email_footer: The footer to append to any emails sent out.
      properties: See TryBase.__init__()
    """
    TryBase.__init__(self, name, [], properties or {})
    self.pollers = pollers
    self.smtp_host = smtp_host
    self.from_addr = from_addr
    self.reply_to = reply_to
    self.email_footer = email_footer

  def startService(self):
    TryBase.startService(self)
    self.startConsumingChanges()

  def stopService(self):
    def rm_temp_dir(result):
      for poller in self.pollers:
        if os.path.isdir(poller.workdir):
          shutil.rmtree(poller.workdir)

    d = TryBase.stopService(self)
    d.addCallback(rm_temp_dir)
    d.addErrback(log.err)
    return d

  def get_props(self, bot, options):
    """Overriding base class method."""
    props = Properties()
    props.setProperty('extra_args', options.get('extra_args', []),
                      self._PROPERTY_SOURCE)
    props.setProperty('slaves_request', options.get('slaves_request', []),
                      self._PROPERTY_SOURCE)
    props.setProperty('chromeos_config', bot, self._PROPERTY_SOURCE)
    return props

  def create_buildset(self, ssid, parsed_job):
    """Overriding base class method."""
    log.msg('Creating try job(s) %s' % ssid)
    result = None
    for bot in parsed_job['bot']:
      buildset_name = '%s:%s' % (parsed_job['user'], parsed_job['name'])
      result = self.addBuildsetForSourceStamp(ssid=ssid,
          reason=buildset_name,
          external_idstring=buildset_name,
          builderNames=[bot],
          properties=self.get_props(bot, parsed_job))

    return result

  def send_validation_fail_email(self, name, emails, error):
    """Notify the user via email about the tryjob error."""
    html_content = []
    html_content.append('<html><body>')
    body = """
Your tryjob with name '%(name)s' failed the validation step.  This is most
likely because <br>you are running an older version of cbuildbot.  Please run
<br><code>repo sync chromiumos/chromite</code> and try again.  If you still
see<br>this message please contact chromeos-build@google.com.<br>
"""
    html_content.append(body % {'name': name})
    html_content.append("Extra error information:")
    html_content.append(error.replace('\n', '<br>\n'))
    html_content.append(self.email_footer)
    m = Message()
    m.set_payload('<br><br>'.join(html_content), 'utf8')
    m.set_type("text/html")
    m['Date'] = formatdate(localtime=True)
    m['Subject'] = 'Tryjob failed validation'
    m['From'] = self.from_addr
    m['Reply-To'] = self.reply_to
    result = defer.Deferred()
    sender_factory = SMTPSenderFactory(self.from_addr, emails,
                                       StringIO(m.as_string()), result)
    reactor.connectTCP(self.smtp_host, 25, sender_factory)

  @defer.deferredGenerator
  def gotChange(self, change, important):
    """Process the received data and send the queue buildset."""
    # Implicitly skips over non-files like directories.
    if len(change.files) != 1:
      # We only accept changes with 1 diff file.
      raise BadJobfile(
          'Try job with too many files %s' % (','.join(change.files)))

    # Find poller that this change came from.
    for poller in self.pollers:
      if poller.repourl == change.repository:
        break
    else:
      raise BadJobfile(
          'Received tryjob from unsupported repository %s' % change.repository)

    # pylint: disable=W0631
    wfd = defer.waitForDeferred(
        get_file_contents(poller, change.branch, change.files[0]))
    yield wfd
    parsed = json.loads(wfd.getResult())
    try:
      validate_job(parsed)
      self.updateJobDesc(parsed)
    except BadJobfile as e:
      self.send_validation_fail_email(parsed.setdefault('name', ''),
                                      parsed['email'], str(e))
      raise

    # The sourcestamp/buildsets created will be merge-able.
    d = self.master.db.sourcestamps.addSourceStamp(
        branch=change.branch,
        revision=change.revision,
        project=change.project,
        repository=change.repository,
        changeids=[change.number])
    d.addCallback(self.create_buildset, parsed)
    d.addErrback(log.err, "Failed to queue a try job!")
