# -*- makefile -*-

nullstring :=
space := $(nullstring) #

THIRDPARTY_PACKAGES :=         \
    buildbot_8_4p1             \
    twisted_10_2               \
    jinja2                     \
    sqlalchemy_0_7_1           \
    sqlalchemy_migrate_0_7_1   \
    tempita_0_5                \
    decorator_3_3_1

BUILDBOT_PATH = $(subst $(space),:,$(THIRDPARTY_PACKAGES:%=$(THIRDPARTY_DIR)/%))
MASTERPATH := master.chromium.git
include ../master-common.mk
