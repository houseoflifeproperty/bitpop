# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A StatusReceiver module to mail someone when a step warns/fails.

Since the behavior is very similar to the MailNotifier, we simply inherit from
it and also reuse some of its methods to send emails.
"""

import datetime
import os
import re
import time
import urllib
try:
  # Create a block to work around evil sys.modules manipulation in
  # email/__init__.py that triggers pylint false positives.
  # pylint has issues importing it.
  # pylint: disable=E0611,F0401
  from email.MIMEMultipart import MIMEMultipart
  from email.MIMEText import MIMEText
  from email.Utils import formatdate
except ImportError:
  raise

from buildbot.status.builder import SUCCESS, FAILURE
from buildbot.status.mail import MailNotifier
from twisted.internet import defer
from twisted.python import log

from master.build_sheriffs import BuildSheriffs
from master import build_utils


class ChromiumNotifier(MailNotifier):
  """This is a status notifier which closes the tree upon failures.

  See builder.interfaces.IStatusReceiver to have more information about the
  parameters type."""
  # Overloaded functions need to be member even if they don't access self.
  # pylint: disable=R0201,W0221

  _CATEGORY_SPLITTER = '|'

  _NAME_UNDECORATOR = re.compile(r'(.*\S)\s*(\[([^\[\]]*)\])$')

  def __init__(self, reply_to=None, categories_steps=None,
      exclusions=None, forgiving_steps=None, status_header=None,
      use_getname=False, sheriffs=None,
      public_html='public_html', minimum_delay_between_alert=600,
      enable_mail=True, **kwargs):
    """Constructor with following specific arguments (on top of base class').

    @type categories_steps: Dictionary of category string mapped to a list of
                            step strings.
    @param categories_steps: For each category name we can specify the steps we
                             want to check for success to keep the tree opened.
                             An empty list of steps means that we simply check
                             for results == FAILURE to close the tree. Defaults
                             to None for the dictionary, which means all
                             categories, and the empty string category can be
                             used to say all builders.

    @type exclusions: Dictionary of strings to arrays of strings.
    @param exclusions: The key is a builder name for which we want to ignore a
                       series of step names set as the value in the form of an
                       array of strings. Defaults to None.

    @type forgiving_steps: List of strings.
    @param forgiving_steps: The list of steps for which a failure email should
                            NOT be sent to the blame list.

    @type status_header: String.
    @param status_header: Formatted header used in mail message.

    @type minimum_delay_between_alert: Integer.
    @param minimum_delay_between_alert: Don't send failure e-mails more often
                                        than the given value (in seconds).

    @type sheriffs: List of strings.
    @param sheriffs: The list of sheriff type names to be used for the set of
                     sheriffs.  The final destination changes over time.

    @type public_html: String.
    @param public_html: Directory from which any additional configuration is
                        read.  E.g. sheriff classes.

    @type use_getname: Boolean.
    @param use_getname: If true, step name is taken from getName(), otherwise
                        the step name is taken from getText().

    @type enable_mail: Boolean.
    @param enable_mail: If true, mail is sent, otherwise mail is formatted
                        and logged, but not sent.
    """
    # Change the default.
    kwargs.setdefault('sendToInterestedUsers', False)
    kwargs.setdefault('subject',
        'buildbot %(result)s in %(projectName)s on %(builder)s')
    MailNotifier.__init__(self, **kwargs)

    self.reply_to = reply_to
    self.categories_steps = categories_steps
    self.exclusions = exclusions or {}
    self.forgiving_steps = forgiving_steps or []
    self.status_header = status_header
    assert self.status_header
    self.minimum_delay_between_alert = minimum_delay_between_alert
    self.sheriffs = sheriffs or []

    self.public_html = public_html
    self.use_getname = use_getname
    self.enable_mail = enable_mail
    self._last_time_mail_sent = None

  def isInterestingBuilder(self, builder_status):
    """Confirm if we are interested in this builder."""
    builder_name = builder_status.getName()
    if builder_name in self.exclusions and not self.exclusions[builder_name]:
      return False
    if not self.categories_steps or '' in self.categories_steps:
      # We don't filter per step.
      return True

    if not builder_status.category:
      return False
    # We hack categories here. This should use a different builder attribute.
    for category in builder_status.category.split(self._CATEGORY_SPLITTER):
      if category in self.categories_steps:
        return True
    return False

  def isInterestingStep(self, build_status, step_status, results):
    """Watch all steps that don't end in success."""
    return results[0] != SUCCESS

  def builderAdded(self, builder_name, builder_status):
    """Only subscribe to builders we are interested in.

    @type name:    string
    @type builder: L{buildbot.status.builder.BuilderStatus} which implements
                   L{buildbot.interfaces.IBuilderStatus}
    """
    # Verify that MailNotifier would subscribe to this builder.
    if not MailNotifier.builderAdded(self, builder_name, builder_status):
      return None

    # Next check that ChromiumNotifier would subscribe.
    if self.isInterestingBuilder(builder_status):
      return self  # subscribe to this builder

  def buildStarted(self, builder_name, build_status):
    """A build has started allowing us to register for stepFinished.

    @type builder_name: string
    @type build_status: L{buildbot.status.builder.BuildStatus} which implements
                        L{buildbot.interfaces.IBuildStatus}
    """
    if self.isInterestingBuilder(build_status.getBuilder()):
      return self

  def buildFinished(self, builder_name, build_status, results):
    """Must be overloaded to avoid the base class sending email."""
    pass

  def getName(self, step_status):
    if not self.use_getname:
      # TODO(maruel): This code needs to die.
      texts = step_status.getText()
      if texts:
        return texts[0]
    return step_status.getName()

  def getGenericName(self, step_name):
    reduced_name = self._NAME_UNDECORATOR.match(step_name.strip())
    if reduced_name:
      return reduced_name.group(1)
    return step_name.strip()


  def stepFinished(self, build_status, step_status, results):
    """A build step has just finished.

    @type builder_status: L{buildbot.status.builder.BuildStatus}
    @type step_status:    L{buildbot.status.builder.BuildStepStatus}
    @type results: tuple described at
                   L{buildbot.interfaces.IBuildStepStatus.getResults}
    """

    if not self.isInterestingStep(build_status, step_status, results):
      return

    builder_status = build_status.getBuilder()
    builder_name = builder_status.getName()
    step_name = self.getName(step_status)
    step_class = self.getGenericName(step_name)

    if builder_name in self.exclusions:
      if step_class in self.exclusions[builder_name]:
        return

    if not self.categories_steps:
      # No filtering on steps.
      return self.buildMessage(builder_name, build_status, results, step_name)

    # Now get all the steps we must check for this builder.
    steps_to_check = []
    wildcard = False
    if builder_status.category:
      for category in builder_status.category.split(self._CATEGORY_SPLITTER):
        if self.categories_steps.get(category) == '*':
          wildcard = True
          break
        if category in self.categories_steps:
          steps_to_check += self.categories_steps[category]
    if '' in self.categories_steps:
      steps_to_check += self.categories_steps['']

    if wildcard or step_class in steps_to_check:
      return self.buildMessage(builder_name, build_status, results, step_name)

  def getFinishedMessage(self, dummy, builder_name, build_status, step_name):
    """Called after being done sending the email."""
    return defer.succeed(0)

  def sendMessage(self, message, recipients):
    if os.path.exists('.suppress_mailer') or not self.enable_mail:
      format_string = 'Not sending mail to %r (suppressed!):\n%s'
      if not self.enable_mail:
        format_string = 'Not sending mail to %r:\n%s'
      log.msg(format_string % (recipients, str(message)))
      return None
    return MailNotifier.sendMessage(self, message, recipients)

  def shouldBlameCommitters(self, step_name):
    if self.getGenericName(step_name) not in self.forgiving_steps:
      return True
    return False

  def _logMail(self, res, recipients, message):
    log.msg('Not sending mail to %r:\n%s' % (recipients, str(message)))

  def buildMessage(self, builder_name, build_status, results, step_name):
    """Send an email about the tree closing.

    Don't attach the patch as MailNotifier.buildMessage does.

    @type builder_name: string
    @type build_status: L{buildbot.status.builder.BuildStatus}
    @type step_name: name of this step
    """
    # TODO(maruel): Update function signature to match
    # mail.MailNotifier.buildMessage().
    if (self._last_time_mail_sent and self._last_time_mail_sent >
        time.time() - self.minimum_delay_between_alert):
      # Rate limit tree alerts.
      log.msg('Supressing repeat email')
      return
    log.msg('About to email')
    self._last_time_mail_sent = time.time()

    # TODO(maruel): Use self.createEmail().
    blame_interested_users = self.shouldBlameCommitters(step_name)
    project_name = self.master_status.getTitle()
    revisions_list = build_utils.getAllRevisions(build_status)
    build_url = self.master_status.getURLForThing(build_status)
    waterfall_url = self.master_status.getBuildbotURL()
    status_text = self.status_header % {
        'buildbotURL': waterfall_url,
        'builder': builder_name,
        'builderName': builder_name,
        'buildProperties': build_status.getProperties(),
        'buildURL': build_url,
        'project': project_name,
        'reason':  build_status.getReason(),
        'slavename': build_status.getSlavename(),
        'steps': step_name,
    }
    # Use the first line as a title.
    status_title = status_text.split('\n', 1)[0]
    blame_list = ','.join(build_status.getResponsibleUsers())
    revisions_string = ''
    latest_revision = 0
    if revisions_list:
      revisions_string = ', '.join([str(rev) for rev in revisions_list])
      latest_revision = max([rev for rev in revisions_list])
    if results[0] == FAILURE:
      result = 'failure'
    else:
      result = 'warning'

    # Generate a HTML table looking like the waterfall.
    # WARNING: Gmail ignores embedded CSS style. I don't know how to fix that so
    # meanwhile, I just won't embedded the CSS style.
    html_content = (
"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>%s</title>
</head>
<body>
  <a href="%s">%s</a><p>
  %s<p>
  <a href="%s">%s</a><p>
  Revision: %s<br>
""" % (status_title, waterfall_url, waterfall_url,
       status_text.replace('\n', "<br>\n"), build_url,
       build_url, revisions_string))

    # Only include the blame list if relevant.
    if blame_interested_users:
      html_content += "  Blame list: %s<p>\n" % blame_list

    html_content += build_utils.EmailableBuildTable(build_status, waterfall_url)
    html_content += "<p>"
    # Add the change list descriptions. getChanges() returns a tuple of
    # buildbot.changes.changes.Change
    for change in build_status.getChanges():
      html_content += change.asHTML()
    html_content += "</body>\n</html>"

    # Simpler text content for non-html aware clients.
    text_content = (
"""%s

%s

%swaterfall?builder=%s

--=>  %s  <=--

Revision: %s
Blame list: %s

Buildbot waterfall: http://build.chromium.org/
""" % (status_title,
       build_url,
       urllib.quote(waterfall_url, '/:'),
       urllib.quote(builder_name),
       status_text,
       revisions_string,
       blame_list))

    m = MIMEMultipart('alternative')
    # The HTML message, is best and preferred.
    m.attach(MIMEText(text_content, 'plain', 'iso-8859-1'))
    m.attach(MIMEText(html_content, 'html', 'iso-8859-1'))

    m['Date'] = formatdate(localtime=True)
    m['Subject'] = self.subject % {
        'result': result,
        'projectName': project_name,
        'builder': builder_name,
        'reason': build_status.getReason(),
        'revision': str(latest_revision),
        'buildnumber': str(build_status.getNumber()),
        'date': str(datetime.date.today()),
        'steps': step_name,
    }
    m['From'] = self.fromaddr
    if self.reply_to:
      m['Reply-To'] = self.reply_to

    recipients = list(self.extraRecipients[:])
    if self.sheriffs:
      recipients.extend(BuildSheriffs.GetSheriffs(classes=self.sheriffs,
                                                  data_dir=self.public_html))

    dl = []
    if self.sendToInterestedUsers and self.lookup and blame_interested_users:
      for u in build_status.getInterestedUsers():
        d = defer.maybeDeferred(self.lookup.getAddress, u)
        d.addCallback(recipients.append)
        dl.append(d)
    defered_object = defer.DeferredList(dl)
    if not self.enable_mail:
      defered_object.addCallback(self._logMail, recipients, m)
    else:
      defered_object.addCallback(self._gotRecipients, recipients, m)
    defered_object.addCallback(self.getFinishedMessage, builder_name,
                               build_status, step_name)
    return defered_object
