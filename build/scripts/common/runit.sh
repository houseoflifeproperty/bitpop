#!/bin/bash -e
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# runit.sh sets up PYTHONPATH to use python scripts straight from the CLI.
# try `scripts/common/runit.sh python -i`
# or  `../common/runit.sh runtest.py --help`

# determine runit.sh's location, to find build directory regardless of where it
# is called from.
SCRIPTFILE=`[[ $0 == /* ]] && echo "$0" || echo "${PWD}/${0#./}"`
SCRIPTDIR=${SCRIPTFILE%/*}
BUILD=`cd $SCRIPTDIR/../../; pwd` # canonicalize path

PYTHONPATH="$PYTHONPATH:$BUILD/third_party/buildbot_8_4p1"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/buildbot_slave_8_4"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/twisted_10_2"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/jinja2"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/sqlalchemy_0_7_1"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/sqlalchemy_migrate_0_7_1"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/tempita_0_5"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party/decorator_3_3_1"
PYTHONPATH="$PYTHONPATH:$BUILD/scripts"
PYTHONPATH="$PYTHONPATH:$BUILD/third_party"
PYTHONPATH="$PYTHONPATH:$BUILD/site_config"
PYTHONPATH="$PYTHONPATH:$BUILD/../build_internal/site_config"
PYTHONPATH="$PYTHONPATH:." "$@"
