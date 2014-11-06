# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from RECIPE_MODULES.gclient import CONFIG_CTX
from slave.recipe_modules.gclient.config import ChromiumSvnSubURL


@CONFIG_CTX()
def libyuv(c):
  s = c.solutions.add()
  s.name = 'src'
  s.url = LibyuvSvnURL(c, 'trunk')
  s.deps_file = 'DEPS'
  s.custom_vars['root_dir'] = 'src'

@CONFIG_CTX(includes=['libyuv', 'android'])
def libyuv_android(c):
  pass

@CONFIG_CTX(includes=['libyuv'])
def libyuv_ios(c):
  c.target_os.add('mac')
  c.target_os.add('ios')

@CONFIG_CTX(includes=['libyuv'])
def libyuv_valgrind(c):
  c.solutions[0].custom_deps['src/chromium/src/third_party/valgrind'] = \
      ChromiumSvnSubURL(c, 'chrome', 'trunk', 'deps', 'third_party', 'valgrind',
                        'binaries')

def LibyuvSvnURL(c, *pieces):
  BASES = ('http://libyuv.googlecode.com/svn',
           'svn://svn-mirror.golo.chromium.org/libyuv')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)
