# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the v8 master BuildFactory's.

Based on gclient_factory.py and adds v8-specific steps."""

from master.factory import v8_commands
from master.factory import gclient_factory
import config


class V8Factory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the v8 master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  CUSTOM_DEPS_VALGRIND = ('src/third_party/valgrind',
                          config.Master.trunk_url +
                          '/deps/third_party/valgrind/binaries')

  # TODO(jkummerow): Figure out if this is actually needed.
  CUSTOM_DEPS_WIN7SDK = (
      'third_party/win7sdk',
      '%s/third_party/platformsdk_win7/files' %
      config.Master.trunk_internal_url)

  CUSTOM_DEPS_MOZILLA = ('v8/test/mozilla/data',
                          config.Master.trunk_url +
                          '/deps/third_party/mozilla-tests')

  def __init__(self, build_dir, target_platform=None,
               branch='branches/bleeding_edge'):
    self.checkout_url = config.Master.v8_url + '/' + branch

    main = gclient_factory.GClientSolution(self.checkout_url, name='v8')
    custom_deps_list = [main]

    gclient_factory.GClientFactory.__init__(self, build_dir, custom_deps_list,
                                            target_platform=target_platform)

  @staticmethod
  def _AddTests(factory_cmd_obj, tests, mode=None, factory_properties=None,
                target_arch=None):
    """Add the tests listed in 'tests' to the factory_cmd_obj."""
    factory_properties = factory_properties or {}

    # Small helper function to check if we should run a test
    def R(test):
      return gclient_factory.ShouldRunTest(tests, test)

    f = factory_cmd_obj
    if R('presubmit'): f.AddPresubmitTest()
    if R('v8initializers'): f.AddV8Initializers()
    if R('v8testing'): f.AddV8Testing()
    if R('fuzz'): f.AddFuzzer()
    if R('test262'): f.AddV8Test262()
    if R('mozilla'): f.AddV8Mozilla()
    if R('gcmole'): f.AddV8GCMole()

  def V8Factory(self, target='Release', clobber=False, tests=None, mode=None,
                slave_type='BuilderTester', options=None, compile_timeout=1200,
                build_url=None, project=None, factory_properties=None,
                target_arch=None, shard_count=1,
                shard_run=1, shell_flags=None, isolates=False):
    tests = tests or []
    factory_properties = factory_properties or {}

    # Automatically set v8_target_arch in GYP_DEFINES to target_arch.
    if not 'gclient_env' in factory_properties:
      factory_properties['gclient_env'] = {}
    gclient_env = factory_properties['gclient_env']
    if 'GYP_DEFINES' in gclient_env:
      gclient_env['GYP_DEFINES'] += " v8_target_arch=%s" % target_arch
    else:
      gclient_env['GYP_DEFINES'] = "v8_target_arch=%s" % target_arch

    if (self._target_platform == 'win32'):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_WIN7SDK)

    if (gclient_factory.ShouldRunTest(tests, 'leak')):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_VALGRIND)

    if (gclient_factory.ShouldRunTest(tests, 'mozilla')):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_MOZILLA)

    if (gclient_factory.ShouldRunTest(tests, 'arm')):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_MOZILLA)

    factory = self.BuildFactory(target=target, clobber=clobber, tests=tests,
                                mode=mode,
                                slave_type=slave_type,
                                options=options,
                                compile_timeout=compile_timeout,
                                build_url=build_url,
                                project=project,
                                factory_properties=factory_properties,
                                target_arch=target_arch)

    # Get the factory command object to create new steps to the factory.
    # Note - we give '' as build_dir as we use our own build in test tools
    v8_cmd_obj = v8_commands.V8Commands(factory,
                                        target,
                                        '',
                                        self._target_platform,
                                        target_arch,
                                        shard_count,
                                        shard_run,
                                        shell_flags,
                                        isolates)
    if factory_properties.get('archive_build'):
      v8_cmd_obj.AddArchiveBuild(
          extra_archive_paths=factory_properties.get('extra_archive_paths'))

    # This is for the arm tester board (we don't have other pure tester slaves).
    if (slave_type == 'Tester'):
      v8_cmd_obj.AddMoveExtracted()

    # Add all the tests.
    self._AddTests(v8_cmd_obj, tests, mode, factory_properties)
    return factory
