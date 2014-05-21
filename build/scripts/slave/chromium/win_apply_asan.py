#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import multiprocessing
import optparse
import os
import shutil
import subprocess
import sys


SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
BLACKLIST = set((
    'crnss.dll',
    'gpu.dll',
    'icuuc.dll',
    'nacl.exe',
    'nacl64.exe',
    'sql.dll',
))


class ASANitizer(object):
  def __init__(self, instrument_exe, stopped):
    self.instrument_exe = instrument_exe
    self.stopped = stopped

  def __call__(self, job):
    retval = 0
    stdout = ''
    pe_image, pdb = job

    try:
      if not self.stopped.is_set():
        out_pe = AddExtensionComponent(pe_image, 'asan')
        out_pdb = AddExtensionComponent(pdb, 'asan')

        # Note that instrument.exe requires --foo=bar format (including the '=')
        command = [
            self.instrument_exe, '--mode=ASAN',
            '--input-image=%s' % pe_image,
            '--output-image=%s' % out_pe,
            '--output-pdb=%s' % out_pdb,
            '2>&1'  # Combine stderr+stdout so that they're in order
        ]

        for fname in filter(os.path.exists, (out_pe, out_pdb)):
          os.remove(fname)

        proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        stdout, _ = proc.communicate()
        retval = proc.returncode

      return (retval, stdout, pe_image)
    except Exception:
      import traceback
      return (1, stdout+'\n'+traceback.format_exc(), pe_image)


def AddExtensionComponent(path, new_ext):
  """Prepends new_ext to the existing extension.

  >>> ChangeExtension('hello.foo.dll', 'asan')
  'hello.asan.foo.dll'
  """
  # Don't use os.path.splitext, because it will split on the rightmost dot
  # instead of the leftmost dot.
  base, ext = path.split('.', 1)
  return base + '.' + new_ext + '.' + ext


def UpdateAsanRuntime(full_directory, runtime_path):
  """Updates the ASAN runtime dll in the build directory, if it exists."""
  runtime = os.path.join(full_directory, os.path.basename(runtime_path))

  if os.path.exists(runtime):
    print('Removing', runtime)
    os.remove(runtime)

  print 'Copying %s -> %s' % (runtime_path, runtime)
  shutil.copy2(runtime_path, runtime)

  fname = os.path.basename(runtime_path)
  print 'Blacklisting %s' % fname
  BLACKLIST.add(fname)


def GetCompatiblePDB(pe_image):
  """Returns <path to pdb> or None (if no good pdb exists)."""
  # TODO(iannucci): Use PE header to look up pdb name.
  # for now, assume that the pdb is always just PE.pdb
  pdb_path = pe_image+'.pdb'
  return pdb_path if os.path.exists(pdb_path) else None


def FindFilesToAsan(directory):
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

  for root, _, files in os.walk(directory):
    for pe_image in (os.path.join(root, f) for f in files if GoodExeOrDll(f)):
      pdb = GetCompatiblePDB(pe_image)
      if not pdb:
        print >> sys.stderr, 'PDB for "%s" does not exist.' % pe_image
        continue

      ret.append((pe_image, pdb))
  return ret


def ApplyAsanToBuild(full_directory, instrument_exe, jobs):
  """Applies ASAN to all exe's/dll's in the build directory."""
  to_asan = FindFilesToAsan(full_directory)

  if not to_asan:
    print >> sys.stderr, 'No files to ASAN!'
    return 1

  manager = multiprocessing.Manager()
  stopped = manager.Event()
  sanitizer = ASANitizer(instrument_exe, stopped)
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
  default_runtime_path = os.path.join(default_asan_dir, 'asan_rtl.dll')

  parser = optparse.OptionParser()
  parser.add_option(
      '--build-dir',
      help='Path to the build directory to asan (required).')
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
      '--runtime_path', default=default_runtime_path,
      help='Specify the path to the ASAN runtime DLL relative to '
           'build-dir (%default).')
  options, args = parser.parse_args()
  options.build_dir = os.path.abspath(options.build_dir)

  if not options.build_dir:
    parser.error('Must specify --build-dir')
  if not options.target:
    parser.error('Must specify --target')
  if args:
    parser.error('Not expecting additional arguments')

  options.full_directory = os.path.join(options.build_dir, options.target)
  if not os.path.exists(options.full_directory):
    parser.error('Could not find directory: %s' % options.full_directory)
  options.instrument_exe = os.path.join(
      options.build_dir, options.instrument_exe)
  if not os.path.exists(options.instrument_exe):
    parser.error('Could not find instrument_exe: %s' % options.instrument_exe)
  options.runtime_path = os.path.join(
      options.build_dir, options.runtime_path)
  if not os.path.exists(options.runtime_path):
    parser.error('Could not find runtime_path: %s' % options.runtime_path)

  print 'Default BLACKLIST is: %r' % BLACKLIST

  UpdateAsanRuntime(options.full_directory, options.runtime_path)
  return ApplyAsanToBuild(
      options.full_directory, options.instrument_exe, options.jobs)


if __name__ == '__main__':
  sys.exit(main())