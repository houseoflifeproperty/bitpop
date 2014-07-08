# Copyright 2014 The Chromium Authors. All rights reserved.
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
  config_vals = {}
  config_vals.update(
    dict((str(k),v) for k,v in api.properties.iteritems() if k.isupper())
  )

  api.chromium.set_config('chromium', **config_vals)

  api.chromium.c.gyp_env.GYP_GENERATORS.add('ninja')
  api.chromium.c.gyp_env.GYP_DEFINES['linux_strip_binary'] = 1

  s = api.gclient.c.solutions[0]

  USE_MIRROR = api.gclient.c.USE_MIRROR
  def DartRepositoryURL(*pieces):
    BASES = ('https://dart.googlecode.com/svn',
             'svn://svn-mirror.golo.chromium.org/dart')
    return '/'.join((BASES[USE_MIRROR],) + pieces)

  deps_name = api.properties.get('deps', 'dartium.deps')
  s.url = DartRepositoryURL('branches', 'bleeding_edge', 'deps', deps_name)
  s.name = deps_name
  s.custom_deps = api.properties.get('gclient_custom_deps') or {}
  s.revision = api.properties.get('revision')
  api.gclient.c.got_revision_mapping.pop('src', None)
  api.gclient.c.got_revision_mapping['src/dart'] = 'got_revision'
  if USE_MIRROR:
    s.custom_vars.update({
      'dartium_base': 'svn://svn-mirror.golo.chromium.org'})

  yield api.gclient.checkout()

  # gclient api incorrectly sets Path('[CHECKOUT]') to build/src/dartium.deps
  # because Dartium has its DEPS file in dartium.deps, not directly in src.
  api.path['checkout'] = api.path['slave_build'].join('src')

  yield api.chromium.runhooks()
  yield api.python('fetch_reference_build',
                   api.path['checkout'].join('dart', 'tools', 'bots',
                                     'fetch_reference_build.py'))
  yield api.chromium.compile()

  results_dir = api.path['slave_build'].join('layout-test-results')
  test = api.path['build'].join('scripts', 'slave', 'chromium',
                        'layout_test_wrapper.py')
  args = ['--target', api.chromium.c.BUILD_CONFIG,
          '-o', results_dir,
          '--build-dir', api.chromium.c.build_dir]
  yield api.chromium.runtest(test, args, name='webkit_tests')

  dashboard_upload_url = 'https://chromeperf.appspot.com'
  build_exe = api.chromium.c.build_dir.join(api.chromium.c.build_config_fs)
  target_platform = {'linux': 'linux2',
                     'mac': 'darwin',
                     'win': 'win32'}[api.platform.name]
  browser_exe = {'linux': 'chrome',
                 'mac': 'Chromium.app/Contents/MacOS/Chromium',
                 'win': 'chrome.exe'}[api.platform.name]
  factory_properties = {
    'blink_config':  'chromium',
    'browser_exe':  str(build_exe.join(browser_exe)),
    'build_dir':  'src/out',
    'expectations':  True,
    'halt_on_missing_build':  True,
    'run_reference_build': True,
    'show_perf_results':  True,
    'target':  'Release',
    'target_os':  None,
    'target_platform':  target_platform,
    'tools_dir':  str(api.path['slave_build'].join('src', 'tools')),
  }
  if 'reference_build_executable' in api.properties:
    factory_properties['reference_build_executable'] = api.properties[
        'reference_build_executable']

  for test in PERF_TESTS:
    factory_properties['test_name'] = test
    factory_properties['step_name'] = test
    fp = "--factory-properties=%s" % json.dumps(factory_properties)
    yield api.chromium.runtest(
        api.chromium.m.path['build'].join('scripts', 'slave', 'telemetry.py'),
        [fp], name=test, python_mode=True,
        results_url=dashboard_upload_url,
        annotate='graphing', perf_dashboard_id=test, test_type=test,
        revision=s.revision,
        perf_id='dartium-linux-release',
    )


def GenTests(api):
  for plat in ('win', 'mac', 'linux'):
    for bits in (64,):
      for use_mirror in (True, False):
        yield (
          api.test('basic_%s_%s_Mirror%s' % (plat, bits, use_mirror)) +
          api.properties.generic(
              TARGET_BITS=bits,
              USE_MIRROR=use_mirror,
              perf_id='dartium-linux-release',
              deps='dartium.deps',
              revision='12345',
              reference_build_executable='src/chrome/tools/refbuild/chrome') +
          api.platform(plat, bits)
      )
