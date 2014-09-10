# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromite',
  'properties',
]

def GenSteps(api):
  bits = api.properties['TARGET_BITS']
  board = 'x86-generic' if bits == 32 else 'amd64-generic'

  api.chromite.checkout()
  api.chromite.setup_board(board, flags={'cache-dir': '.cache'})
  api.chromite.build_packages(board)
  api.chromite.cros_sdk('cros_sdk', ['echo', 'hello'],
                        environ={ 'var1': 'value' })
  api.chromite.cbuildbot('cbuildbot', board + '-release',
                         flags={'clobber': None, 'build-dir': '/here/there'})


def GenTests(api):
  for bits in (32, 64):
    yield api.test('basic_%s' % bits) + api.properties(TARGET_BITS=bits)
