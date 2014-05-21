// Copyright (c) 2011 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef THIRD_PARTY_SPEEX_SPEEX_H_
#define THIRD_PARTY_SPEEX_SPEEX_H_
#pragma once

// This is a shim header to include the right speex header.
// Use this instead of referencing the speex header directly.

#if defined(USE_SYSTEM_SPEEX)
#include <speex/speex.h>
#include <speex/speex_callbacks.h>
#include <speex/speex_stereo.h>
#else
#include "third_party/speex/include/speex/speex.h"
#include "third_party/speex/include/speex/speex_callbacks.h"
#include "third_party/speex/include/speex/speex_stereo.h"
#endif

#endif  // THIRD_PARTY_SPEEX_SPEEX_H_
