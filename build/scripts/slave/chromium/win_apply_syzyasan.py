#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import multiprocessing
import optparse
import os
import shutil
import subprocess
import sys

from slave import build_directory


SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
BLACKLIST = set((
    'blacklist_test_dll_1.dll',
    'crash_service64.exe',
    'mini_installer.exe',
    'nacl.exe',
    'nacl64.exe',
    'sql.dll',
))
SKIP_DIRS = [
    'locales',
    'obj',
    'syzygy/asan',
]


class ASANitizer(object):
  def __init__(self, instrument_exe, stopped, root):
    self.instrument_exe = instrument_exe
    self.stopped = stopped
    self.root = os.path.abspath(root)

  def __call__(self, job):
    retval = 0
    stdout = ''
    pe_image, pdb = job

    try:
      if not self.stopped.is_set():
        out_pe = GetInstrumentedFilepath(pe_image, self.root)
        out_pdb = GetInstrumentedFilepath(pdb, self.root)

        # Note that instrument.exe requires --foo=bar format (including the '=')
        command = [
            self.instrument_exe, '--mode=ASAN',
            '--input-image=%s' % pe_image,
            '--output-image=%s' % out_pe,
            '--output-pdb=%s' % out_pdb,
        ]

        for fname in filter(os.path.exists, (out_pe, out_pdb)):
          os.remove(fname)

        proc = subprocess.Popen(command,
                                stderr=subprocess.STDOUT,
                                stdout=subprocess.PIPE)
        stdout, _ = proc.communicate()
        retval = proc.returncode

      return (retval, stdout, pe_image)
    except Exception:
      import traceback
      return (1, stdout+'\n'+traceback.format_exc(), pe_image)


def GetInstrumentedFilepath(fname, root):
  """Returns the name of the instrumented file. Creates the output directory if
  if doesn't exist.

  >>> GetInstrumentedFilepath('C:/src/out/Release/foo/image.exe',
          'src/out/Release')
  'c:/src/out/Release/syzygy/asan/foo/image.exe'
  TODO(sebmarchand): Separate the path computation from the side-effect of path
      creation.
  """
  asan_root = os.path.join(root, 'syzygy', 'asan')
  asaned_file = fname.replace(root, asan_root)
  out_path = os.path.dirname(asaned_file)
  if not os.path.exists(out_path):
    os.makedirs(out_path)
  elif not os.path.isdir(out_path):
    raise Exception('Invalid output directory for %s.' % fname)
  return asaned_file


def UpdateAsanArtifact(full_directory, artifact_path):
  """Updates an ASAN artifact in the build directory, if it exists."""
  artifact = os.path.join(full_directory, os.path.basename(artifact_path))

  if os.path.exists(artifact):
    print('Removing', artifact)
    os.remove(artifact)

  print 'Copying %s -> %s' % (artifact_path, artifact)
  shutil.copy2(artifact_path, artifact)

  fname = os.path.basename(artifact_path)
  print 'Blacklisting %s' % fname
  BLACKLIST.add(fname)


def GetCompatiblePDB(pe_image, pdbfind_exe):
  """Returns <path to pdb> or None (if no good pdb exists)."""
  try:
    command = [pdbfind_exe, pe_image]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE)
    pdb_path, _ = proc.communicate()
    pdb_path = pdb_path.splitlines()[0]
    retval = proc.returncode
    if retval == 0:
      return os.path.abspath(pdb_path)
    return None
  except Exception:
    return None


def FindFilesToAsan(directory, pdbfind_exe):
  """Finds eligible PE images in given directory.

  A PE image is eligible if it has a corresponding pdb and doesn't already have
  ASAN applied to it. Skips files which have an extra extension (like
  foo.orig.exe).
  """
  ret = []

  def GoodExeOrDll(fname):
    return (
        '.' in fname and
        fname not in BLACKLIST and
        fname.split('.', 1)[-1].lower() in ('exe', 'dll'))

  skip_dirs = set((os.path.abspath(os.path.join(directory, skip_dir))
      for skip_dir in SKIP_DIRS))

  for root, subdirs, files in os.walk(directory):
    for path, sdir in [(os.path.join(root, s), s) for s in subdirs]:
      if path in skip_dirs:
        subdirs.remove(sdir)

    for pe_image in (os.path.join(root, f) for f in files if GoodExeOrDll(f)):
      pdb = GetCompatiblePDB(pe_image, pdbfind_exe)
      if not pdb:
        print >> sys.stderr, 'PDB for "%s" does not exist.' % pe_image
        continue

      ret.append((pe_image, pdb))
  return ret


def ApplyAsanToBuild(full_directory, instrument_exe, pdbfind_exe, jobs):
  """Applies ASAN to all exe's/dll's in the build directory."""
  to_asan = FindFilesToAsan(full_directory, pdbfind_exe)

  if not to_asan:
    print >> sys.stderr, 'No files to ASAN!'
    return 1

  manager = multiprocessing.Manager()
  stopped = manager.Event()
  sanitizer = ASANitizer(instrument_exe, stopped, full_directory)
  pool = multiprocessing.Pool(jobs)

  ret = 0
  try:
    generator = pool.imap_unordered(sanitizer, to_asan)
    for retval, stdout, failed_image in generator:
      ostream = (sys.stderr if retval else sys.stdout)
      print >> ostream, stdout
      sys.stdout.flush()
      sys.stderr.flush()
      if retval:
        print 'Failed to ASAN %s. Stopping remaining jobs.' % failed_image
        ret = retval
        stopped.set()
  except KeyboardInterrupt:
    stopped.set()
  pool.close()
  pool.join()

  return ret


def main():
  # syzygy is relative to --build-dir, not relative to SCRIPT_DIR.
  default_asan_dir = os.path.join(
      os.pardir, 'third_party', 'syzygy', 'binaries', 'exe')
  default_instrument_exe = os.path.join(default_asan_dir, 'instrument.exe')
  default_agent_logger_exe = os.path.join(default_asan_dir, 'agent_logger.exe')
  default_pdbfind_exe = os.path.join(default_asan_dir, 'pdbfind.exe')
  default_runtime_path = os.path.join(default_asan_dir, 'syzyasan_rtl.dll')

  parser = optparse.OptionParser()
  parser.add_option('--build-dir', help='ignored')
  parser.add_option(
      '--target',
      help='The target in the build directory to asan (required).')
  parser.add_option(
      '--jobs', type='int', default=multiprocessing.cpu_count(),
      help='Specify the number of sub-tasks to use (%default).')
  parser.add_option(
      '--instrument_exe', default=default_instrument_exe,
      help='Specify the path to the ASAN instrument.exe relative to '
           'build-dir (%default).')
  parser.add_option(
      '--agent_logger_exe', default=default_agent_logger_exe,
      help='Specify the path to the ASAN agent_logger.exe relative to '
           'build-dir (%default).')
  parser.add_option(
      '--pdbfind_exe', default=default_pdbfind_exe,
      help='Specify the path to the ASAN pdbfind.exe relative to '
           'build-dir (%default).')
  parser.add_option(
      '--runtime_path', default=default_runtime_path,
      help='Specify the path to the ASAN runtime DLL relative to '
           'build-dir (%default).')
  options, args = parser.parse_args()
  options.build_dir = build_directory.GetBuildOutputDirectory()

  options.build_dir = os.path.abspath(options.build_dir)

  if not options.build_dir:
    parser.error('Must specify --build-dir')
  if not options.target:
    parser.error('Must specify --target')
  if args:
    parser.error('Not expecting additional arguments')

  # A 3-tuples list describing the different artifacts needed in a Win ASan
  # build. The tuples values are:
  #     - Artifact name: The name of the parameter to add to the options for
  #                      this artifact.
  #     - Artifact path: The path to this artifact. It is expected to be
  #                      relative to build_dir or absolute.
  #     - should_update: Indicates it this artifact should be copied to the
  #                      build directory.
  artifacts = [
      ('full_directory', options.target, False),
      ('instrument_exe', options.instrument_exe, False),
      ('agent_logger_exe', options.agent_logger_exe, True),
      ('pdbfind_exe', options.pdbfind_exe, False),
      ('runtime_path', options.runtime_path, True),
  ]

  for name, path, should_update in artifacts:
    if not os.path.isabs(path):
      path = os.path.abspath(os.path.join(options.build_dir, path))
    setattr(options, name, path)
    if not os.path.exists(path):
      parser.error('Could not find %s : %s' % (name, path))
    if should_update:
      UpdateAsanArtifact(options.full_directory, path)

  print 'Default BLACKLIST is: %r' % BLACKLIST

  return ApplyAsanToBuild(options.full_directory,
                          options.instrument_exe,
                          options.pdbfind_exe,
                          options.jobs)


if __name__ == '__main__':
  sys.exit(main())
