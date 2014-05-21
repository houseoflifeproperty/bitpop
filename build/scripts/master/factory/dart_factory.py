#!/usr/bin/python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to generate a Dart-specific BuildFactory.

Based on gclient_factory.py.
"""

from buildbot.process.buildstep import RemoteShellCommand
from buildbot.changes import svnpoller
from buildbot.status.mail import MailNotifier

from master.factory import chromium_factory
from master.factory import dart_commands
from master.factory import gclient_factory
from master import master_utils

import config

dartium_url = config.Master.dart_bleeding + '/deps/dartium.deps'
dartium_trunk_url = config.Master.dart_trunk + '/deps/dartium.deps'
dartium_libv2_url = 'https://dart.googlecode.com/svn/experimental/lib_v2/deps/dartium.deps'

# We set these paths relative to the dart root, the scripts need to
# fix these to be absolute if they don't run from there.
linux_env =  {'BUILDBOT_JAVA_HOME': 'third_party/java/linux/j2sdk'}
windows_env = {'BUILDBOT_JAVA_HOME': 'third_party\\java\\windows\\j2sdk',
               'LOGONSERVER': '\\\\AD1'}

dart_revision_url = "http://code.google.com/p/dart/source/detail?r=%s"

# These chromium factories are used for building dartium
F_LINUX_CH = None
F_MAC_CH = None
F_WIN_CH = None
F_LINUX_CH_TRUNK = None
F_MAC_CH_TRUNK = None
F_WIN_CH_TRUNK = None
F_WIN_CH_LIBV2 = None

def setup_chromium_factories():
  gclient_dartium = gclient_factory.GClientSolution(dartium_url, 'dartium.deps')
  gclient_dartium_trunk = gclient_factory.GClientSolution(dartium_trunk_url,
                                                          'dartium.deps')
  gclient_dartium_libv2 = gclient_factory.GClientSolution(dartium_libv2_url,
                                                          'dartium.deps')
  class DartiumFactory(chromium_factory.ChromiumFactory):
    def __init__(self, target_platform=None):
      chromium_factory.ChromiumFactory.__init__(self,
                                                'src/build',
                                                target_platform)
      self._solutions = []

    def add_solution(self, solution):
      self._solutions.append(solution)

  m_linux_ch = DartiumFactory('linux2')
  m_linux_ch.add_solution(gclient_dartium)
  m_mac_ch = DartiumFactory('darwin')
  m_mac_ch.add_solution(gclient_dartium)
  m_win_ch = DartiumFactory()
  m_win_ch.add_solution(gclient_dartium)

  m_linux_ch_trunk = DartiumFactory('linux2')
  m_linux_ch_trunk.add_solution(gclient_dartium_trunk)
  m_mac_ch_trunk = DartiumFactory('darwin')
  m_mac_ch_trunk.add_solution(gclient_dartium_trunk)
  m_win_ch_trunk = DartiumFactory()
  m_win_ch_trunk.add_solution(gclient_dartium_trunk)

  m_win_ch_libv2 = DartiumFactory()
  m_win_ch_libv2.add_solution(gclient_dartium_libv2)

  trunk_internal_url_src = config.Master.trunk_internal_url_src
  if trunk_internal_url_src:
    gclient_trunk_internal = gclient_factory.GClientSolution(
        trunk_internal_url_src)
    m_win_ch.add_solution(gclient_trunk_internal)
    m_win_ch_trunk.add_solution(gclient_trunk_internal)

  # Some shortcut to simplify the code in the master.cfg files
  global F_LINUX_CH, F_MAC_CH, F_WIN_CH
  global F_LINUX_CH_TRUNK, F_MAC_CH_TRUNK, F_WIN_CH_TRUNK
  global F_WIN_CH_LIBV2
  F_LINUX_CH = m_linux_ch.ChromiumFactory
  F_MAC_CH = m_mac_ch.ChromiumFactory
  F_WIN_CH = m_win_ch.ChromiumFactory
  F_LINUX_CH_TRUNK = m_linux_ch_trunk.ChromiumFactory
  F_MAC_CH_TRUNK = m_mac_ch_trunk.ChromiumFactory
  F_WIN_CH_TRUNK = m_win_ch_trunk.ChromiumFactory
  F_WIN_CH_LIBV2 = m_win_ch_libv2.ChromiumFactory
setup_chromium_factories()

def AddGeneralGClientProperties(factory_properties=None):
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

  def __init__(self, build_dir, target_platform=None, trunk=False,
               libv2 = False, target_os=None):
    solutions = []
    self.target_platform = target_platform
    deps_file = '/deps/all.deps'
    dart_url = config.Master.dart_bleeding + deps_file
    # If this is trunk use the deps file from there instead.
    if trunk:
      dart_url = config.Master.dart_trunk + deps_file
    if libv2:
      deps_url = 'https://dart.googlecode.com/svn/experimental/lib_v2'
      dart_url =  deps_url + deps_file
    custom_deps_list = []

    if config.Master.trunk_internal_url:
      custom_deps_list.append(self.CUSTOM_DEPS_JAVA)
      custom_deps_list.append(self.CUSTOM_TZ)

    main = gclient_factory.GClientSolution(
        dart_url,
        needed_components=self.NEEDED_COMPONENTS,
        custom_deps_list = custom_deps_list)
    solutions.append(main)

    gclient_factory.GClientFactory.__init__(self, build_dir, solutions,
                                            target_platform=target_platform,
                                            target_os=target_os)

  def DartFactory(self, target='Release', clobber=False, tests=None,
                  slave_type='BuilderTester', options=None,
                  compile_timeout=1200, build_url=None,
                  factory_properties=None, env=None):
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
                                              self._target_platform,
                                              env=env)

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
      dart_cmd_obj.AddTests(options=options)

    return factory

  def DartAnnotatedFactory(self, python_script,
                           target='Release', tests=None,
                           timeout=1200, factory_properties=None,
                           env=None):
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
    dart_cmd_obj.AddAnnotatedSteps(python_script, timeout=timeout)
    return factory

class DartUtils(object):
  mac_options = ['--compiler=goma-clang',
                 '--',
                 '-target',
                 'dartium_builder']
  mac_dbg_options = ['--compiler=goma-clang',
                     '--build-tool=ninja',
                     '--',
                     'dartium_builder']
  linux_options = ['--compiler=goma', 'dartium_builder']

  win_project = 'all.sln;dartium_builder'

  win_rel_factory_properties = {
    'gclient_env': {
      'GYP_DEFINES': 'fastbuild=1',
    },
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }
  win_dbg_factory_properties = {
    'gclient_env': {
      'GYP_DEFINES': 'fastbuild=1 component=shared_library',
    },
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }
  mac_factory_properties = {
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }
  linux_factory_properties = {
    'gclient_env': {'GYP_GENERATORS' : 'make'},
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }
  linux32_factory_properties = {
    'gclient_env': {'GYP_GENERATORS' : 'make',
                    'GYP_DEFINES': 'target_arch=ia32'},
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }


  factory_base = {
    'vm-mac': DartFactory('dart', 'vm-mac'),
    'vm-linux': DartFactory('dart', 'vm-linux'),
    'vm-win32': DartFactory('dart', 'vm-win32'),
    'dartc-linux': DartFactory('dart', 'dartc-linux'),
    'dart_android': DartFactory('dart', 'dart_android', target_os='android'),
    'dart_client': DartFactory('dart', 'dart_client'),
    'dart_client_libv2': DartFactory('dart', 'dart_client', libv2=True),
    'dart-editor': DartFactory('dart', 'dart-editor'),
    'frog': DartFactory('dart', 'frog'),
    'frogsh': DartFactory('dart', 'frogsh'),
    'dart2dart-linux': DartFactory('dart', 'dart2dart-linux'),
    'vm-mac-trunk': DartFactory('dart', 'vm-mac', trunk=True),
    'vm-linux-trunk': DartFactory('dart', 'vm-linux', trunk=True),
    'vm-win32-trunk': DartFactory('dart', 'vm-win32', trunk=True),
    'dart-editor-trunk': DartFactory('dart', 'dart-editor', trunk=True),
    'vm-win32-libv2': DartFactory('dart', 'dart-editor', libv2=True),
  }
  factory_base_dartium = {
    'dartium-mac-full' : F_MAC_CH(
        target='Release',
        options=mac_options,
        clobber=True,
        tests=['annotated_steps'],
        factory_properties=mac_factory_properties),
    'dartium-mac-inc' : F_MAC_CH(
        target='Release',
        options=mac_options,
        tests=['annotated_steps'],
        factory_properties=mac_factory_properties),
    'dartium-mac-debug' : F_MAC_CH(
        target='Debug',
        compile_timeout=3600,
        options=mac_dbg_options,
        tests=['annotated_steps'],
        factory_properties=mac_factory_properties),
    'dartium-lucid64-full' : F_LINUX_CH(
        target='Release',
        clobber=True,
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux_factory_properties),
    'dartium-lucid64-inc' : F_LINUX_CH(
        target='Release',
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux_factory_properties),
    'dartium-lucid64-debug' : F_LINUX_CH(
        target='Debug',
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux_factory_properties),
    'dartium-win-full' : F_WIN_CH(
        target='Release',
        project=win_project,
        clobber=True,
        tests=['annotated_steps'],
        factory_properties=win_rel_factory_properties),
    'dartium-win-inc' : F_WIN_CH(
        target='Release',
        project=win_project,
        tests=['annotated_steps'],
        factory_properties=win_rel_factory_properties),
    'dartium-win-debug' : F_WIN_CH(
        target='Debug',
        project=win_project,
        tests=['annotated_steps'],
        factory_properties=win_dbg_factory_properties),
    'dartium-lucid32-full' : F_LINUX_CH(
        target='Release',
        clobber=True,
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux32_factory_properties),
    'dartium-lucid64-full-trunk' : F_LINUX_CH_TRUNK(
        target='Release',
        clobber=True,
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux_factory_properties),
    'dartium-win-full-trunk' : F_WIN_CH_TRUNK(
        target='Release',
        project=win_project,
        clobber=True,
        tests=['annotated_steps'],
        factory_properties=win_rel_factory_properties),
    'dartium-mac-full-trunk' : F_MAC_CH_TRUNK(
        target='Release',
        options=mac_options,
        clobber=True,
        tests=['annotated_steps'],
        factory_properties=mac_factory_properties),
    'dartium-lucid32-full-trunk' : F_LINUX_CH_TRUNK(
        target='Release',
        clobber=True,
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux32_factory_properties),
    'release-lucid64-trunk' : F_LINUX_CH(
        target='Release',
        clobber=True,
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux_factory_properties),
    'dartium-win-inc-libv2' : F_WIN_CH_LIBV2(
        target='Release',
        project=win_project,
        tests=['annotated_steps'],
        factory_properties=win_rel_factory_properties),
  }


  def __init__(self, active_master):
    self._active_master = active_master

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
      else:
        return None

    # Polls config.Master.dart_url for changes
    return svnpoller.SVNPoller(svnurl=config.Master.dart_url,
                               split_file=dart_tree_file_splitter,
                               pollinterval=10,
                               revlinktmpl=dart_revision_url)

  def setup_factories(self, variants):
    def setup_factory(v, base, platform):
      env = v.get('env', {})
      if platform in ['dart_client', 'dart-editor', 'dart_android',
                      'dart_client-trunk', 'dart-editor-trunk',
                      'dart_client_libv2']:
        v['factory_builder'] = base.DartAnnotatedFactory(
            python_script='client/tools/buildbot_annotated_steps.py',
            env=env,
        )
      else:
        options = {
            'mode': v['mode'],
            'arch': v['arch'],
            'name': v['name'] }
        # TODO(ricow) Remove shards from here when we move dart2dart
        # to annotated.
        if 'shards' in v and 'shard' in v:
          options['shards'] = v['shards']
          options['shard'] = v['shard']
        v['factory_builder'] = base.DartFactory(
            slave_type='BuilderTester',
            clobber=False,
            options=options,
            env=env
        )

    for v in variants:
      platform = v['platform']
      base = self.factory_base[platform]
      setup_factory(v, base, platform)

  def setup_dartium_factories(self, dartium_variants):
    for variant in dartium_variants:
      variant['factory_builder'] = self.factory_base_dartium[variant['name']]

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
    return statuses

  @staticmethod
  def get_builders_from_variants(variants,
                                 slaves,
                                 slave_locks,
                                 auto_reboot = False):
    builders = []
    for v in variants:
      builders.append({
         'name': v['name'],
         'builddir': v['name'],
         'factory': v['factory_builder'],
         'slavenames': slaves.GetSlavesName(builder=v['name']),
         'category': v['category'],
         'locks': slave_locks,
         'auto_reboot': auto_reboot})
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
      statuses.append(
          MailNotifier(fromaddr=self._active_master.from_address,
                       mode='problem',
                       sendToInterestedUsers=send_to_interested_useres,
                       extraRecipients=extra_recipients,
                       lookup=master_utils.FilterDomain(),
                       builders=notifying_builders))
    return statuses
