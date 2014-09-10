# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'path',
  'perf_dashboard',
  'platform',
  'properties',
  'step',
]

# To run, pass these options into properties:
# slavename="multivm-windows-release", 
# buildername="multivm-windows-perf-be", 
# mastername="client.dart.fyi", buildnumber=75


def GenSteps(api):
  s1 = api.perf_dashboard.get_skeleton_point(
      "sunspider/string-unpack-code/ref", 33241, "18.5")
  s1['supplemental_columns'] = {
      "r_webkit_rev" : "167808"
    }
  s1['error'] = "0.5"
  s1['units'] = "ms"
  s2 = api.perf_dashboard.get_skeleton_point(
      "sunspider/string-unpack-code", 33241, "18.4")
  s2['supplemental_columns'] = {
      "r_webkit_rev" : "167808"
    }
  s2['error'] = "0.4898"
  s2['units'] = "ms"

  api.perf_dashboard.set_default_config()
  api.perf_dashboard.post([s1, s2])

def GenTests(api):
  for platform in ('linux', 'win', 'mac'):
    for production in (True, False):
      yield (
          api.test("%s%s" % (platform, '_use_mirror' if production else '')) +
          api.platform.name(platform) + 
          api.properties(use_mirror=production,
              slavename="multivm-windows-release",
              buildername="multivm-windows-perf-be",
              buildnumber=75, mastername="client.dart.fyi"))
