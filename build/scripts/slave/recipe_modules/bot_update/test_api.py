# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import struct

from slave import bot_update
from slave import recipe_test_api


class BotUpdateTestApi(recipe_test_api.RecipeTestApi):
  def output_json(self, master, builder, slave, root, first_sln,
                  revision_mapping, git_mode):
    """Deterministically synthesize json.output test data for gclient's
    --output-json option.
    """
    active = bot_update.check_valid_host(master, builder, slave)

    output = {
        'did_run': active
    }

    # Add in extra json output if active.
    if active:
      properties = {
          property_name: self.gen_revision(project_name, git_mode)
          for project_name, property_name in revision_mapping.iteritems()
      }
      # We also want to simulate outputting "got_revision_git": ...
      # when git mode is off to match what bot_update.py does.
      if not git_mode:
        properties.update({
            '%s_git' % property_name: self.gen_revision(project_name, True)
            for project_name, property_name in revision_mapping.iteritems()
        })
      output.update({
          'patch_root': root or first_sln,
          'root': first_sln,
          'properties': properties,
          'step_text': 'Some step text'
      })
    return self.m.json.output(output)


  @staticmethod
  def gen_revision(project, GIT_MODE):
    """Hash project to bogus deterministic revision values."""
    h = hashlib.sha1(project)
    if GIT_MODE:
      return h.hexdigest()
    else:
      return struct.unpack('!I', h.digest()[:4])[0] % 300000
