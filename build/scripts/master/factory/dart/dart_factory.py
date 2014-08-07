#!/usr/bin/python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to generate a Dart-specific BuildFactory.

Based on gclient_factory.py.
"""

import random

from buildbot.changes import svnpoller
from buildbot.process.buildstep import RemoteShellCommand
from buildbot.status.mail import MailNotifier
from buildbot.status.status_push import HttpStatusPush
from buildbot.steps import trigger

from common import chromium_utils

from master.factory import v8_factory
from master.factory import chromium_factory
from master.factory.dart import dart_commands
from master.factory.dart.channels import CHANNELS, CHANNELS_BY_NAME
from master.factory import gclient_factory
from master import master_utils

import config

v8_stable_branch = '3.26'
android_tools_rev = '@b12d410c0ee23385da78e6c9f353d28fd992e0bd'
android_resources_rev = '@3855'

chromium_git = 'http://git.chromium.org/git/'

dartium_url = config.Master.dart_bleeding + '/deps/dartium.deps'
android_tools_url = chromium_git + 'android_tools.git' + android_tools_rev
if config.Master.v8_internal_url:
  android_resources_url = (config.Master.v8_internal_url +
      '/buildbot_deps/android_testing_resources' + android_resources_rev )
else:
  android_resources_url = None


# We set these paths relative to the dart root, the scripts need to
# fix these to be absolute if they don't run from there.
linux_env =  {'BUILDBOT_JAVA_HOME': 'third_party/java/linux/j2sdk'}
linux_clang_env =  {'BUILDBOT_JAVA_HOME': 'third_party/java/linux/j2sdk',
                    'CC': 'third_party/clang/linux/bin/clang',
                    'CXX': 'third_party/clang/linux/bin/clang++'}
windows_env = {'BUILDBOT_JAVA_HOME': 'third_party\\java\\windows\\j2sdk',
               'LOGONSERVER': '\\\\AD1'}
dart2dart_backend_env = {'BUILDBOT_JAVA_HOME': 'third_party/java/linux/j2sdk',
                         'DART_VM_OPTIONS': '-DUSE_NEW_BACKEND=true'}

dart_revision_url = "http://code.google.com/p/dart/source/detail?r=%s"

# gclient custom vars
CUSTOM_VARS_SOURCEFORGE_URL = ('sourceforge_url', config.Master.sourceforge_url)
CUSTOM_VARS_GOOGLECODE_URL = ('googlecode_url', config.Master.googlecode_url)
CUSTOM_VARS_CHROMIUM_URL = (
  'chromium_url', config.Master.server_url + config.Master.repo_root)

custom_vars_list = [CUSTOM_VARS_SOURCEFORGE_URL,
                    CUSTOM_VARS_GOOGLECODE_URL,
                    CUSTOM_VARS_CHROMIUM_URL]

# gclient custom deps
if config.Master.trunk_internal_url:
  CUSTOM_DEPS_WIN7_SDK = (
    "src/third_party/platformsdk_win7",
    config.Master.trunk_internal_url + "/third_party/platformsdk_win7@23175")
  CUSTOM_DEPS_WIN8_SDK = (
    "src/third_party/platformsdk_win8",
    config.Master.trunk_internal_url
    + "/third_party/platformsdk_win8_9200@32005")
  CUSTOM_DEPS_DIRECTX_SDK = (
    "src/third_party/directxsdk",
    config.Master.trunk_internal_url + "/third_party/directxsdk@20250")
  custom_deps_list_win = [CUSTOM_DEPS_WIN7_SDK,
                          CUSTOM_DEPS_WIN8_SDK,
                          CUSTOM_DEPS_DIRECTX_SDK]
else:
  custom_deps_list_win = []

# Wix custom deps
if config.Master.trunk_internal_url:
  custom_wix_deps = [(
    'dart/third_party/wix',
    config.Master.trunk_internal_url + "/third_party/wix/v3_6_3303")]
else:
  custom_wix_deps = []

custom_deps_list_chromeOnAndroid = [
    ('dart/third_party/android_tools', android_tools_url),
]
if android_resources_url:
  custom_deps_list_chromeOnAndroid.append(
      ('dart/third_party/android_testing_resources', android_resources_url))

def BuildChromiumFactory(channel, target_platform='win32'):
  def new_solution(deps_url, custom_vars, custom_deps):
    return  gclient_factory.GClientSolution(
        deps_url,
        'dartium.deps',
        custom_vars_list = custom_vars,
        custom_deps_list = custom_deps)

  class DartiumFactory(chromium_factory.ChromiumFactory):
    def __init__(self, target_platform=None):
      if target_platform in ['linux2', 'darwin']:
        # We use make/ninja on our linux/mac dartium builders which use
        # 'src/out' as build directory
        build_directory = 'src/out'
      else:
        # On windows we still use msvc which uses 'src/build' as build directory
        build_directory = 'src/build'
      chromium_factory.ChromiumFactory.__init__(self,
                                                build_directory,
                                                target_platform)
      self._solutions = []

    def add_solution(self, solution):
      self._solutions.append(solution)

  # 'channel.dartium_deps_path' can be for example:
  #   "/branches/bleeding_edge/deps/dartium.deps"
  # config.Master.dart_url will be the base svn url. It will point to the
  # mirror if we're in golo and otherwise to the googlecode location.
  dartium_deps_url = config.Master.dart_url + channel.dartium_deps_path

  factory = DartiumFactory(target_platform)
  if target_platform == 'win32':
    factory.add_solution(
        new_solution(dartium_deps_url, custom_vars_list, custom_deps_list_win))
  else:
    factory.add_solution(new_solution(dartium_deps_url, custom_vars_list, []))

  return factory.ChromiumFactory

# These factories are used for building v8
v8_win_default_opts = ['--build-tool=vs', '--src-dir=v8']
v8_linux_default_opts = ['--build-tool=make', '--src-dir=v8',
                         # TODO(thakis): Remove this once v8 r18257 has reached
                         # the stable branch.
                         '--', 'builddir_name=.']
v8_mac_default_opts = ['--solution=../build/all.xcodeproj',
                       '--build-tool=xcode', '--src-dir=v8']

m_v8_linux_stable = v8_factory.V8Factory('v8', target_platform = 'linux2',
                                         branch='branches/' + v8_stable_branch)
m_v8_win32_stable = v8_factory.V8Factory('v8', target_platform = 'win32',
                                         branch='branches/' + v8_stable_branch)
m_v8_mac_stable = v8_factory.V8Factory('v8', target_platform = 'darwin',
                                       branch='branches/' + v8_stable_branch)

def AddGeneralGClientProperties(factory_properties):
  """Adds the general gclient options to ensure we get the correct revisions"""
  # Make sure that pulled in projects have the right revision based on date.
  factory_properties['gclient_transitive'] = True
  # Don't set branch part on the --revision flag - we don't use standard
  # chromium layout and hence this is doing the wrong thing.
  factory_properties['no_gclient_branch'] = True

class DartFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the dart master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  # A map used to skip dependencies when a test is not run.
  # The map key is the test name. The map value is an array containing the
  # dependencies that are not needed when this test is not run.
  NEEDED_COMPONENTS = {
  }

  NEEDED_COMPONENTS_INTERNAL = {
  }

  if config.Master.trunk_internal_url:
    CUSTOM_DEPS_JAVA = ('dart/third_party/java',
                        config.Master.trunk_internal_url +
                        '/third_party/openjdk')
    # Fix broken ubuntu OpenJDK by importing windows TZ files
    CUSTOM_TZ = ('dart/third_party/java/linux/j2sdk/jre/lib/zi',
                 config.Master.trunk_internal_url +
                 '/third_party/openjdk/windows/j2sdk/jre/lib/zi')

  def __init__(self, channel=None, build_dir='dart', target_platform='posix',
               target_os=None, custom_deps_list=None,
               nohooks_on_update=False, is_standalone=False):
    solutions = []
    self.target_platform = target_platform

    # Default to the bleeding_edge channel
    if not channel:
      channel = CHANNELS_BY_NAME['be']
    self.channel = channel

    # 'channel.all_deps_path' can be for example:
    #   "/branches/bleeding_edge/deps/all.deps"
    # config.Master.dart_url will be the base svn url. It will point to the
    # mirror if we're in golo and otherwise to the googlecode location.
    if is_standalone:
      deps_url = config.Master.dart_url + self.channel.standalone_deps_path
    else:
      deps_url = config.Master.dart_url + self.channel.all_deps_path

    if not custom_deps_list:
      custom_deps_list = []

    if config.Master.trunk_internal_url:
      custom_deps_list.append(self.CUSTOM_DEPS_JAVA)
      custom_deps_list.append(self.CUSTOM_TZ)

    main = gclient_factory.GClientSolution(
        deps_url,
        needed_components=self.NEEDED_COMPONENTS,
        custom_deps_list = custom_deps_list,
        custom_vars_list = custom_vars_list)
    solutions.append(main)

    gclient_factory.GClientFactory.__init__(self, build_dir, solutions,
                                            target_platform=target_platform,
                                            target_os=target_os,
                                            nohooks_on_update=nohooks_on_update)

  def DartFactory(self, target='Release', clobber=False, tests=None,
                  slave_type='BuilderTester', options=None,
                  compile_timeout=1200, build_url=None,
                  factory_properties=None, env=None, triggers=()):
    factory_properties = factory_properties or {}
    AddGeneralGClientProperties(factory_properties)
    tests = tests or []
    gclient_spec = self.BuildGClientSpec(tests)
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               factory_properties=factory_properties)
    # Get the factory command object to create new steps to the factory.
    dart_cmd_obj = dart_commands.DartCommands(factory,
                                              target,
                                              self._build_dir,
                                              self.target_platform,
                                              env=env)

    dart_cmd_obj.AddKillStep(step_name="Taskkill before running")

    # We must always add the MaybeClobberStep, since this factory is
    # created at master start, but the choice of clobber or not may be
    # chosen at runtime (e.g. check the 'clobber' box).
    dart_cmd_obj.AddMaybeClobberStep(clobber, options=options)

    # Add the compile step if needed.
    if slave_type in ['BuilderTester', 'Builder', 'Trybot']:
      dart_cmd_obj.AddCompileStep(options=options,
                                  timeout=compile_timeout)

    # Add all the tests.
    if slave_type in ['BuilderTester', 'Trybot', 'Tester']:
      dart_cmd_obj.AddTests(options=options, channel=self.channel)

     # Archive crash dumps
    if slave_type in ['BuilderTester', 'Trybot', 'Tester']:
      # Currently we only do this on bleeding since scripts have not landed
      # on trunk/stable yet.
      if self.channel.name == 'be':
        dart_cmd_obj.AddArchiveCoredumps(options=options)

    for trigger_instance in triggers:
      dart_cmd_obj.AddTrigger(trigger_instance)

    dart_cmd_obj.AddKillStep(step_name="Taskkill after running")

    return factory

  def DartAnnotatedFactory(self, python_script,
                           target='Release', tests=None,
                           timeout=1200, factory_properties=None,
                           env=None, triggers=(), secondAnnotatedRun=False):
    factory_properties = factory_properties or {}
    AddGeneralGClientProperties(factory_properties)
    tests = tests or []
    # Create the spec for the solutions
    gclient_spec = self.BuildGClientSpec(tests)
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               factory_properties=factory_properties)
    # Get the factory command object to create new steps to the factory.
    dart_cmd_obj = dart_commands.DartCommands(factory,
                                              target,
                                              self._build_dir,
                                              self._target_platform,
                                              env=env)
    dart_cmd_obj.AddKillStep(step_name="Taskkill before running")

    dart_cmd_obj.AddAnnotatedSteps(python_script, timeout=timeout)

    for trigger_instance in triggers:
      dart_cmd_obj.AddTrigger(trigger_instance)

    if secondAnnotatedRun:
      dart_cmd_obj.AddAnnotatedSteps(python_script, timeout=timeout, run=2)

    dart_cmd_obj.AddKillStep(step_name="Taskkill after running")

    return factory

class DartUtils(object):
  mac_options = ['--compiler=goma-clang',
                 '--build-tool=ninja',
                 '--',
                 'dartium_builder']
  mac_dbg_options = ['--compiler=goma-clang',
                     '--build-tool=ninja',
                     '--',
                     'dartium_builder']
  linux_options = ['--compiler=goma', '--build-tool=ninja', 'dartium_builder']
  win_options_ninja = ['--build-tool=ninja', 'dartium_builder']

  win_project = 'all.sln;dartium_builder'

  win_rel_factory_properties = {
    'gclient_env': {
      'GYP_DEFINES': 'fastbuild=1 disable_nacl=1 disable_pnacl=1',
    },
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }
  win_rel_factory_properties_ninja = {
    'gclient_env': {
      'GYP_DEFINES': 'fastbuild=1 disable_nacl=1 disable_pnacl=1',
      'GYP_GENERATORS': 'ninja',
    },
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }

  win_dbg_factory_properties = {
    'gclient_env': {
      # We currently cannot use 'component=shared_library' here, because
      # dartium/src/build/common.gypi will enable 'ExceptionHandling'.
      # This results in the VisualStudio compiler switch '/EHsc' which in turn
      # will unwind the stack and call destructors when doing a longjmp().
      # The DartVM uses it's own mechanism for calling the destructors (see
      # vm/longjump.cc). (i.e. with /EHsc the destructors will be called twice)
      'GYP_DEFINES': 'fastbuild=1 component=static_library '
                     'disable_nacl=1 disable_pnacl=1',
    },
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }
  mac_factory_properties = {
    'gclient_env': {
        'GYP_DEFINES': 'disable_nacl=1 disable_pnacl=1',
    },
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }
  linux_factory_properties = {
    'gclient_env': {
        'GYP_GENERATORS' : 'ninja',
        'GYP_DEFINES': 'disable_nacl=1 disable_pnacl=1',
    },
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }
  linux32_factory_properties = {
    'gclient_env': {
        'GYP_GENERATORS' : 'ninja',
        'GYP_DEFINES': 'target_arch=ia32 disable_nacl=1 disable_pnacl=1',
    },
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }

  @staticmethod
  def get_factory_base(channel):
    postfix = channel.builder_postfix
    factory_base = {
      'posix' + postfix: DartFactory(channel),
      'posix-standalone' + postfix: DartFactory(channel, is_standalone=True),
      'posix-standalone-noRunhooks' + postfix:
          DartFactory(channel, nohooks_on_update=True, is_standalone=True),
      'chromeOnAndroid' + postfix:
          DartFactory(channel,
                      custom_deps_list=custom_deps_list_chromeOnAndroid),
      'android' + postfix: DartFactory(channel, target_os='android'),
      'windows' + postfix: DartFactory(channel, target_platform='win32'),
      'windows-wix' + postfix:
          DartFactory(channel, target_platform='win32',
                      custom_deps_list=custom_wix_deps),
    }
    return factory_base

  @staticmethod
  def get_dartium_factory_base(channel):
    postfix = channel.builder_postfix

    F_MAC_CH = BuildChromiumFactory(channel, target_platform='darwin')
    F_LINUX_CH = BuildChromiumFactory(channel, target_platform='linux2')
    F_WIN_CH = BuildChromiumFactory(channel, target_platform='win32')

    factory_base_dartium = {
      'dartium-mac-full' + postfix: F_MAC_CH(
          target='Release',
          options=DartUtils.mac_options,
          clobber=True,
          tests=['annotated_steps'],
          factory_properties=DartUtils.mac_factory_properties),
      'dartium-mac-inc' + postfix: F_MAC_CH(
          target='Release',
          options=DartUtils.mac_options,
          tests=['annotated_steps'],
          factory_properties=DartUtils.mac_factory_properties),
      'dartium-mac-debug' + postfix: F_MAC_CH(
          target='Debug',
          compile_timeout=3600,
          options=DartUtils.mac_dbg_options,
          tests=['annotated_steps'],
          factory_properties=DartUtils.mac_factory_properties),
      'dartium-lucid64-full' + postfix: F_LINUX_CH(
          target='Release',
          clobber=True,
          options=DartUtils.linux_options,
          tests=['annotated_steps'],
          factory_properties=DartUtils.linux_factory_properties),
      'dartium-lucid64-inc' + postfix: F_LINUX_CH(
          target='Release',
          options=DartUtils.linux_options,
          tests=['annotated_steps'],
          factory_properties=DartUtils.linux_factory_properties),
      'dartium-lucid64-debug' + postfix: F_LINUX_CH(
          target='Debug',
          options=DartUtils.linux_options,
          tests=['annotated_steps'],
          factory_properties=DartUtils.linux_factory_properties),
      'dartium-win-full' + postfix: F_WIN_CH(
          target='Release',
          project=DartUtils.win_project,
          tests=['annotated_steps'],
          factory_properties=DartUtils.win_rel_factory_properties),
      'dartium-win-inc' + postfix: F_WIN_CH(
          target='Release',
          project=DartUtils.win_project,
          tests=['annotated_steps'],
          factory_properties=DartUtils.win_rel_factory_properties),
      'dartium-win-inc-ninja' + postfix: F_WIN_CH(
          target='Release',
          options=DartUtils.win_options_ninja,
          tests=['annotated_steps'],
          factory_properties=DartUtils.win_rel_factory_properties_ninja),
      'dartium-win-debug' + postfix: F_WIN_CH(
          target='Debug',
          project=DartUtils.win_project,
          tests=['annotated_steps'],
          factory_properties=DartUtils.win_dbg_factory_properties),
      'dartium-lucid32-full' + postfix: F_LINUX_CH(
          target='Release',
          clobber=True,
          options=DartUtils.linux_options,
          tests=['annotated_steps'],
          factory_properties=DartUtils.linux32_factory_properties),
    }
    return factory_base_dartium

  factory_base = {}
  factory_base_dartium = {}

  def __init__(self, active_master):
    self._active_master = active_master

    for channel in CHANNELS:
      DartUtils.factory_base.update(DartUtils.get_factory_base(channel))
    for channel in CHANNELS:
      DartUtils.factory_base_dartium.update(
          DartUtils.get_dartium_factory_base(channel))

  @staticmethod
  def monkey_patch_remoteshell():
    # Hack to increase timeout for steps, dart2js debug checked mode takes more
    # than 8 hours.
    RemoteShellCommand.__init__.im_func.func_defaults = (None,
                                                         1,
                                                         1,
                                                         1200,
                                                         48*60*60, {},
                                                         'slave-config',
                                                         True)

  @staticmethod
  def get_svn_poller():
    def dart_tree_file_splitter(path):
      pieces = path.split('/')
      if pieces[0] == 'trunk':
        return ('trunk', '/'.join(pieces[1:]))
      elif pieces[0] == 'branches':
        return ('/'.join(pieces[0:2]),
                '/'.join(pieces[2:]))
      elif pieces[0] == 'experimental':
        return ('/'.join(pieces[0:2]),
                '/'.join(pieces[2:]))
      else:
        return None

    # Polls config.Master.dart_url for changes
    return svnpoller.SVNPoller(svnurl=config.Master.dart_url,
                               svnbin=chromium_utils.SVN_BIN,
                               split_file=dart_tree_file_splitter,
                               pollinterval=10,
                               revlinktmpl=dart_revision_url)

  @staticmethod
  def prioritize_builders(buildmaster, builders):
    def get_priority(name):
      for channel in CHANNELS:
        if name.endswith(channel.builder_postfix):
          return channel.priority
      # Default to a low priority
      return 10
    # Python's sort is stable, which means that builders with the same priority
    # will be in random order.
    random.shuffle(builders)
    builders.sort(key=lambda b: get_priority(b.name))
    return builders


  def setup_factories(self, variants):
    def setup_dart_factory(v, base, no_annotated):
      # If we have triggers specified, create corresponding trigger.Trigger
      # steps. Example of a trigger specification
      # 'triggers' : [{
      #   'schedulerNames': ['scheduler-arm'],
      #   'waitForFinish': False,
      #   'updateSourceStamp': False,
      # }],
      triggers = v.get('triggers', ())
      trigger_instances = []
      for trigger_spec in triggers:
        trigger_instances.append(
            trigger.Trigger(
                schedulerNames=trigger_spec['schedulerNames'],
                waitForFinish=trigger_spec['waitForFinish'],
                updateSourceStamp=trigger_spec['updateSourceStamp']))

      env = v.get('env', {})
      if no_annotated:
        options = {
            'mode': v['mode'],
            'arch': v['arch'],
            'name': v['name'],
            'vm_options': v.get('vm_options', None),
            'checked_config': v.get('checked_config', None),
        }
        if 'shards' in v and 'shard' in v:
          options['shards'] = v['shards']
          options['shard'] = v['shard']
        v['factory_builder'] = base.DartFactory(
            slave_type='BuilderTester',
            clobber=False,
            options=options,
            env=env,
            triggers=trigger_instances,
        )
      else:
        v['factory_builder'] = base.DartAnnotatedFactory(
            python_script='client/tools/buildbot_annotated_steps.py',
            env=env,
            triggers=trigger_instances,
            secondAnnotatedRun=v.get('second_annotated_steps_run', False)
        )

    def setup_v8_factory(v):
      factory = None
      name = v['name']
      arch = v['arch']
      if name.startswith('v8-linux-release'):
        factory = m_v8_linux_stable.V8Factory(
            options=v8_linux_default_opts,
            target='Release',
            factory_properties={
              'gclient_env': {'GYP_DEFINES': 'v8_enable_disassembler=1'},
            },
            tests=[],
            target_arch=arch)
      elif name.startswith('v8-win-release'):
        factory = m_v8_win32_stable.V8Factory(
            options=v8_win_default_opts,
            project='all.sln',
            target='Release',
            factory_properties={
              'gclient_env': {'GYP_DEFINES': 'v8_enable_disassembler=1'},
            },
            tests=[],
            target_arch=arch)
      elif name.startswith('v8-mac-release'):
        factory = m_v8_mac_stable.V8Factory(
            options=v8_mac_default_opts,
            target='Release',
            factory_properties={
              'gclient_env': {'GYP_DEFINES': 'v8_enable_disassembler=1'},
            },
            tests=[],
            target_arch=arch)
      else:
        raise Exception("Unknown v8 builder")
      v['factory_builder'] = factory

    for v in variants:
      platform = v['platform']
      if platform == 'v8_vm':
        setup_v8_factory(v)
      else:
        base = self.factory_base[platform]
        name = v['name']
        no_annotated = ((name.startswith('vm') or
                        name.startswith('dart2dart') or
                        name.startswith('dartc') or
                        name.startswith('new_analyzer') or
                        name.startswith('analyzer_experimental'))
                        and not name.startswith('vm-android')
                        and not name.startswith('cross-')
                        and not name.startswith('target-'))
        setup_dart_factory(v, base, no_annotated)

  def setup_dartium_factories(self, dartium_variants):
    for variant in dartium_variants:
      name = variant['name']
      variant['factory_builder'] = self.factory_base_dartium[name]

  def get_web_statuses(self):
    public_html = '../master.chromium/public_html'
    templates = ['../master.client.dart/templates',
                 '../master.chromium/templates']
    master_port = self._active_master.master_port
    master_port_alt = self._active_master.master_port_alt

    statuses = []
    statuses.append(master_utils.CreateWebStatus(master_port,
                                                 allowForce=True,
                                                 public_html=public_html,
                                                 templates=templates))
    statuses.append(
        master_utils.CreateWebStatus(master_port_alt, allowForce=False))

    http_status_push_url = self._active_master.http_status_push_url
    if self._active_master.is_production_host and http_status_push_url:
      statuses.append(HttpStatusPush(serverUrl=http_status_push_url))
    return statuses

  @staticmethod
  def get_builders_from_variants(variants,
                                 slaves,
                                 slave_locks,
                                 auto_reboot = False):
    builders = []
    for v in variants:
      builder = {
         'name': v['name'],
         'builddir': v['name'],
         'factory': v['factory_builder'],
         'slavenames': slaves.GetSlavesName(builder=v['name']),
         'category': v['category'],
         'locks': slave_locks,
         'auto_reboot': auto_reboot}
      if 'merge_requests' in v:
        builder['mergeRequests'] = v['merge_requests']
      builders.append(builder)
    return builders

  @staticmethod
  def get_builder_names(variants):
    return [variant['name'] for variant in variants]

  @staticmethod
  def get_slaves(builders):
    # The 'slaves' list defines the set of allowable buildslaves. List all the
    # slaves registered to a builder. Remove dupes.
    return master_utils.AutoSetupSlaves(builders,
                                        config.Master.GetBotPassword())

  def get_mail_notifier_statuses(self, mail_notifiers):
    statuses = []
    for mail_notifier in mail_notifiers:
      notifying_builders = mail_notifier['builders']
      extra_recipients = mail_notifier['extraRecipients']
      send_to_interested_useres = mail_notifier.get('sendToInterestedUsers',
                                                    False)
      subject = mail_notifier.get('subject')
      if subject:
        statuses.append(
            MailNotifier(fromaddr=self._active_master.from_address,
                         mode='problem',
                         subject=subject,
                         sendToInterestedUsers=send_to_interested_useres,
                         extraRecipients=extra_recipients,
                         lookup=master_utils.FilterDomain(),
                         builders=notifying_builders))
      else:
        statuses.append(
            MailNotifier(fromaddr=self._active_master.from_address,
                         mode='problem',
                         sendToInterestedUsers=send_to_interested_useres,
                         extraRecipients=extra_recipients,
                         lookup=master_utils.FilterDomain(),
                         builders=notifying_builders))
    return statuses

