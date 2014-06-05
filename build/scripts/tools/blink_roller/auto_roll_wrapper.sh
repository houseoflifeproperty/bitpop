#!/bin/sh
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

while :
do
    # Make sure auto-roll is up to date.
    cd /src/build/scripts/tools/blink_roller
    git pull --rebase

    # FIXME: We should probably remove any stale pyc files.
    ./auto_roll.py blink eseidel@chromium.org /src/chromium/src

    echo 'Waiting 5 minutes between checks...'
    sleep 300
done
