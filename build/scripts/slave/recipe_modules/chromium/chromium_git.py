# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

SPEC = {
  'builders': {
    'WinGit': {
        'recipe_config': 'chromium',
        'testing': {'platform': 'win'},
    },
    'WinGitXP': {
        'recipe_config': 'chromium',
        'testing': {'platform': 'win'},
    },
    'MacGit': {
        'recipe_config': 'chromium',
        'testing': {'platform': 'mac'},
    },
    'LinuxGit': {
        'recipe_config': 'chromium',
        'testing': {'platform': 'linux'},
    },
    'LinuxGit x64': {
        'recipe_config': 'chromium',
        'testing': {'platform': 'linux'},
    },
  }
}
