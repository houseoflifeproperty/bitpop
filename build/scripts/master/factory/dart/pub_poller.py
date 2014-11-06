# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This PollingChangeSource polls pub for new versions of a given set of
packages.

Whenever there is a new version we will trigger a new change.
"""
import json

import traceback
from twisted.internet import defer
from twisted.python import log
from twisted.web.client import getPage

from buildbot.changes import base
from master.factory.dart import semantic_version

VALUE_NOT_SET = -1

class PubPoller(base.PollingChangeSource):
  """Poll a set of pub packages for changes"""

  def __init__(self, packages, pollInterval=5*60, project=None):
    self.packages = packages
    self.pollInterval = pollInterval
    self.project = project
    log.msg("poll interval %s" % pollInterval)
    self.num_versions = {}

  def describe(self):
    return 'Watching pub packages %s' % self.packages

  def make_change(self, package, version):
    self.master.addChange(author='Pub: %s' % package,
                          files=[],
                          comments='Polled from %s' % package,
                          project=self.project,
                          revision=version)

  # pub.dartlang.org is returning the versions in non sorted order
  # We sort them using the same semantic version class that pub uses
  @staticmethod
  def find_new_version(versions):
    return str(max([semantic_version.SemanticVersion(v) for v in versions]))

  @defer.inlineCallbacks
  def poll(self):
    log.msg('Polling all packages on pub')
    for package in self.packages:
      try:
        info = yield self.poll_package(package)
        package_info = json.loads(info)
        count = len(package_info['versions'])
        # If we could not set the initial value, set it now
        if self.num_versions[package] == VALUE_NOT_SET:
          log.msg('Delayed set of initial value for %s' % package)
          self.num_versions[package] = count
        elif self.num_versions[package] != count:
          log.msg('Package %s has new version' % package)
          self.num_versions[package] = count
          version = self.find_new_version(package_info['versions'])
          self.make_change(package, version)
      except Exception :
        log.msg('Could not get version for package %s: %s' %
                (package, traceback.format_exc()))

  def poll_package(self, package):
    poll_url = 'http://pub.dartlang.org/packages/%s?format=json' % package
    log.msg('Polling pub package %s from %s' % (package, poll_url))
    return getPage(poll_url, timeout=self.pollInterval)

  @defer.inlineCallbacks
  def startService(self):
    # Get initial version when starting to poll
    for package in self.packages:
      log.msg("doing initial poll for package %s" % package)
      try:
        info = yield self.poll_package(package)
        package_info = json.loads(info)
        count = len(package_info['versions'])
        log.msg('Initial count for %s is %s' % (package, count))
        log.msg('Initial version: %s' %
                self.find_new_version(package_info['versions']))
        self.num_versions[package] = count
      except Exception :
        log.msg('Could not set initial value for package %s %s' %
                (package, traceback.format_exc()))
        self.num_versions[package] = VALUE_NOT_SET
    base.PollingChangeSource.startService(self)

