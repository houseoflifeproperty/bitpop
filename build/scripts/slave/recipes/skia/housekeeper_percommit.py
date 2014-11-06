# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe for the Skia PerCommit Housekeeper.


DEPS = [
  'path',
  'properties',
  'python',
  'skia',
  'step',
]


def GenSteps(api):
  # Checkout, compile, etc.
  api.skia.gen_steps()

  cwd = api.path['checkout']

  api.skia.run(
    api.step,
    'tool self-tests',
    cmd=[cwd.join('tools', 'tests', 'run.sh')],
    cwd=cwd,
    abort_on_failure=False)

  api.skia.run(
    api.step,
    'gm self-tests',
    cmd=[cwd.join('gm', 'tests', 'run.sh')],
    cwd=cwd,
    abort_on_failure=False)

  api.skia.run(
    api.step,
    'android platform self-tests',
    cmd=['python',
         cwd.join('platform_tools', 'android', 'tests', 'run_all.py')],
    cwd=cwd,
    abort_on_failure=False)

  # TODO(borenet): Detect static initializers?

  if not api.skia.c.is_trybot:
    gsutil_path = api.path['depot_tools'].join('third_party', 'gsutil',
                                               'gsutil')
    api.skia.run(
      api.step,
      'generate and upload pydoc',
      cmd=['python', api.skia.resource('generate_and_upload_doxygen.py'),
           gsutil_path],
      cwd=cwd,
      abort_on_failure=False)


def GenTests(api):
  buildername = 'Housekeeper-PerCommit'
  mastername = 'client.skia.fyi'
  slavename = 'skiabot-linux-housekeeper-000'
  yield (
    api.test(buildername) +
    api.properties(buildername=buildername,
                   mastername=mastername,
                   slavename=slavename)
  )
