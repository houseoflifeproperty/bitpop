# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A class to mail the try bot results.
"""

try:
  # Create a block to work around evil sys.modules manipulation in
  # email/__init__.py that triggers pylint false positives.
  # pylint: disable=E0611,F0401
  from email.MIMEMultipart import MIMEMultipart
  from email.MIMEText import MIMEText
  from email.Utils import formatdate
except ImportError:
  raise

from buildbot.status import mail
from buildbot.status.builder import SUCCESS, WARNINGS
from twisted.internet import defer
from twisted.python import log

from master import build_utils


class TryMailNotifier(mail.MailNotifier):
  def __init__(self, reply_to=None, failure_message=None,
               footer=None, no_email_on_success=None, **kwargs):
    mail.MailNotifier.__init__(self, **kwargs)
    self.reply_to = reply_to
    self.failure_message = failure_message
    self.footer = footer
    # List of builders to NOT send email about if build was successful
    self.no_email_on_success = no_email_on_success or []

  def buildMessage_internal(self, name, build, results):
    """Send an email about the result. Send it as a nice HTML message."""

    if results == SUCCESS and name in self.no_email_on_success:
      log.msg('Skipping success email for %s' % name)
      return

    log.msg('Building try job email')
    projectName = self.master_status.getTitle()

    if len(build) != 1:
      # TODO(maruel): Panic or process them all.
      return

    build = build[0]
    job_stamp = build.getSourceStamp()
    build_url = self.master_status.getURLForThing(build)
    builder_url = self.master_status.getURLForThing(build.getBuilder())
    waterfall_url = self.master_status.getBuildbotURL()
    if results == SUCCESS:
      status_text_html = "You are awesome! Try succeeded!"
      res = "success"
    elif results == WARNINGS:
      status_text_html = "Try Had Warnings"
      res = "warnings"
    else:
      status_text_html = self.failure_message
      if status_text_html is None:
        status_text_html = (
            'TRY FAILED<p>'
            '<strong>If the failure is unrelated to your change, the test may'
            ' be flaky. Contact the sheriffs via irc or gchat, or email the'
            ' team mailing list.<br> If you think the system is broken,'
            ' please reply to this email.</strong><br>'
            ' Common examples of system issues: sync or compile failures'
            ' on a specific machine, or failures that only affect trybots.<br>'
            'Please use "rich text" replies so the links aren\'t lost.'
            ' If you do not receive a reply, don\'t worry. The reply address'
            ' isn\'t a blackhole.<p>Thanks!')
      res = "failure"

    info = {
        'result': res,
        'projectName': projectName,
        'builder': name,
        'reason': build.getReason(),
        'revision': build.getProperties().getProperty('got_revision',
                                                      job_stamp.revision),
        'timestamp': getattr(job_stamp, "timestamp", "")
    }
    subject = self.subject % info
    first_line = (
        "try %(result)s for %(reason)s on %(builder)s @ r%(revision)s" % info)

    build_props = build.getProperties()
    if build_props.getProperty('requester') == 'commit-bot@chromium.org':
      # CQ handles notifying people about the ultimate success/failure of
      # tryjobs by posting to rietveld. It also generates a LOT of email
      # from the tryserver which is noisy.
      return

    parent_html = ''
    if build_props:
      parent_name = build_props.getProperty('parent_buildername')
      parent_buildnum = build_props.getProperty('parent_buildnumber')
      if parent_name and parent_buildnum:
        parent_builder_url = ('%s/builders/%s' %
                      (waterfall_url.rstrip('/'), parent_name))
        parent_build = parent_builder_url + '/builds/%s' % parent_buildnum
        parent_html = (
            '<br>Parent build: <a href="%(build_url)s">%(buildnum)s</a>'
            ' on <a href="%(builder_url)s">%(builder)s</a><br>'
                       % {'builder_url': parent_builder_url,
                          'builder': parent_name,
                          'build_url': parent_build,
                          'buildnum': parent_buildnum})
    slave = build.getSlavename()
    slave_url = '%s/buildslaves/%s' % (waterfall_url.rstrip('/'), slave)

    html_params = {
        'subject': subject,
        'first_line': first_line,
        'waterfall_url': waterfall_url,
        'status_text_html': status_text_html,
        'build_url': build_url,
        'parent_builder_html': parent_html,
        'slave': slave,
        'slave_url': slave_url,
        'build_number': build.getNumber(),
        'builder': build.getBuilder().getName(),
        'builder_url': builder_url,
    }

    # Generate a HTML table looking like the waterfall.
    # WARNING: Gmail ignores embedded CSS style unless it's inline.
    html_content = (
"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>%(subject)s</title>
</head>
<body style="font-family: Verdana, Cursor; font-size: 10px;">
  %(first_line)s<p>
  <a href="%(waterfall_url)s">%(waterfall_url)s</a><p>
  %(status_text_html)s<p> %(parent_builder_html)s
  Build: <a href="%(build_url)s">%(build_number)s</a> on
         <a href="%(builder_url)s">%(builder)s</a><br>
  slave: <a href="%(slave_url)s">%(slave)s</a><br>
    """) % html_params

    html_content += self.SpecialPropertiesAsHTML(build_props.asDict())
    html_content += build_utils.EmailableBuildTable(build, waterfall_url)
    footer = self.footer
    if self.footer is None:
      footer = """<br>
FAQ: <a href="https://sites.google.com/a/chromium.org/dev/developers/testing/try-server-usage">
https://sites.google.com/a/chromium.org/dev/developers/testing/try-server-usage</a><br>
</body>
</html>
"""
    html_content += footer
    m = MIMEMultipart()
    m.attach(MIMEText(html_content, 'html', 'iso-8859-1'))
    m['Date'] = formatdate(localtime=True)
    m['Subject'] = subject
    m['From'] = self.fromaddr
    return m

  def buildMessage(self, name, build, results):
    m = self.buildMessage_internal(name, build, results)
    if m is None:
      return
    if self.reply_to:
      m['Reply-To'] = self.reply_to
    # now, who is this message going to?
    dl = []
    recipients = self.extraRecipients[:]
    if self.sendToInterestedUsers and self.lookup:
      for u in build[0].getInterestedUsers():
        d = defer.maybeDeferred(self.lookup.getAddress, u)
        d.addCallback(recipients.append)
        dl.append(d)
    d = defer.DeferredList(dl)
    d.addCallback(self._gotRecipients, recipients, m)
    return d

  @staticmethod
  def SpecialPropertiesAsHTML(props):
    """Props is a Properties-style dictionary in the form of:
      {'name': (value, 'source')}
    """
    ret = ''

    rev = props.get('got_revision')
    if rev:
      rev = rev[0]
      link = 'https://src.chromium.org/viewvc/chrome?view=rev&revision=%s' % rev
      ret += 'base revision: <a href="%s">%s</a><br>' % (link, rev)

    aux_propnames = ('issue', 'rietveld', 'patchset')
    aux_props = dict(
        (k, v[0]) for k, v in props.iteritems() if k in aux_propnames)

    if len(aux_props) == len(aux_propnames):
      aux_props['issue_link'] = '%(rietveld)s/%(issue)s' % aux_props
      aux_props['patch_link'] = (
          '%(rietveld)s/download/issue%(issue)s_%(patchset)s.diff' % aux_props)

      ret = 'issue: <a href="%(issue_link)s#ps%(patchset)s">%(issue)s</a><br>'
      ret += 'raw patchset: <a href="%(patch_link)s">%(patchset)s</a><br>'
      ret = ret % aux_props

    return ret
