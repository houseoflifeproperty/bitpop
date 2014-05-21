# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A subclass of commands.SVN that allows more flexible error recovery.

This code is only used on the slave but it is living in common/ because it is
directly imported from buildbot/slave/bot.py."""

import os
import re

from twisted.python import log
from twisted.internet import defer

from common import chromium_utils

# TODO(maruel): REMOVE as soon as conversion to buildbot 0.8.4p1 is done.
# pylint: disable=E1101

try:
  # Buildbot 0.8.x
  # Unable to import 'XX'
  # pylint: disable=F0401
  from buildslave.commands.base import Command
  from buildslave.commands.base import SourceBaseCommand
  from buildslave.commands.registry import commandRegistry
  from buildslave import runprocess
  commandbase = Command
  sourcebase = SourceBaseCommand
  runprocesscmd = runprocess.RunProcess
  bbver = 8.4
except ImportError:
  # Buildbot 0.7.12
  # Unable to import 'XX'
  # pylint: disable=E0611,E1101,F0401
  from buildbot.slave import commands
  from buildbot.slave.registry import registerSlaveCommand
  commandbase = commands.ShellCommand
  sourcebase = commands.SourceBase
  runprocesscmd = commands.ShellCommand
  bbver = 7.12

# Local errors.
class InvalidPath(Exception): pass


def FixDiffLineEnding(diff):
  """Fix patch files generated on windows and applied on mac/linux.

  For files with svn:eol-style=crlf, svn diff puts CRLF in the diff hunk header.
  patch on linux and mac barfs on those hunks. As usual, blame svn."""
  output = ''
  for line in diff.splitlines(True):
    if (line.startswith('---') or line.startswith('+++') or
        line.startswith('@@ ') or line.startswith('\\ No')):
      # Strip any existing CRLF on the header lines
      output += line.rstrip() + '\n'
    else:
      output += line
  return output


def untangle(stdout_lines):
  """Sort the lines of stdout by the job number prefix."""
  out = []
  tasks = {}
  UNTANGLE_RE = re.compile(r'^(\d+)>(.*)$')
  for line in stdout_lines:
    m = UNTANGLE_RE.match(line)
    if not m:
      if line:  # skip empty lines
        # Output untangled lines so far.
        for key in sorted(tasks.iterkeys()):
          out.extend(tasks[key])
        tasks = {}
        out.append(line)
    else:
      if m.group(2):  # skip empty lines
        tasks.setdefault(int(m.group(1)), []).append(m.group(2))
  for key in sorted(tasks.iterkeys()):
    out.extend(tasks[key])
  return out


def _RenameDirectoryCommand(src_dir, dest_dir):
  """Returns a command list to rename a directory (or file) using Python."""
  # Use / instead of \ in paths to avoid issues with escaping.
  return ['python', '-c',
          'import os; '
          'os.rename("%s", "%s")' %
              (src_dir.replace('\\', '/'), dest_dir.replace('\\', '/'))]


def _RemoveFileCommand(filename):
  """Returns a command list to remove a directory (or file) using Python."""
  # Use / instead of \ in paths to avoid issues with escaping.
  return ['python', '-c',
          'from common import chromium_utils; '
          'chromium_utils.RemoveFile("%s")' % filename.replace('\\', '/')]


class GClient(sourcebase):
  """Source class that handles gclient checkouts.

  Buildbot 8.3 changed from commands.SourceBase to SourceBaseCommand,
  so this inherits from a variable set to the right item.  Docs below
  assume 8.3 (and this hack should be removed when pre-8.3 clients are
  turned down.

  In addition to the arguments handled by SourceBaseCommand, this command
  reads the following keys:

  ['gclient_spec']:
    if not None, then this specifies the text of the .gclient file to use.
    this overrides any 'svnurl' argument that may also be specified.

  ['rm_timeout']:
    if not None, a different timeout used only for the 'rm -rf' operation in
    doClobber.  Otherwise the svn timeout will be used for that operation too.

  ['svnurl']:
    if not None, then this specifies the svn url to pass to 'gclient config'
    to create a .gclient file.

  ['branch']:
    if not None, then this specifies the module name to pass to 'gclient sync'
    in --revision argument.

  ['env']:
    Augment os.environ.

  ['no_gclient_branch']:
    If --revision is specified, don't prepend it with <branch>@.  This is
    necessary for git, where the solution name is 'src' and the branch name
    is 'master'.

  ['no_gclient_revision']:
    Do not specify the --revision argument to gclient at all.
  """

  # pylint complains that __init__ in GClient's parent isn't called.  This is
  # because it doesn't realize we call it through GetParentClass().  Disable
  # that warning next.
  # pylint: disable=W0231

  header = 'gclient'

  def __init__(self, *args, **kwargs):
    # TODO(maruel): Mainly to keep pylint happy, remove once buildbot fixed
    # their style.
    self.branch = None
    self.srcdir = None
    self.revision = None
    self.env = None
    self.sourcedatafile = None
    self.patch = None
    self.command = None
    self.vcexe = None
    self.svnurl = None
    self.sudo_for_remove = None
    self.gclient_spec = None
    self.gclient_deps = None
    self.rm_timeout = None
    self.gclient_nohooks = False
    self.was_patched = False
    self.no_gclient_branch = False
    self.no_gclient_revision = False
    self.gclient_transitive = False
    self.delete_unversioned_trees_when_updating = True
    self.gclient_jobs = None
    # TODO(maruel): Remove once buildbot 0.8.4p1 conversion is complete.
    self.sourcedata = None
    chromium_utils.GetParentClass(GClient).__init__(self, *args, **kwargs)

  if bbver == 7.12:
    def getCommand(self, arg): # pylint: disable=R0201
      """In BB 8.3, this function is inherited"""
      return commands.getCommand(arg)

  def setup(self, args):
    """Our implementation of command.Commands.setup() method.
    The method will get all the arguments that are passed to remote command
    and is invoked before start() method (that will in turn call doVCUpdate()).
    """

    if bbver == 7.12:
      commands.SourceBase.setup(self, args)
    else:
      sourcebase.setup(self, args)
    self.vcexe = self.getCommand('gclient')
    self.svnurl = args['svnurl']
    self.branch =  args.get('branch')
    self.revision = args.get('revision')
    self.patch = args.get('patch')
    self.sudo_for_remove = args.get('sudo_for_remove')
    self.gclient_spec = args['gclient_spec']
    self.gclient_deps = args.get('gclient_deps')
    self.sourcedata = '%s\n' % self.svnurl
    self.rm_timeout = args.get('rm_timeout', self.timeout)
    self.env = args.get('env')
    self.gclient_nohooks = args.get('gclient_nohooks', False)
    self.env['CHROMIUM_GYP_SYNTAX_CHECK'] = '1'
    self.no_gclient_branch = args.get('no_gclient_branch')
    self.no_gclient_revision = args.get('no_gclient_revision', False)
    self.gclient_transitive = args.get('gclient_transitive')
    self.gclient_jobs = args.get('gclient_jobs')

  def start(self):
    """Start the update process.

    start() is cut-and-paste from the base class, the block calling
    self.sourcedirIsPatched() and the revert support is the only functional
    difference from base."""
    self.sendStatus({'header': "starting " + self.header + "\n"})
    self.command = None

    # self.srcdir is where the VC system should put the sources
    if self.mode == "copy":
      self.srcdir = "source" # hardwired directory name, sorry
    else:
      self.srcdir = self.workdir
    self.sourcedatafile = os.path.join(self.builder.basedir,
                                       self.srcdir,
                                       ".buildbot-sourcedata")

    d = defer.succeed(None)
    # Do we need to clobber anything?
    if self.mode in ("copy", "clobber", "export"):
      d.addCallback(self.doClobber, self.workdir)
    if not (self.sourcedirIsUpdateable() and self.sourcedataMatches()):
      # the directory cannot be updated, so we have to clobber it.
      # Perhaps the master just changed modes from 'export' to
      # 'update'.
      d.addCallback(self.doClobber, self.srcdir)
    elif self.sourcedirIsPatched():
      # The directory is patched. Revert the sources.
      d.addCallback(self.doRevert)
      self.was_patched = True

    d.addCallback(self.doVC)

    if self.mode == "copy":
      d.addCallback(self.doCopy)
    if self.patch:
      d.addCallback(self.doPatch)
    if (self.patch or self.was_patched) and not self.gclient_nohooks:
      # Always run doRunHooks if there *is* or there *was* a patch because
      # revert is run with --nohooks and `gclient sync` will not regenerate the
      # output files if the input files weren't updated..
      d.addCallback(self.doRunHooks)
    d.addCallbacks(self._sendRC, self._checkAbandoned)
    return d

  def sourcedirIsPatched(self):
    return os.path.exists(os.path.join(self.builder.basedir,
                                       self.srcdir, '.buildbot-patched'))

  def sourcedirIsUpdateable(self):
    # Patched directories are updatable.
    return os.path.exists(os.path.join(self.builder.basedir,
                                       self.srcdir, '.gclient'))

  # TODO(pamg): consolidate these with the copies above.
  def _RemoveDirectoryCommand(self, rm_dir):
    """Returns a command list to delete a directory using Python."""
    # Use / instead of \ in paths to avoid issues with escaping.
    cmd = ['python', '-c',
           'from common import chromium_utils; '
           'chromium_utils.RemoveDirectory("%s")' % rm_dir.replace('\\', '/')]
    if self.sudo_for_remove:
      cmd = ['sudo'] + cmd
    return cmd

  def doGclientUpdate(self):
    """Sync the client
    """
    dirname = os.path.join(self.builder.basedir, self.srcdir)
    command = [chromium_utils.GetGClientCommand(),
               'sync', '--verbose', '--reset', '--manually_grab_svn_rev',
               '--force']
    if self.delete_unversioned_trees_when_updating:
      command.append('--delete_unversioned_trees')
    if self.gclient_jobs:
      command.append('-j%d' % self.gclient_jobs)
    # Don't run hooks if it was patched or there is a patch since runhooks will
    # be run after.
    if self.gclient_nohooks or self.patch or self.was_patched:
      command.append('--nohooks')
    # GClient accepts --revision argument of two types 'module@rev' and 'rev'.
    if self.revision and not self.no_gclient_revision:
      command.append('--revision')
      # Ignore non-svn part of compound revisions.
      # Used for nacl.sdk.mono waterfall.
      if ':' in self.revision:
        command.append(self.revision.split(':')[0])
      elif (not self.branch or
          self.no_gclient_branch or
          '@' in str(self.revision)):
        command.append(str(self.revision))
      else:
        # Make the revision look like branch@revision.
        command.append('%s@%s' % (self.branch, self.revision))
      # We only add the transitive flag if we have a revision, otherwise it is
      # meaningless.
      if self.gclient_transitive:
        command.append('--transitive')

    if self.gclient_deps:
      command.append('--deps=' + self.gclient_deps)

    c = runprocesscmd(self.builder, command, dirname,
                      sendRC=False, timeout=self.timeout,
                      keepStdout=True, environ=self.env)
    self.command = c
    return c.start()

  def getGclientConfigCommand(self):
    """Return the command to run the gclient config step.
    """
    dirname = os.path.join(self.builder.basedir, self.srcdir)
    command = [chromium_utils.GetGClientCommand(), 'config']

    if self.gclient_spec:
      command.append('--spec=%s' % self.gclient_spec)
    else:
      command.append(self.svnurl)

    c = runprocesscmd(self.builder, command, dirname,
                      sendRC=False, timeout=self.timeout,
                      keepStdout=True, environ=self.env)
    return c

  def doVCUpdate(self):
    """Sync the client
    """
    # Make sure the .gclient is updated.
    os.remove(os.path.join(self.builder.basedir, self.srcdir, '.gclient'))
    c = self.getGclientConfigCommand()
    self.command = c
    d = c.start()
    d.addCallback(self._abandonOnFailure)
    d.addCallback(lambda _: self.doGclientUpdate())
    return d

  def doVCFull(self):
    """Setup the .gclient file and then sync
    """
    chromium_utils.MaybeMakeDirectory(self.builder.basedir, self.srcdir)

    c = self.getGclientConfigCommand()
    self.command = c
    d = c.start()
    d.addCallback(self._abandonOnFailure)
    d.addCallback(lambda _: self.doGclientUpdate())
    return d

  def doClobber(self, dummy, dirname, _=False):
    """Move the old directory aside, or delete it if that's already been done.

    This function is designed to be used with a source dir.  If it's called
    with anything else, the caller will need to be sure to clean up the
    <dirname>.dead directory once it's no longer needed.

    If this is the first time we're clobbering since we last finished a
    successful update or checkout, move the old directory aside so a human
    can try to recover from it if desired.  Otherwise -- if such a backup
    directory already exists, because this isn't the first retry -- just
    remove the old directory.

    Args:
      dummy: unused
      dirname: the directory within self.builder.basedir to be clobbered
    """
    old_dir = os.path.join(self.builder.basedir, dirname)
    dead_dir = old_dir + '.dead'
    if os.path.isdir(old_dir):
      if os.path.isdir(dead_dir):
        command = self._RemoveDirectoryCommand(old_dir)
      else:
        command = _RenameDirectoryCommand(old_dir, dead_dir)
      c = runprocesscmd(self.builder, command, self.builder.basedir,
                        sendRC=0, timeout=self.rm_timeout,
                        environ=self.env)
      self.command = c
      # See commands.SVN.doClobber for notes about sendRC.
      d = c.start()
      d.addCallback(self._abandonOnFailure)
      return d
    return None

  def doRevert(self, dummy):
    """Revert any modification done by a previous patch.

    This is done in 2 parts to trap potential errors at each step. Note that
    it is assumed that .orig and .rej files will be reverted, e.g. deleted by
    the 'gclient revert' command. If the try bot is configured with
    'global-ignores=*.orig', patch failure will occur."""
    dirname = os.path.join(self.builder.basedir, self.srcdir)
    command = [chromium_utils.GetGClientCommand(), 'revert', '--nohooks']
    c = runprocesscmd(self.builder, command, dirname,
                      sendRC=False, timeout=self.timeout,
                      keepStdout=True, environ=self.env)
    self.command = c
    d = c.start()
    d.addCallback(self._abandonOnFailure)
    # Remove patch residues.
    d.addCallback(lambda _: self._doRevertRemoveSignalFile())
    return d

  def _doRevertRemoveSignalFile(self):
    """Removes the file that signals that the checkout is patched.

    Must be called after a revert has been done and the patch residues have
    been removed."""
    command = _RemoveFileCommand(os.path.join(self.builder.basedir,
                                 self.srcdir, '.buildbot-patched'))
    dirname = os.path.join(self.builder.basedir, self.srcdir)
    c = runprocesscmd(self.builder, command, dirname,
                      sendRC=False, timeout=self.timeout,
                      keepStdout=True, environ=self.env)
    self.command = c
    d = c.start()
    d.addCallback(self._abandonOnFailure)
    return d

  def doPatch(self, res):
    patchlevel = self.patch[0]
    diff = FixDiffLineEnding(self.patch[1])
    root = None
    if len(self.patch) >= 3:
      root = self.patch[2]
    command = [
        self.getCommand("patch"),
        '-p%d' % patchlevel,
        '--remove-empty-files',
        '--force',
        '--forward',
    ]
    dirname = os.path.join(self.builder.basedir, self.workdir)
    # Mark the directory so we don't try to update it later.
    open(os.path.join(dirname, ".buildbot-patched"), "w").write("patched\n")

    # Update 'dirname' with the 'root' option. Make sure it is a subdirectory
    # of dirname.
    if (root and
        os.path.abspath(os.path.join(dirname, root)
                        ).startswith(os.path.abspath(dirname))):
      dirname = os.path.join(dirname, root)

    # Now apply the patch.
    c = runprocesscmd(self.builder, command, dirname,
                      sendRC=False, timeout=self.timeout,
                      initialStdin=diff, environ=self.env)
    self.command = c
    d = c.start()
    d.addCallback(self._abandonOnFailure)
    if diff.find('DEPS') != -1:
      d.addCallback(self.doVCUpdateOnPatch)
      d.addCallback(self._abandonOnFailure)
    return d

  def doVCUpdateOnPatch(self, res):
    if self.revision and not self.branch and '@' not in str(self.revision):
      self.branch = 'src'
    self.delete_unversioned_trees_when_updating = False
    return self.doVCUpdate()

  def doRunHooks(self, dummy):
    """Runs "gclient runhooks" after patching."""
    dirname = os.path.join(self.builder.basedir, self.srcdir)
    command = [chromium_utils.GetGClientCommand(), 'runhooks']
    c = runprocesscmd(self.builder, command, dirname,
                      sendRC=False, timeout=self.timeout,
                      keepStdout=True, environ=self.env)
    self.command = c
    d = c.start()
    d.addCallback(self._abandonOnFailure)
    return d

  def writeSourcedata(self, res):
    """Write the sourcedata file and remove any dead source directory."""
    dead_dir = os.path.join(self.builder.basedir, self.srcdir + '.dead')
    if os.path.isdir(dead_dir):
      msg = 'Removing dead source dir'
      self.sendStatus({'header': msg + '\n'})
      log.msg(msg)
      command = self._RemoveDirectoryCommand(dead_dir)
      c = runprocesscmd(self.builder, command, self.builder.basedir,
                        sendRC=0, timeout=self.rm_timeout,
                        environ=self.env)
      self.command = c
      d = c.start()
      d.addCallback(self._abandonOnFailure)
    open(self.sourcedatafile, 'w').write(self.sourcedata)
    return res

  def parseGotRevision(self):
    """Extract the Chromium and WebKit revision numbers from the svn output.

    svn checkout operations finish with 'Checked out revision 16657.'
    svn update operations finish the line 'At revision 16654.' when there
    is no change. They finish with 'Updated to revision 16655.' otherwise.

    A tuple of the two revisions is always returned, although either or both
    may be None if they could not be found.
    """
    SVN_REVISION_RE = re.compile(
        r'^(Checked out|At|Updated to) revision ([0-9]+)\.')
    def findRevisionNumberFromSvn(line):
      m = SVN_REVISION_RE.search(line)
      if m:
        return int(m.group(2))
      return None
    GIT_REVISION_RE = re.compile(
        r'^Checked out revision ([0-9a-fA-F]{40})$')
    def findRevisionNumberFromGit(line):
      m = GIT_REVISION_RE.search(line)
      if m:
        return m.group(1)
      return None

    WEBKIT_CHECKOUT_PATH = os.path.join(
        'src', 'third_party', 'WebKit', 'Source').replace('\\', '\\\\')

    WEBKIT_UPDATE_RE = re.compile(
        r'svn (checkout|update) .*%s ' % WEBKIT_CHECKOUT_PATH)
    def findWebKitUpdate(line):
      return WEBKIT_UPDATE_RE.search(line)

    NACL_CHECKOUT_PATH = os.path.join(
        'src', 'native_client').replace('\\', '\\\\')

    NACL_UPDATE_RE = re.compile(
        r'svn (checkout|update) .*%s ' % NACL_CHECKOUT_PATH)
    def findNaClUpdate(line):
      return NACL_UPDATE_RE.search(line)

    V8_CHECKOUT_PATH = os.path.join('src', 'v8').replace('\\', '\\\\')

    V8_UPDATE_RE = re.compile(r'svn (checkout|update) .*%s ' % V8_CHECKOUT_PATH)
    def findV8Update(line):
      return V8_UPDATE_RE.search(line)

    def findRevisionNumberFromGclient(repo, line):
      m = re.match(r'_____ %s at ([0-9]+)$' % repo, line)
      if m:
        return int(m.group(1))
      return None

    chromium_revision = None
    webkit_revision = None
    nacl_revision = None
    v8_revision = None
    found_webkit_update = False
    found_nacl_update = False
    found_v8_update = False

    untangled_stdout = untangle(self.command.stdout.splitlines(False))
    # We only care about the last sync which starts with "solutions=[...".
    # Look backwards to find the last one first.
    for i, line in enumerate(reversed(untangled_stdout)):
      if line.startswith('solutions=['):
        # Only keep from "solutions" line to end.
        untangled_stdout = untangled_stdout[-i-1:]
        break

    # http://crbug.com/82939: This is very fragile, see the bug for the
    # details.
    for line in untangled_stdout:
      revision = findRevisionNumberFromSvn(line)
      if not revision:
        revision = findRevisionNumberFromGit(line)
      if revision:
        if (not found_webkit_update and
            not found_nacl_update and
            not found_v8_update and
            not chromium_revision):
          chromium_revision = revision
        elif found_webkit_update and not webkit_revision:
          webkit_revision = revision
        elif found_nacl_update and not nacl_revision:
          nacl_revision = revision
        elif found_v8_update and not v8_revision:
          v8_revision = revision

      # No revision number found, look for the svn update for WebKit.
      if not found_webkit_update:
        found_webkit_update = findWebKitUpdate(line)

      # No revision number found, look for the svn update for NaCl.
      if not found_nacl_update:
        found_nacl_update = findNaClUpdate(line)

      # No revision number found, look for the svn update for V8.
      if not found_v8_update:
        found_v8_update = findV8Update(line)

      # Check for gclient output.
      if not chromium_revision:
        chromium_revision = findRevisionNumberFromGclient('src', line)
      if not webkit_revision:
        webkit_revision = findRevisionNumberFromGclient(
            WEBKIT_CHECKOUT_PATH, line)
      if not nacl_revision:
        nacl_revision = findRevisionNumberFromGclient(
            NACL_CHECKOUT_PATH, line)
      if not v8_revision:
        v8_revision = findRevisionNumberFromGclient(V8_CHECKOUT_PATH, line)

      # Exit if we're done.
      if (chromium_revision and
          webkit_revision and
          nacl_revision and
          v8_revision):
        break

    return chromium_revision, webkit_revision, nacl_revision, v8_revision

  def _handleGotRevision(self, res):
    """Send parseGotRevision() return values as status updates to the master."""
    d = defer.maybeDeferred(self.parseGotRevision)
    def sendStatusUpdatesToMaster(revisions):
      chromium_revision, webkit_revision, nacl_revision, v8_revision = revisions
      self.sendStatus({'got_revision': chromium_revision})
      self.sendStatus({'got_webkit_revision': webkit_revision})
      self.sendStatus({'got_nacl_revision': nacl_revision})
      self.sendStatus({'got_v8_revision': v8_revision})
    d.addCallback(sendStatusUpdatesToMaster)
    return d

  def maybeDoVCFallback(self, rc):
    """Called after doVCUpdate."""
    if type(rc) is int and rc == 2:
      # Non-VC failure, return 2 to turn the step red.
      return rc

    # super
    return sourcebase.maybeDoVCFallback(self, rc)

  def maybeDoVCRetry(self, res):
    """Called after doVCFull."""
    if type(res) is int and res == 2:
      # Non-VC failure, return 2 to turn the step red.
      return res

    # super
    return sourcebase.maybeDoVCRetry(self, res)


class ApplyIssue(commandbase):
  """Command to run apple_issue.py on the checkbout."""

  def __init__(self, *args, **kwargs):
    log.msg('ApplyIssue.__init__')
    self.root = None
    self.issue = None
    self.patchset = None
    self.email = None
    self.password = None
    self.workdir = None
    self.timeout = None
    self.server = None
    chromium_utils.GetParentClass(ApplyIssue).__init__(self, *args, **kwargs)

  def _doApplyIssue(self, _):
    """Run the apply_issue.py script in the source checkout directory."""
    log.msg('ApplyIssue._doApplyIssue')
    cmd = [
        'apply_issue.bat' if chromium_utils.IsWindows() else 'apply_issue',
        '-r', self.root,
        '-i', self.issue,
        '-p', self.patchset,
        '-e', self.email,
        '-w', '-',
    ]

    if self.server:
      cmd.extend(['-s', self.server])

    command = runprocesscmd(
        self.builder, cmd, os.path.join(self.builder.basedir, self.workdir),
        timeout=self.timeout, initialStdin=self.password)
    return command.start()

  # commandbase overrides:

  def setup(self, args):
    self.root = args['root']
    self.issue = args['issue']
    self.patchset = args['patchset']
    self.email = args['email']
    self.password = args['password']
    self.workdir = args['workdir']
    self.timeout = args['timeout']
    self.server = args.get('server')

  def start(self):
    log.msg('ApplyIssue.start')
    d = defer.succeed(None)
    d.addCallback(self._doApplyIssue)
    return d


def RegisterCommands():
  """Registers all command objects defined in this file."""
  try:
    # This version should work on BB 8.3

    # We run this code in a try because it fails with an assertion if
    # the module is loaded twice.
    commandRegistry['gclient'] = 'slave.chromium_commands.GClient'
    commandRegistry['apply_issue'] = 'slave.chromium_commands.ApplyIssue'
    return
  except (AssertionError, NameError):
    pass

  try:
    # This version should work on BB 7.12

    # We run this code in a try because it fails with an assertion if
    # the module is loaded twice.
    registerSlaveCommand('gclient', GClient, commands.command_version)
    registerSlaveCommand('apply_issue', ApplyIssue, commands.command_version)
  except (AssertionError, NameError):
    pass


RegisterCommands()
