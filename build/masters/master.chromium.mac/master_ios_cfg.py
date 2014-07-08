# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}
defaults['category'] = '3mac'

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

def ios():
  return chromium_factory.ChromiumFactory('src/xcodebuild', 'darwin')

#
# Main scheduler for src/
#
S('ios', branch='src', treeStableTimer=60)

#
# iOS Release iphoneos BuilderTester
#
B('iOS Device', 'ios_rel', gatekeeper='ios_rel', scheduler='ios',
  auto_reboot=True, notify_on_missing=True)
F('ios_rel', ios().ChromiumFactory(
  # TODO(lliabraa): Need to upstream support for running tests on devices
  # before we can actually run any tests.
  clobber=False,
  tests=[],
  options = [
    '--', '-project', '../build/all.xcodeproj',
    '-sdk', 'iphoneos7.0', '-target' , 'All'],
  factory_properties={
    'app_name': 'Chromium.app',
    'gclient_deps': 'ios',
    'gclient_env': {
      'GYP_DEFINES': 'component=static_library OS=ios chromium_ios_signing=0',
      'GYP_GENERATOR_FLAGS': 'xcode_project_version=3.2',
    },
  }))

#
# iOS Debug iphonesimulator BuilderTester
#
B('iOS Simulator (dbg)', 'ios_dbg', gatekeeper='ios_dbg', scheduler='ios',
  auto_reboot=True, notify_on_missing=True)
F('ios_dbg', ios().ChromiumFactory(
  clobber=True,
  target='Debug',
  tests=[
    'base_unittests',
    'components_unittests',
    'content_unittests',
    'crypto_unittests',
    'gfx_unittests',
    'net',
    'ui_unittests',
    'unit_sql',
    'unit_sync',
    'url_unittests',
  ],
  options = [
    '--', '-project', '../build/all.xcodeproj', '-sdk',
    'iphonesimulator7.0', '-target', 'All',],
  factory_properties={
    'app_name': 'Chromium.app',
    'test_platform': 'ios-simulator',
    'gclient_deps': 'ios',
    'gclient_env': {
      'GYP_DEFINES': 'component=static_library OS=ios chromium_ios_signing=0',
      'GYP_GENERATOR_FLAGS': 'xcode_project_version=3.2',
    },
  }))

#
# iOS Release iphoneos BuilderTester w/ ninja
#
B('iOS Device (ninja)', 'ios_rel_ninja', gatekeeper='ios_rel_ninja',
  scheduler='ios', auto_reboot=True, notify_on_missing=True)
F('ios_rel_ninja', ios().ChromiumFactory(
  # TODO(lliabraa): Need to upstream support for running tests on devices
  # before we can actually run any tests.
  clobber=False,
  target='Release-iphoneos',
  tests=[],
  options = ['--build-tool=ninja'],
  factory_properties={
    'app_name': 'Chromium.app',
    'gclient_deps': 'ios',
    'gclient_env': {
      'GYP_CROSSCOMPILE': '1',
      'GYP_GENERATORS': 'ninja',
      'GYP_DEFINES': 'component=static_library OS=ios target_subarch=both',
    },
  }))

def Update(config, active_master, c):
  return helper.Update(c)
