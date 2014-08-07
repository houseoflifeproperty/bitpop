#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to build chrome, executed by buildbot.

  When this is run, the current directory (cwd) should be the outer build
  directory (e.g., chrome-release/build/).

  For a list of command-line options, call this script with '--help'.
"""

import datetime
import errno
import multiprocessing
import optparse
import os
import re
import shlex
import socket
import sys
import time

from common import chromium_utils
from slave import build_directory


# Path of the scripts/slave/ checkout on the slave, found by looking at the
# current compile.py script's path's dirname().
SLAVE_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
# Path of the build/ checkout on the slave, found relative to the
# scripts/slave/ directory.
BUILD_DIR = os.path.dirname(os.path.dirname(SLAVE_SCRIPTS_DIR))


class EchoDict(dict):
  """Dict that remembers all modified values."""

  def __init__(self, *args, **kwargs):
    self.overrides = set()
    self.adds = set()
    super(EchoDict, self).__init__(*args, **kwargs)

  def __setitem__(self, key, val):
    if not key in self and not key in self.overrides:
      self.adds.add(key)
    self.overrides.add(key)
    super(EchoDict, self).__setitem__(key, val)

  def __delitem__(self, key):
    self.overrides.add(key)
    if key in self.adds:
      self.adds.remove(key)
      self.overrides.remove(key)
    super(EchoDict, self).__delitem__(key)

  def print_overrides(self, fh=None):
    if not self.overrides:
      return
    if not fh:
      fh = sys.stdout
    fh.write('Environment variables modified in compile.py:\n')
    for k in sorted(list(self.overrides)):
      if k in self:
        fh.write('  %s=%s\n' % (k, self[k]))
      else:
        fh.write('  %s (removed)\n' % k)
    fh.write('\n')


def ReadHKLMValue(path, value):
  """Retrieve the install path from the registry for Visual Studio 8.0 and
  Incredibuild."""
  # Only available on Windows.
  # pylint: disable=F0401
  import win32api, win32con
  try:
    regkey = win32api.RegOpenKeyEx(win32con.HKEY_LOCAL_MACHINE, path, 0,
                                   win32con.KEY_READ)
    value = win32api.RegQueryValueEx(regkey, value)[0]
    win32api.RegCloseKey(regkey)
    return value
  except win32api.error:
    return None


def goma_setup(options, env):
  """Sets up goma if necessary.

  If using the Goma compiler, first call goma_ctl with ensure_start
  (or restart in clobber mode) to ensure the proxy is available, and returns
  True.
  If it failed to start up compiler_proxy, modify options.compiler and
  options.goma_dir and returns False

  """
  if options.compiler not in ('goma', 'goma-clang', 'jsonclang'):
    # Unset goma_dir to make sure we'll not use goma.
    options.goma_dir = None
    return False

  # HACK(shinyak, goma): Enable GLOBAL_FILEID_CACHE_PATTERNS only in
  # Chromium Win Ninja Goma and Chromium Win Ninja Goma (shared) builders,
  # so that we can check whether this feature is not harmful and how much
  # this feature can improve compile performance.
  # If this experiment succeeds, I'll enable this in all Win/Mac platforms.
  hostname = socket.gethostname().split('.')[0].lower()
  if hostname.lower() in ['build28-m1', 'build58-m1']:
    patterns = r'win_toolchain\vs2013_files,third_party,src\chrome,src\content'
    env['GOMA_GLOBAL_FILEID_CACHE_PATTERNS'] = patterns

  # goma is requested.
  goma_key = os.path.join(options.goma_dir, 'goma.key')
  if os.path.exists(goma_key):
    env['GOMA_API_KEY_FILE'] = goma_key
  result = -1
  if not chromium_utils.IsWindows():
    goma_ctl_cmd = [os.path.join(options.goma_dir, 'goma_ctl.sh')]
    goma_start_command = ['ensure_start']
    if options.clobber:
      goma_start_command = ['restart']
    result = chromium_utils.RunCommand(goma_ctl_cmd + goma_start_command,
                                       env=env)
  else:
    env['GOMA_RPC_EXTRA_PARAMS'] = '?win'
    goma_ctl_cmd = [sys.executable,
                    os.path.join(options.goma_dir, 'goma_ctl.py')]
    result = chromium_utils.RunCommand(goma_ctl_cmd + ['start'], env=env)
  if not result:
    # goma started sucessfully.
    return True

  print 'warning: failed to start goma. falling back to non-goma'
  # Drop goma from options.compiler
  options.compiler = options.compiler.replace('goma-', '')
  if options.compiler == 'goma':
    options.compiler = None
  # Reset options.goma_dir.
  # options.goma_dir will be used to check if goma is ready
  # when options.compiler=jsonclang.
  options.goma_dir = None
  env['GOMA_DISABLED'] = '1'
  return False


def goma_teardown(options, env):
  """Tears down goma if necessary. """
  if (options.compiler in ('goma', 'goma-clang', 'jsonclang') and
      options.goma_dir):
    if not chromium_utils.IsWindows():
      goma_ctl_cmd = [os.path.join(options.goma_dir, 'goma_ctl.sh')]
    else:
      goma_ctl_cmd = [sys.executable,
                      os.path.join(options.goma_dir, 'goma_ctl.py')]
    # Show goma stats so that we can investigate goma when
    # something weird happens.
    chromium_utils.RunCommand(goma_ctl_cmd + ['stat'], env=env)
    # Always stop the proxy for now to allow in-place update.
    chromium_utils.RunCommand(goma_ctl_cmd + ['stop'], env=env)


def common_xcode_settings(command, options, env, compiler=None):
  """
  Sets desirable Mac environment variables and command-line options
  that are common to the Xcode builds.
  """
  compiler = options.compiler
  assert compiler in (None, 'clang', 'goma', 'goma-clang')

  if compiler == 'goma':
    print 'using goma'
    assert options.goma_dir
    command.insert(0, '%s/goma-xcodebuild' % options.goma_dir)
    return

  cc = None
  ldplusplus = None
  src_path = os.path.dirname(options.build_dir)
  if compiler in ('clang', 'goma-clang'):
    clang_bin_dir = os.path.abspath(os.path.join(
        src_path, 'third_party', 'llvm-build', 'Release+Asserts', 'bin'))
    cc = os.path.join(clang_bin_dir, 'clang')
    ldplusplus = os.path.join(clang_bin_dir, 'clang++')

    if compiler == 'goma-clang':
      print 'using goma-clang'
      if options.clobber:
        # Disable compiles on local machine.  When the goma server-side object
        # file cache is warm, this can speed up clobber builds by up to 30%.
        env['GOMA_USE_LOCAL'] = '0'
      assert options.goma_dir
      command.insert(0, '%s/goma-xcodebuild' % options.goma_dir)

  if cc:
    print 'Forcing CC = %s' % cc
    env['CC'] = cc

  if ldplusplus:
    print 'Forcing LDPLUSPLUS = %s' % ldplusplus
    env['LDPLUSPLUS'] = ldplusplus


def ninja_clobber(build_output_dir):
  """Removes everything but ninja files from a build directory."""
  for root, _, files in os.walk(build_output_dir, topdown=False):
    for f in files:
      # For .manifest in particular, gyp windows ninja generates manifest
      # files at generation time but clobber nukes at the beginning of
      # compile, so make sure not to delete those generated files, otherwise
      # compile will fail.
      if (f.endswith('.ninja') or f.endswith('.manifest') or
          f.startswith('msvc') or  # VS runtime DLLs.
          f in ('gyp-mac-tool', 'gyp-win-tool',
                'environment.x86', 'environment.x64')):
        continue
      os.unlink(os.path.join(root, f))
    # Delete the directory if empty; this works because the walk is bottom-up.
    try:
      os.rmdir(root)
    except OSError, e:
      if e.errno in (39, 41, 66):
        # If the directory isn't empty, ignore it.
        # On Windows, os.rmdir will raise WindowsError with winerror 145,
        # which e.errno is 41.
        # On Linux, e.errno is 39.
        pass
      else:
        raise


# RunCommandFilter for xcodebuild
class XcodebuildFilter(chromium_utils.RunCommandFilter):
  """xcodebuild filter"""

  # This isn't a full on state machine because there are some builds that
  # invoke xcodebuild as part of a target action.  Instead it relies on
  # the consistent format that Xcode uses for its steps.  The output follows
  # the pattern of:
  #   1. a section line for the target
  #   2. a "header" for each thing done (Compile, PhaseScriptExecution, etc.)
  #   3. all the commands under that step (cd, setenv, /Developer/usr/bin/gcc,
  #      etc.)
  #   4. a blank line
  #   5. any raw output from the command for the step
  #   [loop to 2 for each thing on this target]
  #   [loop to 1 for each target]
  #   6. "** BUILD SUCCEEDED **" or "** BUILD FAILED **".  If the build failed,
  #      an epilog of:
  #         "The following build commands failed:"
  #         [target_name]:
  #            [header(s) from #3, but with a full path in some cases]
  #         "(## failure[s])"
  # So this filter works by watching for some common strings that mark the
  # start of a "section" and buffers or sending on as needed.

  # Enum for the current mode.
  class LineMode:
    # Class has no __init__ method
    # pylint: disable=W0232
    BufferAsCommand, Unbuffered, DroppingFailures = range(3)

  # Enum for output types.
  class LineType:
    # Class has no __init__ method
    # pylint: disable=W0232
    Header, Command, Info, Raw = range(4)

  section_regex = re.compile('^=== BUILD (NATIVE|AGGREGATE) TARGET (.+) OF '
                             'PROJECT (.+) WITH CONFIGURATION (.+) ===\n$')
  section_replacement = r'====Building \3:\2 (\4)\n'

  step_headers = (
    'CompileC',
    'CompileXIB',
    'CopyPlistFile',
    'CopyPNGFile',
    'CopyStringsFile',
    'CpResource',
    'CreateUniversalBinary',
    'Distributed-CompileC',
    'GenerateDSYMFile',
    'Ld',
    'Libtool',
    'PBXCp',
    'PhaseScriptExecution',
    'ProcessInfoPlistFile',
    'Preprocess',
    'ProcessPCH',
    'ProcessPCH++',
    'Strip',
    'Stripping',
    'Touch',
  )
  # Put an space on the end of the headers since that is how they should
  # actually appear in the output line.
  step_headers = tuple([x + ' ' for x in step_headers])

  lines_to_drop = (
    'Check dependencies\n',
  )

  gyp_info_lines = (
    # GYP rules use make for inputs/outputs, so if no work is done, this is
    # output.  If this all that shows up, not much point in showing the command
    # in the log, just show this to show the rules did nothing.
    'make: Nothing to be done for `all\'.\n',
  )
  gyp_info_prefixes = (
    # These are for Xcode's ui to show while work is being done, if this is
    # the only output, don't bother showing the command.
    'note: ',
  )

  failures_start = 'The following build commands failed:\n'
  failures_end_regex = re.compile('^\\([0-9]+ failures?\\)\n$')


  def __init__(self, full_log_file=None):
    # super
    chromium_utils.RunCommandFilter.__init__(self)
    self.line_mode = XcodebuildFilter.LineMode.Unbuffered
    self.full_log_file = full_log_file
    # self.ResetPushed() does the real rest, by pylint doesn't like them being
    # 'defined' outside of __init__.
    self.pushed_commands = None
    self.pushed_infos = None
    self.to_go = None
    self.ResetPushed()

  def ResetPushed(self):
    """Clear out all pushed output"""
    self.pushed_commands = ''
    self.pushed_infos = ''
    self.to_go = None

  def PushLine(self, line_type, a_line):
    """Queues up a line for output into the right buffer."""
    # Only expect one push per line filtered/processed, so to_go should always
    # be empty anytime this is called.
    assert self.to_go is None
    if line_type == XcodebuildFilter.LineType.Header:
      self.to_go = a_line
      # Anything in commands or infos was from previous block, so clear the
      # commands but leave the infos, that way they the shortened output will
      # be returned for this step.
      self.pushed_commands = ''
    elif line_type == XcodebuildFilter.LineType.Command:
      # Infos should never come before commands.
      assert self.pushed_infos == ''
      self.pushed_commands += a_line
    elif line_type == XcodebuildFilter.LineType.Info:
      self.pushed_infos += a_line
    elif line_type == XcodebuildFilter.LineType.Raw:
      self.to_go = a_line

  def AssembleOutput(self):
    """If there is any output ready to go, all the buffered bits are glued
    together and returned."""
    if self.to_go is None:
      return None
    result = self.pushed_commands + self.pushed_infos + self.to_go
    self.ResetPushed()
    return result

  def ProcessLine(self, a_line):
    """Looks at the line and current mode, pushing anything needed into the
    pipeline for output."""
    # Look for section or step headers.
    section_match = self.section_regex.match(a_line)
    if section_match:
      self.line_mode = XcodebuildFilter.LineMode.Unbuffered
      self.PushLine(XcodebuildFilter.LineType.Header,
                    section_match.expand(self.section_replacement))
      return
    if a_line.startswith(self.step_headers):
      self.line_mode = XcodebuildFilter.LineMode.BufferAsCommand
      # Just report the step and the output file (first two things), helps
      # makes the warnings/errors stick out more.
      parsed = shlex.split(a_line)
      if len(parsed) >= 2:
        a_line = '%s %s\n' % (parsed[0], parsed[1])
      self.PushLine(XcodebuildFilter.LineType.Header, '____' + a_line)
      return

    # Remove the ending summary about failures since that seems to confuse some
    # folks looking at logs (the data is all inline when it happened).
    if self.line_mode == XcodebuildFilter.LineMode.Unbuffered and \
        a_line == self.failures_start:
      self.line_mode = XcodebuildFilter.LineMode.DroppingFailures
      # Push an empty string for output to flush any info lines.
      self.PushLine(XcodebuildFilter.LineType.Raw, '')
      return
    if self.line_mode == XcodebuildFilter.LineMode.DroppingFailures:
      if self.failures_end_regex.match(a_line):
        self.line_mode = XcodebuildFilter.LineMode.Unbuffered
      return

    # Wasn't a header, direct the line based on the mode the filter is in.
    if self.line_mode == XcodebuildFilter.LineMode.BufferAsCommand:
      # Blank line moves to unbuffered.
      if a_line == '\n':
        self.line_mode = XcodebuildFilter.LineMode.Unbuffered
      else:
        self.PushLine(XcodebuildFilter.LineType.Command, a_line)
      return

    # By design, GYP generates some lines of output all the time. Save them
    # off as info lines so if they are the only output the command lines can
    # be skipped.
    if (a_line in self.gyp_info_lines) or \
       a_line.startswith(self.gyp_info_prefixes):
      self.PushLine(XcodebuildFilter.LineType.Info, a_line)
      return

    # Drop lines that are pure noise in the logs and never wanted.
    if (a_line == '\n') or (a_line in self.lines_to_drop):
      return

    # It's a keeper!
    self.PushLine(XcodebuildFilter.LineType.Raw, a_line)

  def FilterLine(self, a_line):
    """Called by RunCommand for each line of output."""
    # Log it
    if self.full_log_file:
      self.full_log_file.write(a_line)
    # Process it
    self.ProcessLine(a_line)
    # Return what ever we've got
    return self.AssembleOutput()

  def FilterDone(self, last_bits):
    """Called by RunCommand when the command is done."""
    # last_bits will be anything after the last newline, send it on raw to
    # flush out anything.
    self.PushLine(XcodebuildFilter.LineType.Raw, last_bits)
    return self.AssembleOutput()


def maybe_set_official_build_envvars(options, env):
  if options.mode == 'google_chrome' or options.mode == 'official':
    env['CHROMIUM_BUILD'] = '_google_chrome'

  if options.mode == 'official':
    # Official builds are always Google Chrome.
    env['CHROME_BUILD_TYPE'] = '_official'


def main_xcode(options, args):
  """Interprets options, clobbers object files, and calls xcodebuild.
  """

  env = EchoDict(os.environ)
  goma_ready = goma_setup(options, env)
  if not goma_ready:
    assert options.compiler not in ('goma', 'goma-clang')
    assert options.goma_dir is None

  # Print some basic information about xcodebuild to ease debugging.
  chromium_utils.RunCommand(['xcodebuild', '-sdk', '-version'], env=env)

  # If the project isn't in args, add all.xcodeproj to simplify configuration.
  command = ['xcodebuild', '-configuration', options.target]

  # TODO(mmoss) Support the old 'args' usage until we're confident the master is
  # switched to passing '--solution' everywhere.
  if not '-project' in args:
    # TODO(mmoss) Temporary hack to ignore the Windows --solution flag that is
    # passed to all builders. This can be taken out once the master scripts are
    # updated to only pass platform-appropriate --solution values.
    if (not options.solution or
        os.path.splitext(options.solution)[1] != '.xcodeproj'):
      options.solution = '../build/all.xcodeproj'
    command.extend(['-project', options.solution])

  if options.xcode_target:
    command.extend(['-target', options.xcode_target])

  # Note: this clobbers all targets, not just Debug or Release.
  if options.clobber:
    clobber_dir = os.path.dirname(options.target_output_dir)
    print('Removing %s' % clobber_dir)
    # Deleting output_dir would also delete all the .ninja files. iOS builds
    # generates ninja configuration inside the xcodebuild directory to be able
    # to run sub builds. crbug.com/138950 is tracking this issue.
    # Moreover clobbering should run before runhooks (which creates
    # .ninja files). For now, only delete all non-.ninja files.
    # TODO(thakis): Make "clobber" a step that runs before "runhooks". Once the
    # master has been restarted, remove all clobber handling from compile.py.
    ninja_clobber(clobber_dir)

  common_xcode_settings(command, options, env, options.compiler)
  maybe_set_official_build_envvars(options, env)

  # Add on any remaining args
  command.extend(args)

  # Set up the filter before changing directories so the raw build log can
  # be recorded.
  # Support a local file blocking filters (for debugging).  Also check the
  # Xcode version to make sure it is 3.2, as that is what the filter is coded
  # to.
  xcodebuild_filter = None
  no_filter_path = os.path.join(os.getcwd(), 'no_xcodebuild_filter')
  xcode_info = chromium_utils.GetCommandOutput(['xcodebuild', '-version'])
  if os.path.exists(no_filter_path):
    print 'NOTE: "%s" exists, output is unfiltered' % no_filter_path
  elif not xcode_info.startswith('Xcode 3.2.'):
    # Note: The filter sometimes hides real errors on 4.x+, see crbug.com/260989
    print 'NOTE: Not using Xcode 3.2, output is unfiltered'
  else:
    full_log_path = os.path.join(os.getcwd(), 'full_xcodebuild_log.txt')
    full_log = open(full_log_path, 'w')
    now = datetime.datetime.now()
    full_log.write('Build started ' + now.isoformat() + '\n\n\n')
    print 'NOTE: xcodebuild output filtered, full log at: "%s"' % full_log_path
    xcodebuild_filter = XcodebuildFilter(full_log)

  try:
    os.makedirs(options.build_dir)
  except OSError, e:
    if e.errno != errno.EEXIST:
      raise

  os.chdir(options.build_dir)

  # Run the build.
  env.print_overrides()
  result = chromium_utils.RunCommand(command, env=env,
                                     filter_obj=xcodebuild_filter)

  goma_teardown(options, env)

  return result


def common_make_settings(
    command, options, env, crosstool=None, compiler=None):
  """
  Sets desirable environment variables and command-line options that are used
  in the Make build.
  """
  assert compiler in (None, 'clang', 'goma', 'goma-clang', 'jsonclang')
  maybe_set_official_build_envvars(options, env)

  # Don't stop at the first error.
  command.append('-k')

  # Set jobs parallelization based on number of cores.
  jobs = os.sysconf('SC_NPROCESSORS_ONLN')

  # Test if we can use ccache.
  ccache = ''
  if chromium_utils.IsLinux():
    if os.path.exists('/usr/bin/ccache'):
      # The default CCACHE_DIR is $HOME/.ccache which, on some of our
      # bots, is over NFS.  This is intentional.  Talk to thestig or
      # mmoss if you have questions.
      ccache = 'ccache '

    # Setup crosstool environment variables.
    if crosstool:
      env['AR'] = crosstool + '-ar'
      env['AS'] = crosstool + '-as'
      env['CC'] = ccache + crosstool + '-gcc'
      env['CXX'] = ccache + crosstool + '-g++'
      env['LD'] = crosstool + '-ld'
      env['RANLIB'] = crosstool + '-ranlib'
      command.append('-j%d' % jobs)
      # Don't use build-in rules.
      command.append('-r')
      return

  if options.llvm_tsan:
    supp_path = os.path.join(options.src_dir,
      'tools', 'valgrind', 'tsan_v2', 'suppressions.txt')
    # Do not report thread leaks when running executables compiled with TSan.
    # Use the suppressions file to avoid reporting known errors during
    # compilation.
    # http://dev.chromium.org/developers/testing/threadsanitizer-tsan-v2
    # contains other options that might be worth adding.
    env['TSAN_OPTIONS'] = 'report_thread_leaks=0 suppressions=%s' % supp_path

  if compiler in ('goma', 'goma-clang', 'jsonclang'):
    print 'using', compiler
    if compiler == 'goma':
      assert options.goma_dir
      env['CC'] = 'gcc'
      env['CXX'] = 'g++'
      env['PATH'] = ':'.join([options.goma_dir, env['PATH']])
    elif compiler == 'goma-clang':
      assert options.goma_dir
      env['CC'] = 'clang'
      env['CXX'] = 'clang++'
      clang_dir = os.path.join(options.src_dir,
        'third_party', 'llvm-build', 'Release+Asserts', 'bin')
      env['PATH'] = ':'.join([options.goma_dir, clang_dir, env['PATH']])
    else:  # jsonclang
      env['CC'] = os.path.join(SLAVE_SCRIPTS_DIR, 'chromium', 'jsonclang')
      env['CXX'] = os.path.join(SLAVE_SCRIPTS_DIR, 'chromium', 'jsonclang++')
      command.append('-r')
      command.append('-k')
      # 'jsonclang' assumes the clang binary is in the path.
      clang_dir = os.path.join(options.src_dir,
        'third_party', 'llvm-build', 'Release+Asserts', 'bin')
      if options.goma_dir:
        env['PATH'] = ':'.join([options.goma_dir, clang_dir, env['PATH']])
      else:
        env['PATH'] = ':'.join([clang_dir, env['PATH']])

    command.append('CC.host=' + env['CC'])
    command.append('CXX.host=' + env['CXX'])

    goma_jobs = 50
    if jobs < goma_jobs:
      jobs = goma_jobs
    command.append('-j%d' % jobs)
    return

  if compiler == 'clang':
    clang_dir = os.path.join(options.src_dir,
        'third_party', 'llvm-build', 'Release+Asserts', 'bin')
    env['CC'] = os.path.join(clang_dir, 'clang')
    env['CXX'] = os.path.join(clang_dir, 'clang++')
    command.append('CC.host=' + env['CC'])
    command.append('CXX.host=' + env['CXX'])
    command.append('-r')

  command.append('-j%d' % jobs)


def main_make(options, args):
  """Interprets options, clobbers object files, and calls make.
  """

  env = EchoDict(os.environ)
  goma_ready = goma_setup(options, env)
  if not goma_ready:
    assert options.compiler not in ('goma', 'goma-clang')
    assert options.goma_dir is None

  command = ['make']
  # Try to build from <build_dir>/Makefile, or if that doesn't exist,
  # from the top-level Makefile.
  if os.path.isfile(os.path.join(options.build_dir, 'Makefile')):
    working_dir = options.build_dir
  else:
    working_dir = options.src_dir

  os.chdir(working_dir)
  common_make_settings(command, options, env, options.crosstool,
      options.compiler)

  # V=1 prints the actual executed command
  if options.verbose:
    command.extend(['V=1'])
  command.extend(options.build_args + args)

  # Run the build.
  env.print_overrides()
  result = 0

  def clobber():
    print('Removing %s' % options.target_output_dir)
    chromium_utils.RemoveDirectory(options.target_output_dir)

  assert ',' not in options.target, (
   'Used to allow multiple comma-separated targets for make. This should not be'
   ' in use any more. Asserting from orbit. It\'s the only way to be sure')

  if options.clobber:
    clobber()

  target_command = command + ['BUILDTYPE=' + options.target]
  result = chromium_utils.RunCommand(target_command, env=env)
  if result and not options.clobber:
    clobber()

  goma_teardown(options, env)

  return result

def main_make_android(options, args):
  """Interprets options, clobbers object files, and calls make.
  """

  env = EchoDict(os.environ)
  goma_ready = goma_setup(options, env)
  if not goma_ready:
    assert options.compiler not in ('goma', 'goma-clang')
    assert options.goma_dir is None

  command = ['make']
  if goma_ready:
    gomacc = os.path.join(options.goma_dir, 'gomacc')
    command.extend(['CC_WRAPPER=' + gomacc,
                    'CXX_WRAPPER=' + gomacc,
                    'JAVAC_WRAPPER=' + gomacc,
                    '-j150',
                    '-l%d' % os.sysconf('SC_NPROCESSORS_ONLN'),
                    ])

  working_dir = options.src_dir

  os.chdir(working_dir)

  # V=1 prints the actual executed command
  if options.verbose:
    command.extend(['V=1'])
  command.extend(options.build_args + args)

  # Run the build.
  env.print_overrides()
  result = 0

  def clobber():
    print('Removing %s' % options.target_output_dir)
    chromium_utils.RemoveDirectory(options.target_output_dir)

  # The Android.mk build system handles deps differently than the 'regular'
  # Chromium makefiles which can lead to targets not being rebuilt properly.
  # Fixing this is actually quite hard so we make this bot always clobber.
  clobber()

  result = chromium_utils.RunCommand(command, env=env)

  goma_teardown(options, env)

  return result

def main_ninja(options, args):
  """Interprets options, clobbers object files, and calls ninja."""

  # Prepare environment.
  env = EchoDict(os.environ)
  env.setdefault('NINJA_STATUS', '[%s/%t | %e] ')
  orig_compiler = options.compiler
  goma_ready = goma_setup(options, env)
  try:
    if not goma_ready:
      assert options.compiler not in ('goma', 'goma-clang')
      assert options.goma_dir is None

    # ninja is different from all the other build systems in that it requires
    # most configuration to be done at gyp time. This is why this function does
    # less than the other comparable functions in this file.
    print 'chdir to %s' % options.src_dir
    os.chdir(options.src_dir)

    command = ['ninja', '-C', options.target_output_dir]

    if options.clobber:
      print('Removing %s' % options.target_output_dir)
      # Deleting output_dir would also delete all the .ninja files necessary to
      # build. Clobbering should run before runhooks (which creates .ninja
      # files). For now, only delete all non-.ninja files.
      # TODO(thakis): Make "clobber" a step that runs before "runhooks".
      # Once the master has been restarted, remove all clobber handling
      # from compile.py.
      ninja_clobber(options.target_output_dir)

    if options.verbose:
      command.append('-v')
    command.extend(options.build_args)
    command.extend(args)

    maybe_set_official_build_envvars(options, env)

    if options.llvm_tsan:
      # Do not report thread leaks when running executables compiled with TSan.
      # http://dev.chromium.org/developers/testing/threadsanitizer-tsan-v2
      # contains other options that might be worth adding.
      env['TSAN_OPTIONS'] = 'report_thread_leaks=0'

    if options.compiler:
      print 'using', options.compiler

    if options.compiler in ('goma', 'goma-clang', 'jsonclang'):
      assert options.goma_dir
      if chromium_utils.IsWindows():
        # rewrite cc, cxx line in output_dir\build.ninja.
        # in winja, ninja -t msvc is used to run $cc/$cxx to collect
        # dependency with "cl /showIncludes" and generates dependency info.
        # ninja -t msvc uses environment in output_dir\environment.*,
        # which is generated at gyp time (Note: gyp detect MSVC's path and set
        # it to PATH.  This PATH doesn't include goma_dir.), and ignores PATH
        # to run $cc/$cxx at run time.
        # So modifying PATH in compile.py doesn't afffect to run $cc/$cxx
        # under ninja -t msvc. (PATH is just ignored. Note PATH set/used
        # in compile.py doesn't include MSVC's path).
        # Hence, we'll got
        # "CreateProcess failed: The system cannot find the file specified."
        #
        # So, rewrite cc, cxx line to "$goma_dir/gomacc cl".
        #
        # Note that, on other platform, ninja doesn't use ninja -t msvc
        # (it just simply run $cc/$cxx), so modifying PATH can work to run
        # gomacc without this hack.
        #
        # Another option is to use CC_wrapper, CXX_wrapper environement
        # variables at gyp time (and this is typical usage for chromium
        # developers), but it would make it harder to fallback no-goma when
        # goma is not available.
        # TODO: Set CC / CXX at gyp time instead. This is a horrible hack.
        manifest = os.path.join(options.target_output_dir, 'build.ninja')
        orig_manifest = manifest + '.orig'
        if os.path.exists(orig_manifest):
          os.remove(orig_manifest)
        os.rename(manifest, orig_manifest)
        cc_line_pattern = re.compile(
            r'(cc|cxx|cc_host|cxx_host|cl_x86|cl_x64) = (.*)')
        gomacc = os.path.join(options.goma_dir, 'gomacc.exe')
        modified_lines = []
        with open(orig_manifest) as orig_build:
          with open(manifest, 'w') as new_build:
            for line in orig_build:
              m = cc_line_pattern.match(line)
              if m:
                cc_type = m.group(1)
                cc_cmd = m.group(2).strip()
                # use gomacc if cc_cmd is simple command (e.g. cl.exe), or
                # quoted full path (e.g. "c:\Program Files\...").
                if not ' ' in cc_cmd or re.match('^"[^"]+"$', cc_cmd):
                  orig_line = line
                  line = '%s = %s %s\n' % (cc_type, gomacc, cc_cmd)
                  modified_lines.append((orig_line, line))
              new_build.write(line)
        if modified_lines:
          print 'build.ninja modified in compile.py for goma:\n'
          for (orig_line, line) in modified_lines:
            sys.stdout.write('    ' + orig_line)
            sys.stdout.write(' -> ' + line)

      # CC and CXX are set at gyp time for ninja. PATH still needs to be
      # adjusted.
      if options.compiler == 'goma':
        env['PATH'] = os.pathsep.join([options.goma_dir, env['PATH']])
      elif options.compiler == 'goma-clang':
        clang_dir = os.path.abspath(os.path.join(
            'third_party', 'llvm-build', 'Release+Asserts', 'bin'))
        env['PATH'] = os.pathsep.join(
            [options.goma_dir, clang_dir, env['PATH']])
      elif options.compiler ==  'jsonclang':
        jsonclang_dir = os.path.join(SLAVE_SCRIPTS_DIR, 'chromium')
        clang_dir = os.path.join(options.src_dir,
            'third_party', 'llvm-build', 'Release+Asserts', 'bin')
        if options.goma_dir:
          env['PATH'] = os.pathsep.join(
              [jsonclang_dir, options.goma_dir, clang_dir, env['PATH']])
        else:
          env['PATH'] = os.pathsep.join([jsonclang_dir, clang_dir, env['PATH']])

      def determine_goma_jobs():
        # We would like to speed up build on Windows a bit, since it is slowest.
        number_of_processors = 0
        try:
          number_of_processors = multiprocessing.cpu_count()
        except NotImplementedError:
          print 'cpu_count() is not implemented, using default value'

        # When goma is used, 10 * number_of_processors is almost suitable
        # for -j value. Actually -j value was originally 100 for Linux and
        # Windows. But when goma was overloaded, it was reduced to 50.
        # Actually, goma server could not cope with burst request correctly
        # that time. Currently the situation got better a bit. The goma server
        # is now able to treat such requests well to a certain extent.
        # However, for safety, let's limit incrementing -j value only for
        # Windows now, since it's slowest.
        # Note that currently most try-bot build slaves have 8 processors.
        if chromium_utils.IsMac():
          # On mac, due to the process number limit, we're using 50.
          return 50
        elif chromium_utils.IsWindows() and number_of_processors > 0:
          return min(10 * number_of_processors, 200)
        else:
          return 50

      goma_jobs = determine_goma_jobs()
      command.append('-j%d' % goma_jobs)

      if chromium_utils.IsMac():
        # Work around for crbug.com/347918
        env['GOMA_HERMETIC'] = 'fallback'
        if options.clobber:
          # Enabling this while attempting to solve crbug.com/257467
          env['GOMA_USE_LOCAL'] = '1'

    if orig_compiler == 'goma-clang' and options.compiler == 'clang':
      # goma setup failed, fallback to local clang.
      # Note that ninja.build was generated for goma, so need to set PATH
      # to clang dir.
      # If orig_compiler is not goma, gyp set this path in ninja.build.
      print 'using', options.compiler
      clang_dir = os.path.abspath(os.path.join(
          'third_party', 'llvm-build', 'Release+Asserts', 'bin'))
      env['PATH'] = os.pathsep.join([clang_dir, env['PATH']])

    # Run the build.
    env.print_overrides()
    # TODO(maruel): Remove the shell argument as soon as ninja.exe is in PATH.
    # At the moment of writing, ninja.bat in depot_tools wraps
    # third_party\ninja.exe, which requires shell=True so it is found correctly.
    return chromium_utils.RunCommand(
        command, env=env, shell=sys.platform=='win32')
  finally:
    goma_teardown(options, env)


def main_win(options, args):
  """Interprets options, clobbers object files, and calls the build tool.
  """
  if not options.solution:
    options.solution = 'all.sln'
  solution = os.path.join(options.build_dir, options.solution)

  # Prefer the version specified in the .sln. When devenv.com is used at the
  # command line to start a build, it doesn't accept sln file from a different
  # version.
  if not options.msvs_version:
    sln = open(os.path.join(solution), 'rU')
    header = sln.readline().strip()
    sln.close()
    if header.endswith('13.00'):
      options.msvs_version = '12'
    elif header.endswith('12.00'):
      options.msvs_version = '11'
    elif header.endswith('11.00'):
      options.msvs_version = '10'
    elif header.endswith('10.00'):
      options.msvs_version = '9'
    elif header.endswith('9.00'):
      options.msvs_version = '8'
    else:
      print >> sys.stderr, "Unknown sln header:\n" + header
      return 1

  REG_ROOT = 'SOFTWARE\\Microsoft\\VisualStudio\\'
  devenv = ReadHKLMValue(REG_ROOT + options.msvs_version + '.0', 'InstallDir')
  if devenv:
    devenv = os.path.join(devenv, 'devenv.com')
  else:
    print >> sys.stderr, ("MSVS %s was requested but is not installed." %
        options.msvs_version)
    return 1

  ib = ReadHKLMValue('SOFTWARE\\Xoreax\\IncrediBuild\\Builder', 'Folder')
  if ib:
    ib = os.path.join(ib, 'BuildConsole.exe')

  if ib and os.path.exists(ib) and not options.no_ib:
    tool = ib
    if options.arch == 'x64':
      tool_options = ['/Cfg=%s|x64' % options.target]
    else:
      tool_options = ['/Cfg=%s|Win32' % options.target]
    if options.project:
      tool_options.extend(['/Prj=%s' % options.project])
  else:
    tool = devenv
    if options.arch == 'x64':
      tool_options = ['/Build', '%s|x64' % options.target]
    else:
      tool_options = ['/Build', options.target]
    if options.project:
      tool_options.extend(['/Project', options.project])

  def clobber():
    print('Removing %s' % options.target_output_dir)
    chromium_utils.RemoveDirectory(options.target_output_dir)

  if options.clobber:
    clobber()
  else:
    # Remove the log file so it doesn't grow without limit,
    chromium_utils.RemoveFile(options.target_output_dir, 'debug.log')
    # Remove the chrome.dll version resource so it picks up the new svn
    # revision, unless user explicitly asked not to remove it. See
    # Bug 1064677 for more details.
    if not options.keep_version_file:
      chromium_utils.RemoveFile(options.target_output_dir, 'obj', 'chrome_dll',
                                'chrome_dll_version.rc')

  env = EchoDict(os.environ)

  # no goma support yet for this build tool.
  assert options.compiler != 'goma'

  maybe_set_official_build_envvars(options, env)

  result = -1
  command = [tool, solution] + tool_options + args
  errors = []
  # Examples:
  # midl : command line error MIDL1003 : error returned by the C
  #   preprocessor (-1073741431)
  #
  # Error executing C:\PROGRA~2\MICROS~1\Common7\Tools\Bin\Midl.Exe (tool
  #    returned code: 1282)
  #
  # ---
  #
  # cl : Command line error D8027 : cannot execute 'C:\Program Files
  #    (x86)\Microsoft Visual Studio 8\VC\bin\c2.dll'
  #
  # ---
  #
  # Warning: Could not delete file "c:\b\slave\win\build\src\build\Debug\
  #    chrome.dll" : Access is denied
  # --------------------Build System Warning--------------------------------
  #    -------
  # Could not delete file:
  #     Could not delete file "c:\b\slave\win\build\src\build\Debug\
  #        chrome.dll" : Access is denied
  #     (Automatically running xgHandle on first 10 files that could not be
  #        deleted)
  #     Searching for '\Device\HarddiskVolume1\b\slave\win\build\src\build\
  #        Debug\chrome.dll':
  #     No handles found.
  #     (xgHandle utility returned code: 0x00000000)
  #
  # ---
  #
  # webkit.lib(WebGeolocationError.obj) : fatal error LNK1318: Unexpected PDB
  # error; OK (0) ''
  #
  # Error executing link.exe (tool returned code: 1318)
  #
  # ---
  #
  # browser.lib(background_application_list_model.obj) : fatal error LNK1000:
  # Internal error during IMAGE::Pass2
  # (along with a register dump)
  #
  # ---
  #
  # ...\browser\history\download_create_info.cc : fatal error C1033: cannot open
  #   program database '...\src\build\debug\obj\browser\browser\vc80_ib_2.idb'
  #
  # ---
  #
  # --------------------Build System Error (Agent 'Ib1 (CPU 1)')----------------
  # Fatalerror:
  #     Failed to execute command: extension_function_registry (ID 1591)
  #     Failed to update directory: E:\b\build\slave\win\build\src\build\Release
  #     File table management has failed.
  #     Shared stream group lock abandoned, marking as corrupt
  #     --------
  #     Unable to complete operation (retried 10 times): cl: foo.cc -> foo.obj

  known_toolset_bugs = [
    '\\c2.dll',
    'Midl.Exe (tool returned code: 1282)',
    'LINK : fatal error LNK1102: out of memory',
    'fatal error LNK1318: Unexpected PDB error',
    'fatal error LNK1000: Internal error during IMAGE::Pass2',
    'fatal error C1033',
    'Build System Error',
  ]
  def scan(line):
    for known_line in known_toolset_bugs:
      if known_line in line:
        errors.append(line)
        break

  env.print_overrides()
  result = chromium_utils.RunCommand(
      command, parser_func=scan, env=env, universal_newlines=True)
  if errors:
    print('\n\nRetrying a clobber build because of:')
    print('\n'.join(('  ' + l for l in errors)))
    print('Removing %s' % options.target_output_dir)
    for _ in range(3):
      try:
        chromium_utils.RemoveDirectory(options.target_output_dir)
        break
      except OSError, e:
        print(e)
        print('\nSleeping 15 seconds. Lovely windows file locks.')
        time.sleep(15)
    else:
      print('Failed to delete a file 3 times in a row, aborting.')
      return 1
    result = chromium_utils.RunCommand(command, env=env)

  # TODO(maruel): As soon as the try server is restarted, replace with:
  # if result and not options.clobber and options.clobber_post_fail:
  if result and not options.clobber:
    clobber()

  return result


def landmines_triggered(build_dir):
  trigger_file = os.path.join(build_dir, '.landmines_triggered')
  if os.path.exists(trigger_file):
    print 'Setting clobber due to triggered landmines:'
    with open(trigger_file) as f:
      print f.read()
    return True
  return False


def get_target_build_dir(build_tool, src_dir, target, is_iphone=False):
  """Keep this function in sync with src/build/landmines.py"""
  ret = None
  if build_tool == 'xcode':
    ret = os.path.join(src_dir, 'xcodebuild',
        target + ('-iphoneos' if is_iphone else ''))
  elif build_tool in ['make', 'ninja']:
    ret = os.path.join(src_dir, 'out', target)
  elif build_tool == 'make-android':
    ret = os.path.join(src_dir, 'out')
  elif build_tool in ['vs', 'ib']:
    ret = os.path.join(src_dir, 'build', target)
  else:
    raise NotImplementedError()
  return os.path.abspath(ret)


def real_main():
  option_parser = optparse.OptionParser()
  option_parser.add_option('--clobber', action='store_true', default=False,
                           help='delete the output directory before compiling')
  option_parser.add_option('--clobber-post-fail', action='store_true',
                           default=False,
                           help='delete the output directory after compiling '
                                'only if it failed. Do not affect ninja.')
  option_parser.add_option('--keep-version-file', action='store_true',
                           default=False,
                           help='do not delete the chrome_dll_version.rc file '
                                'before compiling (ignored if --clobber is '
                                'used')
  option_parser.add_option('--target', default='Release',
                           help='build target (Debug or Release)')
  option_parser.add_option('--arch', default=None,
                           help='target architecture (ia32, x64, ...')
  option_parser.add_option('--solution', default=None,
                           help='name of solution/sub-project to build')
  option_parser.add_option('--project', default=None,
                           help='name of project to build')
  option_parser.add_option('--build-dir', help='ignored')
  option_parser.add_option('--src-dir', default=None,
                           help='path to the root of the source tree')
  option_parser.add_option('--mode', default='dev',
                           help='build mode (dev or official) controlling '
                                'environment variables set during build')
  option_parser.add_option('--build-tool', default=None,
                           help='specify build tool (ib, vs, xcode)')
  option_parser.add_option('--build-args', action='append', default=[],
                           help='arguments to pass to the build tool')
  option_parser.add_option('--compiler', default=None,
                           help='specify alternative compiler (e.g. clang)')
  if chromium_utils.IsWindows():
    # Windows only.
    option_parser.add_option('--no-ib', action='store_true', default=False,
                             help='use Visual Studio instead of IncrediBuild')
    option_parser.add_option('--msvs_version',
                             help='VisualStudio version to use')
  # For linux to arm cross compile.
  option_parser.add_option('--crosstool', default=None,
                           help='optional path to crosstool toolset')
  option_parser.add_option('--llvm-tsan', action='store_true',
                           default=False,
                           help='build with LLVM\'s ThreadSanitizer')
  if chromium_utils.IsMac():
    # Mac only.
    option_parser.add_option('--xcode-target', default=None,
                             help='Target from the xcodeproj file')
  option_parser.add_option('--goma-dir',
                           default=os.path.join(BUILD_DIR, 'goma'),
                           help='specify goma directory')
  option_parser.add_option('--verbose', action='store_true')

  options, args = option_parser.parse_args()

  if not options.src_dir:
    options.src_dir = 'src'
  options.src_dir = os.path.abspath(options.src_dir)

  options.build_dir = os.path.abspath(build_directory.GetBuildOutputDirectory(
        os.path.basename(options.src_dir)))

  if options.build_tool is None:
    if chromium_utils.IsWindows():
      # We're in the process of moving to ninja by default on Windows, see
      # http://crbug.com/303291.
      if build_directory.AreNinjaFilesNewerThanMSVSFiles(
          src_dir=options.src_dir):
        main = main_ninja
        options.build_tool = 'ninja'
        if options.project:
          args += [options.project]
      else:
        main = main_win
        options.build_tool = 'vs'
    elif chromium_utils.IsMac():
      # We're in the process of moving to ninja by default on Mac, see
      # http://crbug.com/294387
      # Builders for different branches will use either xcode or ninja depending
      # on the release channel for a while. Until all release channels are on
      # ninja, use build file mtime to figure out which build system to use.
      # TODO(thakis): Just use main_ninja once the transition is complete.
      if build_directory.AreNinjaFilesNewerThanXcodeFiles(
          src_dir=options.src_dir):
        main = main_ninja
        options.build_tool = 'ninja'

        # There is no standard way to pass a build target (such as 'base') to
        # compile.py. --target specifies Debug or Release. --project could do
        # that, but it's only supported by the msvs build tool at the moment.
        # Because of that, most build masters pass additional options to the
        # build tool to specify the build target. For xcode, these are in the
        # form of '-project blah.xcodeproj -target buildtarget'. Translate these
        # into ninja options, if needed.
        xcode_option_parse = optparse.OptionParser()
        xcode_option_parse.add_option('--project')
        xcode_option_parse.add_option('--target', action='append', default=[])
        xcode_options, xcode_args = xcode_option_parse.parse_args(
            [re.sub('^-', '--', a) for a in args])  # optparse wants --options.
        args = xcode_options.target + xcode_args
      else:
        main = main_xcode
        options.build_tool = 'xcode'
    elif chromium_utils.IsLinux():
      main = main_ninja
      options.build_tool = 'ninja'
    else:
      print('Please specify --build-tool.')
      return 1
  else:
    build_tool_map = {
        'ib' : main_win,
        'vs' : main_win,
        'make' : main_make,
        'make-android' : main_make_android,
        'ninja' : main_ninja,
        'xcode' : main_xcode,
    }
    main = build_tool_map.get(options.build_tool)
    if not main:
      sys.stderr.write('Unknown build tool %s.\n' % repr(options.build_tool))
      return 2

  options.target_output_dir = get_target_build_dir(options.build_tool,
      options.src_dir, options.target, 'iphoneos' in args)
  options.clobber = (options.clobber or
      landmines_triggered(options.target_output_dir))

  return main(options, args)


if '__main__' == __name__:
  sys.exit(real_main())
