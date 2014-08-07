# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import urllib

from slave import recipe_api

class AndroidApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(AndroidApi, self).__init__(**kwargs)
    self._internal_names = dict()
    self._cleanup_list = []

  def get_config_defaults(self):
    return {
      'REVISION': self.m.properties.get('revision', '')
    }

  @property
  def internal_dir(self):
    assert self.c.INTERNAL, (
        'Attempt to get internal_dir, but not internal build')
    return self.m.path['checkout'].join(self.c.internal_dir_name)

  @property
  def out_path(self):
    return self.m.path['checkout'].join('out')

  @property
  def coverage_dir(self):
    return self.out_path.join(self.c.BUILD_CONFIG, 'coverage')

  def get_env(self):
    return {
        'PATH': self.m.path.pathsep.join(map(str, [
                   self.m.path['checkout'].join('third_party', 'android_tools',
                                                'sdk', 'platform-tools'),
                   self.m.path['checkout'].join('build', 'android'),
                   '%(PATH)s']))
    }

  def configure_from_properties(self, config_name, **kwargs):
    def set_property(prop, var):
      if prop in self.m.properties:
        if var in kwargs:
          assert kwargs[var] == self.m.properties[prop], (
              "Property/Config conflict: %s=%s but %s=%s", (
                  prop, self.m.properties[prop],
                  var, kwargs[var]))
        kwargs[var] = self.m.properties[prop]

    set_property('target', 'BUILD_CONFIG')
    set_property('internal', 'INTERNAL')
    set_property('repo_name', 'REPO_NAME')
    set_property('repo_url', 'REPO_URL')

    self.set_config(config_name, **kwargs)

  def make_zip_archive(self, step_name, archive_name, files=None,
                       preserve_paths=True, **kwargs):
    """Creates and stores the archive file.

    Args:
      step_name: Name of the step.
      archive_name: Name of the archive file.
      files: List of files. Files can be glob's or file paths. If no files
        are provided, everything in the target directory will be included.
      preserve_paths: If True, files will be stored using the subdolders
        in the archive.
    """
    archive_args = ['--target', self.m.chromium.c.BUILD_CONFIG,
                    '--name', archive_name]

    # TODO(luqui): Clean up when these are covered by the external builders.
    if files:              # pragma: no cover
      archive_args.extend(['--files', ','.join(files)])
    if not preserve_paths: # pragma: no cover
      archive_args.append('--ignore-subfolder-names')

    yield self.m.python(
      step_name,
      str(self.m.path['build'].join(
          'scripts', 'slave', 'android', 'archive_build.py')),
      archive_args,
      always_run=True,
      **kwargs
    )

  def init_and_sync(self):
    # TODO(sivachandra): Move the setting of the gclient spec below to an
    # internal config extension when they are supported by the recipe system.
    spec = self.m.gclient.make_config('android_bare')
    spec.target_os = ['android']
    s = spec.solutions[0]
    s.name = self.c.deps_dir
    s.url = self.c.REPO_URL
    s.custom_deps = self.c.gclient_custom_deps or {}
    s.deps_file = self.c.deps_file
    s.custom_vars = self.c.gclient_custom_vars or {}
    s.managed = self.c.managed
    s.revision = self.c.revision
    spec.revisions = self.c.revisions

    yield self.m.gclient.break_locks()
    yield self.m.bot_update.ensure_checkout(spec)
    if not self.m.step_history.last_step().json.output['did_run']:
      yield self.m.gclient.checkout(spec)

    # TODO(sivachandra): Manufacture gclient spec such that it contains "src"
    # solution + repo_name solution. Then checkout will be automatically
    # correctly set by gclient.checkout
    self.m.path['checkout'] = self.m.path['slave_build'].join('src')

  def envsetup(self):
    # TODO(luqui): remove once no recipes call anymore
    return []

  def clean_local_files(self):
    target = self.c.BUILD_CONFIG
    debug_info_dumps = self.m.path['checkout'].join('out',
                                                    target,
                                                    'debug_info_dumps')
    test_logs = self.m.path['checkout'].join('out', target, 'test_logs')
    return self.m.python.inline(
        'clean local files',
        """
          import shutil, sys, os
          shutil.rmtree(sys.argv[1], True)
          shutil.rmtree(sys.argv[2], True)
          for base, _dirs, files in os.walk(sys.argv[3]):
            for f in files:
              if f.endswith('.pyc'):
                os.remove(os.path.join(base, f))
        """,
        args=[debug_info_dumps, test_logs, self.m.path['checkout']],
    )

  def run_tree_truth(self):
    # TODO(sivachandra): The downstream ToT builder will require
    # 'Show Revisions' step.
    repos = ['src', 'src-internal']
    if self.c.REPO_NAME not in repos:
      repos.append(self.c.REPO_NAME)
    # TODO(sivachandra): Disable subannottations after cleaning up
    # tree_truth.sh.
    yield self.m.step('tree truth steps',
                      [self.m.path['checkout'].join('build', 'tree_truth.sh'),
                       self.m.path['checkout']] + repos,
                      allow_subannotations=False,
                      can_fail_build=False)

  def runhooks(self, extra_env={}):
    return self.m.chromium.runhooks(env=dict(self.get_env().items() +
                                             extra_env.items()))

  def apply_svn_patch(self):
    # TODO(sivachandra): We should probably pull this into its own module
    # (maybe a 'tryserver' module) at some point.
    return self.m.step(
        'apply_patch',
        [self.m.path['build'].join('scripts', 'slave', 'apply_svn_patch.py'),
         '-p', self.m.properties['patch_url'],
         '-r', self.internal_dir])

  def compile(self, **kwargs):
    assert 'env' not in kwargs, (
        "chromium_andoid compile clobbers env in keyword arguments")
    kwargs['env'] = self.get_env()
    return self.m.chromium.compile(**kwargs)

  def findbugs(self, findbugs_options=[]):
    cmd = [self.m.path['checkout'].join('build', 'android', 'findbugs_diff.py')]
    cmd.extend(findbugs_options)

    if self.m.chromium.c.BUILD_CONFIG == 'Release':
      cmd.append('--release-build')

    yield self.m.step('findbugs', cmd, env=self.get_env())

    cmd = [self.m.path['checkout'].join('tools', 'android', 'findbugs_plugin',
               'test', 'run_findbugs_plugin_tests.py')]
    if self.m.chromium.c.BUILD_CONFIG == 'Release':
      cmd.append('--release-build')
    yield self.m.step('findbugs_tests', cmd, env=self.get_env())

  def checklicenses(self):
    yield self.m.step(
      'check_licenses',
      [self.m.path['checkout'].join('android_webview', 'tools',
                                    'webview_licenses.py'),
       'scan'],
      env=self.get_env())

  def git_number(self):
    yield self.m.step(
        'git_number',
        [self.m.path['depot_tools'].join('git_number.py')],
        stdout = self.m.raw_io.output(),
        step_test_data=(
          lambda:
            self.m.raw_io.test_api.stream_output('3000\n')
        ),
        cwd=self.m.path['checkout'])

  def check_webview_licenses(self):
    yield self.m.python(
        'check licenses',
        self.m.path['checkout'].join('android_webview',
                                     'tools',
                                     'webview_licenses.py'),
        args=['scan'],
        can_fail_build=False)

  def upload_build(self, bucket, path):
    archive_name = 'build_product.zip'

    zipfile = self.m.path['checkout'].join('out', archive_name)
    self._cleanup_list.append(zipfile)

    yield self.make_zip_archive(
      'zip_build_product',
      archive_name,
      preserve_paths=True,
      cwd=self.m.path['checkout']
    )

    yield self.m.gsutil.upload(
        name='upload_build_product',
        source=zipfile,
        bucket=bucket,
        dest=path
    )

  def download_build(self, bucket, path):
    base_path = path.split('/')[-1]
    zipfile = self.m.path['checkout'].join('out', base_path)
    self._cleanup_list.append(zipfile)
    yield self.m.gsutil.download(
        name='download_build_product',
        bucket=bucket,
        source=path,
        dest=zipfile
    )
    yield self.m.step(
      'unzip_build_product',
      ['unzip', '-o', zipfile],
      cwd=self.m.path['checkout'],
      abort_on_failure=True
    )

  def spawn_logcat_monitor(self):
    return self.m.step(
        'spawn_logcat_monitor',
        [self.m.path['build'].join('scripts', 'slave', 'daemonizer.py'),
         '--', self.c.cr_build_android.join('adb_logcat_monitor.py'),
         self.m.chromium.c.build_dir.join('logcat')],
        env=self.get_env(), can_fail_build=False)

  def device_status_check(self, restart_usb=False, **kwargs):
    def followup_fn(step_result):
      if not step_result.retcode == 0:
        params = {
          'summary': ('Device Offline on %s %s' %
            (self.m.properties['mastername'], self.m.properties['slavename'])),
          'comment': ('Buildbot: %s\n(Please do not change any labels)' %
            self.m.properties['buildername']),
          'labels': 'Restrict-View-Google,OS-Android,Infra,Infra-Labs',
        }
        link = ('https://code.google.com/p/chromium/issues/entry?%s' %
          urllib.urlencode(params))
        step_result.presentation.links.update({
          'report a bug': link
        })
      # Purple this step if no online device is found.
      if step_result.retcode == 1:
        step_result.presentation.status = 'EXCEPTION'

    args = []
    if restart_usb:
      args = ['--restart-usb']
    yield self.m.step(
        'device_status_check',
        [self.m.path['checkout'].join('build', 'android', 'buildbot',
                              'bb_device_status_check.py')] + args,
        env=self.get_env(),
        followup_fn=followup_fn,
        **kwargs)

  def provision_devices(self, skip_wipe=False, disable_location=False,
                        **kwargs):
    args = ['-t', self.m.chromium.c.BUILD_CONFIG]
    if skip_wipe:
      args.append('--skip-wipe')
    if disable_location:
      args.append('--disable-location')
    yield self.m.python(
        'provision_devices',
        self.m.path['checkout'].join(
            'build', 'android', 'provision_devices.py'),
        args=args,
        can_fail_build=False,
        **kwargs)

  def detect_and_setup_devices(self, restart_usb=False, skip_wipe=False,
                               disable_location=False):
    yield self.device_status_check(restart_usb=restart_usb)
    yield self.provision_devices(skip_wipe=skip_wipe,
                                 disable_location=disable_location)

  def adb_install_apk(self, apk, apk_package):
    install_cmd = [
        self.m.path['checkout'].join('build',
                                     'android',
                                     'adb_install_apk.py'),
        '--apk', apk,
        '--apk_package', apk_package
    ]
    if self.m.chromium.c.BUILD_CONFIG == 'Release':
      install_cmd.append('--release')
    yield self.m.step('install ' + apk, install_cmd,
                      env=self.get_env(), always_run=True)

  def monkey_test(self, **kwargs):
    args = [
        'monkey',
        '-v',
        '--package=%s' % self.c.channel,
        '--event-count=50000'
    ]
    yield self.m.python(
        'Monkey Test',
        str(self.m.path['checkout'].join('build', 'android', 'test_runner.py')),
        args,
        env={'BUILDTYPE': self.c.BUILD_CONFIG},
        always_run=True,
        **kwargs)

  def _run_sharded_tests(self,
                         config='sharded_perf_tests.json',
                         flaky_config=None,
                         **kwargs):
    args = ['perf', '--release', '--verbose', '--steps', config]
    if flaky_config:
      args.extend(['--flaky-steps', flaky_config])

    yield self.m.python(
        'Sharded Perf Tests',
        self.m.path['checkout'].join('build', 'android', 'test_runner.py'),
        args,
        cwd=self.m.path['checkout'],
        always_run=True,
        **kwargs)

  def run_sharded_perf_tests(self, config, flaky_config=None, perf_id=None,
                             perf_dashboard_id_transform=lambda x: x, **kwargs):
    """Run the perf tests from the given config file.

    config: the path of the config file containing perf tests.
    flaky_config: optional file of tests to avoid.
    perf_id: the id of the builder running these tests
    perf_dashboard_id_transform: a lambda transforming the test name to the
      perf dashboard id to upload to.

    returns: a step generator to run and upload the tests.
    """
    # test_runner.py actually runs the tests and records the results
    yield self._run_sharded_tests(config=config, flaky_config=flaky_config,
                                  **kwargs)

    # now obtain the list of tests that were executed.
    yield self.m.step(
        'get perf test list',
        [self.m.path['checkout'].join('build', 'android', 'test_runner.py'),
         'perf', '--steps', config, '--output-json-list', self.m.json.output()],
        step_test_data=lambda: self.m.json.test_api.output([
            'perf-test-1', 'perf-test-2']),
        always_run=True
    )
    perf_tests = self.m.step_history.last_step().json.output

    for test_name in perf_tests:
      test_name = str(test_name)  # un-unicode
      dashboard_id = perf_dashboard_id_transform(test_name)

      yield self.m.chromium.runtest(
          self.m.path['checkout'].join('build', 'android', 'test_runner.py'),
          ['perf', '--print-step', test_name, '--verbose'],
          name=test_name,
          perf_dashboard_id=dashboard_id,
          annotate='graphing',
          results_url='https://chromeperf.appspot.com',
          perf_id=perf_id,
          test_type=test_name,
          always_run=True)

  def run_instrumentation_suite(self, test_apk, test_data=None,
                                flakiness_dashboard=None,
                                annotation=None, except_annotation=None,
                                screenshot=False, verbose=False,
                                apk_package=None, host_driven_root=None,
                                **kwargs):
    args = ['--test-apk', test_apk]
    if test_data:
      args.extend(['--test_data', test_data])
    if flakiness_dashboard:
      args.extend(['--flakiness-dashboard-server', flakiness_dashboard])
    if annotation:
      args.extend(['-A', annotation])
    if except_annotation:
      args.extend(['-E', except_annotation])
    if screenshot:
      args.append('--screenshot')
    if verbose:
      args.append('--verbose')
    if self.m.chromium.c.BUILD_CONFIG == 'Release':
      args.append('--release')
    if self.c.coverage:
      args.extend(['--coverage-dir', self.coverage_dir,
                   '--python-only'])
    if host_driven_root:
      args.extend(['--host-driven-root', host_driven_root])

    yield self.m.python(
        'Instrumentation test %s' % (annotation or test_apk),
        self.m.path['checkout'].join('build', 'android', 'test_runner.py'),
        args=['instrumentation'] + args,
        always_run=True,
        **kwargs)

  def logcat_dump(self):
    if self.m.step_history.get('spawn_logcat_monitor'):
      return self.m.python(
          'logcat_dump',
          self.m.path['build'].join('scripts', 'slave', 'tee.py'),
          [self.m.chromium.output_dir.join('full_log'),
           '--',
           self.m.path['checkout'].join('build', 'android',
                                        'adb_logcat_printer.py'),
           self.m.path['checkout'].join('out', 'logcat')],
          always_run=True)

  def stack_tool_steps(self):
    log_file = self.m.path['checkout'].join('out',
                                            self.m.chromium.c.BUILD_CONFIG,
                                            'full_log')
    yield self.m.step(
        'stack_tool_with_logcat_dump',
        [self.m.path['checkout'].join('third_party', 'android_platform',
                              'development', 'scripts', 'stack'),
         '--more-info', log_file], always_run=True, env=self.get_env())
    yield self.m.step(
        'stack_tool_for_tombstones',
        [self.m.path['checkout'].join('build', 'android', 'tombstones.py'),
         '-a', '-s', '-w'], always_run=True, env=self.get_env())
    if self.c.asan_symbolize:
      yield self.m.step(
          'stack_tool_for_asan',
          [self.m.path['checkout'].join('build',
                                        'android',
                                        'asan_symbolize.py'),
           '-l', log_file], always_run=True, env=self.get_env())

  def test_report(self):
    return self.m.python.inline(
        'test_report',
         """
            import glob, os, sys
            for report in glob.glob(sys.argv[1]):
              with open(report, 'r') as f:
                for l in f.readlines():
                  print l
              os.remove(report)
         """,
         args=[self.m.path['checkout'].join('out',
                                            self.m.chromium.c.BUILD_CONFIG,
                                            'test_logs',
                                            '*.log')],
         always_run=True
    )

  def cleanup_build(self):
    return self.m.step(
        'cleanup_build',
        ['rm', '-rf'] + self._cleanup_list,
        always_run=True)

  def common_tests_setup_steps(self):
    yield self.spawn_logcat_monitor()
    yield self.detect_and_setup_devices()

  def common_tests_final_steps(self):
    yield self.logcat_dump()
    yield self.stack_tool_steps()
    yield self.test_report()
    yield self.cleanup_build()

  def run_bisect_script(self, extra_src='', path_to_config=''):
    yield self.m.step('prepare bisect perf regression',
        [self.m.path['checkout'].join('tools',
                                      'prepare-bisect-perf-regression.py'),
         '-w', self.m.path['slave_build']])
    args = []
    if extra_src:
      args = args + ['--extra_src', extra_src]
    if path_to_config:
      args = args + ['--path_to_config', path_to_config]
    yield self.m.step('run bisect perf regression',
        [self.m.path['checkout'].join('tools',
                                      'run-bisect-perf-regression.py'),
         '-w', self.m.path['slave_build']] + args)

  def run_test_suite(self, suite, verbose=True, isolate_file_path=None,
                     gtest_filter=None, tool=None):
    args = []
    if verbose:
      args.append('--verbose')
    if self.c.BUILD_CONFIG == 'Release':
      args.append('--release')
    if isolate_file_path:
      args.append('--isolate_file_path=%s' % isolate_file_path)
    if gtest_filter:
      args.append('--gtest_filter=%s' % gtest_filter)
    if tool:
      args.append('--tool=%s' % tool)

    yield self.m.python(
        str(suite),
        self.m.path['checkout'].join('build', 'android', 'test_runner.py'),
        ['gtest', '-s', suite] + args,
        env={'BUILDTYPE': self.c.BUILD_CONFIG},
        always_run=True)

  def coverage_report(self, **kwargs):
    assert self.c.coverage, (
        'Trying to generate coverage report but coverage is not enabled')
    gs_dest = 'java/%s/%s' % (
        self.m.properties['buildername'], self.m.properties['revision'])

    yield self.m.python(
        'Generate coverage report',
        self.m.path['checkout'].join(
            'build', 'android', 'generate_emma_html.py'),
        args=['--coverage-dir', self.coverage_dir,
              '--metadata-dir', self.out_path.join(self.c.BUILD_CONFIG),
              '--cleanup',
              '--output', self.coverage_dir.join('coverage_html',
                                                 'index.html')],
        always_run=True,
        **kwargs)

    yield self.m.gsutil.upload(
        source=self.coverage_dir.join('coverage_html'),
        bucket='chrome-code-coverage',
        dest=gs_dest,
        args=['-R'],
        name='upload coverage report',
        link_name='Coverage report',
        always_run=True,
        **kwargs)
