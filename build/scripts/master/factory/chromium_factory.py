# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the chromium master BuildFactory's.

Based on gclient_factory.py and adds chromium-specific steps."""

import os
import re

from master.factory import chromium_commands
from master.factory import gclient_factory
from master.factory.build_factory import BuildFactory

import config


def ForceComponent(target, project, gclient_env):
  # Force all bots to specify the "Component" gyp variables, unless it is
  # already set.
  gyp_defines = gclient_env.setdefault('GYP_DEFINES', '')
  if ('component=' not in gyp_defines and
      # build_for_tool=drmemory wants the component build (crbug.com/137180).
      'build_for_tool=memcheck' not in gyp_defines and
      'build_for_tool=tsan' not in gyp_defines):
    if target == 'Debug':
      component = 'shared_library'
    else:
      component = 'static_library'
    gclient_env['GYP_DEFINES'] = gyp_defines + ' component=' + component


class ChromiumFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the chromium master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  # TODO(rnk): crbug.com/109780, delete this once we've tested that
  # build_for_tool= works on the FYI bots.
  MEMORY_TOOLS_GYP_DEFINES = (
    # gcc flags
    'mac_debug_optimization=1 '
    'mac_release_optimization=1 '
    'release_optimize=1 '
    'no_gc_sections=1 '
    'debug_extra_cflags="-g -fno-inline -fno-omit-frame-pointer '
                        '-fno-builtin -fno-optimize-sibling-calls" '
    'release_extra_cflags="-g -fno-inline -fno-omit-frame-pointer '
                          '-fno-builtin -fno-optimize-sibling-calls" '

    # MSVS flags
    'win_debug_RuntimeChecks=0 '
    'win_debug_disable_iterator_debugging=1 '
    'win_debug_Optimization=1 '
    'win_debug_InlineFunctionExpansion=0 '
    'win_release_InlineFunctionExpansion=0 '
    'win_release_OmitFramePointers=0 '

    'linux_use_tcmalloc=1 '
    'release_valgrind_build=1 '
    'werror= '
    'component=static_library '
    'use_system_zlib=0 '
  )

  # gclient custom vars
  CUSTOM_VARS_GOOGLECODE_URL = ('googlecode_url', config.Master.googlecode_url)
  CUSTOM_VARS_SOURCEFORGE_URL = ('sourceforge_url',
                                 config.Master.sourceforge_url)
  CUSTOM_VARS_WEBKIT_MIRROR = ('webkit_trunk', config.Master.webkit_trunk_url)
  # $$WK_REV$$ below will be substituted with the revision that triggered the
  # build in chromium_step.py@GClient.startVC. Use this only with builds
  # triggered by a webkit poller.
  CUSTOM_VARS_WEBKIT_LATEST = [('webkit_revision', '$$WK_REV$$')]
  CUSTOM_VARS_NACL_TRUNK_URL = ('nacl_trunk', config.Master.nacl_trunk_url)
  # safe sync urls
  SAFESYNC_URL_CHROMIUM = 'http://chromium-status.appspot.com/lkgr'

  # gclient additional custom deps
  CUSTOM_DEPS_V8_LATEST = ('src/v8',
    'http://v8.googlecode.com/svn/branches/bleeding_edge')
  CUSTOM_DEPS_WEBRTC_LATEST = ('src/third_party/webrtc',
    config.Master.webrtc_url + 'trunk/webrtc')
  CUSTOM_DEPS_AVPERF = ('src/chrome/test/data/media/avperf',
    config.Master.trunk_url + '/deps/avperf')
  CUSTOM_VARS_NACL_LATEST = [
    ('nacl_revision', '$$NACL_REV$$'),
  ]
  CUSTOM_DEPS_VALGRIND = ('src/third_party/valgrind',
     config.Master.trunk_url + '/deps/third_party/valgrind/binaries')
  CUSTOM_DEPS_DEVTOOLS_PERF = [
    ('src/third_party/WebKit/PerformanceTests',
     config.Master.webkit_trunk_url + '/PerformanceTests'),
    ('src/third_party/WebKit/LayoutTests/http/tests/inspector',
     config.Master.webkit_trunk_url + '/LayoutTests/http/tests/inspector'),
    ('src/third_party/WebKit/LayoutTests/inspector',
     config.Master.webkit_trunk_url + '/LayoutTests/inspector'),
  ]
  CUSTOM_DEPS_TSAN_WIN = ('src/third_party/tsan',
     config.Master.trunk_url + '/deps/third_party/tsan')
  CUSTOM_DEPS_NACL_VALGRIND = ('src/third_party/valgrind/bin',
     config.Master.nacl_trunk_url + '/src/third_party/valgrind/bin')
  CUSTOM_DEPS_TSAN_GCC = ('src/third_party/compiler-tsan',
     config.Master.trunk_url + '/deps/third_party/compiler-tsan')
  CUSTOM_DEPS_WEBDRIVER_JAVA_TESTS = (
     'src/chrome/test/chromedriver/third_party/java_tests',
     config.Master.trunk_url + '/deps/third_party/webdriver')

  CUSTOM_DEPS_GYP = [
    ('src/tools/gyp', 'http://gyp.googlecode.com/svn/trunk')]

  # A map used to skip dependencies when a test is not run.
  # The map key is the test name. The map value is an array containing the
  # dependencies that are not needed when this test is not run.
  NEEDED_COMPONENTS = {
    '^(webkit|avperf)$':
      [('src/webkit/data/layout_tests/LayoutTests', None),
       ('src/third_party/WebKit/LayoutTests', None),],
  }

  NEEDED_COMPONENTS_INTERNAL = {
    'memory':
      [('src/data/memory_test', None)],
    '(frame_rate|gpu_frame_rate)':
      [('src/chrome/test/data/perf/frame_rate/private', None)],
    'page_cycler':
      [('src/data/page_cycler', None)],
    '(selenium|chrome_frame)':
      [('src/data/selenium_core', None)],
    'tab_switching':
      [('src/data/tab_switching', None)],
    'browser_tests':
      [('src/chrome/test/data/firefox2_profile/searchplugins', None),
       ('src/chrome/test/data/firefox2_searchplugins', None),
       ('src/chrome/test/data/firefox3_profile/searchplugins', None),
       ('src/chrome/test/data/firefox3_searchplugins', None),
       ('src/chrome/test/data/ssl/certs', None)],
    '(pyauto_chromoting_tests)':
      [('src/chrome/test/data/plugin', None)],
    'unit':
      [('src/chrome/test/data/osdd', None)],
    '^(webkit|test_shell)$':
      [('src/webkit/data/bmp_decoder', None),
       ('src/webkit/data/ico_decoder', None),
       ('src/webkit/data/test_shell/plugins', None),
       ('src/webkit/data/xbm_decoder', None)],
    'mach_ports':
      [('src/data/mach_ports', None)],
    # Unused stuff:
    'autodiscovery':
      [('src/data/autodiscovery', None)],
    'esctf':
      [('src/data/esctf', None)],
    'grit':
      [('src/tools/grit/grit/test/data', None)],
    'mozilla_js':
      [('src/data/mozilla_js_tests', None)],
  }

  # List of test groups for media tests.  Media tests generate a lot of data, so
  # it's nice to separate them into different graphs.  Each tuple corresponds to
  # a PyAuto test suite name and indicates if the suite contains perf tests.
  MEDIA_TEST_GROUPS = [
      ('AV_PERF', True),
  ]

  # Minimal deps for running PyAuto.
  # http://dev.chromium.org/developers/pyauto
  PYAUTO_DEPS = \
      [('src/chrome/test/data',
        config.Master.trunk_url + '/src/chrome/test/data'),
       ('src/chrome/test/pyautolib',
        config.Master.trunk_url + '/src/chrome/test/pyautolib'),
       ('src/chrome/test/functional',
        config.Master.trunk_url + '/src/chrome/test/functional'),
       ('src/content/test/data',
        config.Master.trunk_url + '/src/content/test/data'),
       ('src/third_party/simplejson',
        config.Master.trunk_url + '/src/third_party/simplejson'),
       ('src/net/data/ssl/certificates',
        config.Master.trunk_url + '/src/net/data/ssl/certificates'),
       ('src/net/tools/testserver',
        config.Master.trunk_url + '/src/net/tools/testserver'),
       # It would be better to use config.Master.googlecode_url here.
       # But it causes QA buildbot failures on Mac beta and stable.
       # See http://crbug.com/155918#c21 .
       ('src/third_party/pyftpdlib/src',
        'http://pyftpdlib.googlecode.com/svn/trunk'),
       ('src/third_party/pywebsocket/src',
        'http://pywebsocket.googlecode.com/svn/trunk/src'),
       ('src/third_party/tlslite',
        config.Master.trunk_url + '/src/third_party/tlslite'),
       ('src/third_party/python_26',
        config.Master.trunk_url + '/tools/third_party/python_26'),
       ('src/chrome/test/data/media/avperf',
        config.Master.trunk_url + '/deps/avperf'),
       ('webdriver.DEPS',
        config.Master.trunk_url + '/src/chrome/test/pyautolib/' +
            'webdriver.DEPS'),
        ]
  # Extend if we can.
  # pylint: disable=E1101
  if config.Master.trunk_internal_url:
    PYAUTO_DEPS.append(('src/content/test/data/plugin',
                        config.Master.trunk_internal_url +
                        '/data/chrome_plugin_tests'))
    PYAUTO_DEPS.append(('src/chrome/test/data/pyauto_private',
                        config.Master.trunk_internal_url +
                        '/data/pyauto_private'))
    PYAUTO_DEPS.append(('src/data/page_cycler',
                        config.Master.trunk_internal_url +
                        '/data/page_cycler'))
    CUSTOM_DEPS_DEVTOOLS_PERF.append(('src/data/devtools_test_pages',
                                      config.Master.trunk_internal_url +
                                      '/data/devtools_test_pages'))

  CHROMEBOT_DEPS = [
    ('src/tools/chromebot',
     config.Master.trunk_url + '/tools/chromebot'),
    ('src/chrome/tools/process_dumps',
     config.Master.trunk_url + '/src/chrome/tools/process_dumps'),
    ('src/chrome/test/data/reliability',
     config.Master.trunk_url + '/src/chrome/test/data/reliability')]

  def __init__(self, build_dir, target_platform=None, pull_internal=True,
               full_checkout=False, additional_svn_urls=None, name=None,
               custom_deps_list=None, nohooks_on_update=False, target_os=None):
    if full_checkout:
      needed_components = None
    else:
      needed_components = self.NEEDED_COMPONENTS
    main = gclient_factory.GClientSolution(config.Master.trunk_url_src,
               needed_components=needed_components,
               name=name,
               custom_deps_list=custom_deps_list,
               custom_vars_list=[self.CUSTOM_VARS_WEBKIT_MIRROR,
                                 self.CUSTOM_VARS_GOOGLECODE_URL,
                                 self.CUSTOM_VARS_SOURCEFORGE_URL,
                                 self.CUSTOM_VARS_NACL_TRUNK_URL])
    internal_custom_deps_list = [main]
    if config.Master.trunk_internal_url_src and pull_internal:
      if full_checkout:
        needed_components = None
      else:
        needed_components = self.NEEDED_COMPONENTS_INTERNAL
      internal = gclient_factory.GClientSolution(
                     config.Master.trunk_internal_url_src,
                     needed_components=needed_components)
      internal_custom_deps_list.append(internal)

    additional_svn_urls = additional_svn_urls or []
    for svn_url in additional_svn_urls:
      solution = gclient_factory.GClientSolution(svn_url)
      internal_custom_deps_list.append(solution)

    gclient_factory.GClientFactory.__init__(self, build_dir,
                                            internal_custom_deps_list,
                                            target_platform=target_platform,
                                            nohooks_on_update=nohooks_on_update,
                                            target_os=target_os)

  def _AddTests(self, factory_cmd_obj, tests, mode=None,
                factory_properties=None):
    """Add the tests listed in 'tests' to the factory_cmd_obj."""
    factory_properties = factory_properties or {}
    tests = (tests or [])[:]

    # This function is too crowded, try to simplify it a little.
    def R(*testnames):
      for test in testnames:
        if gclient_factory.ShouldRunTest(tests, test):
          tests.remove(test)
          return True
    f = factory_cmd_obj
    fp = factory_properties

    # Copy perf expectations from slave to master for use later.
    if factory_properties.get('expectations'):
      f.AddUploadPerfExpectations(factory_properties)

    # When modifying the order of the tests here, please take
    # http://build.chromium.org/buildbot/waterfall/stats into account.
    # Tests that fail more often should be earlier in the queue.

    # Check for goma
    if R('diagnose_goma'):
      f.AddDiagnoseGomaStep()

    # Run interactive_ui_tests first to make sure it does not fail if another
    # test running before it leaks a window or a popup (crash dialog, etc).
    if R('interactive_ui'):
      f.AddAnnotatedGTestTestStep('interactive_ui_tests', fp)
    if R('interactive_ui_br'):
      f.AddBuildrunnerGTest('interactive_ui_tests', fp)

    # Check for an early bail.  Do early since this may cancel other tests.
    if R('check_lkgr'):
      f.AddCheckLKGRStep()

    # Scripted checks to verify various properties of the codebase:
    if R('check_deps2git'):
      f.AddDeps2GitStep()
    if R('check_deps2git_br'):
      f.AddBuildrunnerDeps2GitStep()
    if R('check_deps'):
      f.AddCheckDepsStep()
    if R('check_deps_br'):
      f.AddBuildrunnerCheckDepsStep()
    if R('check_bins'):
      f.AddCheckBinsStep()
    if R('check_bins_br'):
      f.AddCheckBinsStep()
    if R('check_perms'):
      f.AddCheckPermsStep()
    if R('check_perms_br'):
      f.AddBuildrunnerCheckPermsStep()
    if R('check_licenses'):
      f.AddCheckLicensesStep(fp)
    if R('check_licenses_br'):
      f.AddBuildrunnerCheckLicensesStep(fp)

    # Small ("module") unit tests:
    if R('base', 'base_unittests'):
      f.AddAnnotatedGTestTestStep('base_unittests', fp)
    if R('base_br'):
      f.AddBuildrunnerGTest('base_unittests', fp)
    if R('cacheinvalidation', 'cacheinvalidation_unittests'):
      f.AddAnnotatedGTestTestStep('cacheinvalidation_unittests', fp)
    if R('cacheinvalidation_br'):
      f.AddBuildrunnerGTest('cacheinvalidation_unittests', fp)
    if R('cc_unittests'):
      f.AddAnnotatedGTestTestStep('cc_unittests', fp)
    if R('cc_unittests_br'):
      f.AddBuildrunnerGTest('cc_unittests', fp)
    if R('chromedriver2_unittests'):
      f.AddAnnotatedGTestTestStep('chromedriver2_unittests', fp)
    if R('chromeos_unittests'):
      f.AddAnnotatedGTestTestStep('chromeos_unittests', fp)
    if R('courgette'):
      f.AddAnnotatedGTestTestStep('courgette_unittests', fp)
    if R('courgette_br'):
      f.AddBuildrunnerGTest('courgette_unittests', fp)
    if R('crypto', 'crypto_unittests'):
      f.AddAnnotatedGTestTestStep('crypto_unittests', fp)
    if R('crypto_br'):
      f.AddBuildrunnerGTest('crypto_unittests', fp)
    if R('dbus'):
      f.AddAnnotatedGTestTestStep('dbus_unittests', fp)
    if R('dbus_br'):
      f.AddBuildrunnerGTest('dbus_unittests', fp)
    if R('googleurl', 'googleurl_unittests'):
      f.AddAnnotatedGTestTestStep('googleurl_unittests', fp)
    if R('googleurl_br'):
      f.AddBuildrunnerGTest('googleurl_unittests', fp)
    if R('gpu', 'gpu_unittests'):
      f.AddAnnotatedGTestTestStep(
          'gpu_unittests', fp, arg_list=['--gmock_verbose=error'])
    if R('gpu_br'):
      f.AddBuildrunnerGTest(
          'gpu_unittests', fp, arg_list=['--gmock_verbose=error'])
    if R('jingle', 'jingle_unittests'):
      f.AddAnnotatedGTestTestStep('jingle_unittests', fp)
    if R('jingle_br'):
      f.AddBuildrunnerGTest('jingle_unittests', fp)
    if R('content_unittests'):
      f.AddAnnotatedGTestTestStep('content_unittests', fp)
    if R('content_unittests_br'):
      f.AddBuildrunnerGTest('content_unittests', fp)
    if R('device_unittests'):
      f.AddAnnotatedGTestTestStep('device_unittests', fp)
    if R('device_unittests_br'):
      f.AddBuildrunnerGTest('device_unittests', fp)
    if R('media', 'media_unittests'):
      f.AddAnnotatedGTestTestStep('media_unittests', fp)
    if R('media_br'):
      f.AddBuildrunnerGTest('media_unittests', fp)
    if R('net', 'net_unittests'):
      f.AddAnnotatedGTestTestStep('net_unittests', fp)
    if R('net_br'):
      f.AddBuildrunnerGTest('net_unittests', fp)
    if R('ppapi_unittests'):
      f.AddAnnotatedGTestTestStep('ppapi_unittests', fp)
    if R('ppapi_unittests_br'):
      f.AddBuildrunnerGTest('ppapi_unittests', fp)
    if R('printing', 'printing_unittests'):
      f.AddAnnotatedGTestTestStep('printing_unittests', fp)
    if R('printing_br'):
      f.AddBuildrunnerGTest('printing_unittests', fp)
    if R('remoting', 'remoting_unittests'):
      f.AddAnnotatedGTestTestStep('remoting_unittests', fp)
    if R('remoting_br'):
      f.AddBuildrunnerGTest('remoting_unittests', fp)
    if R('test_shell'):
      f.AddAnnotatedGTestTestStep('test_shell_tests', fp)
    if R('test_shell_br'):
      f.AddBuildrunnerGTest('test_shell_tests', fp)
    # Windows sandbox
    if R('sandbox'):
      f.AddAnnotatedGTestTestStep('sbox_unittests', fp)
      f.AddAnnotatedGTestTestStep('sbox_integration_tests', fp)
      f.AddAnnotatedGTestTestStep('sbox_validation_tests', fp)
    if R('sandbox_br'):
      f.AddBuildrunnerGTest('sbox_unittests', fp)
      f.AddBuildrunnerGTest('sbox_integration_tests', fp)
      f.AddBuildrunnerGTest('sbox_validation_tests', fp)
    # Linux sandbox
    if R('sandbox_linux_unittests'):
      f.AddAnnotatedGTestTestStep('sandbox_linux_unittests', fp)
    if R('sandbox_linux_unittests_br'):
      f.AddBuildrunnerGTest('sandbox_linux_unittests', fp)
    if R('ui_unittests'):
      f.AddAnnotatedGTestTestStep('ui_unittests', fp)
    if R('ui_unittests_br'):
      f.AddBuildrunnerGTest('ui_unittests', fp)
    if R('views', 'views_unittests'):
      f.AddAnnotatedGTestTestStep('views_unittests', fp)
    if R('views_br'):
      f.AddBuildrunnerGTest('views_unittests', fp)
    if R('aura'):
      f.AddAnnotatedGTestTestStep('aura_unittests', fp)
    if R('aura_br'):
      f.AddBuildrunnerGTest('aura_unittests', fp)
    if R('aura_shell') or R('ash') or R('ash_unittests'):
      f.AddAnnotatedGTestTestStep('ash_unittests', fp)
    if R('compositor'):
      f.AddAnnotatedGTestTestStep('compositor_unittests', fp)
    if R('compositor_br'):
      f.AddBuildrunnerGTest('compositor_unittests', fp)

    # Medium-sized tests (unit and browser):
    if R('unit'):
      f.AddAnnotatedChromeUnitTests(fp)
    if R('unit_br'):
      f.AddBuildrunnerChromeUnitTests(fp)
    # A snapshot of the "ChromeUnitTests" available for individual selection
    if R('unit_ipc', 'ipc_tests'):
      f.AddAnnotatedGTestTestStep('ipc_tests', fp)
    if R('unit_ipc_br'):
      f.AddBuildrunnerGTest('ipc_tests', fp)
    if R('unit_sync', 'sync_unit_tests'):
      f.AddAnnotatedGTestTestStep('sync_unit_tests', fp)
    if R('unit_sync_br'):
      f.AddBuildrunnerGTest('sync_unit_tests', fp)
    if R('unit_unit', 'unit_tests'):
      f.AddAnnotatedGTestTestStep('unit_tests', fp)
    if R('unit_unit_br'):
      f.AddBuildrunnerGTest('unit_tests', fp)
    if R('unit_sql', 'sql_unittests'):
      f.AddAnnotatedGTestTestStep('sql_unittests', fp)
    if R('unit_sql_br'):
      f.AddBuildrunnerGTest('sql_unittests', fp)
    if R('browser_tests'):
      f.AddAnnotatedBrowserTests(fp)
    if R('browser_tests_br'):
      f.AddBuildrunnerBrowserTests(fp)
    if R('chromedriver2_tests'):
      f.AddAnnotatedGTestTestStep('chromedriver2_tests', fp)
    if R('content_browsertests'):
      f.AddAnnotatedGTestTestStep('content_browsertests', fp)
    if R('content_browsertests_br'):
      f.AddBuildrunnerGTest('content_browsertests', fp)

    # Big, UI tests:
    if R('automated_ui'):
      f.AddAnnotatedAutomatedUiTests(fp)
    if R('automated_ui_br'):
      f.AddBuildrunnerAutomatedUiTests(fp)
    if R('dom_checker'):
      f.AddDomCheckerTests()
    if R('dom_checker_br'):
      f.AddBuildrunnerDomCheckerTests()

    if R('installer'):
      f.AddAnnotatedInstallerTests(fp)
    if R('installer_br'):
      f.AddBuildrunnerInstallerTests(fp)

    # WebKit-related tests:
    if R('webkit_compositor_bindings_unittests'):
      f.AddAnnotatedGTestTestStep('webkit_compositor_bindings_unittests', fp)
    if R('webkit_compositor_bindings_unittests_br'):
      f.AddBuildrunnerGTest('webkit_compositor_bindings_unittests', fp)
    if R('webkit_unit'):
      f.AddAnnotatedGTestTestStep('webkit_unit_tests', fp)
    if R('webkit_unit_br'):
      f.AddBuildrunnerGTest('webkit_unit_tests', fp)
    if R('webkit_lint'):
      f.AddWebkitLint(factory_properties=fp)
    if R('webkit_lint_br'):
      f.AddBuildrunnerWebkitLint(factory_properties=fp)
    if R('webkit'):
      f.AddWebkitTests(factory_properties=fp)
    if R('devtools_perf'):
      f.AddDevToolsTests(factory_properties=fp)

    # Benchmark tests:
    if R('page_cycler_moz'):
      f.AddPageCyclerTest('page_cycler_moz', fp)
    if R('page_cycler_morejs'):
      f.AddPageCyclerTest('page_cycler_morejs', fp)
    if R('page_cycler_intl1'):
      f.AddPageCyclerTest('page_cycler_intl1', fp)
    if R('page_cycler_intl2'):
      f.AddPageCyclerTest('page_cycler_intl2', fp)
    if R('page_cycler_bloat'):
      f.AddPageCyclerTest('page_cycler_bloat', fp)
    if R('page_cycler_dhtml'):
      f.AddPageCyclerTest('page_cycler_dhtml', fp)
    if R('page_cycler_database'):
      f.AddPageCyclerTest('page_cycler_database', fp, suite='Database*')
    if R('page_cycler_indexeddb'):
      f.AddPageCyclerTest('page_cycler_indexeddb', fp, suite='IndexedDB*')
    if R('page_cycler_2012Q2-netsim'):
      fp['use_xvfb_on_linux'] = True
      f.AddPyAutoFunctionalTest(
          'page_cycler_2012Q2-netsim',
          test_args=['perf.PageCyclerNetSimTest.test2012Q2'],
          factory_properties=fp, perf=True)
    if R('scrolling_benchmark'):
      f.AddTelemetryTest(
          'scrolling_benchmark', 'top_25.json', factory_properties=fp)
    if R('jsgamebench'):
      f.AddTelemetryTest(
          'jsgamebench', 'jsgamebench.json', factory_properties=fp)
    if R('kraken'):
      f.AddTelemetryTest('kraken', 'kraken.json', factory_properties=fp)
    if R('robohornetpro'):
      f.AddTelemetryTest(
          'robohornetpro', 'robohornetpro.json', factory_properties=fp)
    if R('memory_benchmark'):
      f.AddTelemetryTest(
          'memory_benchmark', 'top_25.json', factory_properties=fp)

    if R('memory'):
      f.AddMemoryTests(fp)
    if R('tab_switching'):
      f.AddTabSwitchingTests(fp)
    if R('sunspider'):
      f.AddTelemetryTest('sunspider', 'sunspider.json', factory_properties=fp)
    if R('octane'):
      f.AddTelemetryTest('octane', 'octane.json', factory_properties=fp)
    if R('image_decoding_benchmark'):
      f.AddTelemetryTest(
          'image_decoding_benchmark', 'tough_image_cases.json',
          factory_properties=fp)
    if R('dromaeo'):
      f.AddTelemetryTest('dromaeo', 'dromaeo/domcoreattr.json',
                         step_name='dromaeo_domcoreattr', factory_properties=fp)
      f.AddTelemetryTest('dromaeo', 'dromaeo/domcoremodify.json',
                         step_name='dromaeo_domcoremodify',
                         factory_properties=fp)
      f.AddTelemetryTest('dromaeo', 'dromaeo/domcorequery.json',
                         step_name='dromaeo_domcorequery',
                         factory_properties=fp)
      f.AddTelemetryTest('dromaeo', 'dromaeo/domcoretraverse.json',
                         step_name='dromaeo_domcoretraverse',
                         factory_properties=fp)
      f.AddTelemetryTest('dromaeo', 'dromaeo/jslibattrjquery.json',
                         step_name='dromaeo_jslibattrjquery',
                         factory_properties=fp)
      f.AddTelemetryTest('dromaeo', 'dromaeo/jslibattrprototype.json',
                         step_name='dromaeo_jslibattrprototype',
                         factory_properties=fp)
      f.AddTelemetryTest('dromaeo', 'dromaeo/jslibeventjquery.json',
                         step_name='dromaeo_jslibeventjquery',
                         factory_properties=fp)
      f.AddTelemetryTest('dromaeo', 'dromaeo/jslibeventprototype.json',
                         step_name='dromaeo_jslibeventprototype',
                         factory_properties=fp)
      f.AddTelemetryTest('dromaeo', 'dromaeo/jslibmodifyjquery.json',
                         step_name='dromaeo_jslibmodifyjquery',
                         factory_properties=fp)
      f.AddTelemetryTest('dromaeo', 'dromaeo/jslibmodifyprototype.json',
                         step_name='dromaeo_jslibmodifyprototype',
                         factory_properties=fp)
      f.AddTelemetryTest('dromaeo', 'dromaeo/jslibstylejquery.json',
                         step_name='dromaeo_jslibstylejquery',
                         factory_properties=fp)
      f.AddTelemetryTest('dromaeo', 'dromaeo/jslibstyleprototype.json',
                         step_name='dromaeo_jslibstyleprototype',
                         factory_properties=fp)
      f.AddTelemetryTest('dromaeo', 'dromaeo/jslibtraversejquery.json',
                         step_name='dromaeo_jslibtraversejquery',
                         factory_properties=fp)
      f.AddTelemetryTest('dromaeo', 'dromaeo/jslibtraverseprototype.json',
                         step_name='dromaeo_jslibtraverseprototype',
                         factory_properties=fp)
    if R('frame_rate'):
      f.AddFrameRateTests(fp)
    if R('gpu_frame_rate'):
      f.AddGpuFrameRateTests(fp)
    if R('gpu_latency'):
      f.AddGpuLatencyTests(fp)
    if R('gpu_throughput'):
      f.AddGpuThroughputTests(fp)
    if R('dom_perf'):
      f.AddDomPerfTests(fp)
    if R('idb_perf'):
      f.AddIDBPerfTests(fp)
    if R('page_cycler_moz-http'):
      f.AddPageCyclerTest('page_cycler_moz-http', fp)
    if R('page_cycler_bloat-http'):
      f.AddPageCyclerTest('page_cycler_bloat-http', fp)
    if R('startup'):
      f.AddStartupTests(fp)
      f.AddNewTabUITests(fp)
    if R('sizes'):
      f.AddSizesTests(fp)
    if R('sync'):
      f.AddSyncPerfTests(fp)
    if R('mach_ports'):
      f.AddMachPortsTests(fp)

    if R('sync_integration'):
      f.AddAnnotatedSyncIntegrationTests(fp)
    if R('sync_integration_br'):
      f.AddBuildrunnerSyncIntegrationTests(fp)

    # GPU tests:
    if R('gl_tests'):
      f.AddAnnotatedGLTests(fp)
    if R('gl_tests_br'):
      f.AddBuildrunnerGLTests(fp)
    if R('gles2_conform_test'):
      f.AddAnnotatedGLES2ConformTest(fp)
    if R('gles2_conform_test_br'):
      f.AddBuildrunnerGLES2ConformTest(fp)
    if R('gpu_tests'):
      f.AddAnnotatedGpuTests(fp)
    if R('gpu_tests_br'):
      f.AddBuildrunnerGpuTests(fp)
    if R('soft_gpu_tests'):
      f.AddAnnotatedSoftGpuTests(fp)
    if R('soft_gpu_tests_br'):
      f.AddBuildrunnerAnnotatedSoftGpuTests(fp)
    if R('gpu_content_tests'):
      f.AddAnnotatedGpuContentTests(fp)
    if R('spaceport'):
      f.AddTelemetryTest('spaceport', 'spaceport.json', factory_properties=fp)

    # ChromeFrame tests:
    if R('chrome_frame_perftests'):
      f.AddChromeFramePerfTests(fp)
    if R('chrome_frame'):
      # Add all major CF tests.
      f.AddAnnotatedGTestTestStep('chrome_frame_net_tests', fp)
      f.AddAnnotatedGTestTestStep('chrome_frame_unittests', fp)
      f.AddAnnotatedGTestTestStep('chrome_frame_tests', fp)
    elif R('chrome_frame_br'):
      f.AddBuildrunnerGTest('chrome_frame_net_tests', fp)
      f.AddBuildrunnerGTest('chrome_frame_unittests', fp)
      f.AddBuildrunnerGTest('chrome_frame_tests', fp)
    else:
      if R('chrome_frame_net_tests'):
        f.AddAnnotatedGTestTestStep('chrome_frame_net_tests', fp)
      if R('chrome_frame_net_tests_br'):
        f.AddBuildrunnerGTest('chrome_frame_net_tests', fp)
      if R('chrome_frame_unittests'):
        f.AddAnnotatedGTestTestStep('chrome_frame_unittests', fp)
      if R('chrome_frame_unittests_br'):
        f.AddBuildrunnerGTest('chrome_frame_unittests', fp)
      if R('chrome_frame_tests'):
        f.AddAnnotatedGTestTestStep('chrome_frame_tests', fp)
      if R('chrome_frame_tests_br'):
        f.AddBuildrunnerGTest('chrome_frame_tests', fp)

    def S(test, prefix, add_functor):
      if test.startswith(prefix):
        test_name = test[len(prefix):]
        tests.remove(test)
        add_functor(test_name)
        return True

    def M(test, prefix, test_type, fp):
      return S(
          test, prefix, lambda test_name:
          f.AddAnnotatedMemoryTest(test_name, test_type, factory_properties=fp))

    # Valgrind tests:
    for test in tests[:]:
      # TODO(timurrrr): replace 'valgrind' with 'memcheck'
      #                 below and in master.chromium/master.cfg
      if M(test, 'valgrind_', 'memcheck', fp):
        continue
      if M(test, 'tsan_gcc_', 'tsan_gcc', fp):
        continue
      # Run TSan in two-stage RaceVerifier mode.
      if M(test, 'tsan_rv_', 'tsan_rv', fp):
        continue
      if M(test, 'tsan_', 'tsan', fp):
        continue
      if M(test, 'drmemory_light_', 'drmemory_light', fp):
        continue
      if M(test, 'drmemory_full_', 'drmemory_full', fp):
        continue
      if M(test, 'drmemory_pattern_', 'drmemory_pattern', fp):
        continue
      if S(test, 'heapcheck_',
           lambda name: f.AddAnnotatedHeapcheckTest(name,
                                                    timeout=1200,
                                                    factory_properties=fp)):
        continue

    # PyAuto functional tests.
    if R('pyauto_chromoting_tests'):
      f.AddPyAutoFunctionalTest('pyauto_chromoting_tests', suite='CHROMOTING',
                                factory_properties=fp)
    if R('pyauto_official_tests'):
      # Mapping from self._target_platform to a chrome-*.zip
      platmap = {'win32': 'win32',
                 'darwin': 'mac',
                 'linux2': 'lucid64bit'}
      zip_plat = platmap[self._target_platform]
      workdir = os.path.join(f.working_dir, 'chrome-' + zip_plat)
      f.AddPyAutoFunctionalTest('pyauto_functional_tests',
                                src_base='..',
                                workdir=workdir,
                                factory_properties=fp)
    if R('pyauto_perf_tests'):
      # Mapping from self._target_platform to a chrome-*.zip
      platmap = {'win32': 'win32',
                 'darwin': 'mac',
                 'linux2': 'lucid64bit'}
      zip_plat = platmap[self._target_platform]
      workdir = os.path.join(f.working_dir, 'chrome-' + zip_plat)
      f.AddPyAutoFunctionalTest('pyauto_perf_tests',
                                suite='PERFORMANCE',
                                src_base='..',
                                workdir=workdir,
                                factory_properties=fp,
                                perf=True)
    if R('pyauto_webrtc_tests'):
      # Mapping from self._target_platform to a chrome-*.zip
      platmap = {'win32': 'win32',
                 'darwin': 'mac',
                 'linux2': 'lucid64bit'}
      zip_plat = platmap[self._target_platform]
      workdir = os.path.join(f.working_dir, 'chrome-' + zip_plat)
      f.AddPyAutoFunctionalTest('pyauto_webrtc_tests',
                                suite='WEBRTC',
                                src_base='..',
                                workdir=workdir,
                                factory_properties=fp,
                                perf=True)

    # Endurance tests.
    endure_tests = {
      'control': [
        'perf_endure.ChromeEndureControlTest.testControlAttachDetachDOMTree',
        'perf_endure.ChromeEndureControlTest.'
          'testControlAttachDetachDOMTreeWebDriver',
      ],
      'docs': [
        'perf_endure.ChromeEndureDocsTest.testDocsAlternatelyClickLists',
      ],
      'gmail': [
        'perf_endure.ChromeEndureGmailTest.testGmailComposeDiscard',
        'perf_endure.ChromeEndureGmailTest.'
          'testGmailAlternateThreadlistConversation',
        'perf_endure.ChromeEndureGmailTest.testGmailAlternateTwoLabels',
        'perf_endure.ChromeEndureGmailTest.testGmailExpandCollapseConversation',
      ],
      'indexeddb': [
        'perf_endure.IndexedDBOfflineTest.testOfflineOnline',
      ],
      'plus': [
        'perf_endure.ChromeEndurePlusTest.testPlusAlternatelyClickStreams',
      ],
    }
    # Live sites.
    if R('endure_control_tests'):
      f.AddChromeEndureTest('endure_control_test', endure_tests['control'], fp)
    if R('endure_docs_tests'):
      f.AddChromeEndureTest('endure_docs_test', endure_tests['docs'], fp)
    if R('endure_gmail_tests'):
      f.AddChromeEndureTest('endure_gmail_test', endure_tests['gmail'], fp)
    if R('endure_indexeddb_tests'):
      f.AddChromeEndureTest('endure_indexeddb_test', endure_tests['indexeddb'],
                            fp)
    if R('endure_plus_tests'):
      f.AddChromeEndureTest('endure_plus_test', endure_tests['plus'], fp)
    # Web Page Replay.
    if R('endure_docs_wpr_tests'):
      f.AddChromeEndureTest('endure_docs_wpr_test', endure_tests['docs'], fp,
                            wpr=True)
    if R('endure_gmail_wpr_tests'):
      f.AddChromeEndureTest('endure_gmail_wpr_test', endure_tests['gmail'], fp,
                            wpr=True)
    if R('endure_plus_wpr_tests'):
      f.AddChromeEndureTest('endure_plus_wpr_test', endure_tests['plus'], fp,
                            wpr=True)

    # HTML5 media tag performance/functional test using PyAuto.
    if R('avperf'):
      # Performance test should be run on virtual X buffer.
      fp['use_xvfb_on_linux'] = True
      f.AddWebkitTests(factory_properties=fp)
      f.AddMediaTests(factory_properties=fp, test_groups=self.MEDIA_TEST_GROUPS)
    if R('chromedriver_tests'):
      f.AddChromeDriverTest()
    if R('webdriver_tests'):
      f.AddWebDriverTest()

    # When adding a test that uses a new executable, update kill_processes.py.

    # Coverage tests.  Add coverage processing absoluely last, after
    # all tests have run.  Tests which run after coverage processing
    # don't get counted.
    if R('run_coverage_bundles'):
      f.AddRunCoverageBundles(fp)
    if R('process_coverage'):
      f.AddProcessCoverage(fp)

    # Add nacl integration tests (do these toward the end as they use the
    # annotator).
    if R('nacl_integration'):
      f.AddNaClIntegrationTestStep(fp)
    if R('nacl_integration_memcheck'):
      f.AddNaClIntegrationTestStep(fp, None, 'memcheck-browser-tests')
    if R('nacl_integration_tsan'):
      f.AddNaClIntegrationTestStep(fp, None, 'tsan-browser-tests')

    if R('buildrunner_tests'):
      f.AddBuildStep(factory_properties, name='buildrunner_tests')

    # Add an optional set of annotated steps.
    # NOTE: This really should go last as it can be confusing if the annotator
    # isn't the last thing to run.
    if R('annotated_steps'):
      f.AddAnnotatedSteps(fp)

    # If this assert triggers and the test name is valid, make sure R() is used.
    # If you are using a subclass, make sure the tests list provided to
    # _AddTests() had the factory-specific tests stripped off.
    assert not tests, 'Did you make a typo? %s wasn\'t processed' % tests

  @property
  def build_dir(self):
    return self._build_dir

  def ForceMissingFilesToBeFatal(self, project, gclient_env):
    """Force Windows bots to fail GYPing if referenced files do not exist."""
    gyp_generator_flags = gclient_env.setdefault('GYP_GENERATOR_FLAGS', '')
    if (self._target_platform == 'win32' and
        'msvs_error_on_missing_sources=' not in gyp_generator_flags):
      gclient_env['GYP_GENERATOR_FLAGS'] = (
          gyp_generator_flags + ' msvs_error_on_missing_sources=1')

  def ChromiumFactory(self, target='Release', clobber=False, tests=None,
                      mode=None, slave_type='BuilderTester',
                      options=None, compile_timeout=1200, build_url=None,
                      project=None, factory_properties=None, gclient_deps=None,
                      enable_swarm_tests=False):
    factory_properties = (factory_properties or {}).copy()
    factory_properties['gclient_env'] = \
        factory_properties.get('gclient_env', {}).copy()
    # Defaults gyp to VS2010.
    if self._target_platform == 'win32':
      factory_properties['gclient_env'].setdefault('GYP_MSVS_VERSION', '2010')
    tests = tests or []

    if factory_properties.get('needs_valgrind'):
      self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_VALGRIND]
    elif factory_properties.get('needs_tsan_win'):
      self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_TSAN_WIN]
    elif factory_properties.get('needs_drmemory'):
      if 'drmemory.DEPS' not in [s.name for s in self._solutions]:
        self._solutions.append(gclient_factory.GClientSolution(
            config.Master.trunk_url +
            '/deps/third_party/drmemory/drmemory.DEPS',
            'drmemory.DEPS'))
    elif factory_properties.get('needs_tsan_gcc'):
      self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_TSAN_GCC]
    elif factory_properties.get('needs_webdriver_java_tests'):
      self._solutions[0].custom_deps_list = [
        self.CUSTOM_DEPS_WEBDRIVER_JAVA_TESTS
      ]

    if 'devtools_perf' in tests:
      self._solutions[0].custom_deps_list.extend(self.CUSTOM_DEPS_DEVTOOLS_PERF)

    if factory_properties.get('safesync_url'):
      self._solutions[0].safesync_url = factory_properties.get('safesync_url')
    elif factory_properties.get('lkgr'):
      self._solutions[0].safesync_url = self.SAFESYNC_URL_CHROMIUM

    tests_for_build = [
        re.match('^(?:valgrind_|heapcheck_)?(.*)$', t).group(1) for t in tests]

    # Ensure that component is set correctly in the gyp defines.
    ForceComponent(target, project, factory_properties['gclient_env'])

    # Ensure GYP errors out if files referenced in .gyp files are missing.
    self.ForceMissingFilesToBeFatal(project, factory_properties['gclient_env'])

    is_windows_asan_builder = (slave_type == 'Builder' and
                               self._target_platform == 'win32' and
                               factory_properties.get('asan'))

    factory = self.BuildFactory(target, clobber, tests_for_build, mode,
                                slave_type, options, compile_timeout, build_url,
                                project, factory_properties,
                                gclient_deps=gclient_deps,
                                skip_archive_steps=is_windows_asan_builder)

    # Get the factory command object to create new steps to the factory.
    chromium_cmd_obj = chromium_commands.ChromiumCommands(factory,
                                                          target,
                                                          self._build_dir,
                                                          self._target_platform)

    # Add ASANification step for windows
    # MUST BE FIRST STEP ADDED AFTER BuildFactory CALL in order to add back
    # the ZipBuild step in it's expected place
    if is_windows_asan_builder:
      chromium_cmd_obj.AddWindowsASANStep()
      # Need to add the Zip Build step back
      chromium_cmd_obj.AddZipBuild(halt_on_failure=True,
                                   factory_properties=factory_properties)

    # Add this archive build step.
    if factory_properties.get('archive_build'):
      chromium_cmd_obj.AddArchiveBuild(factory_properties=factory_properties)

    if factory_properties.get('asan_archive_build'):
      chromium_cmd_obj.AddAsanArchiveBuild(
          factory_properties=factory_properties)

    # Add the package source step.
    if slave_type == 'Indexer':
      chromium_cmd_obj.AddPackageSource(factory_properties=factory_properties)

    # Add a trigger step if needed.
    self.TriggerFactory(factory, slave_type=slave_type,
                        factory_properties=factory_properties)

    # Trigger swarm tests.
    if enable_swarm_tests:
      chromium_cmd_obj.AddTriggerSwarmTests(tests, factory_properties)

    # Start the crash handler process.
    if ((self._target_platform == 'win32' and slave_type != 'Builder' and
         self._build_dir == 'src/chrome') or
        factory_properties.get('start_crash_handler')):
      chromium_cmd_obj.AddRunCrashHandler()

    # Add all the tests.
    self._AddTests(chromium_cmd_obj, tests, mode, factory_properties)

    if factory_properties.get('process_dumps'):
      chromium_cmd_obj.AddProcessDumps()

    test_parity_platform = factory_properties.get('test_parity_platform')
    if test_parity_platform:
      chromium_cmd_obj.AddSendTestParityStep(test_parity_platform)

    return factory

  def ChromiumAnnotationFactory(self, annotation_script,
                                branch='master',
                                target='Release',
                                slave_type='AnnotatedBuilderTester',
                                clobber=False,
                                compile_timeout=6000,
                                project=None,
                                factory_properties=None, options=None,
                                tests=None,
                                gclient_deps=None):
    """Annotation-driven Chromium buildbot factory.

    Like a ChromiumFactory, but non-sync steps (compile, run tests)
    are specified in a script that uses @@@BUILD_STEP descriptive
    text@@@ style annotations.

    Note new slave type AnnotatedBuilderTester; we don't want a
    compile step added.
    TODO(jrg): is a new slave type the right direction?
    """
    # Setup factory.
    factory_properties = factory_properties or {}
    options = options or {}

    # Ensure that component is set correctly in the gyp defines.
    ForceComponent(target, project, factory_properties)

    factory = self.BuildFactory(target=target, clobber=clobber,
                                tests=tests, mode=None, slave_type=slave_type,
                                options=options,
                                compile_timeout=compile_timeout, build_url=None,
                                project=project,
                                factory_properties=factory_properties,
                                gclient_deps=gclient_deps)

    # Get the factory command object to create new steps to the factory.
    chromium_cmd_obj = chromium_commands.ChromiumCommands(
        factory=factory,
        target=target,
        build_dir=self._build_dir,
        target_platform=self._target_platform,
        target_os=self._target_os)

    # Add the main build.
    env = factory_properties.get('annotation_env')
    factory_properties['target'] = target
    factory_properties.setdefault('clobber', clobber)

    chromium_cmd_obj.AddAnnotationStep('build', annotation_script, env=env,
                                       factory_properties=factory_properties)

    # Add all the tests.
    self._AddTests(factory_cmd_obj=chromium_cmd_obj, tests=tests,
                   factory_properties=factory_properties)

    # Add a trigger step if needed.
    self.TriggerFactory(factory, slave_type=slave_type,
                        factory_properties=factory_properties)

    return factory


  def ReliabilityTestsFactory(self, platform='win'):
    """Create a BuildFactory to run a reliability slave."""
    factory = BuildFactory({})
    cmd_obj = chromium_commands.ChromiumCommands(factory,
                                                 'Release', '',
                                                 self._target_platform)
    cmd_obj.AddUpdateScriptStep()
    cmd_obj.AddReliabilityTests(platform=platform)
    return factory

  def ChromiumV8LatestFactory(self, target='Release', clobber=False, tests=None,
                              mode=None, slave_type='BuilderTester',
                              options=None, compile_timeout=1200,
                              build_url=None, project=None,
                              factory_properties=None):
    self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_V8_LATEST]
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumWebRTCLatestFactory(self, target='Release', clobber=False,
                                  tests=None, mode=None,
                                  slave_type='BuilderTester', options=None,
                                  compile_timeout=1200, build_url=None,
                                  project=None, factory_properties=None):
    self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_WEBRTC_LATEST]
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumAVPerfFactory(self, target='Release', clobber=False, tests=None,
                              mode=None, slave_type='BuilderTester',
                              options=None, compile_timeout=1200,
                              build_url=None, project=None,
                              factory_properties=None):
    self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_AVPERF]
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumNativeClientLatestFactory(
      self, target='Release', clobber=False, tests=None, mode=None,
      slave_type='BuilderTester', options=None, compile_timeout=1200,
      build_url=None, project=None, factory_properties=None,
      on_nacl_waterfall=True, use_chrome_lkgr=True):
    factory_properties = factory_properties or {}
    if on_nacl_waterfall:
      factory_properties['primary_repo'] = 'nacl_'
    # Remove nacl_trunk variable.
    self._solutions[0].custom_vars_list = [
      v for v in self._solutions[0].custom_vars_list if v[0] != 'nacl_trunk'
    ]
    self._solutions[0].custom_vars_list.extend(self.CUSTOM_VARS_NACL_LATEST)
    self._solutions[0].safesync_url = self.SAFESYNC_URL_CHROMIUM
    if factory_properties.get('needs_nacl_valgrind'):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_NACL_VALGRIND)
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def _InitWebkitLatestFactorySettings(self, factory_properties):
    self._solutions[0].custom_vars_list.extend(self.CUSTOM_VARS_WEBKIT_LATEST)

    # This will let builders embed their webkit revision in their output
    # filename and will let testers look for zip files containing a webkit
    # revision in their filename. For this to work correctly, the testers
    # need to be on a Triggerable that's activated by their builder.
    factory_properties.setdefault('webkit_dir', 'third_party/WebKit/Source')

  def ChromiumWebkitLatestAnnotationFactory(self, annotation_script,
                                            branch='master', target='Release',
                                            slave_type='AnnotatedBuilderTester',
                                            clobber=False, compile_timeout=6000,
                                            project=None,
                                            factory_properties=None,
                                            tests=None):
    factory_properties = factory_properties or {}
    self._InitWebkitLatestFactorySettings(factory_properties)

    return self.ChromiumAnnotationFactory(
        annotation_script=annotation_script, branch=branch, target=target,
        slave_type=slave_type, clobber=clobber, compile_timeout=compile_timeout,
        project=project, factory_properties=factory_properties, tests=tests)

  def ChromiumWebkitLatestFactory(self, target='Release', clobber=False,
                                  tests=None, mode=None,
                                  slave_type='BuilderTester', options=None,
                                  compile_timeout=1200, build_url=None,
                                  project=None, factory_properties=None):
    factory_properties = factory_properties or {}
    self._InitWebkitLatestFactorySettings(factory_properties)

    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumOSWebkitLatestFactory(self, target='Release', clobber=False,
                                    tests=None, mode=None,
                                    slave_type='BuilderTester', options=None,
                                    compile_timeout=1200, build_url=None,
                                    project=None, factory_properties=None):
    # Make sure the solution is not already there.
    if 'cros_deps' not in [s.name for s in self._solutions]:
      self._solutions.append(gclient_factory.GClientSolution(
          config.Master.trunk_url + '/src/tools/cros.DEPS', name='cros_deps'))

    return self.ChromiumWebkitLatestFactory(target, clobber, tests, mode,
                                            slave_type, options,
                                            compile_timeout, build_url,
                                            project, factory_properties)

  def ChromiumGYPLatestFactory(self, target='Debug', clobber=False, tests=None,
                               mode=None, slave_type='BuilderTester',
                               options=None, compile_timeout=1200,
                               build_url=None, project=None,
                               factory_properties=None, gyp_format=None):

    if tests is None:
      tests = ['unit']

    if gyp_format:
      # Set GYP_GENERATORS in the environment used to execute
      # gclient so we get the right build tool configuration.
      if factory_properties is None:
        factory_properties = {}
      gclient_env = factory_properties.get('gclient_env', {})
      gclient_env['GYP_GENERATORS'] = gyp_format
      factory_properties['gclient_env'] = gclient_env

      # And tell compile.py what build tool to use.
      if options is None:
        options = []
      options.append('--build-tool=' + gyp_format)

    self._solutions[0].custom_deps_list = self.CUSTOM_DEPS_GYP
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumArmuFactory(self, target='Release', clobber=False, tests=None,
                          mode=None, slave_type='BuilderTester', options=None,
                          compile_timeout=1200, build_url=None, project=None,
                          factory_properties=None):
    self._project = 'webkit_armu.sln'
    self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_V8_LATEST]
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumOSFactory(self, target='Release', clobber=False, tests=None,
                        mode=None, slave_type='BuilderTester', options=None,
                        compile_timeout=1200, build_url=None, project=None,
                        factory_properties=None):
    # Make sure the solution is not already there.
    if 'cros_deps' not in [s.name for s in self._solutions]:
      self._solutions.append(gclient_factory.GClientSolution(
          config.Master.trunk_url + '/src/tools/cros.DEPS', name='cros_deps'))

    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumBranchFactory(
      self, target='Release', clobber=False, tests=None, mode=None,
      slave_type='BuilderTester', options=None, compile_timeout=1200,
      build_url=None, project=None, factory_properties=None,
      trunk_src_url=None):
    self._solutions = [gclient_factory.GClientSolution(trunk_src_url, 'src')]
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumGPUFactory(self, target='Release', clobber=False, tests=None,
                         mode=None, slave_type='Tester', options=None,
                         compile_timeout=1200, build_url=None, project=None,
                         factory_properties=None):
    # Make sure the solution is not already there.
    if 'gpu_reference.DEPS' not in [s.name for s in self._solutions]:
      self._solutions.append(gclient_factory.GClientSolution(
          config.Master.trunk_url + '/deps/gpu_reference/gpu_reference.DEPS',
          'gpu_reference.DEPS'))
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumASANFactory(self, target='Release', clobber=False, tests=None,
                          mode=None, slave_type='BuilderTester', options=None,
                          compile_timeout=1200, build_url=None, project=None,
                          factory_properties=None):
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumCodesearchFactory(self, target='Release', clobber=False,
                                tests=None, mode=None,
                                slave_type='BuilderTester', options=None,
                                compile_timeout=1200, build_url=None,
                                project=None, factory_properties=None):
    # Make sure the solution is not already there.
    assert 'clang_indexer.DEPS' not in [s.name for s in self._solutions]
    self._solutions.append(gclient_factory.GClientSolution(
        'svn://svn.chromium.org/chrome-internal/trunk/deps/'
        'clang_indexer.DEPS'))
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumGITFactory(self, target='Release', clobber=False, tests=None,
                         mode=None, slave_type='Tester', options=None,
                         compile_timeout=1200, build_url=None, project=None,
                         git_url=None, factory_properties=None):
    if not factory_properties:
      factory_properties = {}
    factory_properties['no_gclient_branch'] = True
    if git_url is None:
      git_url = '%s/chromium/src.git' % config.Master.git_server_url
    main = gclient_factory.GClientSolution(
        svn_url=git_url, name='src', custom_deps_file='.DEPS.git')
    self._solutions[0] = main
    if (len(self._solutions) > 1 and
        self._solutions[1].svn_url == config.Master.trunk_internal_url_src):
      svn_url = 'ssh://gerrit-int.chromium.org:29419/chrome/src-internal'
      self._solutions[1] = gclient_factory.GClientSolution(
          svn_url=svn_url,
          name='src-internal',
          custom_deps_file='.DEPS.git',
          needed_components=self.NEEDED_COMPONENTS_INTERNAL)
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumOSASANFactory(self, target='Release', clobber=False, tests=None,
                            mode=None, slave_type='BuilderTester', options=None,
                            compile_timeout=1200, build_url=None, project=None,
                            factory_properties=None):
    # Make sure the solution is not already there.
    if 'cros_deps' not in [s.name for s in self._solutions]:
      self._solutions.append(gclient_factory.GClientSolution(
          config.Master.trunk_url + '/src/tools/cros.DEPS', name='cros_deps'))
    if 'asan.DEPS' not in [s.name for s in self._solutions]:
      self._solutions.append(gclient_factory.GClientSolution(
          config.Master.trunk_url + '/deps/asan.DEPS',
          'asan.DEPS'))
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumChromebotFactory(
      self, target='Release', clobber=False, tests=None,
      mode=None, slave_type='ChromebotClient', options=None,
      compile_timeout=1200, build_url=None, project=None,
      factory_properties=None, web_build_dir=None):
    factory_properties = factory_properties or {}
    self._solutions = []

    for name, url in self.CHROMEBOT_DEPS:
      self._solutions.append(gclient_factory.GClientSolution(url, name))

    # Ensure that component is set correctly in the gyp defines.
    ForceComponent(target, project, factory_properties)

    factory = self.BuildFactory(target, clobber, tests, mode,
                                slave_type, options, compile_timeout, build_url,
                                project, factory_properties)

    # Get the factory command object to create new steps to the factory.
    chromium_cmd_obj = chromium_commands.ChromiumCommands(factory,
                                                          target,
                                                          self._build_dir,
                                                          self._target_platform)

    # Add steps.
    client_os = factory_properties.get('client_os')
    if slave_type == 'ChromebotServer':
      chromium_cmd_obj.AddDownloadFileStep(factory_properties.get('config'),
                                           'src/tools/chromebot/custom.cfg')
      chromium_cmd_obj.AddGetBuildForChromebot(client_os,
                                               archive_url=build_url,
                                               build_dir=web_build_dir)
      chromium_cmd_obj.AddChromebotServer(factory_properties)
      chromium_cmd_obj.AddReliabilityTests(client_os)
    elif slave_type == 'ChromebotClient':
      chromium_cmd_obj.AddGetBuildForChromebot(client_os,
                                               extract=True,
                                               build_url=build_url)
      chromium_cmd_obj.AddChromebotClient(factory_properties)

    return factory
