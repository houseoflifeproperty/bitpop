# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Top-level presubmit script for buildbot.

See http://dev.chromium.org/developers/how-tos/depottools/presubmit-scripts for
details on the presubmit API built into gcl.
"""

import sys

def CommonChecks(input_api, output_api):
  output = []

  def join(*args):
    return input_api.os_path.join(input_api.PresubmitLocalPath(), *args)

  black_list = list(input_api.DEFAULT_BLACK_LIST) + [
      r'.*slave/.*/build.*/.*',
      r'.*depot_tools/.*',
      r'.*scripts/release/.*',
      r'.+_bb7\.py$',
      r'.*masters/.*/templates/.*\.html$',
  ]

  sys_path_backup = sys.path
  try:
    sys.path = [
        join('third_party'),
        join('third_party', 'buildbot_8_4p1'),
        join('third_party', 'decorator_3_3_1'),
        join('third_party', 'jinja2'),
        join('third_party', 'mock-0.7.2'),
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
        join('site_config'),
        join('test'),
    ] + sys.path

    disabled_warnings = [
      'C0301',  # Line too long (NN/80)
      'C0321',  # More than one statement on a single line
      'W0613',  # Unused argument
    ]
    output.extend(input_api.canned_checks.RunPylint(
        input_api,
        output_api,
        black_list=black_list,
        disabled_warnings=disabled_warnings))
  finally:
    sys.path = sys_path_backup

  if input_api.is_committing:
    output.extend(input_api.canned_checks.PanProjectChecks(
      input_api, output_api, excluded_paths=black_list))

  output.extend(input_api.canned_checks.RunUnitTestsInDirectory(
      input_api, output_api, 'test', [r'slaves_cfg_test\.py$']))

  return output


def RunTests(input_api, output_api):
  out = []
  whitelist = [r'.+_test\.py$']
  # slaves_cfg_test.py already runs in CommonChecks.
  blacklist = [r'slaves_cfg_test\.py$']
  out.extend(input_api.canned_checks.RunUnitTestsInDirectory(
      input_api, output_api, 'test', whitelist, blacklist))
  out.extend(input_api.canned_checks.RunUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('scripts', 'master', 'unittests'),
      whitelist))
  out.extend(input_api.canned_checks.RunUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('scripts', 'slave', 'unittests'),
      whitelist))
  out.extend(input_api.canned_checks.RunUnitTestsInDirectory(
      input_api,
      output_api,
      input_api.os_path.join('scripts', 'common', 'unittests'),
      whitelist))
  internal_path = input_api.os_path.join('..', 'build_internal', 'test')
  if input_api.os_path.isfile(internal_path):
    out.extend(input_api.canned_checks.RunUnitTestsInDirectory(
        input_api, output_api, internal_path, whitelist))
  return out


def CheckChangeOnUpload(input_api, output_api):
  return CommonChecks(input_api, output_api)


def CheckChangeOnCommit(input_api, output_api):
  output = []
  output.extend(CommonChecks(input_api, output_api))
  output.extend(RunTests(input_api, output_api))
  return output
