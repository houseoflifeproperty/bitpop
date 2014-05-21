#!/usr/bin/env bash
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Runs a command in a loop. This is to have the commit queue automatically
# restart. 23 is an arbitrary value to signal that the loop must stop.

while true; do
  "$@"
  if [ $? -eq 23 ]; then
    break
  fi
done
