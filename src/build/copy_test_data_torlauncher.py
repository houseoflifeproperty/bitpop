#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Copies test data files or directories into a given output directory."""

import optparse
import os
import shutil
import sys

class WrongNumberOfArgumentsException(Exception):
  pass

def EscapePath(path):
  """Returns a path with spaces escaped."""
  return path.replace(" ", "\\ ")

def ListFilesForPath(path):
  """Returns a list of all the files under a given path."""
  output = []
  # Ignore revision control metadata directories.
  if (os.path.basename(path).startswith('.git') or
      os.path.basename(path).startswith('.svn')):
    return output

  # Files get returned without modification.
  if not os.path.isdir(path):
    output.append(path)
    return output

  # Directories get recursively expanded.
  contents = os.listdir(path)
  for item in contents:
    full_path = os.path.join(path, item)
    output.extend(ListFilesForPath(full_path))
  return output

def CalcInputs(inputs):
  """Computes the full list of input files for a set of command-line arguments.
  """
  # |inputs| is a list of paths, which may be directories.
  output = []
  for input in inputs:
    output.extend(ListFilesForPath(input))
  return output

def CalcOutputs(inputs):
  # |inputs| is a list of paths, which must be directories.
  output = []
  for input in inputs:
    files = ListFilesForPath(input)
    mod_files = []
    for f in files:
      mod_files.append(f[len(input):len(f)])

    output.extend(mod_files)
  return output

def CopyFiles(input_filenames, relative_filenames, output_basedir):
  """Copies files to the given output directory."""
  for i in range(len(relative_filenames)):
    file = relative_filenames[i]
    relative_dirname = os.path.dirname(file)
    output_dir = os.path.join(output_basedir, relative_dirname)
    output_filename = os.path.join(output_basedir, file)

    # In cases where a directory has turned into a file or vice versa, delete it
    # before copying it below.
    if os.path.exists(output_dir) and not os.path.isdir(output_dir):
      os.remove(output_dir)
    if os.path.exists(output_filename) and os.path.isdir(output_filename):
      shutil.rmtree(output_filename)

    if not os.path.exists(output_dir):
      os.makedirs(output_dir)

    # print >>sys.stderr, input_filenames[i], output_filename
    shutil.copy(input_filenames[i], output_filename)

def DoMain(argv):
  parser = optparse.OptionParser()
  usage = 'Usage: %prog -o <output_dir> [--inputs] [--outputs] <input_files>'
  parser.set_usage(usage)
  parser.add_option('-o', dest='output_dir')
  parser.add_option('--inputs', action='store_true', dest='list_inputs')
  parser.add_option('--outputs', action='store_true', dest='list_outputs')
  options, arglist = parser.parse_args(argv)

  if len(arglist) == 0:
    raise WrongNumberOfArgumentsException('<input_files> required.')

  files_to_copy = CalcInputs(arglist)
  escaped_files = [EscapePath(x) for x in CalcInputs(arglist)]
  if options.list_inputs:
    return '\n'.join(escaped_files)

  if not options.output_dir:
    raise WrongNumberOfArgumentsException('-o required.')

  dst_files = CalcOutputs(arglist)
  escaped_dst_files = [EscapePath(x) for x in CalcOutputs(arglist)]
  if options.list_outputs:
    outputs = [os.path.join(options.output_dir, x) for x in escaped_dst_files]
    return '\n'.join(outputs)

  CopyFiles(files_to_copy, dst_files, options.output_dir)
  return

def main(argv):
  try:
    result = DoMain(argv[1:])
  except WrongNumberOfArgumentsException, e:
    print >>sys.stderr, e
    return 1
  if result:
    print result
  return 0

if __name__ == '__main__':
  sys.exit(main(sys.argv))
