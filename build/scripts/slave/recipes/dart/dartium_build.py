# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
  'python',
]

def GenSteps(api):
  config_vals = {}
  config_vals.update(
    dict((str(k),v) for k,v in api.properties.iteritems() if k.isupper())
  )

  api.chromium.set_config('chromium', **config_vals)

  api.chromium.c.gyp_env.GYP_GENERATORS.add('ninja')
  api.chromium.c.gyp_env.GYP_DEFINES['linux_strip_binary'] = 1

  s = api.gclient.c.solutions[0]

  USE_MIRROR = api.gclient.c.USE_MIRROR
  def DartRepositoryURL(*pieces):
    BASES = ('https://dart.googlecode.com/svn',
             'svn://svn-mirror.golo.chromium.org/dart')
    return '/'.join((BASES[USE_MIRROR],) + pieces)

  deps_name = api.properties.get('deps', 'dartium.deps')
  s.url = DartRepositoryURL('branches', 'bleeding_edge', 'deps', deps_name)
  s.name = deps_name
  s.custom_deps = api.properties.get('gclient_custom_deps') or {}
  s.revision = api.properties.get('revision')
  api.gclient.c.got_revision_mapping.pop('src', None)
  api.gclient.c.got_revision_mapping['src/dart'] = 'got_revision'
  if USE_MIRROR:
    s.custom_vars.update({
      'dartium_base': 'svn://svn-mirror.golo.chromium.org'})

  yield api.gclient.checkout()

  # gclient api incorrectly sets Path('[CHECKOUT]') to build/src/dartium.deps
  # because Dartium has its DEPS file in dartium.deps, not directly in src.
  api.path['checkout'] = api.path['slave_build'].join('src')

  yield api.chromium.runhooks()
  yield api.chromium.compile()
  yield api.python('archive_build',
                   api.path['slave_build'].join(
                       'src', 'dart', 'tools', 'dartium', 'multivm_archive.py'),
                   [s.revision])


def GenTests(api):
  for plat in ('win', 'mac', 'linux'):
    for bits in (64,):
      for use_mirror in (True, False):
        yield (
          api.test('basic_%s_%s_Mirror%s' % (plat, bits, use_mirror)) +
          api.properties.generic(
              TARGET_BITS=bits,
              USE_MIRROR=use_mirror,
              deps='dartium.deps',
              revision='12345') +
          api.platform(plat, bits)
      )
