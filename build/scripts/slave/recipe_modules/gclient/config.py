# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import types

from slave.recipe_config import config_item_context, ConfigGroup, BadConf
from slave.recipe_config import ConfigList, Dict, Single, Static, Set, List

def BaseConfig(USE_MIRROR=True, GIT_MODE=False, CACHE_DIR=None, **_kwargs):
  deps = '.DEPS.git' if GIT_MODE else 'DEPS'
  cache_dir = str(CACHE_DIR) if GIT_MODE and CACHE_DIR else None
  return ConfigGroup(
    solutions = ConfigList(
      lambda: ConfigGroup(
        name = Single(basestring),
        url = Single(basestring),
        deps_file = Single(basestring, empty_val=deps, required=False,
                           hidden=False),
        managed = Single(bool, empty_val=True, required=False, hidden=False),
        custom_deps = Dict(value_type=(basestring, types.NoneType)),
        custom_vars = Dict(value_type=basestring),
        safesync_url = Single(basestring, required=False),

        revision = Single(basestring, required=False, hidden=True),
      )
    ),
    deps_os = Dict(value_type=basestring),
    hooks = List(basestring),
    target_os = Set(basestring),
    target_os_only = Single(bool, empty_val=False, required=False),
    cache_dir = Static(cache_dir, hidden=False),

    # Maps 'solution' -> build_property
    got_revision_mapping = Dict(hidden=True),

    # TODO(iannucci): HACK! The use of None here to indicate that we apply this
    #   to the solution.revision field is really terrible. I mostly blame
    #   gclient.
    # Maps 'parent_build_property' -> 'custom_var_name'
    # Maps 'parent_build_property' -> None
    # If value is None, the property value will be applied to
    # solutions[0].revision. Otherwise, it will be applied to
    # solutions[0].custom_vars['custom_var_name']
    parent_got_revision_mapping = Dict(hidden=True),

    GIT_MODE = Static(bool(GIT_MODE)),
    USE_MIRROR = Static(bool(USE_MIRROR)),
  )

VAR_TEST_MAP = {
  'USE_MIRROR': (True, False),
  'GIT_MODE':   (True, False),
  'CACHE_DIR':  (None, 'CACHE_DIR'),
}

TEST_NAME_FORMAT = lambda kwargs: (
  'using_mirror-%(USE_MIRROR)s-git_mode-%(GIT_MODE)s-cache_dir-%(using)s' %
  dict(using=bool(kwargs['CACHE_DIR']), **kwargs)
)

config_ctx = config_item_context(BaseConfig, VAR_TEST_MAP, TEST_NAME_FORMAT)

def ChromiumSvnSubURL(c, *pieces):
  BASES = ('https://src.chromium.org',
           'svn://svn-mirror.golo.chromium.org')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)

def ChromiumGitURL(_c, *pieces):
  return '/'.join(('https://chromium.googlesource.com',) + pieces)

def ChromiumSrcURL(c):
  if c.GIT_MODE:
    return ChromiumGitURL(c, 'chromium', 'src.git')
  else:
    return ChromiumSvnSubURL(c, 'chrome', 'trunk', 'src')

def BlinkURL(c):
  if c.GIT_MODE:
    return ChromiumGitURL(c, 'chromium', 'blink.git')
  else:
    return ChromiumSvnSubURL(c, 'blink', 'trunk')

def ChromeSvnSubURL(c, *pieces):
  BASES = ('svn://svn.chromium.org',
           'svn://svn-mirror.golo.chromium.org')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)

def ChromeInternalGitURL(_c, *pieces):
  return '/'.join(('https://chrome-internal.googlesource.com',) + pieces)

def ChromeInternalSrcURL(c):
  if c.GIT_MODE:
    return ChromeInternalGitURL(c, 'chrome', 'src-internal.git')
  else:
    return ChromeSvnSubURL(c, 'chrome-internal', 'trunk', 'src-internal')

def mirror_only(c, obj, default=None):
  return obj if c.USE_MIRROR else (default or obj.__class__())

@config_ctx()
def chromium_bare(c):
  s = c.solutions.add()
  s.name = 'src'
  s.url = ChromiumSrcURL(c)
  s.custom_vars = mirror_only(c, {
    'googlecode_url': 'svn://svn-mirror.golo.chromium.org/%s',
    'nacl_trunk': 'svn://svn-mirror.golo.chromium.org/native_client/trunk',
    'sourceforge_url': 'svn://svn-mirror.golo.chromium.org/%(repo)s',
    'webkit_trunk': BlinkURL(c)})
  m = c.got_revision_mapping
  m['src'] = 'got_revision'
  m['src/native_client'] = 'got_nacl_revision'
  m['src/tools/swarm_client'] = 'got_swarm_client_revision'
  m['src/tools/swarming_client'] = 'got_swarming_client_revision'
  m['src/v8'] = 'got_v8_revision'
  m['src/third_party/WebKit'] = 'got_webkit_revision'
  m['src/third_party/webrtc'] = 'got_webrtc_revision'

  p = c.parent_got_revision_mapping
  p['parent_got_revision'] = None
  p['parent_got_nacl_revision'] = 'nacl_revision'
  p['parent_got_swarming_client_revision'] = 'swarming_revision'
  p['parent_got_v8_revision'] = 'v8_revision'
  p['parent_got_webkit_revision'] = 'webkit_revision'
  p['parent_got_webrtc_revision'] = 'webrtc_revision'

@config_ctx(includes=['chromium_bare'])
def chromium_empty(c):
  c.solutions[0].deps_file = ''

@config_ctx(includes=['chromium_bare'])
def chromium(c):
  s = c.solutions[0]
  s.custom_deps = mirror_only(c, {})

@config_ctx(includes=['chromium'])
def chromium_lkcr(c):
  # TODO(phajdan.jr): Add git hashes for LKCR crbug.com/349277.
  if c.GIT_MODE:
    raise BadConf('Git has problems with safesync_url and LKCR, '
                  'crbug.com/349277 crbug.com/109191')
  s = c.solutions[0]
  s.safesync_url = 'https://build.chromium.org/p/chromium/lkcr-status/lkgr'

@config_ctx(includes=['chromium'])
def chromium_lkgr(c):
  s = c.solutions[0]
  safesync_url = 'https://chromium-status.appspot.com/lkgr'
  if c.GIT_MODE:
    safesync_url = 'https://chromium-status.appspot.com/git-lkgr'
    raise BadConf('Git has problems with safesync_url, crbug.com/109191.')
  s.safesync_url = safesync_url

@config_ctx()
def android_bare(c):
  s = c.solutions.add()
  s.deps_file = '.DEPS.git'

# TODO(iannucci,vadimsh): Switch this to src-limited
@config_ctx()
def chrome_internal(c):
  s = c.solutions.add()
  s.name = 'src-internal'
  s.url = ChromeInternalSrcURL(c)
  # Remove some things which are generally not needed
  s.custom_deps = {
    "src/data/autodiscovery" : None,
    "src/data/page_cycler" : None,
    "src/tools/grit/grit/test/data" : None,
    "src/chrome/test/data/perf/frame_rate/private" : None,
    "src/data/mozilla_js_tests" : None,
    "src/chrome/test/data/firefox2_profile/searchplugins" : None,
    "src/chrome/test/data/firefox2_searchplugins" : None,
    "src/chrome/test/data/firefox3_profile/searchplugins" : None,
    "src/chrome/test/data/firefox3_searchplugins" : None,
    "src/chrome/test/data/ssl/certs" : None,
    "src/data/mach_ports" : None,
    "src/data/esctf" : None,
    "src/data/selenium_core" : None,
    "src/chrome/test/data/plugin" : None,
    "src/data/memory_test" : None,
    "src/data/tab_switching" : None,
    "src/chrome/test/data/osdd" : None,
    "src/webkit/data/bmp_decoder":None,
    "src/webkit/data/ico_decoder":None,
    "src/webkit/data/test_shell/plugins":None,
    "src/webkit/data/xbm_decoder":None,
  }

@config_ctx(includes=['chromium'])
def blink(c):
  del c.solutions[0].custom_deps
  c.solutions[0].custom_vars['webkit_revision'] = 'HEAD'

@config_ctx()
def android(c):
  c.target_os.add('android')

@config_ctx(includes=['chromium'])
def show_v8_revision(c):
  # Have the V8 revision appear in the web UI instead of Chromium's.
  del c.got_revision_mapping['src']
  c.got_revision_mapping['src/v8'] = 'got_revision'
  # Needed to get the testers to properly sync the right revision.
  c.parent_got_revision_mapping['parent_got_revision'] = 'got_revision'

@config_ctx(includes=['blink'])
def v8_blink_flavor(c):
    del c.solutions[0].custom_vars['webkit_revision']
    c.solutions[0].custom_vars['v8_branch'] = 'branches/bleeding_edge'
    c.solutions[0].custom_vars['v8_revision'] = 'HEAD'

@config_ctx(includes=['chromium'])
def oilpan(c):
  if c.GIT_MODE:
    raise BadConf("Oilpan requires SVN for now")
  c.solutions[0].custom_vars = {
    'webkit_trunk': ChromiumSvnSubURL(c, 'blink', 'branches', 'oilpan')
  }
  c.solutions[0].custom_vars['sourceforge_url'] = mirror_only(
    c,
    'svn://svn-mirror.golo.chromium.org/%(repo)s',
    'svn://svn.chromium.org/%(repo)s'
  )

  c.solutions[0].custom_vars['webkit_revision'] = 'HEAD'
  c.solutions[0].revision = '197341'

  c.solutions[0].custom_deps = {
    'src/chrome/tools/test/reference_build/chrome_linux' :
      ChromiumSvnSubURL(c, 'blink', 'branches', 'oilpan', 'Tools',
                        'reference_build', 'chrome_linux')
  }
  del c.got_revision_mapping['src']
  c.got_revision_mapping['src/third_party/WebKit/Source'] = 'got_revision'

@config_ctx(includes=['blink', 'chrome_internal'])
def blink_internal(c):
  # Add back the webkit data dependencies
  needed_components_internal = [
    "src/webkit/data/bmp_decoder",
    "src/webkit/data/ico_decoder",
    "src/webkit/data/test_shell/plugins",
    "src/webkit/data/xbm_decoder",
  ]
  for key in needed_components_internal:
    del c.solutions[1].custom_deps[key]

@config_ctx(includes=['oilpan', 'chrome_internal'])
def oilpan_internal(c):
  # Add back the oilpan data dependencies
  needed_components_internal = [
    "src/data/memory_test",
    "src/data/mozilla_js_tests",
    "src/data/page_cycler",
    "src/data/tab_switching",
    "src/webkit/data/bmp_decoder",
    "src/webkit/data/ico_decoder",
    "src/webkit/data/test_shell/plugins",
    "src/webkit/data/xbm_decoder",
  ]
  for key in needed_components_internal:
    del c.solutions[1].custom_deps[key]

@config_ctx()
def nacl(c):
  if c.GIT_MODE:
    raise BadConf('nacl only supports svn')
  s = c.solutions.add()
  s.name = 'native_client'
  s.url = ChromiumSvnSubURL(c, 'native_client', 'trunk', 'src', 'native_client')
  s.custom_vars = mirror_only(c, {
    'webkit_trunk': BlinkURL(c),
    'googlecode_url': 'svn://svn-mirror.golo.chromium.org/%s',
    'sourceforge_url': 'svn://svn-mirror.golo.chromium.org/%(repo)s'})

  s = c.solutions.add()
  s.name = 'supplement.DEPS'
  s.url = ChromiumSvnSubURL(c, 'native_client', 'trunk', 'deps',
                            'supplement.DEPS')

@config_ctx(config_vars={'GIT_MODE': True})
def tools_build(c):
  if not c.GIT_MODE:
    raise BadConf('tools_build only supports git')
  s = c.solutions.add()
  s.name = 'build'
  s.url = ChromiumGitURL(c, 'chromium', 'tools', 'build.git')
  m = c.got_revision_mapping
  m['build'] = 'got_revision'

@config_ctx()
def drmemory(c):
  s = c.solutions.add()
  s.name = 'drmemory.DEPS'
  s.deps_file = 'DEPS'
  s.url = ChromiumSvnSubURL(c, 'chrome', 'trunk', 'deps', 'third_party',
                            'drmemory', 'drmemory.DEPS')
