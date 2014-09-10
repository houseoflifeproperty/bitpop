# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'path',
  'properties',
  'python',
  'step',
  'tryserver',
]

OZONE_TESTS = [
    # Linux tests.
    'base_unittests',
    # 'browser_tests', Not sensible.
    'cacheinvalidation_unittests',
    'cc_unittests',
    'components_unittests',
    'content_browsertests',
    'content_unittests',
    'crypto_unittests',
    # 'dbus_unittests', Not sensible; use_dbus==0.
    'device_unittests',
    # 'google_apis_unittests', Not sensible.
    'gpu_unittests',
    # 'interactive_ui_tests', Not sensible.
    'ipc_tests',
    # 'jingle_unittests', Later.
    'media_unittests',
    'net_unittests',
    'ozone_unittests',
    'ppapi_unittests',
    # 'printing_unittests', Not sensible.
    'sandbox_linux_unittests',
    'sql_unittests',
    'sync_unit_tests',
    'ui_unittests',
    # 'unit_tests',  Not sensible.
    'url_unittests',
    # 'sync_integration_tests', Not specified in bug.
    # 'chromium_swarm_tests', Not specified in bug.
] + [
    'aura_unittests',
    'compositor_unittests',
    'events_unittests',
    'gfx_unittests',
]

tests_that_do_not_compile = [
]

tests_that_do_not_pass = [
]

dbus_tests = [
    'dbus_unittests',
]

def GenSteps(api):

  api.chromium.set_config('chromium', BUILD_CONFIG='Debug')

  step_result = api.bot_update.ensure_checkout()
  if not step_result.json.output['did_run']:
    api.gclient.checkout()

    api.tryserver.maybe_apply_issue()

  api.chromium.c.gyp_env.GYP_DEFINES['embedded'] = 1

  api.chromium.runhooks()
  api.chromium.compile(['content_shell'], name='compile content_shell')

  try:
    api.python('check ecs deps', api.path['checkout'].join('tools',
      'check_ecs_deps', 'check_ecs_deps.py'),
      cwd=api.chromium.c.build_dir.join(api.chromium.c.build_config_fs))
  except api.step.StepFailure:
    pass

  tests_to_compile = list(set(OZONE_TESTS) - set(tests_that_do_not_compile))
  tests_to_compile.sort()
  api.chromium.compile(tests_to_compile, name='compile tests')

  tests_to_run = list(set(tests_to_compile) - set(tests_that_do_not_pass))
  #TODO(martiniss) convert loop
  for x in sorted(tests_to_run):
    api.chromium.runtest(x, xvfb=False, spawn_dbus=(x in dbus_tests))

  # Compile the failing targets.
  #TODO(martiniss) convert loop
  for x in sorted(set(OZONE_TESTS) &
                  set(tests_that_do_not_compile)): # pragma: no cover
    try:
      api.chromium.compile([x], name='experimentally compile %s' % x)
    except api.step.StepFailure:
      pass

  # Run the failing tests.
  tests_to_try = list(set(tests_to_compile) & set(tests_that_do_not_pass))
  #TODO(martiniss) convert loop
  for x in sorted(tests_to_try): # pragma: no cover
    try:
      api.chromium.runtest(x, xvfb=False, name='experimentally run %s' % x)
    except api.step.StepFailure:
      pass

def GenTests(api):
  yield api.test('basic') + api.properties.scheduled()
  yield api.test('trybot') + api.properties.tryserver()

  yield (
    api.test('check_ecs_deps_fail') +
    api.properties.scheduled() +
    api.step_data('check ecs deps', retcode=1)
  )
