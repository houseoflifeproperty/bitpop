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

  def buildMessage(self, name, build, results):
    """Send an email about the result. Send it as a nice HTML message."""

    if results == SUCCESS and name in self.no_email_on_success:
      log.msg('Skipping success email for %s' % name)
      return

    log.msg('Building try job email')
    projectName = self.master_status.getTitle()

    if len(build) != 1:
      # TODO(maruel): Panic or process them all.
      pass
    build = build[0]
    job_stamp = build.getSourceStamp()
    build_url = self.master_status.getURLForThing(build)
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
            '<strong>If you think the try slave is broken (it happens!),'
            'please REPLY to this email, don\'t ask on irc, mailing '
            'list or IM.<br>'
            'If you think the test is flaky, notify the sheriffs.</strong><br>'
            'Please use "rich text" replies so the links aren\'t lost.<br>'
            'It is possible that you get no reply, don\'t worry, the reply '
            'address isn\'t a blackhole.'
            '<p>'
            'Thanks!')

      res = "failure"

    info = {
        'result': res,
        'projectName': projectName,
        'builder': name,
        'reason': build.getReason(),
        'revision': job_stamp.revision,
        'timestamp': getattr(job_stamp, "timestamp", "")
    }
    subject = self.subject % info
    first_line = (
        "try %(result)s for %(reason)s on %(builder)s @ r%(revision)s" % info)

    build_props = build.getProperties()
    parent_html = ''
    if build_props:
      parent_name = build_props.getProperty('parent_buildername')
      parent_buildnum = build_props.getProperty('parent_buildnumber')
      if parent_name and parent_buildnum:
        parent_url = ('%s/builders/%s/builds/%s' %
                      (waterfall_url.rstrip('/'), parent_name, parent_buildnum))
        parent_html = ('<br>Parent builder: <a href="%(url)s">%(url)s</a><br>'
                       % {'url': parent_url})

    html_params = {
        'subject': subject,
        'first_line': first_line,
        'waterfall_url': waterfall_url,
        'status_text_html': status_text_html,
        'build_url': build_url,
        'parent_builder_html': parent_html,
        'slave': build.getSlavename(),
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
  <a href="%(build_url)s">%(build_url)s</a><br>
  slave: %(slave)s<br>
    """) % html_params

    html_content += build_utils.EmailableBuildTable(build, waterfall_url)
    footer = self.footer
    if self.footer is None:
      footer = """<br>
FAQ: <a href="http://sites.google.com/a/chromium.org/dev/developers/testing/try-server-usage">
http://sites.google.com/a/chromium.org/dev/developers/testing/try-server-usage</a><br>
</body>
</html>
"""
    html_content += footer
    m = MIMEMultipart()
    m.attach(MIMEText(html_content, 'html', 'iso-8859-1'))
    m['Date'] = formatdate(localtime=True)
    m['Subject'] = subject
    m['From'] = self.fromaddr
    if self.reply_to:
      m['Reply-To'] = self.reply_to
    # now, who is this message going to?
    dl = []
    recipients = self.extraRecipients[:]
    if self.sendToInterestedUsers and self.lookup:
      for u in build.getInterestedUsers():
        d = defer.maybeDeferred(self.lookup.getAddress, u)
        d.addCallback(recipients.append)
        dl.append(d)
    d = defer.DeferredList(dl)
    d.addCallback(self._gotRecipients, recipients, m)
    return d
