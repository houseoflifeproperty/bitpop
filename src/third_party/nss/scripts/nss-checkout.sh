#!/bin/sh
# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This shell script checks out the NSS source tree from CVS and prepares
# it for Chromium.

# Make the script exit as soon as something fails.
set -ex

rm -rf mozilla/security/nss/lib
cvs -q -d :pserver:anonymous@cvs-mirror.mozilla.org:/cvsroot export \
    -r NSS_3_14_1_RC0 mozilla/security/nss/lib

# Rename one of the utf8.c files to avoid name conflict.
mv mozilla/security/nss/lib/base/utf8.c mozilla/security/nss/lib/base/nssutf8.c

rm -r mozilla/security/nss/lib/ckfw/capi
rm -r mozilla/security/nss/lib/ckfw/dbm
rm -r mozilla/security/nss/lib/ckfw/nssmkey
rm -r mozilla/security/nss/lib/crmf
rm -r mozilla/security/nss/lib/freebl/ecl/tests
rm -r mozilla/security/nss/lib/freebl/mpi/doc
rm -r mozilla/security/nss/lib/freebl/mpi/tests
rm -r mozilla/security/nss/lib/freebl/mpi/utils
rm -r mozilla/security/nss/lib/jar
rm -r mozilla/security/nss/lib/pkcs12
rm -r mozilla/security/nss/lib/pki/doc
rm -r mozilla/security/nss/lib/softoken/legacydb
rm -r mozilla/security/nss/lib/sqlite
rm -r mozilla/security/nss/lib/sysinit
rm -r mozilla/security/nss/lib/zlib

find mozilla/security/nss/lib -name .cvsignore -print | xargs rm
find mozilla/security/nss/lib -name README -print | xargs rm

# Remove the build system.
find mozilla/security/nss/lib -name Makefile -print | xargs rm
find mozilla/security/nss/lib -name manifest.mn -print | xargs rm
find mozilla/security/nss/lib -name "*.mk" -print | xargs rm

# Remove files for building shared libraries/DLLs.
find mozilla/security/nss/lib -name "*.def" -print | xargs rm
find mozilla/security/nss/lib -name "*.rc" -print | xargs rm

# Remove obsolete files or files we don't need.
rm mozilla/security/nss/lib/ckfw/builtins/certdata.perl
rm mozilla/security/nss/lib/ckfw/builtins/certdata.txt
rm mozilla/security/nss/lib/ckfw/ck.api
rm mozilla/security/nss/lib/ckfw/ckapi.perl
rm mozilla/security/nss/lib/libpkix/pkix/params/pkix_buildparams.c
rm mozilla/security/nss/lib/libpkix/pkix/params/pkix_buildparams.h
rm mozilla/security/nss/lib/util/secload.c
rm mozilla/security/nss/lib/util/secplcy.c
rm mozilla/security/nss/lib/util/secplcy.h
rm mozilla/security/nss/lib/smime/*.c

find mozilla/security/nss/lib/ssl -type f ! -name sslerr.h | xargs rm

find mozilla/security/nss/lib/freebl -type f \
    ! -name aeskeywrap.c ! -name alg2268.c ! -name alghmac.c \
    ! -name alghmac.h ! -name arcfive.c ! -name arcfour.c \
    ! -name blapi.h ! -name blapii.h ! -name blapit.h \
    ! -name camellia.c ! -name camellia.h \
    ! -name ctr.c ! -name ctr.h ! -name cts.c ! -name cts.h \
    ! -name des.c ! -name des.h ! -name desblapi.c ! -name dh.c \
    ! -name drbg.c ! -name dsa.c ! -name ec.c \
    ! -name ec.h ! -name ec2.h ! -name ecl-curve.h \
    ! -name ecl-exp.h ! -name ecl-priv.h ! -name ecl.c \
    ! -name ecl.c ! -name ecl.h ! -name ecl_curve.c \
    ! -name ecl_gf.c ! -name ecl_mult.c ! -name ecp.h \
    ! -name ecp_aff.c ! -name ecp_jac.c ! -name ecp_jm.c \
    ! -name ecp_mont.c ! -name ec_naf.c ! -name gcm.c ! -name gcm.h \
    ! -name jpake.c ! -name md2.c ! -name md5.c ! -name logtab.h \
    ! -name mpcpucache.c \
    ! -name mpi-config.h \
    ! -name mpi-priv.h ! -name mpi.c ! -name mpi.h \
    ! -name mpi_amd64.c ! -name mpi_x86_asm.c ! -name mplogic.c \
    ! -name mplogic.h ! -name mpmontg.c ! -name mpprime.c \
    ! -name mpprime.h \
    ! -name mp_gf2m-priv.h ! -name mp_gf2m.c ! -name mp_gf2m.h \
    ! -name primes.c ! -name pqg.c ! -name pqg.h ! -name rawhash.c \
    ! -name rijndael.c ! -name rijndael.h ! -name rijndael32.tab \
    ! -name rsa.c ! -name secmpi.h \
    ! -name secrng.h ! -name seed.c ! -name seed.h \
    ! -name sha256.h ! -name sha512.c ! -name sha_fast.c \
    ! -name sha_fast.h ! -name shsign.h ! -name shvfy.c \
    ! -name sysrand.c ! -name tlsprfalg.c ! -name unix_rand.c \
    ! -name win_rand.c \
    | xargs rm
