# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import json

DEPS = [
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
]

PERF_TESTS = [
  'blink_perf.animation',
  'canvasmark',
  'dromaeo.domcoreattr',
  'dromaeo.domcoremodify',
  'dromaeo.domcorequery',
  'dromaeo.domcoretraverse',
  'dromaeo.jslibattrjquery',
  'dromaeo.jslibattrprototype',
  'dromaeo.jslibeventjquery',
  'dromaeo.jslibeventprototype',
  'dromaeo.jslibmodifyjquery',
  'dromaeo.jslibmodifyprototype',
  'dromaeo.jslibstylejquery',
  'dromaeo.jslibstyleprototype',
  'dromaeo.jslibtraversejquery',
  'dromaeo.jslibtraverseprototype',
  'image_decoding.image_decoding_measurement',
  'kraken',
  'octane',
  'pica.pica',
  'spaceport',
  'sunspider',
]


def GenSteps(api):
  dashboard_upload_url = 'https://chromeperf.appspot.com'
  config_vals = {}
  config_vals.update(
    dict((str(k),v) for k,v in api.properties.iteritems() if k.isupper())
  )

  api.chromium.set_config('chromium', **config_vals)
  api.gclient.set_config('oilpan', **config_vals)

  api.chromium.c.gyp_env.GYP_DEFINES['linux_strip_binary'] = 1
  api.chromium.c.gyp_env.GYP_DEFINES['target_arch'] = 'x64'

  patch_exe = api.path['slave_build'].join('src', 'third_party', 'WebKit',
                                   'Source', 'apply_oilpan_patches.py')

  yield api.gclient.checkout(revert=True)
  yield (
    api.chromium.runhooks(),
    api.chromium.m.python('apply oilpan patches', patch_exe),
    api.chromium.compile(),
  )

  if api.chromium.c.HOST_PLATFORM == 'linux':
    build_exe = api.chromium.c.build_dir.join(api.chromium.c.build_config_fs,
                                              platform_ext={'win': '.exe'})
    test_dir = api.path['slave_build'].join('test')
    api.gclient.set_config('oilpan_internal', **config_vals)
    api.gclient.spec_alias = 'test_checkout'
    api.gclient.c.solutions[0].revision = 'HEAD'
    api.gclient.c.got_revision_mapping.clear()
    yield api.path.makedirs('test_checkout', test_dir)
    yield api.gclient.checkout(cwd=test_dir)

    test_out_dir = test_dir.join('src', 'out', api.chromium.c.build_config_fs)
    yield api.path.makedirs('test_out_dir', test_out_dir)
    yield api.python.inline(
      'copy minidump_stackwalk',
      """
      import shutil
      import sys
      shutil.copy(sys.argv[1], sys.argv[2])
      """,
      args=[build_exe.join('minidump_stackwalk'), test_out_dir]
    )

    results_dir = api.path['slave_build'].join('layout-test-results')
    test = api.path['build'].join('scripts', 'slave', 'chromium',
                          'layout_test_wrapper.py')
    args = ['--target', api.chromium.c.BUILD_CONFIG,
            '-o', results_dir,
            '--additional-expectations',
            api.path['checkout'].join('third_party', 'WebKit', 'LayoutTests',
                              'OilpanExpectations'),
            '--build-dir', api.chromium.c.build_dir]
    yield api.chromium.runtest(test, args, name='webkit_tests')

    factory_properties = {
      'blink_config':  'chromium',
      'browser_exe':  str(build_exe.join('chrome')),
      'build_dir':  'src/out',
      'expectations':  True,
      'halt_on_missing_build':  True,
      'show_perf_results':  True,
      'target':  'Release',
      'target_os':  None,
      'target_platform':  'linux2',
      'tools_dir':  str(test_dir.join('src', 'tools'))
    }

    for test in PERF_TESTS:
      factory_properties['test_name'] = test
      factory_properties['step_name'] = test
      fp = "--factory-properties=%s" % json.dumps(factory_properties)
      yield api.chromium.runtest(
          api.chromium.m.path['build'].join('scripts', 'slave', 'telemetry.py'),
          [fp], name=test, python_mode=True,
          results_url=dashboard_upload_url,
          annotate='graphing', perf_dashboard_id=test, test_type=test
      )

def GenTests(api):
  for plat in ('linux', 'win', 'mac'):
    yield (
      api.test('basic_%s' % plat) +
      api.properties.generic(TARGET_BITS=64, perf_id="%s-release" % plat) +
      api.platform(plat, 64)
    )
