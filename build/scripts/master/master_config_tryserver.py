# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Shared configuration for the tryserver masters."""

# These modules come from scripts, which must be in the PYTHONPATH.
from master.factory import annotator_factory
from master.factory import chromium_factory


## BUILDER FACTORIES

m_chromium_win = chromium_factory.ChromiumFactory(
    'src/build',
    target_platform='win32')

m_chromium_win_ninja = chromium_factory.ChromiumFactory(
    'src/out',
    target_platform='win32')

m_chromium_linux = chromium_factory.ChromiumFactory(
    'src/out',
    target_platform='linux2')

m_chromium_linux_nohooks = chromium_factory.ChromiumFactory(
    'src/out',
    nohooks_on_update=True,
    target_platform='linux2')

m_chromium_mac = chromium_factory.ChromiumFactory(
    'src/xcodebuild',
    target_platform='darwin')

m_chromium_mac_ninja = chromium_factory.ChromiumFactory(
    'src/out',
    target_platform='darwin')

# Chromium for ChromiumOS
m_chromium_chromiumos = chromium_factory.ChromiumFactory(
    'src/out',
    target_platform='linux2')

m_chromium_android = chromium_factory.ChromiumFactory(
    '',
    target_platform='linux2',
    nohooks_on_update=True,
    target_os='android')

m_annotator = annotator_factory.AnnotatorFactory()

# Tests that are single-machine shard-safe.
sharded_tests = [
  'accessibility_unittests',
  'aura_unittests',
  'base_unittests',
  'browser_tests',
  'buildrunner_tests',
  'cacheinvalidation_unittests',
  'cast_unittests',
  'cc_unittests',
  'chromedriver_tests',
  'chromedriver_unittests',
  'components_unittests',
  'content_browsertests',
  'content_unittests',
  'crypto_unittests',
  'device_unittests',
  'events_unittests',
  'gcm_unit_tests',
  'google_apis_unittests',
  'gpu_unittests',
  'jingle_unittests',
  'media_unittests',
  'nacl_loader_unittests',
  'net_unittests',
  'ppapi_unittests',
  'printing_unittests',
  'remoting_unittests',
  'sync_integration_tests',
  'sync_unit_tests',
  'ui_unittests',
  'unit_tests',
  'views_unittests',
]

# http://crbug.com/157234
win_sharded_tests = sharded_tests[:]
win_sharded_tests.remove('sync_integration_tests')

def CreateBuilder(platform, builder_name, target,
                  options, tests,
                  slavebuilddir=None,
                  factory_properties=None,
                  annotation_script=None,
                  ninja=True,
                  goma=False,
                  clang=False,
                  clobber=False,
                  run_default_swarm_tests=None,
                  maxTime=8*60*60,
                  slave_type='Trybot',
                  build_url=None):
  """Generates and register a builder along with its slave(s)."""
  if platform not in ('win32', 'win64', 'linux', 'mac', 'android'):
    raise Exception(platform + ' is not a known os type')
  assert tests is not None or annotation_script, (
      'Must either specify tests or use an annotation script')

  factory_properties = (factory_properties or {}).copy()
  run_default_swarm_tests = run_default_swarm_tests or []

  factory_properties.setdefault('non_default', [
      'check_licenses',
      'chromedriver_tests',
      'courgette_unittests',
      'sync_integration_tests',
      'url_unittests',
    ])

  factory_properties.setdefault('gclient_env', {})
  factory_properties['gclient_env'].setdefault('GYP_DEFINES', '')
  factory_properties['gclient_env']['GYP_DEFINES'] += ' dcheck_always_on=1'
  if not 'fastbuild=0' in factory_properties['gclient_env']['GYP_DEFINES']:
    factory_properties['gclient_env']['GYP_DEFINES'] += ' fastbuild=1'
  if platform in ('win32', 'win64'):
    # http://crbug.com/157234
    factory_properties.setdefault('sharded_tests', win_sharded_tests)
  else:
    factory_properties.setdefault('sharded_tests', sharded_tests)

  build_tool = []
  if platform in ('win32', 'win64'):
    factory_properties['process_dumps'] = True
    factory_properties['start_crash_handler'] = True

    if ninja:
      factory = m_chromium_win_ninja
      factory_properties['gclient_env']['GYP_DEFINES'] += ' chromium_win_pch=0'
    else:
      factory = m_chromium_win

  elif platform == 'linux' and slave_type == 'TrybotTester':
    factory = m_chromium_linux_nohooks
  elif platform == 'linux':
    factory = m_chromium_linux
  elif platform == 'android':
    factory = m_chromium_android
  elif platform == 'mac':
    if ninja:
      factory = m_chromium_mac_ninja
    else:
      factory = m_chromium_mac

  if ninja:
    factory_properties['gclient_env']['GYP_GENERATORS'] = 'ninja'
    build_tool.append('--build-tool=ninja')
  if goma:
    if clang:
      build_tool.append('--compiler=goma-clang')
    else:
      build_tool.append('--compiler=goma')
  if clang:
    factory_properties['gclient_env']['GYP_DEFINES'] += ' clang=1'

  options = build_tool + ['--clobber-post-fail'] + (options or [])

  compile_timeout = 3600
  if annotation_script:
    # Note new slave type AnnotatedTrybot; we don't want a compile step added
    # in gclient_factory.py.
    # TODO(maruel): Support enable_swarm_tests
    builder_factory = factory.ChromiumAnnotationFactory(
        slave_type='AnnotatedTrybot', target=target, tests=tests,
        clobber=clobber,
        options=options,
        compile_timeout=compile_timeout,
        factory_properties=factory_properties,
        annotation_script=annotation_script, maxTime=maxTime)
  else:
    builder_factory = factory.ChromiumFactory(
        slave_type=slave_type, target=target, tests=tests, options=options,
        clobber=clobber,
        compile_timeout=compile_timeout,
        factory_properties=factory_properties,
        # Forcibly disable default swarming tests until the Swarming
        # infrastructure failure rate goes down to a reasonable level.
        # Tracked as http://crbug.com/354263
        # run_default_swarm_tests=run_default_swarm_tests,
        build_url=build_url)
  builder_info = {
    'name': builder_name,
    'factory': builder_factory,
  }
  if slavebuilddir:
    builder_info['slavebuilddir'] = slavebuilddir
  return builder_info


def prepend_type(prefix, test_list):
  """Prepend a prefix to a test name unless it's a special target.

  This is used to mark valgrind tests, such as valgrind_ash_unittests.
  """
  br_test = 'buildrunner_tests'
  return (
      ['%s_%s' % (prefix, value) for value in test_list if value != br_test] +
      filter(br_test.__eq__, test_list))  # Add back in buildrunner_tests.

def valgrind_tests(test_list):
  return prepend_type('valgrind', test_list)

def without_tests(tests, without):
  """Exclude tests from a list."""
  return [t for t in tests if t not in without]

# 32 bits tools can't link libwebcore.a anymore due to lack of virtual address
# space, including OSX 10.5.
valgrind_gyp_defines = (
    chromium_factory.ChromiumFactory.MEMORY_TOOLS_GYP_DEFINES + ' enable_svg=0')
# drmemory_gyp_defines = 'build_for_tool=drmemory'

nacl_sdk_script = 'nacl_sdk_buildbot_run.py'

nacl_sdk_script_build = 'src/native_client_sdk/src/build_tools/buildbot_run.py'
