# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Top-level presubmit script for buildbot.

See http://dev.chromium.org/developers/how-tos/depottools/presubmit-scripts for
details on the presubmit API built into gcl.
"""

import sys


def CommonChecks(input_api, output_api):
  def join(*args):
    return input_api.os_path.join(input_api.PresubmitLocalPath(), *args)

  black_list = list(input_api.DEFAULT_BLACK_LIST) + [
      r'.*slave/.*/build.*/.*',
      r'.*slave/.*/isolate.*/.*',
      r'.*depot_tools/.*',
      r'.*scripts/release/.*',
      r'.*scripts/slave/recipe_modules/.*',
      r'.*scripts/gsd_generate_index/.*',
      r'.*masters/.*/templates/.*\.html$',
      r'.*masters/.*/templates/.*\.css$',
      r'.*masters/.*/public_html/.*\.html$',
      r'.*masters/.*/public_html/.*\.css$',
  ]
  tests = []
  sys_path_backup = sys.path
  try:
    sys.path = [
        join('third_party'),
        join('third_party', 'buildbot_8_4p1'),
        join('third_party', 'buildbot_slave_8_4'),
        join('third_party', 'coverage-3.7.1'),
        join('third_party', 'decorator_3_3_1'),
        join('third_party', 'jinja2'),
        join('third_party', 'mock-1.0.1'),
        join('third_party', 'sqlalchemy_0_7_1'),
        join('third_party', 'sqlalchemy_migrate_0_7_1'),
        join('third_party', 'tempita_0_5'),
        join('third_party', 'twisted_10_2'),
        join('scripts'),
        # Initially, a separate run was done for unit tests but now that
        # pylint is fetched in memory with setuptools, it seems it caches
        # sys.path so modifications to sys.path aren't kept.
        join('scripts', 'master', 'unittests'),
        join('scripts', 'slave', 'unittests'),
        join('scripts', 'tools', 'deps2git'),
        join('site_config'),
        join('tests'),
    ] + sys.path

    disabled_warnings = [
      'C0301',  # Line too long (NN/80)
      'C0321',  # More than one statement on a single line
      'W0613',  # Unused argument
    ]
    tests.extend(input_api.canned_checks.GetPylint(
        input_api,
        output_api,
        black_list=black_list,
        disabled_warnings=disabled_warnings))
  finally:
    sys.path = sys_path_backup

  whitelist = [r'.+_test\.py$']
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api, output_api, 'tests', whitelist=whitelist))
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('scripts', 'master', 'unittests'),
      whitelist))
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('scripts', 'slave', 'unittests'),
      whitelist))
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('scripts', 'common', 'unittests'),
      whitelist))
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('scripts', 'tools', 'unittests'),
      whitelist))
  tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('scripts', 'tools', 'blink_roller'),
      whitelist))

  recipe_modules_tests = input_api.glob(
      join('scripts', 'slave', 'recipe_modules', '*', 'tests'))
  for path in recipe_modules_tests:
    tests.extend(input_api.canned_checks.GetUnitTestsInDirectory(
        input_api,
        output_api,
        path,
        whitelist))

  try:
    sys.path = [join('scripts', 'common')] + sys.path
    import master_cfg_utils  # pylint: disable=F0401
    # Run the tests.
    with master_cfg_utils.TemporaryMasterPasswords():
      output = input_api.RunTests(tests)

    output.extend(input_api.canned_checks.PanProjectChecks(
      input_api, output_api, excluded_paths=black_list))
    return output
  finally:
    sys.path = sys_path_backup


def BuildInternalCheck(output, input_api, output_api):
  if output:
    b_i = input_api.os_path.join(input_api.PresubmitLocalPath(), '..',
                                 'build_internal')
    if input_api.os_path.exists(b_i):
      return [output_api.PresubmitNotifyResult(
          'You have a build_internal checkout. '
          'Updating it may resolve some issues.')]
  return []


def CheckChangeOnUpload(input_api, output_api):
  output = CommonChecks(input_api, output_api)
  output.extend(BuildInternalCheck(output, input_api, output_api))
  return output


def CheckChangeOnCommit(input_api, output_api):
  return CheckChangeOnUpload(input_api, output_api)
