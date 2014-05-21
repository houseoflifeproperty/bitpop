# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions specific to build slaves, shared by several buildbot scripts.
"""

import datetime
import glob
import os
import re
import sys
import tempfile
import time

from common import chromium_utils
from slave.bootstrap import ImportMasterConfigs # pylint: disable=W0611
from slave.bootstrap import GetActiveMaster # pylint: disable=W0611
import config
from slave import xvfb

# These codes used to distinguish true errors from script warnings.
ERROR_EXIT_CODE = 1
WARNING_EXIT_CODE = 88


# Local errors.
class PageHeapError(Exception):
  pass


# Cache the path to gflags.exe.
_gflags_exe = None


def SubversionExe():
  # TODO(pamg): move this into platform_utils to support Mac and Linux.
  if chromium_utils.IsWindows():
    return 'svn.bat'  # Find it in the user's path.
  elif chromium_utils.IsLinux() or chromium_utils.IsMac():
    return 'svn'  # Find it in the user's path.
  else:
    raise NotImplementedError(
        'Platform "%s" is not currently supported.' % sys.platform)


def SubversionCat(wc_dir):
  """Output the content of specified files or URLs in SVN.
  """
  try:
    return chromium_utils.GetCommandOutput([SubversionExe(), 'cat',
                                            wc_dir])
  except chromium_utils.ExternalError:
    return None


def SubversionRevision(wc_dir):
  """Finds the last svn revision of a working copy by running 'svn info',
  and returns it as an integer.
  """
  svn_regexp = re.compile(r'.*Revision: (\d+).*', re.DOTALL)
  try:
    svn_info = chromium_utils.GetCommandOutput([SubversionExe(), 'info',
                                                wc_dir])
    return_value = re.sub(svn_regexp, r'\1', svn_info)
    if return_value.isalnum():
      return int(return_value)
    else:
      return 0
  except chromium_utils.ExternalError:
    return 0


def SubversionLastChangedRevision(wc_dir):
  """Finds the svn revision where this file/dir was last edited by running
  'svn info', and returns it as an integer.
  """
  svn_regexp = re.compile(r'.*Last Changed Rev: (\d+).*', re.DOTALL)
  try:
    svn_info = chromium_utils.GetCommandOutput([SubversionExe(), 'info',
                                                wc_dir])
    return_value = re.sub(svn_regexp, r'\1', svn_info)
    if return_value.isalnum():
      return int(return_value)
    else:
      return 0
  except chromium_utils.ExternalError:
    return 0


def GetZipFileNames(build_properties, build_dir, webkit_dir=None,
                    extract=False):
  base_name = 'full-build-%s' % chromium_utils.PlatformName()

  chromium_revision = SubversionRevision(os.path.dirname(build_dir))
  if 'try' in build_properties.get('mastername'):
    if extract:
      if not build_properties.get('parent_buildnumber'):
        raise Exception('build_props does not have parent data: %s' %
                        build_properties)
      version_suffix = '_%(parent_buildnumber)s' % build_properties
    else:
      version_suffix = '_%(buildnumber)s' % build_properties
  elif webkit_dir:
    webkit_revision = SubversionRevision(webkit_dir)
    version_suffix = '_wk%d_%d' % (webkit_revision, chromium_revision)
  else:
    version_suffix = '_%d' % chromium_revision

  return base_name, version_suffix


def SlaveBuildName(chrome_dir):
  """Extracts the build name of this slave (e.g., 'chrome-release') from the
  leaf subdir of its build directory.
  """
  return os.path.basename(SlaveBaseDir(chrome_dir))


def SlaveBaseDir(chrome_dir):
  """Finds the full path to the build slave's base directory (e.g.
  'c:/b/chrome/chrome-release').  This is assumed to be the parent of the
  shallowest 'build' directory in the chrome_dir path.

  Raises chromium_utils.PathNotFound if there is no such directory.
  """
  result = ''
  prev_dir = ''
  curr_dir = chrome_dir
  while prev_dir != curr_dir:
    (parent, leaf) = os.path.split(curr_dir)
    if leaf == 'build':
      # Remember this one and keep looking for something shallower.
      result = parent
    if leaf == 'slave':
      # We are too deep, stop now.
      break
    prev_dir = curr_dir
    curr_dir = parent
  if not result:
    raise chromium_utils.PathNotFound('Unable to find slave base dir above %s' %
                                      chrome_dir)
  return result


def GetStagingDir(start_dir):
  """Creates a chrome_staging dir in the starting directory. and returns its
  full path.
  """
  staging_dir = os.path.join(SlaveBaseDir(start_dir), 'chrome_staging')
  chromium_utils.MaybeMakeDirectory(staging_dir)
  return staging_dir


def SetPageHeap(chrome_dir, exe, enable):
  """Enables or disables page-heap checking in the given executable, depending
  on the 'enable' parameter.  gflags_exe should be the full path to gflags.exe.
  """
  global _gflags_exe
  if _gflags_exe is None:
    _gflags_exe = chromium_utils.FindUpward(chrome_dir,
                                            'tools', 'memory', 'gflags.exe')
  command = [_gflags_exe]
  if enable:
    command.extend(['/p', '/enable', exe, '/full'])
  else:
    command.extend(['/p', '/disable', exe])
  result = chromium_utils.RunCommand(command)
  if result:
    description = {True: 'enable', False: 'disable'}
    raise PageHeapError('Unable to %s page heap for %s.' %
                        (description[enable], exe))


def LongSleep(secs):
  """A sleep utility for long durations that avoids appearing hung.

  Sleeps for the specified duration.  Prints output periodically so as not to
  look hung in order to avoid being timed out.  Since this function is meant
  for long durations, it assumes that the caller does not care about losing a
  small amount of precision.

  Args:
    secs: The time to sleep, in seconds.
  """
  secs_per_iteration = 60
  time_slept = 0

  # Make sure we are dealing with an integral duration, since this function is
  # meant for long-lived sleeps we don't mind losing floating point precision.
  secs = int(round(secs))

  remainder = secs % secs_per_iteration
  if remainder > 0:
    time.sleep(remainder)
    time_slept += remainder
    sys.stdout.write('.')
    sys.stdout.flush()

  while time_slept < secs:
    time.sleep(secs_per_iteration)
    time_slept += secs_per_iteration
    sys.stdout.write('.')
    sys.stdout.flush()

  sys.stdout.write('\n')


def RunPythonCommandInBuildDir(build_dir, target, command_line_args,
                               server_dir=None, filter_obj=None):
  if sys.platform == 'win32':
    python_exe = 'python.exe'

    setup_mount = chromium_utils.FindUpward(build_dir,
                                            'third_party',
                                            'cygwin',
                                            'setup_mount.bat')

    chromium_utils.RunCommand([setup_mount])
  else:
    os.environ['PYTHONPATH'] = (chromium_utils.FindUpward(build_dir, 'tools',
                                                          'python')
                                + ':' +os.environ.get('PYTHONPATH', ''))
    python_exe = 'python'

  if chromium_utils.IsLinux():
    slave_name = SlaveBuildName(build_dir)
    xvfb.StartVirtualX(slave_name,
                       os.path.join(build_dir, '..', 'out', target),
                       server_dir=server_dir)

  command = [python_exe]

  # The list of tests is given as arguments.
  command.extend(command_line_args)

  result = chromium_utils.RunCommand(command, filter_obj=filter_obj)

  if chromium_utils.IsLinux():
    xvfb.StopVirtualX(slave_name)

  return result


class RunCommandCaptureFilter(object):
  lines = []

  def FilterLine(self, in_line):
    self.lines.append(in_line)
    return None

  def FilterDone(self, last_bits):
    self.lines.append(last_bits)
    return None


def GypFlagIsOn(options, flag):
  value = GetGypFlag(options, flag, False)
  # The values we understand as Off are False and a text zero.
  if value is False or value == '0':
    return False
  return True


def GetGypFlag(options, flag, default=None):
  gclient = options.factory_properties.get('gclient_env', {})
  defines = gclient.get('GYP_DEFINES', '')
  gypflags = dict([(a, c if b == '=' else True) for (a, b, c) in
                   [x.partition('=') for x in defines.split(' ')]])
  if flag not in gypflags:
    return default
  return gypflags[flag]



def CopyFileToArchiveHost(src, dest_dir):
  """A wrapper method to copy files to the archive host.
  It calls CopyFileToDir on Windows and SshCopyFiles on Linux/Mac.
  TODO: we will eventually want to change the code to upload the
  data to appengine.

  Args:
      src: full path to the src file.
      dest_dir: destination directory on the host.
  """
  host = config.Archive.archive_host
  if not os.path.exists(src):
    raise chromium_utils.ExternalError('Source path "%s" does not exist' % src)
  chromium_utils.MakeWorldReadable(src)
  if chromium_utils.IsWindows():
    chromium_utils.CopyFileToDir(src, dest_dir)
  elif chromium_utils.IsLinux() or chromium_utils.IsMac():
    chromium_utils.SshCopyFiles(src, host, dest_dir)
  else:
    raise NotImplementedError(
        'Platform "%s" is not currently supported.' % sys.platform)


def MaybeMakeDirectoryOnArchiveHost(dest_dir):
  """A wrapper method to create a directory on the archive host.
  It calls MaybeMakeDirectory on Windows and SshMakeDirectory on Linux/Mac.

  Args:
      dest_dir: destination directory on the host.
  """
  host = config.Archive.archive_host
  if chromium_utils.IsWindows():
    chromium_utils.MaybeMakeDirectory(dest_dir)
    print 'saving results to %s' % dest_dir
  elif chromium_utils.IsLinux() or chromium_utils.IsMac():
    chromium_utils.SshMakeDirectory(host, dest_dir)
    print 'saving results to "%s" on "%s"' % (dest_dir, host)
  else:
    raise NotImplementedError(
        'Platform "%s" is not currently supported.' % sys.platform)


def GSUtilSetup():
  # Get the path to the gsutil script.
  gsutil = os.path.join(os.path.dirname(__file__), 'gsutil')
  gsutil = os.path.normpath(gsutil)
  if chromium_utils.IsWindows():
    gsutil += '.bat'

  # Get the path to the boto file containing the password.
  boto_file = os.path.join(os.path.dirname(__file__), '..', '..', 'site_config',
                           '.boto')

  # Make sure gsutil uses this boto file.
  os.environ['AWS_CREDENTIAL_FILE'] = boto_file
  os.environ['BOTO_CONFIG'] = boto_file
  return gsutil


def GSUtilCopy(source, dest, mimetype=None, gs_acl=None):
  """Copy a file to Google Storage.

  Runs the following command:
    gsutil -h Content-Type:<mimetype> \
        cp -a <gs_acl> file://<filename> <gs_base>/<subdir>/<filename w/o path>

  Args:
    source: the source URI
    dest: the destination URI
    mimetype: optional value to add as a Content-Type header
    gs_acl: optional value to add as a canned-acl
  Returns:
    The status code returned from running the generated gsutil command.
  """

  if not source.startswith('gs://') and not source.startswith('file://'):
    source = 'file://' + source
  if not dest.startswith('gs://') and not dest.startswith('file://'):
    dest = 'file://' + dest
  gsutil = GSUtilSetup()
  # Run the gsutil command. gsutil internally calls command_wrapper, which
  # will try to run the command 10 times if it fails.
  command = [gsutil]
  if mimetype:
    command.extend(['-h', 'Content-Type:%s' % mimetype])
  command.extend(['cp'])
  if gs_acl:
    command.extend(['-a', gs_acl])
  command.extend([source, dest])
  return chromium_utils.RunCommand(command)


def GSUtilCopyFile(filename, gs_base, subdir=None, mimetype=None, gs_acl=None):
  """Copy a file to Google Storage.

  Runs the following command:
    gsutil -h Content-Type:<mimetype> \
        cp -a <gs_acl> file://<filename> <gs_base>/<subdir>/<filename w/o path>

  Args:
    filename: the file to upload
    gs_base: the bucket to upload the file to
    subdir: optional subdirectory withing the bucket
    mimetype: optional value to add as a Content-Type header
    gs_acl: optional value to add as a canned-acl
  Returns:
    The status code returned from running the generated gsutil command.
  """

  source = 'file://' + filename
  dest = gs_base
  if subdir:
    # HACK(nsylvain): We can't use normpath here because it will break the
    # slashes on Windows.
    if subdir == '..':
      dest = os.path.dirname(gs_base)
    else:
      dest = '/'.join([gs_base, subdir])
  dest = '/'.join([dest, os.path.basename(filename)])
  return GSUtilCopy(source, dest, mimetype, gs_acl)


def GSUtilCopyDir(src_dir, gs_base, dest_dir=None, gs_acl=None):
  """Create a list of files in a directory and pass each to GSUtilCopyFile."""

  # Walk the source directory and find all the files.
  # Alert if passed a file rather than a directory.
  if os.path.isfile(src_dir):
    assert os.path.isdir(src_dir), '%s must be a directory' % src_dir

  # Get the list of all files in the source directory.
  file_list = []
  for root, _, files in os.walk(src_dir):
    file_list.extend((os.path.join(root, name) for name in files))

  # Find the absolute path of the source directory so we can use it below.
  base = os.path.abspath(src_dir) + os.sep

  for filename in file_list:
    # Strip the base path off so we just have the relative file path.
    path = filename.partition(base)[2]

    # If we have been given a destination directory, add that to the path.
    if dest_dir:
      path = os.path.join(dest_dir, path)

    # Trim the filename and last slash off to create a destination path.
    path = path.rpartition(os.sep + os.path.basename(path))[0]

    # If we're on windows, we need to reverse slashes, gsutil wants posix paths.
    if chromium_utils.IsWindows():
      path = path.replace('\\', '/')

    # Pass the file off to copy.
    status = GSUtilCopyFile(filename, gs_base, path, gs_acl=gs_acl)

    # Bail out on any failure.
    if status:
      return status

  return 0


def GSUtilDownloadFile(src, dst):
  """Copy a file from Google Storage."""
  gsutil = GSUtilSetup()

  # Run the gsutil command. gsutil internally calls command_wrapper, which
  # will try to run the command 10 times if it fails.
  command = [gsutil]
  command.extend(['cp', src, dst])
  return chromium_utils.RunCommand(command)


def GSUtilMoveFile(source, dest, gs_acl=None):
  """Move a file on Google Storage."""

  gsutil = GSUtilSetup()

  # Run the gsutil command. gsutil internally calls command_wrapper, which
  # will try to run the command 10 times if it fails.
  command = [gsutil]
  command.extend(['mv', source, dest])
  status = chromium_utils.RunCommand(command)

  if status:
    return status

  if gs_acl:
    command = [gsutil]
    command.extend(['setacl', gs_acl, dest])
    status = chromium_utils.RunCommand(command)

  return status


def GSUtilDeleteFile(filename):
  """Delete a file on Google Storage."""

  gsutil = GSUtilSetup()

  # Run the gsutil command. gsutil internally calls command_wrapper, which
  # will try to run the command 10 times if it fails.
  command = [gsutil]
  command.extend(['rm', filename])
  return chromium_utils.RunCommand(command)


# Python doesn't support the type of variable scope in nested methods needed
# to avoid the global output variable.  This variable should only ever be used
# by GSUtilListBucket.
command_output = ''


def GSUtilListBucket(gs_base, args):
  """List the contents of a Google Storage bucket."""

  gsutil = GSUtilSetup()

  # Run the gsutil command. gsutil internally calls command_wrapper, which
  # will try to run the command 10 times if it fails.
  global command_output
  command_output = ''

  def GatherOutput(line):
    global command_output
    command_output += line + '\n'
  command = [gsutil, 'ls'] + args + [gs_base]
  status = chromium_utils.RunCommand(command, parser_func=GatherOutput)
  return (status, command_output)


def LogAndRemoveFiles(temp_dir, regex_pattern):
  """Removes files in |temp_dir| that match |regex_pattern|.
  This function prints out the name of each directory or filename before
  it deletes the file from disk."""
  regex = re.compile(regex_pattern)
  if not os.path.isdir(temp_dir):
    return
  for dir_item in os.listdir(temp_dir):
    if regex.search(dir_item):
      full_path = os.path.join(temp_dir, dir_item)
      print 'Removing leaked temp item: %s' % full_path
      try:
        if os.path.islink(full_path) or os.path.isfile(full_path):
          os.remove(full_path)
        elif os.path.isdir(full_path):
          chromium_utils.RemoveDirectory(full_path)
        else:
          print 'Temp item wasn\'t a file or directory?'
      except OSError, e:
        print >> sys.stderr, e
        # Don't fail.


def RemoveOldSnapshots(desktop):
  """Removes ChromiumSnapshot files more than one day old. Such snapshots are
  created when certain tests timeout (e.g., Chrome Frame integration tests)."""
  # Compute the file prefix of a snapshot created one day ago.
  yesterday = datetime.datetime.now() - datetime.timedelta(1)
  old_snapshot = yesterday.strftime('ChromiumSnapshot%Y%m%d%H%M%S')
  # Collect snapshots at least as old as that one created a day ago.
  to_delete = []
  for snapshot in glob.iglob(os.path.join(desktop, 'ChromiumSnapshot*.png')):
    if os.path.basename(snapshot) < old_snapshot:
      to_delete.append(snapshot)
  # Delete the collected snapshots.
  for snapshot in to_delete:
    print 'Removing old snapshot: %s' % snapshot
    try:
      os.remove(snapshot)
    except OSError, e:
      print >> sys.stderr, e


def RemoveChromeDesktopFiles():
  """Removes Chrome files (i.e. shortcuts) from the desktop of the current user.
  This does nothing if called on a non-Windows platform."""
  if chromium_utils.IsWindows():
    desktop_path = os.environ['USERPROFILE']
    desktop_path = os.path.join(desktop_path, 'Desktop')
    LogAndRemoveFiles(desktop_path, '^(Chromium|chrome) \(.+\)?\.lnk$')
    RemoveOldSnapshots(desktop_path)


def RemoveJumpListFiles():
  """Removes the files storing jump list history.
  This does nothing if called on a non-Windows platform."""
  if chromium_utils.IsWindows():
    custom_destination_path = os.path.join(os.environ['USERPROFILE'],
                                           'AppData',
                                           'Roaming',
                                           'Microsoft',
                                           'Windows',
                                           'Recent',
                                           'CustomDestinations')
    LogAndRemoveFiles(custom_destination_path, '.+')


def RemoveChromeTemporaryFiles():
  """A large hammer to nuke what could be leaked files from unittests or
  files left from a unittest that crashed, was killed, etc."""
  # NOTE: print out what is cleaned up so the bots don't timeout if
  # there is a lot to cleanup and also se we see the leaks in the
  # build logs.
  # At some point a leading dot got added, support with and without it.
  kLogRegex = '^\.?(com\.google\.Chrome|org\.chromium)\.'
  if chromium_utils.IsWindows():
    kLogRegex = r'^(base_dir|scoped_dir|nps|chrome_test|SafeBrowseringTest)'
    LogAndRemoveFiles(tempfile.gettempdir(), kLogRegex)
    # Dump and temporary files.
    LogAndRemoveFiles(tempfile.gettempdir(), r'^.+\.(dmp|tmp)$')
    LogAndRemoveFiles(tempfile.gettempdir(), r'^_CL_.*$')
    RemoveChromeDesktopFiles()
    RemoveJumpListFiles()
  elif chromium_utils.IsLinux():
    kLogRegexHeapcheck = '\.(sym|heap)$'
    LogAndRemoveFiles(tempfile.gettempdir(), kLogRegex)
    LogAndRemoveFiles(tempfile.gettempdir(), kLogRegexHeapcheck)
    LogAndRemoveFiles('/dev/shm', kLogRegex)
  elif chromium_utils.IsMac():
    nstempdir_path = '/usr/local/libexec/nstempdir'
    if os.path.exists(nstempdir_path):
      ns_temp_dir = chromium_utils.GetCommandOutput([nstempdir_path]).strip()
      if ns_temp_dir:
        LogAndRemoveFiles(ns_temp_dir, kLogRegex)
    for i in ('Chromium', 'Google Chrome'):
      # Remove dumps.
      crash_path = '%s/Library/Application Support/%s/Crash Reports' % (
          os.environ['HOME'], i)
      LogAndRemoveFiles(crash_path, r'^.+\.dmp$')
  else:
    raise NotImplementedError(
        'Platform "%s" is not currently supported.' % sys.platform)


def WriteLogLines(logname, lines, perf=None):
  for line in lines:
    print '@@@STEP_LOG_LINE@%s@%s@@@' % (logname, line)
  if perf:
    print '@@@STEP_LOG_END_PERF@%s@%s@@@' % (logname, perf)
  else:
    print '@@@STEP_LOG_END@%s@@@' % logname
