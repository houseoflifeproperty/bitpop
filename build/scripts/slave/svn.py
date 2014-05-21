#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Perform various operations on an SVN checkout.
"""

import re
import subprocess

from slave import slave_utils

# workaround for the fact that default list arguments are dangerous in python
DEFAULT_ADDITIONAL_SVN_FLAGS = ['--no-auth-cache', '--non-interactive']

def CreateCheckout(repo_url, local_dir, username, password,
                   additional_svn_flags=None):
  """Check out a local copy of an SVN repository and return an Svn object
  pointing at its root directory.

  @param repo_url URL pointing at the SVN repository to check out
  @param local_dir directory within which to create the local copy
  @param username SVN username
  @param password SVN password
  @param additional_svn_flags list of flags to pass to every svn operation
         (if None, uses DEFAULT_ADDITIONAL_SVN_FLAGS)
  """
  local_repo = Svn(directory=local_dir, username=username, password=password,
                   additional_svn_flags=additional_svn_flags)
  local_repo.Checkout(repo_url, '.')
  return local_repo

class Svn(object):

  def __init__(self, directory, username, password, additional_svn_flags=None):
    """Set up to manipulate SVN control within the given directory.

    @param directory directory within which to perform SVN operations
    @param username SVN username
    @param password SVN password
    @param additional_svn_flags list of flags to pass to every svn operation
           (if None, uses DEFAULT_ADDITIONAL_SVN_FLAGS)
    """
    self._directory = directory
    self._username = username
    self._password = password
    self._svn_binary = slave_utils.SubversionExe()
    # workaround for the fact that default list args are dangerous in python
    if additional_svn_flags is None:
      self._additional_svn_flags = DEFAULT_ADDITIONAL_SVN_FLAGS
    else:
      self._additional_svn_flags = additional_svn_flags

  def _RunCommand(self, args):
    """Run a command (from self._directory) and return stdout as a single
    string.

    @param args a list of arguments
    """
    proc = subprocess.Popen(args, cwd=self._directory,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = proc.communicate()
    returncode = proc.returncode
    if returncode is not 0:
      # Don't include the command in the exception message, because it might
      # contain the SVN password.
      raise Exception('command failed in dir "%s" (returncode=%s): %s' %
                      (self._directory, returncode, stderr))
    return stdout

  def _RunSvnCommand(self, args):
    """Run an SVN command (from self._directory) and return stdout as a single
    string.

    @param args a list of arguments
    """
    print 'running svn command %s in directory %s' % (args, self._directory)
    return self._RunCommand([self._svn_binary, '--username', self._username,
                             '--password', self._password]
                            + self._additional_svn_flags + args)

  def Checkout(self, url, path):
    """Check out a working copy from a repository.
    Returns stdout as a single string.

    @param url URL from which to check out the working copy
    @param path path (within self._directory) where the local copy will be
           written
    """
    return self._RunSvnCommand(['checkout', url, path])

  def Commit(self, message):
    """Commit the working copy to the repository.
    Returns stdout as a single string.

    @param message commit message
    """
    return self._RunSvnCommand(['commit', '--message', message])

  def GetNewFiles(self):
    """Return a list of files which are in this directory but NOT under
    SVN control.
    """
    stdout = self._RunSvnCommand(['status'])
    new_regex = re.compile('^\?.....\s+(.+)$', re.MULTILINE)
    files = new_regex.findall(stdout)
    return files

  def GetNewAndModifiedFiles(self):
    """Return a list of files in this dir which are newly added or modified,
    including those that are not (yet) under SVN control.
    """
    stdout = self._RunSvnCommand(['status'])
    new_regex = re.compile('^[AM\?].....\s+(.+)$', re.MULTILINE)
    files = new_regex.findall(stdout)
    return files

  def AddFiles(self, filenames):
    """Adds these files to SVN control.
    Returns stdout as a single string.

    @param filenames files to add to SVN control
    """
    if filenames:
      return self._RunSvnCommand(['add'] + filenames)

  def SetProperty(self, filenames, property_name, property_value):
    """Sets a svn property for these files.
    Returns stdout as a single string.

    @param filenames files to set property on
    @param property_name property_name to set for each file
    @param property_value what to set the property_name to
    """
    if filenames:
      return self._RunSvnCommand(
          ['propset', property_name, property_value] + filenames)

  def SetPropertyByFilenamePattern(self, filename_pattern,
                                   property_name, property_value):
    """Sets a svn property for all files matching filename_pattern.
    Returns stdout as a single string.

    @param filename_pattern set the property for all files whose names match
           this Unix-style filename pattern (e.g., '*.jpg')
    @param property_name property_name to set for each file
    @param property_value what to set the property_name to
    """
    return self.SetProperty([filename_pattern], property_name, property_value)
