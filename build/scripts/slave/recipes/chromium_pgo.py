# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
  'step',
]


# List of the benchmark that we run during the profiling step.
_BENCHMARKS_TO_RUN = {
  'peacekeeper.dom',
  'peacekeeper.array',
  'peacekeeper.html5',
  'peacekeeper.string',
  'peacekeeper.render',
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
  'sunspider',
  'jsgamebench',
}


# Run a telemetry benchmark under the Windows PGO profiler.
def RunTelemetryBenchmark(api, testname):
  return api.python(
      'Telemetry benchmark: %s' % testname,
      api.path['checkout'].join('tools', 'perf', 'run_benchmark'),
      ['--profiler=win_pgo_profiler', '--use-live-sites', testname]
  )


def GenSteps(api):
  api.step.auto_resolve_conflicts = True
  api.chromium.set_config('chrome_pgo_instrument', BUILD_CONFIG='Release')
  api.gclient.set_config('chromium_lkgr')

  api.chromium.taskkill()
  api.bot_update.ensure_checkout()

  # First step: compilation of the instrumented build.
  api.chromium.runhooks()
  api.chromium.compile()

  # Remove the profile files from the previous builds.
  api.path.rmwildcard('*.pgc',
                            str(api.chromium.output_dir))

  # Second step: profiling of the instrumented build.
  for benchmark in _BENCHMARKS_TO_RUN:
    RunTelemetryBenchmark(api, benchmark)

  # Third step: Compilation of the optimized build, this will use the profile
  #     data files produced by the previous step.
  api.chromium.set_config('chrome_pgo_optimize', BUILD_CONFIG='Release')
  api.chromium.runhooks()
  api.chromium.compile()

def GenTests(api):
  mastername = 'chromium.fyi'
  buildername = 'Chromium Win PGO Builder'

  def _sanitize_nonalpha(text):
    return ''.join(c if c.isalnum() else '_' for c in text)

  yield (
    api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                             _sanitize_nonalpha(buildername))) +
    api.properties.generic(mastername=mastername, buildername=buildername) +
    api.platform('win', 32)
  )
