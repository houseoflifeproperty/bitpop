// Copyright (c) 2011 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef THIRD_PARTY_LIBVPX_LIBVPX_H_
#define THIRD_PARTY_LIBVPX_LIBVPX_H_
#pragma once

// This is a shim header to include the right libvpx headers.
// Use this instead of referencing the libvpx headers directly.

#if defined(USE_SYSTEM_LIBVPX)
#include "vpx/vpx_codec.h"
#include "vpx/vpx_decoder.h"
#include "vpx/vpx_encoder.h"
#include "vpx/vp8cx.h"
#include "vpx/vp8dx.h"
#else
#include "third_party/libvpx/source/libvpx/vpx/vpx_codec.h"
#include "third_party/libvpx/source/libvpx/vpx/vpx_decoder.h"
#include "third_party/libvpx/source/libvpx/vpx/vpx_encoder.h"
#include "third_party/libvpx/source/libvpx/vpx/vp8cx.h"
#include "third_party/libvpx/source/libvpx/vpx/vp8dx.h"
#endif

#endif  // THIRD_PARTY_LIBVPX_LIBVPX_H_
