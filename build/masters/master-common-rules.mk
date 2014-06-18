# -*- makefile -*-
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This should be included by a makefile which lives in a buildmaster/buildslave
# directory (next to the buildbot.tac file). That including makefile *must*
# define MASTERPATH.

# The 'start' and 'stop' targets start and stop the buildbot master.
# The 'reconfig' target will tell a buildmaster to reload its config file.

# Note that a relative PYTHONPATH entry is relative to the current directory.

# Confirm that MASTERPATH has been defined.
ifeq ($(MASTERPATH),)
  $(error MASTERPATH not defined.)
endif

# Get the current host's short hostname.  We may use this in Makefiles that
# include this file.
SHORT_HOSTNAME := $(shell hostname -s)

# On the Mac, the buildbot is started via the launchd mechanism as a
# LaunchAgent to give the slave a proper Mac UI environment for tests.  In
# order for this to work, the plist must be present and loaded by launchd, and
# the user must be logged in to the UI.  The plist is loaded by launchd at user
# login (and the job may have been initially started at that time too).  Our
# Mac build slaves are all set up this way, and have auto-login enabled, so
# "make start" should just work and do the right thing.
#
# When using launchd to start the job, it also needs to be used to stop the
# job.  Otherwise, launchd might try to restart the job when stopped manually
# by SIGTERM.  Using SIGHUP for reconfig is safe with launchd.
#
# Because it's possible to have more than one slave on a machine (for testing),
# this tests to make sure that the slave is in the known slave location,
# /b/slave, which is what the LaunchAgent operates on.
USE_LAUNCHD := \
  $(shell [ -f ~/Library/LaunchAgents/org.chromium.buildbot.$(MASTERPATH).plist ] && \
          [ "$$(pwd -P)" = "/b/build/masters/$(MASTERPATH)" ] && \
          echo 1)

printstep:
ifndef NO_REVISION_AUDIT
	@echo "**  `date`	make $(MAKECMDGOALS)" >> actions.log
endif

ifeq ($(BUILDBOT_PATH),$(BUILDBOT8_PATH))
start: printstep bootstrap
else
start: printstep
endif
ifndef NO_REVISION_AUDIT
	@if [ ! -f "$(GCLIENT)" ]; then \
	    echo "gclient not found.  Add depot_tools to PATH or use DEPS checkout."; \
	    exit 2; \
	fi
	$(GCLIENT) revinfo -a >> actions.log || true
	$(GCLIENT) diff >> actions.log || true
endif
ifneq ($(USE_LAUNCHD),1)
	PYTHONPATH=$(PYTHONPATH) python $(SCRIPTS_DIR)/common/twistd --no_save -y buildbot.tac
else
	launchctl start org.chromium.buildbot.$(MASTERPATH)
endif

ifeq ($(BUILDBOT_PATH),$(BUILDBOT8_PATH))
start-prof: bootstrap
else
start-prof:
endif
ifneq ($(USE_LAUNCHD),1)
	TWISTD_PROFILE=1 PYTHONPATH=$(PYTHONPATH) python $(SCRIPTS_DIR)/common/twistd --no_save -y buildbot.tac
else
	launchctl start org.chromium.buildbot.$(MASTERPATH)
endif

stop: printstep
ifneq ($(USE_LAUNCHD),1)
	if `test -f twistd.pid`; then kill -TERM -$$(ps h -o pgid= $$(cat twistd.pid) | awk '{print $$1}'); fi;
else
	launchctl stop org.chromium.buildbot.$(MASTERPATH)
endif

kill: printstep
ifneq ($(USE_LAUNCHD),1)
	if `test -f twistd.pid`; then kill -KILL -$$(ps h -o pgid= $$(cat twistd.pid) | awk '{print $$1}'); fi;
else
	launchctl stop org.chromium.buildbot.$(MASTERPATH)
endif

reconfig: printstep
	kill -HUP `cat twistd.pid`

no-new-builds: printstep
	kill -USR1 `cat twistd.pid`

log:
	tail -F twistd.log

exceptions:
	# Searches for exception in the last 11 log files.
	grep -A 10 "exception caught here" twistd.log twistd.log.?

last-restart:
	@if `test -f twistd.pid`; then stat -c %y `readlink -f twistd.pid` | \
	    cut -d "." -f1; fi;
	@ls -t -1 twistd.log* | while read f; do tac $$f | grep -m 1 \
	    "Creating BuildMaster"; done | head -n 1

wait:
	while `test -f twistd.pid`; do sleep 1; done;

restart: stop wait start log

restart-prof: stop wait start-prof log

# This target is only known to work on 0.8.x masters.
upgrade: printstep
	@[ -e '.dbconfig' ] || [ -e 'state.sqlite' ] || \
	PYTHONPATH=$(PYTHONPATH) python buildbot upgrade-master .

# This target is only known to be useful on 0.8.x masters.
bootstrap: printstep
	@[ -e '.dbconfig' ] || [ -e 'state.sqlite' ] || \
	PYTHONPATH=$(PYTHONPATH) python $(SCRIPTS_DIR)/tools/state_create.py \
	--restore --db='state.sqlite' --txt '../state-template.txt'

setup:
	@echo export PYTHONPATH=$(PYTHONPATH)
