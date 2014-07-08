# -*- makefile -*-
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Elements used to construct PYTHONPATH. These may be overridden by the
# including Makefile.
#
# For example: while we transition from buildbot 0.7.12 to buildbot 0.8.x ,
# some masters will override BUILDBOT_PATH in their local Makefiles.
TOPLEVEL_DIR ?= ../..
THIRDPARTY_DIR ?= $(TOPLEVEL_DIR)/third_party
SCRIPTS_DIR ?= $(TOPLEVEL_DIR)/scripts
PUBLICCONFIG_DIR ?= $(TOPLEVEL_DIR)/site_config
PRIVATECONFIG_DIR ?= $(TOPLEVEL_DIR)/../build_internal/site_config

GCLIENT = $(shell which gclient || echo "$(TOPLEVEL_DIR)/../depot_tools/gclient")


# Packages needed by buildbot8
BUILDBOT8_DEPS :=               \
    buildbot_8_4p1              \
    twisted_10_2                \
    jinja2                      \
    sqlalchemy_0_7_1            \
    sqlalchemy_migrate_0_7_1    \
    tempita_0_5                 \
    decorator_3_3_1

nullstring :=
space := $(nullstring) #
BUILDBOT8_PATH = $(subst $(space),:,$(BUILDBOT8_DEPS:%=$(THIRDPARTY_DIR)/%))

BUILDBOT_PATH ?= $(BUILDBOT8_PATH)

PYTHONPATH := $(BUILDBOT_PATH):$(SCRIPTS_DIR):$(THIRDPARTY_DIR):$(PUBLICCONFIG_DIR):$(PRIVATECONFIG_DIR):.

include $(TOPLEVEL_DIR)/masters/master-common-rules.mk
