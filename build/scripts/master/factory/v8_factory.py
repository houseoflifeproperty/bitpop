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
               branch='branches/bleeding_edge',
               custom_deps_list=None):
    self.checkout_url = config.Master.v8_url + '/' + branch

    main = gclient_factory.GClientSolution(self.checkout_url, name='v8',
                                           custom_deps_list=custom_deps_list)
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
    if R('v8testing'):
      f.AddV8TestTC('mjsunit fuzz-natives cctest message preparser', 'Check')
    if R('v8try'):
      f.AddV8Test('mjsunit fuzz-natives cctest message preparser', 'Check',
                  options=['--quickcheck'])
    if R('experimental_parser'):
      f.AddV8TestTC('', 'CheckParser')
    if R('mjsunit'):
      f.AddV8TestTC('mjsunit', 'Mjsunit')
    if R('optimize_for_size'):
      f.AddV8TestTC('cctest mjsunit webkit', 'OptimizeForSize',
                    options=['--no-variants',
                             '--shell_flags="--optimize-for-size"'])
    if R('fuzz'): f.AddFuzzer()
    if R('deopt'): f.AddDeoptFuzzer()
    if R('webkit'): f.AddV8TestTC('webkit', 'Webkit')
    if R('benchmarks'): f.AddV8Test('benchmarks', 'Benchmarks')
    if R('test262'): f.AddV8Test('test262', 'Test262')
    if R('mozilla'): f.AddV8Test('mozilla', 'Mozilla')
    if R('gcmole'): f.AddV8GCMole()
    if R('simpleleak'): f.AddSimpleLeakTest()

  def V8Factory(self, target='Release', clobber=False, tests=None, mode=None,
                slave_type='BuilderTester', options=None, compile_timeout=1200,
                build_url=None, project=None, factory_properties=None,
                target_arch=None, shard_count=1,
                shard_run=1, shell_flags=None, isolates=False,
                command_prefix=None):
    tests = tests or []
    factory_properties = (factory_properties or {}).copy()

    # Automatically set v8_target_arch in GYP_DEFINES to target_arch.
    if not 'gclient_env' in factory_properties:
      factory_properties['gclient_env'] = {}
    gclient_env = factory_properties['gclient_env'].copy()
    factory_properties['gclient_env'] = gclient_env
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

    test_env = factory_properties.get('test_env', {})
    test_options = factory_properties.get('test_options', [])

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
                                        isolates,
                                        command_prefix,
                                        test_env=test_env,
                                        test_options=test_options)
    if factory_properties.get('archive_build'):
      v8_cmd_obj.AddArchiveBuild(
          extra_archive_paths=factory_properties.get('extra_archive_paths'))

    # Add a trigger step if needed.
    self.TriggerFactory(factory, slave_type=slave_type,
                        factory_properties=factory_properties)

    # Add all the tests.
    self._AddTests(v8_cmd_obj, tests, mode, factory_properties)
    return factory

  def V8LinuxBuilderFactory(self, target, target_arch, gclient_env, build_url,
                            trigger):
    return self.V8Factory(
        slave_type='Builder',
        options=['--build-tool=make', '--src-dir=v8'],
        target=target,
        factory_properties={
          'build_url': build_url,
          'trigger': trigger,
          'gclient_env': gclient_env,
          'trigger_set_properties': {'parent_cr_revision': None},
          'zip_build_src_dir': 'v8',
        },
        target_arch=target_arch)

  def V8Linux32BuilderFactory(self, target, gclient_env, build_url, trigger):
    return self.V8LinuxBuilderFactory(target, 'ia32', gclient_env, build_url,
                                      trigger)

  def V8Linux64BuilderFactory(self, target, gclient_env, build_url, trigger):
    return self.V8LinuxBuilderFactory(target, 'x64', gclient_env, build_url,
                                      trigger)

  def V8TesterFactory(self, target, build_url, factory_properties=None, *args,
                      **kwargs):
    factory_properties = factory_properties or {}
    factory_properties['extract_build_src_dir'] = 'v8'
    return self.V8Factory(
        slave_type='Tester',
        target=target,
        build_url=build_url,
        factory_properties=factory_properties,
        *args, **kwargs)
