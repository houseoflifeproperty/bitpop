# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.gclient import CONFIG_CTX
from slave.recipe_config import BadConf

# TODO(machenbach): Move this to an external configuration file.
STABLE_BRANCH = '3.26'
BETA_BRANCH = '3.27'


# TODO(machenbach): This is copied from gclient's config.py and should be
# unified somehow.
def ChromiumSvnSubURL(c, *pieces):
  BASES = ('https://src.chromium.org',
           'svn://svn-mirror.golo.chromium.org')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)


# TODO(machenbach): Remove the method above in favor of this one.
def ChromiumSvnTrunkURL(c, *pieces):
  BASES = ('https://src.chromium.org/svn/trunk',
           'svn://svn-mirror.golo.chromium.org/chrome/trunk')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)


def _V8URL(branch):
  return 'http://v8.googlecode.com/svn/%s' % branch


@CONFIG_CTX()
def v8(c):
  soln = c.solutions.add()
  soln.name = 'v8'
  soln.url = _V8URL('branches/bleeding_edge')
  soln.custom_vars = {'chromium_trunk': ChromiumSvnTrunkURL(c)}
  c.got_revision_mapping['v8'] = 'got_revision'
  # Needed to get the testers to properly sync the right revision.
  # TODO(infra): Upload full buildspecs for every build to isolate and then use
  # them instead of this gclient garbage.
  c.parent_got_revision_mapping['parent_got_revision'] = 'got_revision'


@CONFIG_CTX(includes=['v8'])
def mozilla_tests(c):
  c.solutions[0].custom_deps['v8/test/mozilla/data'] = ChromiumSvnSubURL(
      c, 'chrome', 'trunk', 'deps', 'third_party', 'mozilla-tests')


@CONFIG_CTX(includes=['v8'])
def clang(c):
  c.solutions[0].custom_deps['v8/tools/clang/scripts'] = ChromiumSvnSubURL(
      c, 'chrome', 'trunk', 'src', 'tools', 'clang', 'scripts')


@CONFIG_CTX(includes=['v8'])
def beta_branch(c):
  c.solutions[0].url = _V8URL('branches/%s' % BETA_BRANCH)


@CONFIG_CTX(includes=['v8'])
def stable_branch(c):
  c.solutions[0].url = _V8URL('branches/%s' % STABLE_BRANCH)


@CONFIG_CTX(includes=['v8'])
def trunk(c):
  c.solutions[0].url = _V8URL('trunk')


@CONFIG_CTX(includes=['v8'])
def v8_lkgr(c):
  if c.GIT_MODE:
    raise BadConf('Git has problems with safesync_url.')
  c.solutions[0].safesync_url = 'https://v8-status.appspot.com/lkgr'
