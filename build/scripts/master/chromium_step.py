# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Subclasses of various slave command classes."""

import copy
import errno
import json
import logging
import os
import time

from twisted.internet import defer
from twisted.python import log

from buildbot import interfaces, util
from buildbot.process import buildstep
from buildbot.process.properties import WithProperties
from buildbot.status import builder
from buildbot.steps import shell
from buildbot.steps import source

from common import annotator
from common import chromium_utils
import config


def change_to_revision(c):
  """Handle revision == None or any invalid value."""
  try:
    return int(str(c.revision).split('@')[-1])
  except (ValueError, TypeError):
    return 0


def updateText(section):
  # Reflect step status in text2.
  if section['status'] == builder.EXCEPTION:
    result = ['exception', section['name']]
  elif section['status'] == builder.FAILURE:
    result = ['failed', section['name']]
  else:
    result = []

  section['step'].setText([section['name']] + section['step_text'])
  section['step'].setText2(result + section['step_summary_text'])


# derived from addCompleteLog in process/buildstep.py
def addLogToStep(step, name, text):
  """Add a complete log to a step."""
  loog = step.addLog(name)
  size = loog.chunkSize
  for start in range(0, len(text), size):
    loog.addStdout(text[start:start+size])
  loog.finish()


class GClient(source.Source):
  """Check out a source tree using gclient."""

  name = 'update'

  def __init__(self, svnurl=None, rm_timeout=None, gclient_spec=None, env=None,
               sudo_for_remove=False, gclient_deps=None, gclient_nohooks=False,
               no_gclient_branch=False, no_gclient_revision=False,
               gclient_transitive=False, primary_repo=None,
               gclient_jobs=None, blink_config=None, **kwargs):
    # TODO: We shouldn't need to hard-code blink-specific info here. We
    # should figure out how to generalize this to sub-repos somehow.
    source.Source.__init__(self, **kwargs)
    if env:
      self.args['env'] = env.copy()
    self.args['rm_timeout'] = rm_timeout
    self.args['svnurl'] = svnurl
    self.args['sudo_for_remove'] = sudo_for_remove
    # linux doesn't handle spaces in command line args properly so remove them.
    # This doesn't matter for the format of the DEPS file.
    self.args['gclient_spec'] = gclient_spec.replace(' ', '')
    self.args['gclient_deps'] = gclient_deps
    self.args['gclient_nohooks'] = gclient_nohooks
    self.args['no_gclient_branch'] = no_gclient_branch
    self.args['no_gclient_revision'] = no_gclient_revision
    self.args['gclient_transitive'] = gclient_transitive
    self.args['primary_repo'] = primary_repo or ''
    self.args['gclient_jobs'] = gclient_jobs
    self.args['blink_config'] = blink_config

  def computeSourceRevision(self, changes):
    """Finds the latest revision number from the changeset that have
    triggered the build.

    This is a hook method provided by the parent source.Source class and
    default implementation in source.Source returns None. Return value of this
    method is be used to set 'revsion' argument value for startVC() method."""
    if not changes:
      return None
    # Change revision numbers can be invalid, for a try job for instance.
    # TODO(maruel): Make this work for git hash.
    lastChange = max([change_to_revision(c) for c in changes])
    return lastChange

  def startVC(self, branch, revision, patch):
    warnings = []
    args = copy.copy(self.args)

    if args.get('gclient_spec'):
      self.adjustGclientSpecForBlink(branch, revision, args)
      self.adjustGclientSpecForNaCl(branch, revision, patch, args)
      self.adjustGclientSpecForV8(branch, revision, patch, args)
      self.adjustGclientSpecForWebRTC(branch, revision, patch, args)

    try:
      # parent_cr_revision might be set, but empty.
      if self.getProperty('parent_cr_revision'):
        revision = 'src@' + self.getProperty('parent_cr_revision')
    except KeyError:
      pass
    self.setProperty('primary_repo', args['primary_repo'], 'Source')
    args['revision'] = revision
    args['branch'] = branch

    if patch:
      args['patch'] = patch
    elif args.get('patch') is None:
      del args['patch']

    args['project'] = self.build.getSourceStamp().project
    cmd = buildstep.LoggedRemoteCommand('gclient', args)
    self.startCommand(cmd, warnings)

  def adjustGclientSpecForBlink(self, branch, revision, args):
    # If the bot in question is a dedicated bot for Blink changes (either
    # on a waterfall, or a blink-specific trybot), we want to set a custom
    # version of Blink, otherwise we leave the gclient spec alone.
    if args['blink_config'] != 'blink':
      return

    # branch == 'trunk' means the change came from the blink poller, and the
    # revision is a blink revision; otherwise, we use '', or HEAD.
    wk_revision = ''
    if branch == 'trunk':
      wk_revision = revision

    try:
      # parent_wk_revision might be set, but empty.
      if self.getProperty('parent_wk_revision'):
        wk_revision = self.getProperty('parent_wk_revision')
    except KeyError:
      pass

    # TODO: Make this be something less fragile.
    args['gclient_spec'] = args['gclient_spec'].replace(
        '"webkit_trunk"',
        '"webkit_revision":"%s","webkit_trunk"' % wk_revision)

  def adjustGclientSpecForNaCl(self, branch, revision, patch, args):
    nacl_revision = revision
    try:
      # parent_nacl_revision might be set, but empty.
      if self.getProperty('parent_got_nacl_revision'):
        nacl_revision = self.getProperty('parent_got_nacl_revision')
    except KeyError:
      pass
    args['gclient_spec'] = args['gclient_spec'].replace(
        '$$NACL_REV$$', str(nacl_revision or ''))

  def adjustGclientSpecForV8(self, branch, revision, patch, args):
    v8_revision = revision
    try:
      # parent_v8_revision might be set, but empty.
      if self.getProperty('parent_got_v8_revision'):
        v8_revision = self.getProperty('parent_got_v8_revision')
    except KeyError:
      pass
    args['gclient_spec'] = args['gclient_spec'].replace(
        '$$V8_REV$$', str(v8_revision or ''))

  def adjustGclientSpecForWebRTC(self, branch, revision, patch, args):
    webrtc_revision = revision
    try:
      # parent_webrtc_revision might be set, but empty.
      if self.getProperty('parent_got_webrtc_revision'):
        webrtc_revision = self.getProperty('parent_got_webrtc_revision')
    except KeyError:
      pass
    args['gclient_spec'] = args['gclient_spec'].replace(
        '$$WEBRTC_REV$$', str(webrtc_revision or ''))

  def describe(self, done=False):
    """Tries to append the revision number to the description."""
    description = source.Source.describe(self, done)
    self.appendChromeRevision(description)
    self.appendWebKitRevision(description)
    self.appendNaClRevision(description)
    self.appendV8Revision(description)
    self.appendWebRTCRevision(description)
    return description

  def appendChromeRevision(self, description):
    """Tries to append the Chromium revision to the given description."""
    revision = None
    try:
      revision = self.getProperty('got_revision')
    except KeyError:
      # 'got_revision' doesn't exist yet, check 'revision'
      try:
        revision = self.getProperty('revision')
      except KeyError:
        pass  # neither exist, go on without revision
    if revision:
      # TODO: Right now, 'no_gclient_branch' is a euphemism for 'git', but we
      # probably ought to be explicit about this switch.
      if not self.args['no_gclient_branch']:
        revision = 'r%s' % revision
      # Only append revision if it's not already there.
      if not revision in description:
        description.append(revision)

  def appendWebKitRevision(self, description):
    """Tries to append the WebKit revision to the given description."""
    webkit_revision = None
    try:
      webkit_revision = self.getProperty('got_webkit_revision')
    except KeyError:
      pass
    if webkit_revision:
      webkit_revision = 'webkit r%s' % webkit_revision
      # Only append revision if it's not already there.
      if not webkit_revision in description:
        description.append(webkit_revision)

  def appendNaClRevision(self, description):
    """Tries to append the NaCl revision to the given description."""
    nacl_revision = None
    try:
      nacl_revision = self.getProperty('got_nacl_revision')
    except KeyError:
      pass
    if nacl_revision:
      nacl_revision = 'nacl r%s' % nacl_revision
      # Only append revision if it's not already there.
      if not nacl_revision in description:
        description.append(nacl_revision)

  def appendV8Revision(self, description):
    """Tries to append the V8 revision to the given description."""
    v8_revision = None
    try:
      v8_revision = self.getProperty('got_v8_revision')
    except KeyError:
      pass
    if v8_revision:
      v8_revision = 'v8 r%s' % v8_revision
      # Only append revision if it's not already there.
      if not v8_revision in description:
        description.append(v8_revision)

  def appendWebRTCRevision(self, description):
    """Tries to append the WebRTC revision to the given description."""
    webrtc_revision = None
    try:
      webrtc_revision = self.getProperty('got_webrtc_revision')
    except KeyError:
      pass
    if webrtc_revision:
      webrtc_revision = 'webrtc r%s' % webrtc_revision
      # Only append revision if it's not already there.
      if not webrtc_revision in description:
        description.append(webrtc_revision)

  def commandComplete(self, cmd):
    """Handles status updates from buildbot slave when the step is done.

    Update the relevant got_XX_revision build properties if available.
    """
    source.Source.commandComplete(self, cmd)
    primary_repo = self.args.get('primary_repo', '')
    primary_revision_key = 'got_' + primary_repo + 'revision'
    properties = (
      ('got_revision', primary_revision_key),
      ('got_nacl_revision', 'got_nacl_revision'),
      ('got_swarming_client_revision', 'got_swarming_client_revision'),
      ('got_v8_revision', 'got_v8_revision'),
      ('got_webkit_revision', 'got_webkit_revision'),
      ('got_webrtc_revision', 'got_webrtc_revision'),
    )
    for prop_name, cmd_arg in properties:
      if cmd_arg in cmd.updates:
        got_revision = cmd.updates[cmd_arg][-1]
        if got_revision:
          self.setProperty(prop_name, str(got_revision), 'Source')


class BuilderStatus(object):
  # Order in asceding severity.
  BUILD_STATUS_ORDERING = [
      builder.SUCCESS,
      builder.WARNINGS,
      builder.FAILURE,
      builder.EXCEPTION,
  ]

  @classmethod
  def combine(cls, a, b):
    """Combine two status, favoring the more severe."""
    if a not in cls.BUILD_STATUS_ORDERING:
      return b
    if b not in cls.BUILD_STATUS_ORDERING:
      return a
    a_rank = cls.BUILD_STATUS_ORDERING.index(a)
    b_rank = cls.BUILD_STATUS_ORDERING.index(b)
    pick = max(a_rank, b_rank)
    return cls.BUILD_STATUS_ORDERING[pick]


class ProcessLogShellStep(shell.ShellCommand):
  """Step that can process log files.

    Delegates actual processing to log_processor, which is a subclass of
    process_log.PerformanceLogParser.

    Sample usage:
    # construct class that will have no-arg constructor.
    log_processor_class = chromium_utils.PartiallyInitialize(
        process_log.GraphingPageCyclerLogProcessor,
        report_link='http://host:8010/report.html,
        output_dir='~/www')
    # We are partially constructing Step because the step final
    # initialization is done by BuildBot.
    step = chromium_utils.PartiallyInitialize(
        chromium_step.ProcessLogShellStep,
        log_processor_class)

  """

  def  __init__(self, log_processor_class=None, *args, **kwargs):
    """
    Args:
      log_processor_class: subclass of
        process_log.PerformanceLogProcessor that will be initialized and
        invoked once command was successfully completed.
    """
    self._result_text = []
    self._log_processor = None
    # If log_processor_class is not None, it should be a class.  Create an
    # instance of it.
    if log_processor_class:
      self._log_processor = log_processor_class()
    shell.ShellCommand.__init__(self, *args, **kwargs)

  def start(self):
    """Overridden shell.ShellCommand.start method.

    Adds a link for the activity that points to report ULR.
    """
    self._CreateReportLinkIfNeccessary()
    shell.ShellCommand.start(self)

  def _GetRevision(self):
    """Returns the revision number for the build.

    Result is the revision number of the latest change that went in
    while doing gclient sync. Tries 'got_revision' (from log parsing)
    then tries 'revision' (usually from forced build). If neither are
    found, will return -1 instead.
    """
    try:
      repo = self.build.getProperty('primary_repository')
      if not repo:
        repo = ''
    except KeyError:
      repo = ''
    revision = None
    try:
      revision = self.build.getProperty('got_' + repo + 'revision')
    except KeyError:
      pass  # 'got_revision' doesn't exist (yet)
    if not revision:
      try:
        revision = self.build.getProperty('revision')
      except KeyError:
        pass  # neither exist
    if not revision:
      revision = -1
    return revision

  def _GetWebkitRevision(self):
    """Returns the webkit revision number for the build.
    """
    try:
      return self.build.getProperty('got_webkit_revision')
    except KeyError:
      return None

  def _GetBuildProperty(self):
    """Returns a dict with the channel and version."""
    build_properties = {}
    try:
      channel = self.build.getProperty('channel')
      if channel:
        build_properties.setdefault('channel', channel)
    except KeyError:
      pass  # 'channel' doesn't exist.
    try:
      version = self.build.getProperty('version')
      if version:
        build_properties.setdefault('version', version)
    except KeyError:
      pass  # 'version' doesn't exist.
    return build_properties

  def commandComplete(self, cmd):
    """Callback implementation that will use log process to parse 'stdio' data.
    """
    if self._log_processor:
      self._result_text = self._log_processor.Process(
          self._GetRevision(), self.getLog('stdio').getText(),
          self._GetBuildProperty(), webkit_revision=self._GetWebkitRevision())

  def getText(self, cmd, results):
    text_list = self.describe(True)
    if self._result_text:
      self._result_text.insert(0, '<div class="BuildResultInfo">')
      self._result_text.append('</div>')
      text_list += self._result_text
    return text_list

  def evaluateCommand(self, cmd):
    shell_result = shell.ShellCommand.evaluateCommand(self, cmd)
    log_result = None
    if self._log_processor and 'evaluateCommand' in dir(self._log_processor):
      log_result = self._log_processor.evaluateCommand(cmd)
    return BuilderStatus.combine(shell_result, log_result)

  def _CreateReportLinkIfNeccessary(self):
    if self._log_processor and self._log_processor.ReportLink():
      self.addURL('results', '%s' % self._log_processor.ReportLink())


def Prepend(filename, data, output_dir, perf_output_dir):
  READABLE_FILE_PERMISSIONS = int('644', 8)

  fullfn = chromium_utils.AbsoluteCanonicalPath(output_dir, filename)
  dir_path = os.path.dirname(fullfn)
  MakeOutputDirectory(dir_path)

  # This whitelists writing to files only directly under output_dir
  # or perf_expectations_dir for security reasons.
  if not (dir_path.startswith(output_dir) or
          dir_path.startswith(perf_output_dir)):
    raise Exception('Attempted to write to log file outside of \'%s\' or '
                    '\'%s\': \'%s\'' % (output_dir,
                                        perf_output_dir,
                                        os.path.join(output_dir,
                                                     filename)))

  chromium_utils.Prepend(fullfn, data)
  os.chmod(fullfn, READABLE_FILE_PERMISSIONS)


def MakeOutputDirectory(output_dir):
  if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir)


class AnnotationObserver(buildstep.LogLineObserver):
  """This class knows how to understand annotations.

  Here are a list of the currently supported annotations:

  @@@BUILD_STEP <stepname>@@@
  Add a new step <stepname> after the last step. End the step at the cursor,
  marking with last available status. Advance the step cursor to the added step.

  @@@SEED_STEP <stepname>@@@
  Add a new step <stepname> after the last step. Do not end the step at the
  cursor, don't advance the cursor to the seeded step.

  @@@STEP_CURSOR <stepname>@@@
  Set the cursor to the named step. All further commands apply to the current
  cursor.

  @@@STEP_LINK@<label>@<url>@@@
  Add a link with label <label> linking to <url> to the current stage.

  @@@STEP_STARTED@@@
  Start the step at the cursor location.

  @@@STEP_WARNINGS@@@
  Mark the current step as having warnings (orange).

  @@@STEP_FAILURE@@@
  Mark the current step as having failed (red).

  @@@STEP_EXCEPTION@@@
  Mark the current step as having exceptions (magenta).

  @@@STEP_CLOSED@@@
  Close the current step, finalizing its log and moving the cursor to the
  preamble. The step will be marked SUCCESS unless a status message marked it
  otherwise.

  @@@STEP_LOG_LINE@<label>@<line>@@@
  Add a log line to a log named <label>. Multiple lines can be added.

  @@@STEP_LOG_END@<label>@@@
  Finalizes a log added by STEP_LOG_LINE and calls addCompleteLog().

  @@@STEP_LOG_END_PERF@<label>@@@
  Same as STEP_LOG_END, but signifies that this is a perf log and should be
  saved to the master.

  @@@STEP_CLEAR@@@
  Reset the text description of the current step.

  @@@STEP_SUMMARY_CLEAR@@@
  Reset the text summary of the current step.

  @@@STEP_TEXT@<msg>@@@
  Append <msg> to the current step text.

  @@@SEED_STEP_TEXT@step@<msg>@@@
  Append <msg> to the specified seeded step.

  @@@STEP_SUMMARY_TEXT@<msg>@@@
  Append <msg> to the step summary (appears on top of the waterfall).

  @@@HALT_ON_FAILURE@@@
  Halt if exception or failure steps are encountered (default is not).

  @@@HONOR_ZERO_RETURN_CODE@@@
  Honor the return code being zero (success), even if steps have other results.

  @@@STEP_TRIGGER@<spec>@@@
  Trigger build(s), where <spec> is a JSON-encoded dict with keys:
    builderNames - A list of builder names that should be triggered.
    properties - A dictionary of properties to override the default ones.

  Deprecated annotations:
  TODO(bradnelson): drop these when all users have been tracked down.

  @@@BUILD_WARNINGS@@@
  Equivalent to @@@STEP_WARNINGS@@@

  @@@BUILD_FAILED@@@
  Equivalent to @@@STEP_FAILURE@@@

  @@@BUILD_EXCEPTION@@@
  Equivalent to @@@STEP_EXCEPTION@@@

  @@@link@<label>@<url>@@@
  Equivalent to @@@STEP_LINK@<label>@<url>@@@
  """

  # Base URL for performance test results.
  PERF_BASE_URL = config.Master.perf_base_url
  PERF_REPORT_URL_SUFFIX = config.Master.perf_report_url_suffix

  # Directory in which to save perf output data files.
  PERF_OUTPUT_DIR = config.Master.perf_output_dir

  # For the GraphingLogProcessor, the file into which it will save a list
  # of graph names for use by the JS doing the plotting.
  GRAPH_LIST = config.Master.perf_graph_list

  # --------------------------------------------------------------------------
  # PERF TEST SETTINGS
  # In each mapping below, the first key is the target and the second is the
  # perf_id. The value is the directory name in the results URL.

  # Configuration of most tests.
  PERF_TEST_MAPPINGS = {
    'Release': {
      'chrome-linux32-beta': 'linux32-beta',
      'chrome-linux32-stable': 'linux32-stable',
      'chrome-linux64-beta': 'linux64-beta',
      'chrome-linux64-stable': 'linux64-stable',
      'chrome-mac-beta': 'mac-beta',
      'chrome-mac-stable': 'mac-stable',
      'chrome-win-beta': 'win-beta',
      'chrome-win-stable': 'win-stable',
      'chromium-linux-targets': 'linux-targets',
      'chromium-mac-targets': 'mac-targets',
      'chromium-rel-linux': 'linux-release',
      'chromium-rel-linux-64': 'linux-release-64',
      'chromium-rel-linux-hardy': 'linux-release-hardy',
      'chromium-rel-linux-hardy-lowmem': 'linux-release-lowmem',
      'chromium-rel-linux-webkit': 'linux-release-webkit-latest',
      'chromium-rel-mac': 'mac-release',
      'chromium-rel-mac5': 'mac-release-10.5',
      'chromium-rel-mac6': 'mac-release-10.6',
      'chromium-rel-mac5-v8': 'mac-release-10.5-v8-latest',
      'chromium-rel-mac6-v8': 'mac-release-10.6-v8-latest',
      'chromium-rel-mac6-webkit': 'mac-release-10.6-webkit-latest',
      'chromium-rel-old-mac6': 'mac-release-old-10.6',
      'chromium-rel-vista-dual': 'vista-release-dual-core',
      'chromium-rel-vista-dual-v8': 'vista-release-v8-latest',
      'chromium-rel-vista-single': 'vista-release-single-core',
      'chromium-rel-vista-webkit': 'vista-release-webkit-latest',
      'chromium-rel-xp': 'xp-release',
      'chromium-rel-xp-dual': 'xp-release-dual-core',
      'chromium-rel-xp-single': 'xp-release-single-core',
      'chromium-win-targets': 'win-targets',
      'nacl-lucid64-spec-x86': 'nacl-lucid64-spec-x86',
      'nacl-lucid64-spec-arm': 'nacl-lucid64-spec-arm',
      'nacl-lucid64-spec-trans': 'nacl-lucid64-spec-trans',
    },
    'Debug': {
      'chromium-dbg-linux': 'linux-debug',
      'chromium-dbg-win': 'win-debug',
      'chromium-dbg-mac': 'mac-debug',
      'chromium-dbg-xp': 'xp-debug',
      'chromium-dbg-linux-try': 'linux-try-debug',
    },
  }
  def __init__(self, command=None, show_perf=False, perf_id=None,
               perf_report_url_suffix=None, target=None, *args, **kwargs):
    buildstep.LogLineObserver.__init__(self, *args, **kwargs)
    self.command = command
    self.sections = []
    self.annotate_status = builder.SUCCESS
    self.halt_on_failure = False
    self.honor_zero_return_code = False
    self.cursor = None

    self.show_perf = show_perf
    self.perf_id = perf_id
    self.perf_report_url_suffix = perf_report_url_suffix
    self.target = target

  def initialSection(self):
    """Initializes the annotator's sections.

    Annotator uses a list of dictionaries which hold information stuch as status
    and logs for each added step. This method populates the section list with an
    entry referencing the original buildbot step."""
    if self.sections:
      return
    # Add a log section for output before the first section heading.
    preamble = self.command.addLog('preamble')

    self.addSection(self.command.name, self.command.step_status)
    self.sections[0]['log'] = preamble
    self.sections[0]['started'] = util.now()
    self.cursor = self.sections[0]

  def sectionIsPreamble(self, section):
    return section is self.sections[0]

  def cursorIsPreamble(self):
    return self.sectionIsPreamble(self.cursor)

  def ensureCursorIsNotPreamble(self):
    if self.cursorIsPreamble():
      raise ValueError('This operation is not supported when the cursor is '
                       'set to preamble.')

  def describe(self):
    """Used for the 'original' step, when updated by buildbot's getText().

    This is needed to ensure any STEP_TEXT annotations don't get overwritten
    when the step is finished and buildbot calls a final getText()."""
    self.initialSection()

    return self.sections[0]['step_text']

  def cleanupSteps(self, exclude_async_pending=False):
    """Prepares steps for build finalization.

    Closes open started steps and marks any unfinished steps as failure (except
    for parent step).

    Args:
      exclude_async_pending - if True, do not finish steps that have async ops.
    """
    self.closeSections()
    for section in self.sections[1:]:
      if (section['step'].isStarted() and not section['step'].isFinished() and
          not (exclude_async_pending and section['async_ops'])):
        reason = 'step was unfinished at finalization.'
        self.finishStep(section, status=builder.FAILURE, reason=reason)

  def ensureStepIsStarted(self, section):
    if not section['step'].isStarted():
      self.startStep(section)

  def addAsyncOpToCursor(self, deferred, description):
    section = self.cursor
    if section['closed']:
      raise Exception('Can\'t add an async operation to a closed step')
    section['async_ops'].append({
        'deferred': deferred,
        'description': description,
    })

  def finishStep(self, section, status=None, reason=None):
    """Mark the specified step as 'finished.'"""

    # The initial section will be closed by self.finished when runCommand
    # completes, so finishStep should not close it.
    assert not self.sectionIsPreamble(section), ('The initial section cannot '
                                                 'be finalized at annotator '
                                                 'level.')

    status_map = {
        builder.SUCCESS: 'SUCCESS',
        builder.WARNINGS: 'WARNINGS',
        builder.FAILURE: 'FAILURE',
        builder.EXCEPTION: 'EXCEPTION',
        builder.RETRY: 'RETRY',
        builder.SKIPPED: 'SKIPPED',
    }

    # Update status if set as an argument.
    if status is not None:
      section['status'] = status
    else:
      # Wasn't set as an argument, so we know it came from annotations.
      if not reason:
        if section['status'] == builder.SUCCESS:
          reason = 'step finished normally.'
        else:
          reason = 'parsed annotations marked step as %s.' % status_map[
              section['status']]

    self.ensureStepIsStarted(section)
    # Final update of text.
    updateText(section)
    # Add timing info.
    section['ended'] = section.get('ended', util.now())
    started = section['started']
    ended = section['ended']

    msg = '\n\n' + '-' * 80 + '\n'
    msg += '\n'.join([
        'started: %s' % time.ctime(started),
        'ended: %s' % time.ctime(ended),
        'duration: %s' % util.formatInterval(ended - started),
        'status: %s' % status_map[section['status']],
        'status reason: %s' % reason,
        '',  # So we get a final \n
    ])
    section['log'].addHeader(msg)
    # Change status (unless handling the preamble).
    if len(self.sections) != 1:
      section['step'].stepFinished(section['status'])
    # Finish log.
    section['log'].finish()

  def finishCursor(self, status=None, reason=None):
    """Mark the step at the current cursor as finished."""
    # Potentially start initial section here, as initial section might have
    # no output at all.
    self.initialSection()

    self.finishStep(self.cursor, status=status, reason=reason)

  def closeSection(self, section):
    """Closes the step and finalizes when async_ops complete."""
    assert not section['closed'], 'Can\'t close a closed step'
    # The initial section will be closed by self.finished when runCommand
    # completes.
    assert not self.sectionIsPreamble(section), ('The initial section cannot '
                                                 'be closed')
    section['closed'] = True
    if section['step'].isFinished():
      return

    # Everything was fine on the slave side,
    # so the final result depends on async operations.
    async_ops = section['async_ops']
    if async_ops:
      op_list = '\n'.join('* %s' % o['description']
                          for o in async_ops)
      msg = 'Will wait till async operations complete:\n%s' % (op_list,)
      section['log'].addStdout(msg)

    d = defer.DeferredList([o['deferred'] for o in async_ops])
    def finish(results):
      try:
        reasons = []
        status = section['status']
        for succeeded, defer_result in results:
          if succeeded:
            # callback was called.
            op_result, reason = defer_result
          else:
            # errback was called
            op_result = builder.FAILURE
            reason = defer_result
          status = BuilderStatus.combine(status, op_result)
          if reason is not None:
            reasons.append(reason)

        if not section['step'].isFinished():
          reason = '\n'.join(map(str, reasons))
          self.finishStep(section, status=status, reason=reason)
          self.annotate_status = BuilderStatus.combine(self.annotate_status,
                                                       status)
      except Exception as ex:
        self.finishStep(section, status=builder.EXCEPTION, reason=ex)

    d.addCallback(finish)

  def closeCursor(self):
    self.closeSection(self.cursor)

  def closeSections(self):
    """Closes open started sections."""
    for section in self.sections[1:]:
      if section['step'].isStarted() and not section['closed']:
        self.closeSection(section)

  def errLineReceived(self, line):
    self.handleOutputLine(line)

  def outLineReceived(self, line):
    self.handleOutputLine(line)

  # Override logChunk to intercept headers and to prevent more than one line's
  # worth of data from being processed in a chunk, so we can direct incomplete
  # chunks to the right sub-log (so we get output promptly and completely).
  def logChunk(self, build, step, logmsg, channel, text):
    for line in text.splitlines(True):
      if channel == interfaces.LOG_CHANNEL_STDOUT:
        self.outReceived(line)
      elif channel == interfaces.LOG_CHANNEL_STDERR:
        self.errReceived(line)
      elif channel == interfaces.LOG_CHANNEL_HEADER:
        self.headerReceived(line)

  def outReceived(self, data):
    buildstep.LogLineObserver.outReceived(self, data)
    if self.sections:
      self.ensureStepIsStarted(self.cursor)
      self.cursor['log'].addStdout(data)

  def errReceived(self, data):
    buildstep.LogLineObserver.errReceived(self, data)
    if self.sections:
      self.ensureStepIsStarted(self.cursor)
      self.cursor['log'].addStderr(data)

  def headerReceived(self, data):
    if self.sections:
      preamble = self.sections[0]
      self.ensureStepIsStarted(preamble)
      if preamble['log'].finished:
        # Silently discard message when a log is marked as finished.
        # TODO(maruel): Fix race condition?
        log.msg(
            'Received data unexpectedly on a finished build step log: %r' %
            data)
      else:
        preamble['log'].addHeader(data)


  def updateStepStatus(self, status):
    """Update current step status and annotation status based on a new event."""
    self.annotate_status = BuilderStatus.combine(self.annotate_status, status)
    self.cursor['status'] = BuilderStatus.combine(self.cursor['status'], status)
    if self.halt_on_failure and self.cursor['status'] in [
        builder.FAILURE, builder.EXCEPTION]:
      if not self.sectionIsPreamble(self.cursor):
        self.finishCursor()
      self.cleanupSteps()
      self.command.finished(self.cursor['status'])

  def lookupCursor(self, step_name):
    """Given a step name, find the latest section with that name."""
    if self.sections:
      for section in self.sections[::-1]:  # loop backwards in case of dup steps
        if section['name'] == step_name:
          return section

    raise IndexError('step %s doesn\'t exist!' % step_name)

  def updateCursorText(self):
    """Update the text on the waterfall at the current cursor."""
    updateText(self.cursor)

  def startStep(self, section):
    """Marks a section as started."""
    step = section['step']
    if not step.isStarted():
      step.stepStarted()
      section['started'] = util.now()
      # parent step already has its logging set up by buildbot
      if section != self.sections[0]:
        stdio = step.addLog('stdio')
        section['log'] = stdio

  def addSection(self, step_name, step=None):
    """Adds a new section to annotator sections, does not change cursor."""
    if not step:
      step = self.command.step_status.getBuild().addStepWithName(step_name)
      step.setText([step_name])
    self.sections.append({
        'name': step_name,
        'step': step,
        'closed': False,
        'log': None,
        'annotated_logs': {},
        'status': builder.SUCCESS,
        'links': [],
        'step_summary_text': [],
        'step_text': [],
        'started': None,
        'async_ops': [],
    })

    return self.sections[-1]

  def _PerfStepMappings(self, show_results, perf_id, test_name, suffix=None):
    """Looks up test IDs in PERF_TEST_MAPPINGS and returns test info."""
    report_link = None
    output_dir = None
    perf_name = None

    if show_results:
      perf_name = perf_id
      if (self.target in self.PERF_TEST_MAPPINGS and
          perf_id in self.PERF_TEST_MAPPINGS[self.target]):
        perf_name = self.PERF_TEST_MAPPINGS[self.target][perf_id]
      if not suffix:
        suffix = self.PERF_REPORT_URL_SUFFIX
      report_link = '%s/%s/%s/%s' % (self.PERF_BASE_URL, perf_name, test_name,
                                     suffix)
      output_dir = '%s/%s/%s' % (self.PERF_OUTPUT_DIR, perf_name, test_name)

    return report_link, output_dir, perf_name

  def _SaveGraphInfo(self, newgraphdata, output_dir):
    EXECUTABLE_FILE_PERMISSIONS = int('755', 8)

    graph_filename = os.path.join(output_dir, self.GRAPH_LIST)
    try:
      graph_file = open(graph_filename)
    except IOError, e:
      if e.errno != errno.ENOENT:
        raise
      graph_file = None
    graph_list = []
    if graph_file:
      try:
        # We keep the original content of graphs.dat to avoid accidentally
        # removing graphs when a test encounters a failure.
        graph_list = json.load(graph_file)
      except ValueError:
        graph_file.seek(0)
        logging.error('Error parsing %s: \'%s\'' % (self.GRAPH_LIST,
                                                    graph_file.read().strip()))
      graph_file.close()

    # We need the graph names from graph_list so we can skip graphs that already
    # exist in graph_list.
    graph_names = [x['name'] for x in graph_list]

    newgraphs = {}
    try:
      newgraphs = json.loads(newgraphdata)
    except ValueError:
      logging.error('Error parsing incoming \'%s\'' % (self.GRAPH_LIST))

    # Group all of the new graphs into their own list, ...
    new_graph_list = []
    for graph_name, graph in newgraphs.iteritems():
      if graph_name in graph_names:
        continue
      new_graph_list.append(graph)
      new_graph_list[-1]['name'] = graph_name

    # sort them by not-'important', since True > False, and by graph_name, ...
    new_graph_list.sort(lambda x, y: cmp((not x['important'], x['name']),
                                         (not y['important'], y['name'])))

    # then add the new graph list to the main graph list.
    graph_list.extend(new_graph_list)

    # Write the resulting graph list.
    graph_file = open(graph_filename, 'w')
    json.dump(graph_list, graph_file)
    graph_file.close()
    os.chmod(graph_filename, EXECUTABLE_FILE_PERMISSIONS)

  def addLinkToCursor(self, link_label, link_url):
    self.cursor['links'].append((link_label, link_url))
    self.cursor['step'].addURL(link_label, link_url)

  def handleOutputLine(self, line):
    """This is called once with each line of the test log."""
    # Handle initial setup here, as step_status might not exist yet at init.
    self.initialSection()

    annotator.MatchAnnotation(line.rstrip(), self)

  def SET_BUILD_PROPERTY(self, name, value):
    # Support: @@@SET_BUILD_PROPERTY@<name>@<json>@@@
    # Sets the property and indicates that it came from an annoation on the
    # current step.
    self.command.build.setProperty(name, json.loads(value), 'Annotation(%s)'
                                   % self.cursor['name'])

  def STEP_LOG_LINE(self, log_label, log_line):
    # Support: @@@STEP_LOG_LINE@<label>@<line>@@@ (add log to step)
    # Appends a line to the log's array. When STEP_LOG_END is called,
    # that will finalize the log and call addCompleteLog().
    current_logs = self.cursor['annotated_logs']
    current_logs[log_label] = current_logs.get(log_label, []) + [log_line]

  def STEP_LOG_END(self, log_label):
    # Support: @@@STEP_LOG_END@<label>@@@ (finalizes log to step)
    current_logs = self.cursor['annotated_logs']
    log_text = '\n'.join(current_logs.get(log_label, []))
    addLogToStep(self.cursor['step'], log_label, log_text)

  def STEP_LOG_END_PERF(self, log_label, perf_dashboard_name):
    # Support: @@@STEP_LOG_END_PERF@<label>@<line>@@@
    # (finalizes log to step, marks it as being a perf step
    # requiring logs to be stored on the master)
    current_logs = self.cursor['annotated_logs']
    log_text = '\n'.join(current_logs.get(log_label, [])) + '\n'

    report_link = None
    output_dir = None
    if self.perf_id:
      report_link, output_dir, _ = self._PerfStepMappings(
          self.show_perf, self.perf_id, perf_dashboard_name,
          self.perf_report_url_suffix)

    PERF_EXPECTATIONS_PATH = ('../../scripts/master/log_parser/'
                              'perf_expectations/')
    perf_output_dir = None
    if output_dir:
      output_dir = chromium_utils.AbsoluteCanonicalPath(output_dir)
      perf_output_dir = chromium_utils.AbsoluteCanonicalPath(output_dir,
          PERF_EXPECTATIONS_PATH)

    if report_link and output_dir:
      MakeOutputDirectory(output_dir)
      if log_label == self.GRAPH_LIST:
        self._SaveGraphInfo(log_text, output_dir)
      else:
        Prepend(log_label, log_text, output_dir, perf_output_dir)

  def STEP_LINK(self, link_label, link_url):
    # Support: @@@STEP_LINK@<name>@<url>@@@ (emit link)
    # Also support depreceated @@@link@<name>@<url>@@@
    self.addLinkToCursor(link_label, link_url)

  def STEP_STARTED(self):
    # Support: @@@STEP_STARTED@@@ (start a step at cursor)
    self.ensureCursorIsNotPreamble()
    self.startStep(self.cursor)

  def STEP_CLOSED(self):
    # Support: @@@STEP_CLOSED@@@
    self.ensureCursorIsNotPreamble()
    self.closeCursor()
    self.cursor = self.sections[0]

  def STEP_WARNINGS(self):
    # Support: @@@STEP_WARNINGS@@@ (warn on a stage)
    # Also support deprecated @@@BUILD_WARNINGS@@@
    self.updateStepStatus(builder.WARNINGS)

  def STEP_FAILURE(self):
    # Support: @@@STEP_FAILURE@@@ (fail a stage)
    # Also support deprecated @@@BUILD_FAILED@@@
    if self.halt_on_failure:
      self.ensureCursorIsNotPreamble()
    self.updateStepStatus(builder.FAILURE)

  def STEP_EXCEPTION(self):
    # Support: @@@STEP_EXCEPTION@@@ (exception on a stage)
    # Also support deprecated @@@BUILD_FAILED@@@
    if self.halt_on_failure:
      self.ensureCursorIsNotPreamble()
    self.updateStepStatus(builder.EXCEPTION)

  def HALT_ON_FAILURE(self):
    # Support: @@@HALT_ON_FAILURE@@@ (halt if a step fails immediately)
    self.halt_on_failure = True

  def HONOR_ZERO_RETURN_CODE(self):
    # Support: @@@HONOR_ZERO_RETURN_CODE@@@ (succeed on 0 return, even if some
    #     steps have failed)
    self.honor_zero_return_code = True

  def STEP_CLEAR(self):
    # Support: @@@STEP_CLEAR@@@ (reset step description)
    self.cursor['step_text'] = []
    self.updateCursorText()

  def STEP_SUMMARY_CLEAR(self):
    # Support: @@@STEP_SUMMARY_CLEAR@@@ (reset step summary)
    self.cursor['step_summary_text'] = []
    self.updateCursorText()

  def STEP_TEXT(self, msg):
    # Support: @@@STEP_TEXT@<msg>@@@
    self.cursor['step_text'].append(msg)
    self.updateCursorText()

  def STEP_SUMMARY_TEXT(self, msg):
    # Support: @@@STEP_SUMMARY_TEXT@<msg>@@@
    self.cursor['step_summary_text'].append(msg)
    self.updateCursorText()

  def SEED_STEP(self, step_name):
    # Support: @@@SEED_STEP <stepname>@@@ (seed a new section)
    self.addSection(step_name)

  def SEED_STEP_TEXT(self, step_name, step_text):
    # Support: @@@SEED_STEP_TEXT@<stepname>@<step text@@@ (change step text of a
    # seeded step)
    target = self.lookupCursor(step_name)
    target['step_text'].append(step_text)
    updateText(target)

  def STEP_CURSOR(self, step_name):
    # Support: @@@STEP_CURSOR <stepname>@@@ (set cursor to specified section)
    self.cursor = self.lookupCursor(step_name)

  def BUILD_STEP(self, step_name):
    # Support: @@@BUILD_STEP <step_name>@@@ (start a new section)
    # Ignore duplicate consecutive step labels (for robustness).
    if step_name != self.sections[-1]['name']:
      # When using BUILD_STEP, close the last section, unless it is a preamble.
      if not (self.cursor['step'].isFinished() or self.cursorIsPreamble()):
        self.closeCursor()
      section = self.addSection(step_name)
      self.startStep(section)
      self.cursor = section

  def STEP_TRIGGER(self, spec):
    # Support: @@@STEP_TRIGGER <json spec>@@@ (trigger build(s)).
    try:
      spec = json.loads(spec)
      builder_names = spec.get('builderNames')
      if not builder_names:
        raise ValueError('builderNames is not specified: %r' % (spec,))

      # Start builds.
      d = self.triggerBuilds(builder_names, spec.get('properties') or {})
      # addAsyncOpToCursor expects a deferred to return a build result. If a
      # buildset is added, then it is a success. This lambda function returns a
      # tuple, which is received by addAsyncOpToCursor.
      d.addCallback(lambda _: (builder.SUCCESS, None))
      description = 'Triggering build(s) on %s' % (', '.join(builder_names),)
      self.addAsyncOpToCursor(d, description)
    except Exception as ex:
      self.finishStep(self.cursor, builder.FAILURE, ex)

  @staticmethod
  def getPropertiesForTriggeredBuild(current_properties, new_properties):
    props = {
        'parent_buildername': current_properties.getProperty('buildername'),
        'parent_buildnumber': current_properties.getProperty('buildnumber'),
    }
    props.update(new_properties)
    # Specify property sources.
    return dict((k, (v, 'ParentBuild'))
            for k, v in props.iteritems())

  @defer.inlineCallbacks
  def triggerBuilds(self, builder_names, properties):
    """Creates a new buildset."""
    build = self.command.build
    master = build.builder.botmaster.parent
    current_properties = build.getProperties()

    # Use the same source stamp.
    source_stamp = build.getSourceStamp()
    revision = current_properties.getProperty('got_revision')
    if revision:
      source_stamp = source_stamp.getAbsoluteSourceStamp(revision)
    ssid = yield source_stamp.getSourceStampId(master)

    properties = self.getPropertiesForTriggeredBuild(current_properties,
                                                     properties)

    bsid, brids = yield master.addBuildset(
        ssid=ssid,
        reason='Triggered by %s' % build.builder.name,
        properties=properties,
        builderNames=builder_names)
    log.msg('Triggered a buildset %s with builders %s' % (bsid, builder_names))
    defer.returnValue((bsid, brids))

  def handleReturnCode(self, return_code):
    # Treat all non-zero return codes as failure.
    # We could have a special return code for warnings/exceptions, however,
    # this might conflict with some existing use of a return code.
    # Besides, applications can always intercept return codes and emit
    # STEP_* tags.
    succeeded = return_code == 0
    if succeeded:
      # Do not close the initial section because it will be closed by
      # self.finished when runCommand completes.
      if not self.cursorIsPreamble():
        self.closeCursor()
      if self.honor_zero_return_code:
        self.annotate_status = builder.SUCCESS
    else:
      self.annotate_status = builder.FAILURE
      if not self.cursorIsPreamble():
        self.finishCursor(builder.FAILURE,
                          reason='return code was %d.' % return_code)
    self.cleanupSteps(exclude_async_pending=succeeded)

  def stepsToWait(self):
    return [s for s in self.sections[1:]
            if s['step'].isStarted() and not s['step'].isFinished()]

  def waitForSteps(self):
    sections_to_wait = self.stepsToWait()

    # Assume this function is called after annotated script execution completes
    # for assertion only.
    for section in sections_to_wait:
      assert section['async_ops'], ('The annotated script finished execution '
                                    'but a step without async ops was not '
                                    'closed')

    step_deferreds = [s['step'].waitUntilFinished()
                      for s in sections_to_wait]
    return defer.DeferredList(step_deferreds)


class AnnotatedCommand(ProcessLogShellStep):
  """Buildbot command that knows how to display annotations."""

  def __init__(self, target=None, *args, **kwargs):
    clobber = ''
    perf_id = None
    perf_report_url_suffix = None
    show_perf = None
    if 'factory_properties' in kwargs:
      if kwargs['factory_properties'].get('clobber'):
        clobber = '1'
      perf_id = kwargs['factory_properties'].get('perf_id')
      perf_report_url_suffix = kwargs['factory_properties'].get(
          'perf_report_url_suffix')
      show_perf = kwargs['factory_properties'].get('show_perf_results')
      # kwargs is passed eventually to RemoteShellCommand(**kwargs).
      # This constructor (in buildbot/process/buildstep.py) does not
      # accept unknown arguments (like factory_properties)
      del kwargs['factory_properties']

    # Inject standard tags into the environment.
    env = {
        'BUILDBOT_BLAMELIST': WithProperties('%(blamelist:-[])s'),
        'BUILDBOT_BRANCH': WithProperties('%(branch:-None)s'),
        'BUILDBOT_BUILDBOTURL': WithProperties('%(buildbotURL:-None)s'),
        'BUILDBOT_BUILDERNAME': WithProperties('%(buildername:-None)s'),
        'BUILDBOT_BUILDNUMBER': WithProperties('%(buildnumber:-None)s'),
        'BUILDBOT_CLOBBER': clobber or WithProperties('%(clobber:+1)s'),
        'BUILDBOT_GOT_REVISION': WithProperties('%(got_revision:-None)s'),
        'BUILDBOT_MASTERNAME': WithProperties('%(mastername:-None)s'),
        'BUILDBOT_REVISION': WithProperties('%(revision:-None)s'),
        'BUILDBOT_SCHEDULER': WithProperties('%(scheduler:-None)s'),
        'BUILDBOT_SLAVENAME': WithProperties('%(slavename:-None)s'),
    }
    # Apply the passed in environment on top.
    old_env = kwargs.get('env') or {}
    env.update(old_env)
    # Change passed in args (ok as a copy is made internally).
    kwargs['env'] = env

    ProcessLogShellStep.__init__(self, *args, **kwargs)
    self.script_observer = AnnotationObserver(
        self, show_perf=show_perf, perf_id=perf_id,
        perf_report_url_suffix=perf_report_url_suffix, target=target)
    self.addLogObserver('stdio', self.script_observer)

  def describe(self, done=False):
    if self.step_status and self.step_status.isStarted():
      observer_text = self.script_observer.describe()
    else:
      observer_text = []
    if observer_text:
      return observer_text
    else:
      return ProcessLogShellStep.describe(self, done)

  def _removePreamble(self):
    """Remove preamble if there is only section.

    'stdio' will be identical to 'preamble' if there is only one annotator
    section, so it's redundant to show both on the waterfall.
    """
    if len(self.script_observer.sections) == 1:
      self.step_status.logs = [x for x in self.step_status.logs if
                               x.name != 'preamble']

  def interrupt(self, reason):
    if not self.script_observer.cursorIsPreamble():
      self.script_observer.finishCursor(builder.EXCEPTION,
                                        reason='step was interrupted.')
    self.script_observer.cleanupSteps()
    self._removePreamble()
    return ProcessLogShellStep.interrupt(self, reason)

  def evaluateCommand(self, cmd):
    observer_result = self.script_observer.annotate_status
    # Check if ProcessLogShellStep detected a failure or warning also.
    log_processor_result = ProcessLogShellStep.evaluateCommand(self, cmd)
    return BuilderStatus.combine(observer_result, log_processor_result)

  def scriptComplete(self, cmd):
    self.script_observer.handleReturnCode(cmd.rc)
    self._removePreamble()

  def runCommand(self, command):
    """Runs command and waits for emitted steps to finish."""
    d = ProcessLogShellStep.runCommand(self, command)
    def onCommandFinished(command_result):
      """Gets executed after remote command completes. Handles command_result
      and starts to wait for remaining steps to finish. Returns command_result
      as Deferred."""
      self.scriptComplete(command_result)
      steps_d = self.script_observer.waitForSteps()
      # Ignore the waitForSteps' result and return the original result,
      # so the caller of runCommand receives command_result.
      steps_d.addCallback(lambda *_: command_result)
      return steps_d
    d.addCallback(onCommandFinished)
    return d
