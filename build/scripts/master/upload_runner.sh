#! /bin/bash
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Runs a single instance of the log uploader.
# invocation: upload_runner.sh <master name>
# This script is intended to be run from cron.

UPLOAD_SCRIPT=~/buildbot/build/scripts/master/upload_logs_to_storage.py
LIMIT=2

function msg_exit() {
    echo 'Upload script already running, exiting.'
    exit 0
}

function usage() {
    echo "Usage: $0 <master name> <bucket name>"
    exit 1
}
if [ -z "$1" ]; then
    usage
fi

if [ -z "$2" ]; then
    usage
fi


mastername="$1"
bucketname="$2"
(
    flock -n 9 || msg_exit
    $UPLOAD_SCRIPT --master-name=$mastername --bucket=$bucketname --limit=$LIMIT
) 9>/var/lock/upload_logs_to_storage-$mastername
# the '9' on the previous line is the file descriptor used by flock above.
