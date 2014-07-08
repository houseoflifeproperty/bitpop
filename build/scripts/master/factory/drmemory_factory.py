# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import ntpath
import posixpath
import re
from buildbot.process import factory
from buildbot.process.properties import WithProperties
from buildbot.steps.source import SVN
from buildbot.steps.shell import Compile
from buildbot.steps.shell import Configure
from buildbot.steps.shell import ShellCommand
from buildbot.steps.shell import SetProperty
from buildbot.steps.shell import Test
from buildbot.steps.transfer import DirectoryUpload
from buildbot.steps.transfer import FileUpload
from buildbot.steps.transfer import FileDownload
from buildbot.status.builder import SUCCESS, WARNINGS, FAILURE

from master.factory import v8_factory

LATEST_WIN_BUILD = 'public_html/builds/drmemory-windows-latest-sfx.exe'

dr_svnurl = 'http://dynamorio.googlecode.com/svn/trunk'
drm_svnurl = 'http://drmemory.googlecode.com/svn/trunk'
bot_tools_svnurl = 'http://drmemory.googlecode.com/svn/buildbot/bot_tools'

# TODO(rnk): Don't make assumptions about absolute path layout.  This won't work
# on bare metal bots.  We can't use a relative path because we often configure
# builds at different directory depths.
WIN_BUILD_ENV_PATH = r'E:\b\build\scripts\slave\drmemory\build_env.bat'

# These tests are ordered roughly from shortest to longest so failure is
# reported earlier.
LINUX_CHROME_TESTS = [
  'content_shell',
  'base_unittests',
  'browser_tests',
  'crypto_unittests',
  'ipc_tests',
  'media_unittests',
  'net_unittests',
  'printing_unittests',
  'remoting_unittests',
  'sql_unittests',
  'unit_tests',
  'url_unittests',
]


def WindowsToOs(windows):
  """Takes a boolean windows value and returns a platform string."""
  if windows:
    return 'windows'
  else:
    return 'linux'


def OsFullName(platform):
  if platform.startswith('win'):
    return 'Windows'
  elif platform.startswith('linux'):
    return 'Linux'
  else:
    raise ValueError('Unknown platform %s' % platform)


def OsShortName(platform):
  if platform.startswith('win'):
    return 'win'
  elif platform.startswith('linux'):
    return 'linux'
  else:
    raise ValueError('Unknown platform %s' % platform)


def ArchToBits(arch):
  """Takes an arch string like x64 and ia32 and returns its bitwidth."""
  if not arch:  # Default to x64.
    return 64
  elif arch == 'x64':
    return 64
  elif arch == 'ia32':
    return 32
  assert False, 'Unsupported architecture'


class DrCommands(object):

  """Encapsulates state for adding commands to BuildFactories.

  Encapsulates the two things that we really need to pass everywhere: the
  BuildFactory and the target platform.
  """

  def __init__(self, target_platform=None, os_version=None, build_factory=None):
    if not build_factory:
      build_factory = factory.BuildFactory()
    self.factory = build_factory
    self.target_platform = OsShortName(target_platform)
    self.os_version = os_version

  def IsWindows(self):
    """Returns true if we're targetting Windows."""
    return self.target_platform.startswith('win')

  def PathJoin(self, *args):
    """Join paths using the separator of the os of the bot."""
    if self.IsWindows():
      return ntpath.normpath(ntpath.join(*args))
    else:
      return posixpath.normpath(posixpath.join(*args))

  def AddStep(self, step_class, **kwargs):
    """Adds a regular buildbot step."""
    self.factory.addStep(step_class(**kwargs))

  def AddToolStep(self, step_class, **kwargs):
    """Adds a buildbot step that uses one of our custom tools.

    Currently this includes cmake, ctest, and 7zip.
    """
    self.factory.addStep(ToolStep(step_class, self.target_platform, **kwargs))

  def AddDynamoRIOSource(self):
    """Checks out or updates DR's sources."""
    self.AddStep(SVN,
                 svnurl=dr_svnurl,
                 workdir='dynamorio',
                 mode='update',
                 name='Checkout DynamoRIO')

  def AddDrMemorySource(self):
    """Checks out or updates drmemory's sources."""
    self.AddStep(SVN,
                 svnurl=drm_svnurl,
                 workdir='drmemory',
                 mode='update',
                 name='Checkout Dr. Memory')

  def AddTools(self):
    """Add steps to update and unpack drmemory's custom tools."""
    if self.target_platform.startswith('win'):
      # Using a SVN step breaks the console view because bb thinks we're at a
      # different revision.  Therefore we run the checkout command manually.
      self.AddStep(ShellCommand,
                   command=['svn', 'checkout', '--force',
                            bot_tools_svnurl, '.'],
                   workdir='bot_tools',
                   description='update tools',
                   name='update tools')
      self.AddStep(ShellCommand,
                   command=['unpack.bat'],
                   workdir='bot_tools',
                   name='unpack tools',
                   description='unpack tools')

  def AddFindFileIntoPropertyStep(self, pattern, property_name):
    """Finds a file on the slave and stores the name in property_name.

    TODO(rnk): This won't work if pattern matches more than one file.
    """
    if self.IsWindows():
      ls_cmd = 'dir /B'  # /B means "bare", like ls with no -l.
    else:
      ls_cmd = 'ls'
    self.AddStep(SetProperty,
                 name='find package file',
                 description='find package file',
                 # Use a string command here to let the shell expand *.
                 command=WithProperties(ls_cmd + ' ' + pattern),
                 property=property_name)

  def AddDRSuite(self, step_name, suite_args):
    """Run DR's test suite with arguments."""
    timeout = 20 * 60  # 20min w/o output.  10 is too short for Windows.
    runsuite_cmd = '../dynamorio/suite/runsuite.cmake'
    if suite_args:
      runsuite_cmd += ',' + suite_args
    cmd = ['ctest', '--timeout', '120', '-VV', '-S', runsuite_cmd]
    self.AddToolStep(CTest,
                     command=cmd,
                     name=step_name,
                     descriptionDone=step_name,
                     timeout=timeout)

  def AddDRBuild(self, target, target_arch):
    """Build a single configuration of DR."""
    cflags = '-m%s' % ArchToBits(target_arch)
    cmake_env = {'CFLAGS': cflags, 'CXXFLAGS': cflags}
    debug = 'OFF'
    if target == 'Debug':
      debug = 'ON'
    self.AddToolStep(Configure,
                     command=['cmake', '..', '-DDEBUG=' + debug],
                     workdir='dynamorio/build',
                     name='Configure %s %s DynamoRIO' % (target, target_arch),
                     env=cmake_env)
    assert not self.IsWindows(), "windows AddDRBuild NYI"
    self.AddToolStep(Compile,
                     command=['make', '-j5'],
                     workdir='dynamorio/build',
                     name='Compile %s %s DynamoRIO' % (target, target_arch))

  def AddTSanTestBuild(self):
    self.AddStep(ShellCommand,
                 command=['svn', 'checkout', '--force',
                          'http://data-race-test.googlecode.com/svn/trunk/',
                          '../tsan'],
                 name='Checkout TSan tests',
                 description='checkout tsan tests')
    self.AddToolStep(ShellCommand,
                     command=['make', '-C', '../tsan/unittest'],
                     # suppress cygwin 'MSDOS' warnings
                     env={'CYGWIN': 'nodosfilewarning'},
                     name='Build TSan tests',
                     descriptionDone='build tsan tests',
                     description='build tsan tests')

  def DynamoRIOSuite(self):
    """Build and test all configurations in the DR pre-commit suite."""
    self.AddDynamoRIOSource()
    self.AddTools()
    self.AddDRSuite('pre-commit suite', '')
    # The Linux bot has all the dependencies for docs generation, so we have it
    # upload the docs to the master.
    if self.target_platform == 'linux':
      self.AddStep(DirectoryUpload,
                   slavesrc='install/docs/html',
                   masterdest='public_html/dr_docs')
    return self.factory

  def DynamoRIONightly(self):
    """Build and test all configurations in the DR nightly suite."""
    self.AddDynamoRIOSource()
    self.AddTools()
    site_name = '%s.%s.BuildBot' % (OsFullName(self.target_platform),
                                    self.os_version.capitalize())
    suite_args = 'nightly;long;site=%s' % site_name
    self.AddDRSuite('nightly suite', suite_args)
    return self.factory

  def DynamoRIOPackage(self):
    """Build, package, and upload all configurations of DR."""
    self.AddDynamoRIOSource()
    self.AddTools()
    package_cmd = '../dynamorio/make/package.cmake,build=42'
    cmd = ['ctest', '-VV', '-S', package_cmd]
    self.AddToolStep(ShellCommand,
                     command=cmd,
                     description='Package DynamoRIO',
                     name='Package DynamoRIO')
    # For DR, we use plain cpack archives since we don't have existing scripts
    # that expect sfx exes.
    if self.IsWindows():
      src_file = 'DynamoRIO-Windows-*.%(got_revision)s-42.zip'
      dst_file = 'dynamorio-windows-r%(got_revision)s.zip'
    else:
      src_file = 'DynamoRIO-Linux-*.%(got_revision)s-42.tar.gz'
      dst_file = 'dynamorio-linux-r%(got_revision)s.tar.gz'
    self.AddFindFileIntoPropertyStep(src_file, 'package_name')
    self.AddStep(FileUpload,
                 slavesrc=WithProperties('%(package_name)s'),
                 masterdest=WithProperties('public_html/builds/' + dst_file),
                 name='Upload DR package')
    return self.factory

  def DrMemorySuite(self):
    """Build and test all configurations in the drmemory pre-commit suite."""
    self.AddDrMemorySource()
    self.AddStep(SetProperty,
                 command=['svnversion', '../drmemory/dynamorio'],
                 property='dr_revision',
                 name='Get DR revision',
                 descriptionDone='Get DR revision',
                 description='DR revision')
    self.AddTools()
    cmd = ['ctest', '--timeout', '60', '-VV', '-S',
           WithProperties('../drmemory/tests/runsuite.cmake,' +
                          'drmemory_only;build=%(buildnumber)s')]
    self.AddToolStep(CTest,
                     command=cmd,
                     name='Dr. Memory ctest',
                     descriptionDone='runsuite',
                     # failure doesn't mark the whole run as failure
                     flunkOnFailure=False,
                     warnOnFailure=True,
                     timeout=600)
    return self.factory

  def DrMemoryPackage(self):
    """Build the drmemory package."""
    self.AddDrMemorySource()
    self.AddTools()
    # The default package name has the version and revision, so we override it
    # to something we can predict.  package.cmake will complain if this does not
    # start with 'DrMemory-'
    # TODO(rnk): Instead of overriding the package name, have package.cmake
    # output the name to stderr or in a symlink.
    package_name = 'DrMemory-package'
    cpack_arg = 'cpackappend=set(CPACK_PACKAGE_FILE_NAME "%s")' % package_name
    cmd = ['ctest', '-VV', '-S', '../drmemory/package.cmake,build=42;' +
           cpack_arg]
    self.AddToolStep(ShellCommand,
                     command=cmd,
                     description='Package Dr. Memory',
                     name='Package Dr. Memory')
    if self.IsWindows():
      # For Windows, our chromium scripts expect to find an sfx, so we figure
      # out where cpack installed everything before archiving it, and re-archive
      # it with 7z -sfx.
      install_dir = ('build_drmemory-debug-32\\' +
                     '_CPack_Packages\\Windows\\ZIP\\' + package_name)
      sfx_file = 'drmemory-windows-r%(got_revision)s-sfx.exe'
      dst_file = sfx_file
      src_file = self.PathJoin(install_dir, sfx_file)
      self.AddToolStep(ShellCommand,
                       command=['7z', 'a', '-sfx',
                                WithProperties(sfx_file), '*'],
                       workdir='build\\' + install_dir,
                       haltOnFailure=True,
                       name='create sfx archive',
                       description='create sfx archive')
      self.AddStep(FileUpload,
                   slavesrc=WithProperties(src_file),
                   masterdest=LATEST_WIN_BUILD,
                   name='upload latest build')
    else:
      # For Linux, we just use the tgz that cpack made for us.
      src_file = package_name + '.tar.gz'
      dst_file = 'drmemory-linux-r%(got_revision)s.tar.gz'
    self.AddStep(FileUpload,
                 slavesrc=WithProperties(src_file),
                 masterdest=WithProperties('public_html/builds/' + dst_file),
                 name='upload revision build')
    return self.factory

  def AddTSanTestConfig(self, build_mode, run_mode, use_syms=True, **kwargs):
    """Add a test of a single drmemory config on the tsan tests."""
    app_cmd = [('..\\tsan\\unittest\\bin\\'
                'racecheck_unittest-windows-x86-O0.exe'),
               ('--gtest_filter="-PositiveTests.FreeVsRead'
                ':NegativeTests.WaitForMultiple*"'),
               '-147']
    # Pick exe from build mode.
    if self.IsWindows():
      cmd = ['build_drmemory-%s-32\\bin\\drmemory' % build_mode]
    else:
      cmd = ['build_drmemory-%s-32/bin/drmemory.pl' % build_mode]
    # Default flags turn off message boxes, notepad, and print to stderr.
    cmd += ['-dr_ops', '-msgbox_mask 0 -stderr_mask 15',
            '-results_to_stderr', '-batch']
    if self.IsWindows():
      # FIXME: The point of these app tests is to verify that we get no false
      # positives on well-behaved applications, so we should remove these
      # extra suppressions.  We're not using them on dev machines but we'll
      # leave them on the bots and for tsan tests for now.
      cmd += ['-suppress',
              '..\\drmemory\\tests\\app_suite\\default-suppressions.txt']
    # Full mode flags are default, light mode turns off uninits and leaks.
    if run_mode == 'light':
      cmd += ['-light']
    cmd.append('--')
    cmd += app_cmd
    # Set _NT_SYMBOL_PATH appropriately.
    syms_part = ''
    env = {}
    if not use_syms:
      syms_part = 'nosyms '
      if self.IsWindows():
        env['_NT_SYMBOL_PATH'] = ''
    step_name = '%s %s %sTSan tests' % (build_mode, run_mode, syms_part)
    self.AddToolStep(DrMemoryTest,
                     command=cmd,
                     env=env,
                     name=step_name,
                     descriptionDone=step_name,
                     description='run ' + step_name,
                     **kwargs)

  def AddDrMemoryTSanTests(self):
    """Run the tsan tests in a variety of configs."""
    assert self.IsWindows()
    # Run tsan tests in (dbg, rel) cross (full, light).
    for build_mode in ('dbg', 'rel'):
      for run_mode in ('full', 'light'):
        self.AddTSanTestConfig(build_mode, run_mode, use_syms=True)
    # Do one more run of TSan + app_suite without any pdb symbols to make
    # sure our default suppressions match.
    self.AddTSanTestConfig('dbg', 'full', use_syms=False)

  def AddDrMemoryLogsUpload(self):
    """Upload drmemory's logs after running the suite and the app tests."""
    # TODO(rnk): What would make this *really* useful for reproducing bot issues
    # is if we had a way of forcing a build with higher logging.
    if self.IsWindows():
      del_cmd = ['del']
    else:
      del_cmd = ['rm', '-f']
    self.AddStep(ShellCommand,
                 command=del_cmd + ['testlogs.7z'],
                 haltOnFailure=False,
                 flunkOnFailure=False,
                 warnOnFailure=True,
                 name='Prepare to pack test results',
                 description='cleanup')
    testlog_dirs = ['build_drmemory-dbg-32/logs',
                    'build_drmemory-dbg-32/Testing/Temporary',
                    'build_drmemory-rel-32/logs',
                    'build_drmemory-rel-32/Testing/Temporary',
                    'build_drmemory-dbg-64/logs',
                    'build_drmemory-dbg-64/Testing/Temporary',
                    'build_drmemory-rel-64/logs',
                    'build_drmemory-rel-64/Testing/Temporary']
    if self.IsWindows():
      testlog_dirs += ['xmlresults']
    else:
      testlog_dirs += ['xml:results']
    self.AddToolStep(ShellCommand,
                     command=['7z', 'a', 'testlogs.7z'] + testlog_dirs,
                     haltOnFailure=True,
                     name='Pack test results',
                     description='pack results')
    self.AddStep(FileUpload,
                 slavesrc='testlogs.7z',
                 masterdest=WithProperties(
                     'public_html/testlogs/' +
                     'from_%(buildername)s/testlogs_r%(got_revision)s_b' +
                     '%(buildnumber)s.7z'),
                 name='Upload test logs to the master')


class CTest(Test):

  """BuildStep that parses DR's runsuite output."""

  def __init__(self, **kwargs):
    self.__result = None
    Test.__init__(self, **kwargs)

  def createSummary(self, log):
    passed_count = 0
    failure_count = 0
    flaky_count = 0

    summary_lines = []
    found_summary = False
    # Don't use 'readlines' because we want both stdout and stderr.
    for line in log.getText().split('\n'):
      if line.strip() == 'RESULTS':
        assert not found_summary, 'Found two summaries!'
        found_summary = True
      if found_summary:
        summary_lines.append(line)
        # We try to recognize every line of the summary, because
        # if we fail to match the failure count line we might stay
        # green when we should be red.
        if line.strip() == 'RESULTS':
          continue  # Start of summary line
        if not line.strip():
          continue  # Blank line
        if re.match('^\t', line):
          continue  # Test failure lines start with tabs
        if 'build successful; no tests for this build' in line:
          continue  # Successful build with no tests
        if 'Error in read script' in line:
          continue  # DR i#636: Spurious line from ctest

        # All tests passed for this config.
        match = re.search('all (?P<passed>\d+) tests passed', line)
        if match:
          passed_count += int(match.group('passed'))
          continue

        # Some tests failed in this config.
        match = re.match(r'^[^:]*: (?P<passed>\d+) tests passed, '
                          '\*\*\*\* (?P<failed>\d+) tests failed'
                          '(, of which (?P<flaky>\d+) were flaky)?:',
                         line)
        if match:
          passed_count += int(match.group('passed'))
          failure_count += int(match.group('failed'))
          num_flaky_str = match.group('flaky')
          if num_flaky_str:
            flaky_count += int(num_flaky_str)
        else:
          # Add a fake failure so we get notified.  Put the warning
          # before the line we don't recognize.
          failure_count += 1
          summary_lines[-1:-1] = ['WARNING: next line unrecognized\n']

    if not found_summary:
      # Add a fake failure so we get notified.
      failure_count += 1
      summary_lines.append('WARNING: Failed to find summary in stdio.\n')

    self.setTestResults(passed=passed_count,
                        failed=failure_count - flaky_count,
                        warnings=flaky_count)

    if failure_count > 0:
      if failure_count > flaky_count:
        self.__result = FAILURE
      else:
        self.__result = WARNINGS
      summary_name = 'summary: %d failed' % failure_count
      if flaky_count > 0:
        summary_name += ', %d flaky failed' % flaky_count
      self.addCompleteLog(summary_name, ''.join(summary_lines))
    else:
      self.__result = SUCCESS

    got_revision = self.getProperty('got_revision')
    buildnumber  = self.getProperty('buildnumber')
    buildername  = self.getProperty('buildername')
    if 'drm' in buildername:
      self.addURL('test logs',
                  'http://build.chromium.org/p/client.drmemory/testlogs/' +
                  'from_%s/testlogs_r%s_b%s.7z' % \
                  (buildername, got_revision, buildnumber))

  def evaluateCommand(self, cmd):
    if self.__result is not None:
      return self.__result
    return Test.evaluateCommand(self, cmd)


class DrMemoryTest(Test):
  def __init__(self, **kwargs):
    self.failed__ = False  # there's a 'failed' method in Test, ouch!
    Test.__init__(self, **kwargs)

  def createSummary(self, log):
    failed_tests = []
    summary = []
    report_count = 0
    assert_failure = None

    # Don't use 'readlines' because we want both stdout and stderr.
    for line in log.getText().split('\n'):
      m = re.match('\[  FAILED  \] (.*\..*) \([0-9]+ ms\)', line.strip())
      if m:
        failed_tests.append(m.groups()[0])  # Append failed test name.

      DRM_PREFIX = '~~[Dr\.M0-9]+~~ '
      m = re.match(DRM_PREFIX + '(.*)', line)
      if m:
        summary.append(m.groups()[0])

      m = re.match(DRM_PREFIX + '*([0-9]+) unique,.*total,* (.*)', line)
      if m:
        (error_count, _) = m.groups()
        error_count = int(error_count)
        report_count += error_count

      m = re.match(DRM_PREFIX + 'ASSERT FAILURE \(.*\): (.*)', line)
      if m:
        assert_failure = 'ASSERT FAILURE: ' + m.groups()[0]

    if assert_failure:
      self.failed__ = True
      self.addCompleteLog('ASSERT FAILURE!!!', assert_failure)

    if failed_tests:
      self.failed__ = True
      self.setTestResults(failed=len(failed_tests))
      self.addCompleteLog('%d tests failed' % len(failed_tests),
                            '\n'.join(failed_tests))
    if report_count > 0:
      self.failed__ = True
      self.setTestResults(warnings=report_count)

    self.addCompleteLog('summary: %d report(s)' % report_count,
                        ''.join(summary))

  def evaluateCommand(self, cmd):
    if self.failed__:
      return FAILURE
    return Test.evaluateCommand(self, cmd)


class V8DrFactory(v8_factory.V8Factory):

  """Subclass of V8Factory to build DR alongside V8 for the same arch."""

  def BuildFactory(self, target_arch=None, *args, **kwargs):
    f = super(V8DrFactory, self).BuildFactory(*args,
                                              target_arch=target_arch,
                                              **kwargs)
    # Add in a build of DR.
    b = DrCommands(self._target_platform, os_version=None, build_factory=f)
    b.AddDynamoRIOSource()
    b.AddTools()
    # Debug DR is too slow for the V8 tests so use release.
    b.AddDRBuild(target='Release', target_arch=target_arch)
    return f

  def V8Factory(self, target_arch=None, *args, **kwargs):
    assert 'shell_flags' not in kwargs
    bits = ArchToBits(target_arch)
    drrun = '../../dynamorio/build/bin%d/drrun' % bits
    kwargs['command_prefix'] = '%s -reset_every_nth_pending 0 --' % drrun
    return super(V8DrFactory, self).V8Factory(*args, target_arch=target_arch,
                                              **kwargs)


def ToolStep(step_class, os, **kwargs):
  """Modify build step arguments to run the command with our custom tools."""
  if os.startswith('win'):
    command = kwargs.get('command')
    env = kwargs.get('env')
    if isinstance(command, list):
      command = [WIN_BUILD_ENV_PATH] + command
    else:
      command = WIN_BUILD_ENV_PATH + ' ' + command
    if env:
      env = dict(env)  # Copy
    else:
      env = {}
    env['BOTTOOLS'] = WithProperties('%(workdir)s\\bot_tools')
    kwargs['command'] = command
    kwargs['env'] = env
  return step_class(**kwargs)


def DynamoRIOSuiteFactory(os='', os_version=''):
  return DrCommands(os, os_version).DynamoRIOSuite()


def DynamoRIONightlyFactory(os='', os_version=''):
  return DrCommands(os, os_version).DynamoRIONightly()


def DynamoRIOPackageFactory(os='', os_version=''):
  return DrCommands(os, os_version).DynamoRIOPackage()


def CreateDrMFactory(windows):
  # Build and run the drmemory pre-commit suite.
  cmds = DrCommands(WindowsToOs(windows))
  cmds.DrMemorySuite()
  if cmds.IsWindows():
    cmds.AddTSanTestBuild()
    cmds.AddDrMemoryTSanTests()
    # We used to kill stale drmemory processes, but now we use auto-reboot.
  cmds.AddDrMemoryLogsUpload()
  return cmds.factory


def CreateDrMPackageFactory(windows):
  return DrCommands(WindowsToOs(windows)).DrMemoryPackage()


def CreateWinChromeFactory(builder):
  """Run chrome tests with the latest drmemory.

  Do *not* build TOT chrome or sync it.  Building chrome takes a lot of
  resources and the tests are flaky, so we only do at known good revisions.  We
  don't want to fall too far behind, or we're not really testing Chrome's full
  test suite.
  """
  ret = factory.BuildFactory()
  sfx_name = 'drm-sfx'  # TODO: add .exe when BB supports that, d'oh!
  ret.addStep(
      FileDownload(mastersrc=LATEST_WIN_BUILD,
                   slavedest=(sfx_name + '.exe'),
                   name='Download the latest build'))
  ret.addStep(
      ShellCommand(command=[sfx_name, '-ounpacked', '-y'],
                   haltOnFailure=True,
                   name='Unpack the build',
                   description='unpack the build'))

  # Find out the revision number using -version
  def get_revision(rc, stdout, stderr):
    m = re.search(r'version \d+\.\d+\.(\d+)', stdout)
    if m:
      return { 'got_revision': int(m.groups()[0]) }
    return { 'failed_to_parse': stdout }
  ret.addStep(
      SetProperty(
          command=['unpacked\\bin\\drmemory', '-version'],
          extract_fn=get_revision,
          name='Get the revision number',
          description='get revision',
          descriptionDone='get revision'))

  # VP8 tests
  # TODO(rnk): Add back the VP8 test step.  We might be able to make this part
  # of the buildbot steps if it doesn't update often and builds incrementally.
  if False:
    ret.addStep(
        ToolStep(
            DrMemoryTest,
            'windows',
            command=[
                'bash',
                'E:\\vpx\\vp8-test-vectors\\run_tests.sh',
                ('--exec=unpacked/bin/drmemory.exe -batch '
                 '-no_check_leaks -no_count_leaks '
                 '-no_check_uninitialized '
                 'e:/vpx/b/Win32/Debug/vpxdec.exe'),
                'E:\\vpx\\vp8-test-vectors',
                ],
            env={'PATH': 'C:\\cygwin\\bin;%PATH%'},
            name='VP8 tests',
            descriptionDone='VP8 tests',
            description='run vp8 tests'))

  # Chromium tests
  for test in ['url', 'printing', 'media', 'sql', 'crypto_unittests',
               'remoting', 'ipc_tests', 'base_unittests', 'net', 'unit']:
    ret.addStep(
        Test(command=[
                 # Use the build dir of the chrome builder on this slave.
                 ('..\\..\\' + builder + '\\build\\' +
                  'src\\tools\\valgrind\\chrome_tests.bat'),
                 '-t', test, '--tool', 'drmemory_light', '--keep_logs',
             ],
             env={'DRMEMORY_COMMAND': 'unpacked/bin/drmemory.exe'},
             name=('Chromium \'%s\' tests' % test),
             descriptionDone=('\'%s\' tests' % test),
             description=('run \'%s\' tests' % test)))

  return ret


def CreateLinuxChromeFactory():
  """Run chrome tests with the latest dynamorio.

  TODO(rnk): Run drmemory, not dynamorio.

  We use a build of chrome produced weekly from a known good revision on the
  same slave.
  """
  cr_src = '../../linux-cr-builder/build/src'
  ret = factory.BuildFactory()
  ret.addStep(
      SVN(
          svnurl=dr_svnurl,
          workdir='dynamorio',
          mode='update',
          name='Checkout DynamoRIO'))

  # If we need to execute 32-bit children, we'll need a full exports package.
  ret.addStep(Configure(command=['cmake', '..', '-DDEBUG=OFF'],
                        workdir='dynamorio/build',
                        name='Configure release DynamoRIO'))
  ret.addStep(Compile(command=['make', '-j5'],
                      workdir='dynamorio/build',
                      name='Compile release DynamoRIO'))

  # Don't follow python children.  This should speed up net_unittests, which
  # spawns a bunch of simple http servers to talk to.
  ret.addStep(ShellCommand(
      command=['bin64/drconfig', '-reg', 'python', '-norun', '-v'],
      workdir='dynamorio/build',
      name='don\'t follow python',
      description='don\'t follow python',
      descriptionDone='don\'t follow python'))

  # Chromium tests
  for test in LINUX_CHROME_TESTS:
    cmd = [
        'xvfb-run', '-a',
        '../dynamorio/build/bin64/drrun',
        '-stderr_mask', '12',  # Show DR crashes
        '--',
        cr_src + '/out/Release/' + test
    ]
    if test == 'browser_tests':
      cmd += ['--gtest_filter=AutofillTest.BasicFormFill']
    elif test == 'net_unittests':
      cmd += ['--gtest_filter=-CertDatabaseNSSTest.ImportCACertHierarchy*']
    elif test == 'remoting_unittests':
      cmd += ['--gtest_filter='
              '-VideoFrameCapturerTest.Capture:'
              'DesktopProcessTest.DeathTest']
    elif test == 'base_unittests':
      # crbug.com/308273: this test is flaky
      cmd += ['--gtest_filter=-TraceEventTestFixture.TraceContinuousSampling']
    elif test == 'content_shell':
      cmd += ['-dump-render-tree',
              'file:///home/chrome-bot/bb.html']
    # We used to md5 the output, but that's too brittle.  Just dump it to stdout
    # so humans can verify it.  The return code will tell us if we crash.
    # TODO(rnk): We should run some selection of layout tests if we want to
    # verify output.
    ret.addStep(Test(command=cmd,
                     env={'CHROME_DEVEL_SANDBOX':
                          '/opt/chromium/chrome_sandbox'},
                     name=test,
                     descriptionDone=test,
                     description=test))

  return ret
