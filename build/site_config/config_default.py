# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Seeds a number of variables defined in chromium_config.py.

The recommended way is to fork this file and use a custom DEPS forked from
config/XXX/DEPS with the right configuration data."""


class Master(object):
  # Repository URLs used by the SVNPoller and 'gclient config'.
  server_url = 'http://src.chromium.org'
  git_server_url =  'http://src.chromium.org/git'
  repo_root = '/svn'

  # External repos.
  googlecode_url = 'http://%s.googlecode.com/svn'
  sourceforge_url = 'https://%(repo)s.svn.sourceforge.net/svnroot/%(repo)s'

  # Directly fetches from anonymous webkit svn server.
  webkit_root_url = 'http://svn.webkit.org/repository/webkit'
  nacl_trunk_url = 'http://src.chromium.org/native_client/trunk'

  llvm_url = 'http://llvm.org/svn/llvm-project'

  # Other non-redistributable repositories.
  repo_root_internal = None
  trunk_internal_url = None
  trunk_internal_url_src = None
  gears_url_internal = None
  o3d_url_internal = None
  nacl_trunk_url_internal = None
  nacl_url_internal = None
  slave_internal_url = None

  syzygy_internal_url = None
  webrtc_internal_url = None

  swarm_server_internal_url = 'http://fake.swarm.url.server.com'
  swarm_server_dev_internal_url = 'http://fake.swarm.dev.url.server.com'
  swarm_hashtable_server_internal = 'http://fake.swarm.hashtable.server.com'

  # Actually for Chromium OS slaves.
  chromeos_url = git_server_url + '/chromiumos.git'
  chromeos_internal_url = None

  # Please change this accordingly.
  master_domain = 'example.com'
  permitted_domains = ('example.com',)

  # Your smtp server to enable mail notifications.
  smtp = 'smtp'

  # By default, bot_password will be filled in by config.GetBotPassword();
  # if the private config wants to override this, it can do so.
  bot_password = None

  class _Base(object):
    # If set to True, the master will do nasty stuff like closing the tree,
    # sending emails or other similar behaviors. Don't change this value unless
    # you modified the other settings extensively.
    is_production_host = False
    # Master address. You should probably copy this file in another svn repo
    # so you can override this value on both the slaves and the master.
    master_host = 'localhost'
    # Additional email addresses to send gatekeeper (automatic tree closage)
    # notifications. Unnecessary for experimental masters and try servers.
    tree_closing_notification_recipients = []
    # 'from:' field for emails sent from the server.
    from_address = 'nobody@example.com'
    # Code review site to upload results. You should setup your own Rietveld
    # instance with the code at
    # http://code.google.com/p/rietveld/source/browse/#svn/branches/chromium
    # You can host your own private rietveld instance on Django, see
    # http://code.google.com/p/google-app-engine-django and
    # http://code.google.com/appengine/articles/pure_django.html
    code_review_site = 'https://chromiumcodereview.appspot.com'

    # For the following values, they are used only if non-0. Do not set them
    # here, set them in the actual master configuration class.

    # Used for the waterfall URL and the waterfall's WebStatus object.
    master_port = 0
    # Which port slaves use to connect to the master.
    slave_port = 0
    # The alternate read-only page. Optional.
    master_port_alt = 0
    # HTTP port for try jobs.
    try_job_port = 0

  ## Chrome related

  class _ChromiumBase(_Base):
    # Tree status urls. You should fork the code from tools/chromium-status/ and
    # setup your own AppEngine instance (or use directly Django to create a
    # local instance).
    # Defaulting urls that are used to POST data to 'localhost' so a local dev
    # server can be used for testing and to make sure nobody updates the tree
    # status by error!
    #
    # This url is used for HttpStatusPush:
    base_app_url = 'http://localhost:8080'
    # HTTP url that should return 0 or 1, depending if the tree is open or
    # closed. It is also used as POST to update the tree status.
    tree_status_url = base_app_url + '/status'
    # Used by LKGR to POST data.
    store_revisions_url = base_app_url + '/revisions'
    # Used by the try server to sync to the last known good revision:
    last_good_url = 'http://chromium-status.appspot.com/lkgr'

  class Chromium(_ChromiumBase):
    # Used by the waterfall display.
    project_name = 'Chromium'
    master_port = 9010
    slave_port = 9112
    master_port_alt = 9014

  class ChromiumFYI(_ChromiumBase):
    project_name = 'Chromium FYI'
    master_port = 9016
    slave_port = 9117
    master_port_alt = 9019

  class ChromiumMemory(_ChromiumBase):
    project_name = 'Chromium Memory'
    master_port = 9014
    slave_port = 9119
    master_port_alt = 9047

  class ChromiumPerf(_ChromiumBase):
    project_name = 'Chromium Perf'
    master_port = 9050
    slave_port = 9151
    master_port_alt = 9052

  class ChromiumWebkit(_ChromiumBase):
    project_name = 'Chromium Webkit'
    master_port = 9053
    slave_port = 9154
    master_port_alt = 9055

  class ChromiumChrome(_ChromiumBase):
    project_name = 'Chromium Chrome'
    master_port = 9056
    slave_port = 9157
    master_port_alt = 9058

  class ChromiumPyauto(_ChromiumBase):
    project_name = 'Chromium PyAuto'
    master_port = 9016
    slave_port = 9116
    master_port_alt = 9216

  class ChromiumEndure(_ChromiumBase):
    project_name = 'Chromium Endure'
    master_port = 9021
    slave_port = 9121
    master_port_alt = 9221

  class ChromiumGPU(_ChromiumBase):
    project_name = 'Chromium GPU'
    master_port = 9076
    slave_port = 9189
    master_port_alt = 9077

  class ChromiumGPUFYI(_ChromiumBase):
    project_name = 'Chromium GPU FYI'
    master_port = 9059
    slave_port = 9160
    master_port_alt = 9061

  class ChromiumLKGR(_ChromiumBase):
    project_name = 'Chromium LKGR'
    master_port = 9018
    slave_port = 9118
    master_port_alt = 9218

  class ChromiumGIT(_ChromiumBase):
    project_name = 'Chromium Git'
    master_port = 9062
    slave_port = 9163
    master_port_alt = 9064

  class ChromiumFlaky(_ChromiumBase):
    project_name = 'Chromium Flaky'
    master_port = 9065
    slave_port = 9166
    master_port_alt = 9067

  class ChromiumSwarm(_ChromiumBase):
    project_name = 'Chromium Swarm'
    master_port = 9068
    slave_port = 9169
    master_port_alt = 9070

  class ChromiumMemoryFYI(_ChromiumBase):
    project_name = 'Chromium Memory FYI'
    master_port = 9071
    slave_port = 9172
    master_port_alt = 9073

  class ChromiumChromebot(_ChromiumBase):
    project_name = 'Chromium Chromebot'
    master_port = 9090
    slave_port = 9190
    master_port_alt = 9290

  class TryServer(_ChromiumBase):
    project_name = 'Chromium Try Server'
    master_port = 9011
    slave_port = 9113
    master_port_alt = 9015
    try_job_port = 9018
    # The svn repository to poll to grab try patches. For chrome, we use a
    # separate repo to put all the diff files to be tried.
    svn_url = None

  class MyChromeFork(_Base):
    # Place your continuous build fork settings here.
    project_name = 'My Forked Chrome'
    master_port = 9010
    slave_port = 9111
    from_address = 'nobody@example.com'

  ## ChromiumOS related

  class ChromiumChromiumOS(_ChromiumBase):
    project_name = 'Chromium ChromiumOS'
    master_port = 9035
    slave_port = 9127
    master_port_alt = 9037

  class ChromiumOS(_Base):
    project_name = 'ChromiumOS'
    master_port = 9030
    slave_port = 9127
    master_port_alt = 9043
    base_app_url = 'http://localhost:8080'
    tree_status_url = base_app_url + '/status'
    store_revisions_url = base_app_url + '/revisions'
    last_good_url = 'https://chromiumos-status.appspot.com/lkgr'

  class ChromiumOSTryServer(_Base):
    project_name = 'ChromiumOS Try Server'
    master_port = 9051
    slave_port = 9153
    master_port_alt = 9063
    repo_url_ext = 'https://git.chromium.org/chromiumos/tryjobs.git'
    repo_url_int = None
    # The reply-to address to set for emails sent from the server.
    reply_to = 'nobody@example.com'

  ## V8

  class V8(_Base):
    project_name = 'V8'
    master_host = 'localhost'
    master_port = 9030
    slave_port = 9131
    master_port_alt = 9043
    server_url = 'http://v8.googlecode.com'
    project_url = 'http://v8.googlecode.com'
    perf_base_url = 'http://build.chromium.org/f/client/perf'

  ## Dart

  class Dart(_Base):
    project_name = 'Dart'
    master_port = 8040
    slave_port = 8140
    # Enable when there's a public waterfall.
    master_port_alt = 8240

  class DartFYI(_Base):
    project_name = 'Dart FYI'
    master_port = 8051
    slave_port = 8151
    # Enable when there's a public waterfall.
    master_port_alt = 8251


  ## Native Client related

  class _NaClBase(_Base):
    base_app_url = 'http://localhost:8080'
    tree_status_url = base_app_url + '/status'
    store_revisions_url = base_app_url + '/revisions'
    last_good_url = 'http://nativeclient-status.appspot.com/lkgr'
    perf_base_url = 'http://build.chromium.org/f/client/perf'

  class NativeClient(_NaClBase):
    project_name = 'NativeClient'
    master_port = 9080
    slave_port = 9180
    master_port_alt = 9280

  class NativeClientToolchain(_NaClBase):
    project_name = 'NativeClientToolchain'
    master_port = 9081
    slave_port = 9181
    master_port_alt = 9281

  class NativeClientChrome(_NaClBase):
    project_name = 'NativeClientChrome'
    master_port = 9082
    slave_port = 9182
    master_port_alt = 9282

  class NativeClientRagel(_NaClBase):
    project_name = 'NativeClientRagel'
    master_port = 9083
    slave_port = 9183
    master_port_alt = 9283

  class NativeClientSDK(_NaClBase):
    project_name = 'NativeClientSDK'
    master_port = 9084
    slave_port = 9184
    master_port_alt = 9284

  class NativeClientPorts(_NaClBase):
    project_name = 'NativeClientPorts'
    master_port = 9085
    slave_port = 9185
    master_port_alt = 9285

  class NativeClientTryServer(_Base):
    project_name = 'NativeClient-Try'
    master_port = 9086
    slave_port = 9186
    master_port_alt = 9286
    try_job_port = 9386
    svn_url = None

  class NativeClientLLVM(_NaClBase):
    project_name = 'NativeClientLLVM'
    master_port = 9087
    slave_port = 9187
    master_port_alt = 9287

  class NativeClientSDKMono(_NaClBase):
    project_name = 'NativeClientSDKMono'
    master_port = 9088
    slave_port = 9188
    master_port_alt = 9288

  class NativeClientSDKAddIn(_NaClBase):
    project_name = 'NativeClientSDKAddIn'
    master_port = 9089
    slave_port = 9191
    master_port_alt = 9289

  ## Others

  class O3D(_Base):
    project_name = 'O3D'
    master_port = 9028
    slave_port = 9129
    master_port_alt = 9042
    base_app_url = 'http://localhost:8080'
    tree_status_url = base_app_url + '/status'
    store_revisions_url = base_app_url + '/revisions'
    last_good_url = 'http://o3d-status.appspot.com/lkgr'

  class PageSpeed(_Base):
    project_name = 'PageSpeed'
    master_port = 9038
    slave_port = 9138
    master_port_alt = 9238
    tree_closing_notification_recipients = []
    # Select tree status urls and codereview location.
    base_app_url = 'https://page-speed-status.appspot.com'
    tree_status_url = base_app_url + '/status'
    store_revisions_url = base_app_url + '/revisions'
    last_good_url = base_app_url + '/lkgr'

  class Skia(_Base):
    project_name = 'Skia'
    master_host = 'localhost'
    master_port = 9068
    slave_port = 9169
    master_port_alt = 9070
    server_url = 'http://skia.googlecode.com'
    project_url = 'http://skia.googlecode.com'
    is_production_host = False

  class Omaha(_Base):
    project_name = 'Omaha'
    master_port = 9044
    slave_port = 9144
    master_port_alt = 9244

  # Used for testing on a local machine
  class Experimental(Chromium):
    project_name = 'Chromium Experimental'
    master_host = 'localhost'
    master_port = 9010
    slave_port = 9111
    master_port_alt = 9012

  # Used for perf testing
  # TODO: Remove this when performance testing with clang is done, but no
  # later than EOQ2 2011.
  class ChromiumPerfClang(_ChromiumBase):
    project_name = 'Chromium Perf Clang'
    master_port = 9040
    slave_port = 9141
    master_port_alt = 9042

  class Sfntly(_Base):
    project_name = 'Sfntly'
    project_url = 'http://code.google.com/p/sfntly/'
    master_port = 9048
    slave_port = 9148
    master_port_alt = 9248

  class ChromiumPerfAv(_ChromiumBase):
    project_name = 'Chromium Perf Av'
    master_port = 9075
    slave_port = 9175
    master_port_alt = 9275
    # Need @google name to enable post to google groups.
    from_address = 'perf_av@google.com'

  class DevTools(Chromium):
    project_name = 'Chromium DevTools'
    master_host = 'localhost'
    master_port = 9010
    slave_port = 9111
    master_port_alt = 9012

  class DrMemory(_Base):
    project_name = 'DrMemory'
    master_host = 'localhost'
    master_port = 9092
    slave_port = 9192
    master_port_alt = 9292

  class DynamoRIO(_Base):
    project_name = 'DynamoRIO'
    master_host = 'localhost'
    master_port = 9093
    slave_port = 9193
    master_port_alt = 9293

  class WebRTC(_Base):
    project_name = 'WebRTC'
    master_port = 9094
    slave_port = 9194
    master_port_alt = 9294
    server_url = 'http://webrtc.googlecode.com'
    project_url = 'http://webrtc.googlecode.com'
    from_address = 'webrtc-cb-watchlist@google.com'

  class ChromiumWebRTC(WebRTC):
    project_name = 'Chromium WebRTC'
    master_port = 9095
    slave_port = 9195
    master_port_alt = 9295


class Archive(object):
  archive_host = 'localhost'
  # Skip any filenames (exes, symbols, etc.) starting with these strings
  # entirely, typically because they're not built for this distribution.
  exes_to_skip_entirely = []
  # Web server base path.
  www_dir_base = "\\\\" + archive_host + "\\www\\"

  @staticmethod
  def Internal():
    pass


class Distributed(object):
  """Not much to describe."""
