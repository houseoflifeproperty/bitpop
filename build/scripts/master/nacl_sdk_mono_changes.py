#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This script is used to trigger master.client.nacl.sdk.mono.

This script currently monitors github.com/elijahtaylor/mono.git and
the latest version of the nacl sdk uploaded.

It requires:
  - gsutil credentials to scan for the sdk
"""

import re
import subprocess

from twisted.cred import credentials
from twisted.internet import reactor
from twisted.spread import pb


MONO_GIT_URL = 'git://github.com/elijahtaylor/mono.git'
LAST_VERSION_FILENAME = 'last_trigger.txt'


def LatestSDKVersion():
  """Get the latest svn revision for which the nacl sdk has been archive.

  Returns:
    A string containing latest nacl sdk revision that has been archive for
    linux.
  """
  p = subprocess.Popen([
      'gsutil', 'ls',
      'gs://nativeclient-mirror/nacl/nacl_sdk/trunk.*/naclsdk_linux.tar.bz2'],
      stdout=subprocess.PIPE)
  p_stdout, _ = p.communicate()
  assert p.returncode == 0
  versions = str(p_stdout).splitlines()
  latest = None
  for version in versions:
    m = re.match('gs\:\/\/nativeclient\-mirror\/nacl\/nacl_sdk\/'
                 'trunk\.(.*)/naclsdk_linux.tar.bz2', version)
    svn_rev = int(m.group(1))
    if not latest or svn_rev > latest:
      latest = svn_rev
  assert latest
  return str(latest)


def LatestMonoRevision():
  """Get the git hash of the head revision from the mono repo.

  Returns:
    The git hash of the latest revision from the mono repo.
  """
  p = subprocess.Popen([
      'git', 'ls-remote', MONO_GIT_URL, 'refs/heads/master'
  ], stdout=subprocess.PIPE)
  p_stdout, _ = p.communicate()
  parts = str(p_stdout).rstrip().split('\t')
  assert parts[1] == 'refs/heads/master'
  return parts[0]


def GetCurrentVersion():
  """Return the complete version string for the latest version.

  Returns:
    A version string: SDK_REV:MONO_GIT_REV
  """
  return LatestSDKVersion() + ':' + LatestMonoRevision()


def NeedTrigger(version):
  """Detect if a new version of the client.nacl.sdk.mono build need to happen.

  Returns:
    A version string for the latest version if new, or None otherwise.
  """
  # Get last trigger reason.
  try:
    fh = open(LAST_VERSION_FILENAME, 'r')
    last = fh.read()
    fh.close()
  except IOError:
    last = None
  # Check that the syntax is as expected.
  assert not last or re.match('[0-9]+:[0-9a-f]', last)
  return version != last


def UpdateStamp(version):
  """Update last trigger stamp to a new version.

  Args:
    version: version string to save.
  """
  fh = open(LAST_VERSION_FILENAME, 'w')
  fh.write(version)
  fh.close()


def Trigger(version):
  """Trigger the client.nacl.sdk.mono waterfall for a given version.

  Args:
    version: The version number to trigger at.
  """
  def Done(*args):
    reactor.stop()

  def Err(*args):
    reactor.stop()
    assert False

  def SendChange(remote):
    change = {
        'who': 'chrome-bot@google.com',
        'files': [],
        'revision': version,
        'comments': 'Triggered by automated script',
        }
    d = remote.callRemote('addChange', change)
    d.addCallback(Done)

  f = pb.PBClientFactory()
  d = f.login(credentials.UsernamePassword('change', 'changepw'))
  reactor.connectTCP('localhost', 8150, f)
  # Use this for local testing:
  #reactor.connectTCP('localhost', 9148, f)
  d.addCallback(SendChange).addErrback(Err)
  reactor.run()


def Main():
  version = GetCurrentVersion()
  if NeedTrigger(version):
    Trigger(version)
    UpdateStamp(version)


if __name__ == '__main__':
  Main()
