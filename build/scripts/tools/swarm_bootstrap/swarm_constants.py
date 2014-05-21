# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Various swarm constants required by the server and the swarm slaves.

This allows the swarm slaves to have this files and the needed variables without
having to download the whole swarm directory.
"""

# The exit code to return when the machine should restart.
RESTART_EXIT_CODE = 99
