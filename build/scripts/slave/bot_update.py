#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(hinoka): Use logging.

import cStringIO
import codecs
import copy
import ctypes
import json
import optparse
import os
import pprint
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib2
import urlparse
import uuid

import os.path as path

# Set this to true on flag day.
FLAG_DAY = False

# Should we upload the status of this step?
UPLOAD_TELEMETRY = True

# Define a bunch of directory paths.
# Relative to the current working directory.
CURRENT_DIR = path.abspath(os.getcwd())
BUILDER_DIR = path.dirname(CURRENT_DIR)
SLAVE_DIR = path.dirname(BUILDER_DIR)

# Relative to this script's filesystem path.
THIS_DIR = path.dirname(path.abspath(__file__))
SCRIPTS_DIR = path.dirname(THIS_DIR)
BUILD_DIR = path.dirname(SCRIPTS_DIR)
ROOT_DIR = path.dirname(BUILD_DIR)
BUILD_INTERNAL_DIR = path.join(ROOT_DIR, 'build_internal')
DEPOT_TOOLS_DIR = path.join(ROOT_DIR, 'depot_tools')


CHROMIUM_GIT_HOST = 'https://chromium.googlesource.com'
CHROMIUM_SRC_URL = CHROMIUM_GIT_HOST + '/chromium/src.git'

# Official builds use buildspecs, so this is a special case.
BUILDSPEC_RE = r'^/chrome-internal/trunk/tools/buildspec/build/(.*)$'
GIT_BUILDSPEC_PATH = ('https://chrome-internal.googlesource.com/chrome/tools/'
                      'buildspec')

# This is the repository that the buildspecs2git cron job mirrors
# all buildspecs into. When we see an svn buildspec, we rely on the
# buildspecs2git cron job to produce the git version of the buildspec.
GIT_BUILDSPEC_REPO = (
    'https://chrome-internal.googlesource.com/chrome/tools/git_buildspecs')

# Copied from scripts/recipes/chromium.py.
GOT_REVISION_MAPPINGS = {
    '/chrome/trunk/src': {
        'src/': 'got_revision',
        'src/native_client/': 'got_nacl_revision',
        'src/tools/swarm_client/': 'got_swarm_client_revision',
        'src/tools/swarming_client/': 'got_swarming_client_revision',
        'src/third_party/WebKit/': 'got_webkit_revision',
        'src/third_party/webrtc/': 'got_webrtc_revision',
        'src/v8/': 'got_v8_revision',
    }
}


BOT_UPDATE_MESSAGE = """
What is the "Bot Update" step?
==============================

This step ensures that the source checkout on the bot (e.g. Chromium's src/ and
its dependencies) is checked out in a consistent state. This means that all of
the necessary repositories are checked out, no extra repositories are checked
out, and no locally modified files are present.

These actions used to be taken care of by the "gclient revert" and "update"
steps. However, those steps are known to be buggy and occasionally flaky. This
step has two main advantages over them:
  * it only operates in Git, so the logic can be clearer and cleaner; and
  * it is a slave-side script, so its behavior can be modified without
    restarting the master.

Why Git, you ask? Because that is the direction that the Chromium project is
heading. This step is an integral part of the transition from using the SVN repo
at chrome/trunk/src to using the Git repo src.git. Please pardon the dust while
we fully convert everything to Git. This message will get out of your way
eventually, and the waterfall will be a happier place because of it.

This step can be activated or deactivated independently on every builder on
every master. When it is active, the "gclient revert" and "update" steps become
no-ops. When it is inactive, it prints this message, cleans up after itself, and
lets everything else continue as though nothing has changed. Eventually, when
everything is stable enough, this step will replace them entirely.

Debugging information:
(master/builder/slave may be unspecified on recipes)
master: %(master)s
builder: %(builder)s
slave: %(slave)s
forced by recipes: %(recipe)s
bot_update.py is:"""

ACTIVATED_MESSAGE = """ACTIVE.
The bot will perform a Git checkout in this step.
The "gclient revert" and "update" steps are no-ops.

"""

NOT_ACTIVATED_MESSAGE = """INACTIVE.
This step does nothing. You actually want to look at the "update" step.

"""


GCLIENT_TEMPLATE = """solutions = %(solutions)s

cache_dir = %(cache_dir)s
%(target_os)s
%(target_os_only)s
"""


internal_data = {}
if os.path.isdir(BUILD_INTERNAL_DIR):
  local_vars = {}
  try:
    execfile(os.path.join(
        BUILD_INTERNAL_DIR, 'scripts', 'slave', 'bot_update_cfg.py'),
        local_vars)
  except Exception:
    # Same as if BUILD_INTERNAL_DIR didn't exist in the first place.
    print 'Warning: unable to read internal configuration file.'
    print 'If this is an internal bot, this step may be erroneously inactive.'
  internal_data = local_vars

RECOGNIZED_PATHS = {
    # If SVN path matches key, the entire URL is rewritten to the Git url.
    '/chrome/trunk/src':
        CHROMIUM_SRC_URL,
    '/chrome/trunk/deps/third_party/webrtc/webrtc.DEPS':
        CHROMIUM_GIT_HOST + '/chromium/deps/webrtc/webrtc.DEPS.git',
}
RECOGNIZED_PATHS.update(internal_data.get('RECOGNIZED_PATHS', {}))

ENABLED_MASTERS = [
    'bot_update.always_on',
    'chromium.chromedriver',
    'chromium.chromiumos',
    'chromium.endure',
    'chromium',
    'chromium.fyi',
    'chromium.git',
    'chromium.gpu',
    'chromium.gpu.fyi',
    'chromium.linux',
    'chromium.mac',
    'chromium.memory',
    'chromium.memory.fyi',
    'chromium.perf',
    'chromium.swarm',
    'client.drmemory',
    'client.nacl.sdk.mono',
    'tryserver.chromium',
]
ENABLED_MASTERS += internal_data.get('ENABLED_MASTERS', [])

ENABLED_BUILDERS = {
    'tryserver.chromium.gpu': [
        'linux_gpu',
        'mac_gpu',
    ],
    'chromium.webkit': [
        'WebKit Linux Oilpan',
    ],
    'chromium.lkgr': [
        'Android',
        'Linux x64',
        'Linux',
        'Mac',
        'Telemetry Harness Upload',
    ],
    'tryserver.blink': [
        # Linux
        'android_blink_compile_dbg',
        'android_blink_compile_rel',
        'blink_presubmit',
        'linux_blink_bot_update',
        'linux_blink_compile_dbg',
        'linux_blink_compile_rel',
        'linux_blink_dbg',
        'linux_blink_oilpan_dbg',
        'linux_blink_oilpan_rel',
        'linux_blink_rel',

        # Mac
        'mac_blink_compile_dbg',
        'mac_blink_compile_rel',
        'mac_blink_dbg',
        'mac_blink_rel',
    ]
}
ENABLED_BUILDERS.update(internal_data.get('ENABLED_BUILDERS', {}))

ENABLED_SLAVES = {
    # This is enabled on a bot-to-bot basis to ensure that we don't have
    # bots that have mixed configs.
    'chromium.fyi': [
        'build1-m1',  # Chromium Builder / Chromium Builder (dbg)
        'vm928-m1',   # Chromium Linux Buildrunner
        'vm859-m1',   # Chromium Linux Redux
        'vm933-m1',   # ChromiumOS Linux Tests
    ],

    # Tryserver bots need to be enabled on a bot basis to make sure checkouts
    # on the same bot do not conflict.
    'tryserver.chromium': ['slave%d-c4' % i for i in range(250, 400)] +
                          ['slave%d-c4' % i for i in range(102, 121)] +
                          ['vm%d-m4' % i for i in [468, 469, 497, 502, 503]] +
                          ['vm%d-m4' % i for i in range(800, 810)] +
                          ['vm%d-m4' % i for i in range(666, 671)] +
                          ['build%d-a4' % i for i in range(100, 140)],
}
ENABLED_SLAVES.update(internal_data.get('ENABLED_SLAVES', {}))

# Disabled filters get run AFTER enabled filters, so for example if a builder
# config is enabled, but a bot on that builder is disabled, that bot will
# be disabled.
DISABLED_BUILDERS = {
    'chromium.gpu': [
        'GPU Win Builder',
        'GPU Win Builder (dbg)',
    ],
    'chromium.chromedriver': [
        'Win7',
    ],
    'chromium.gpu.fyi': [
        'GPU Win Builder (dbg)',
        'GPU Win Builder',
        'Win7 Audio',
        'Win7 Debug (NVIDIA)',
        'Win8 Debug (NVIDIA)',
        'WinXP Debug (NVIDIA)',
    ],
    'chromium.win': ['Win Builder'],  # crbug.com/370473
    'chromium.fyi': [
        'Chromium Linux Codesearch',
        'ChromiumOS Codesearch',
        # ClusterFuzz relies on svn revisions to do bisection checks.
        # crbug.com/377963
        'Win SyzyASAN LKGR',
    ],
    'chromium.perf': [
        # Windows disabled for performance reasons.
        'Win Builder',
        'Win x64 Builder',
        'Win 8 Perf (1)',
        'Win 8 Perf (2)',
        'Win 7 Perf (1)',
        'Win 7 Perf (2)',
        'Win 7 Perf (3)',
        'Win 7 Perf (4)',
        'Win 7 Perf (5)',
        'Win 7 x64 Perf (1)',
        'Win 7 x64 Perf (2)',
        'Win 7 ATI GPU Perf',
        'Win 7 Intel GPU Perf',
        'Win 7 Nvidia GPU Perf',
        'Win 7 Low-End Perf (1)',
        'Win 7 Low-End Perf (2)',
        'Win XP Perf (1)',
        'Win XP Perf (2)',
        'Win XP Perf (3)',
        'Win XP Perf (4)',
        'Win XP Perf (5)',
    ],
    'chromium.swarm': [
        'Windows Swarm Tests',
        'Windows Swarm Tests (dbg)',
    ],
    'tryserver.chromium': [
        # These don't exist, but are just here to satisfy recipes.
        'linux_no_bot_update',
        'win_no_bot_update',
        'win_blink',
        'win_blink_compile',
        'win_blink_compile_rel',
    ],
}
DISABLED_BUILDERS.update(internal_data.get('DISABLED_BUILDERS', {}))

DISABLED_SLAVES = {}
DISABLED_SLAVES.update(internal_data.get('DISABLED_SLAVES', {}))

# These masters work only in Git, meaning for got_revision, always output
# a git hash rather than a SVN rev. This goes away if flag_day is True.
GIT_MASTERS = ['chromium.git']
GIT_MASTERS += internal_data.get('GIT_MASTERS', [])


# How many times to retry failed subprocess calls.
RETRIES = 3

# Find deps2git
DEPS2GIT_DIR_PATH = path.join(SCRIPTS_DIR, 'tools', 'deps2git')
DEPS2GIT_PATH = path.join(DEPS2GIT_DIR_PATH, 'deps2git.py')
S2G_INTERNAL_PATH = path.join(SCRIPTS_DIR, 'tools', 'deps2git_internal',
                              'svn_to_git_internal.py')

# ../../cache_dir aka /b/build/slave/cache_dir
GIT_CACHE_PATH = path.join(DEPOT_TOOLS_DIR, 'git_cache.py')
CACHE_DIR = path.join(SLAVE_DIR, 'cache_dir')
# Because we print CACHE_DIR out into a .gclient file, and then later run
# eval() on it, backslashes need to be escaped, otherwise "E:\b\build" gets
# parsed as "E:[\x08][\x08]uild".
if sys.platform.startswith('win'):
  CACHE_DIR = CACHE_DIR.replace('\\', '\\\\')

# Find the patch tool.
if sys.platform.startswith('win'):
  PATCH_TOOL = path.join(BUILD_INTERNAL_DIR, 'tools', 'patch.EXE')
else:
  PATCH_TOOL = '/usr/bin/patch'

# For uploading some telemetry data.
GS_BUCKET = 'chrome-bot-update'
GSUTIL_BIN = path.join(DEPOT_TOOLS_DIR, 'third_party', 'gsutil', 'gsutil')

# If there is less than 100GB of disk space on the system, then we do
# a shallow checkout.
SHALLOW_CLONE_THRESHOLD = 100 * 1024 * 1024 * 1024


class SubprocessFailed(Exception):
  def __init__(self, message, code, output):
    Exception.__init__(self, message)
    self.code = code
    self.output = output


class PatchFailed(SubprocessFailed):
  pass


class GclientSyncFailed(SubprocessFailed):
  pass


class SVNRevisionNotFound(Exception):
  pass


class InvalidDiff(Exception):
  pass


RETRY = object()
OK = object()
FAIL = object()

def call(*args, **kwargs):
  """Interactive subprocess call."""
  kwargs['stdout'] = subprocess.PIPE
  kwargs['stderr'] = subprocess.STDOUT
  cwd = kwargs.get('cwd', os.getcwd())
  result_fn = kwargs.pop('result_fn', lambda code, out: RETRY if code else OK)
  stdin_data = kwargs.pop('stdin_data', None)
  tries = kwargs.pop('tries', RETRIES)
  if stdin_data:
    kwargs['stdin'] = subprocess.PIPE
  out = cStringIO.StringIO()
  new_env = kwargs.get('env', {})
  env = copy.copy(os.environ)
  env.update(new_env)
  kwargs['env'] = env
  attempt = 0
  for attempt in range(1, tries + 1):
    attempt_msg = ' (retry #%d)' % attempt if attempt else ''
    if new_env:
      print '===Injecting Environment Variables==='
      for k, v in sorted(new_env.items()):
        print '%s: %s' % (k, v)
    print '===Running %s%s===' % (' '.join(args), attempt_msg)
    start_time = time.time()
    proc = subprocess.Popen(args, **kwargs)
    if stdin_data:
      proc.stdin.write(stdin_data)
      proc.stdin.close()
    # This is here because passing 'sys.stdout' into stdout for proc will
    # produce out of order output.
    last_was_cr = False
    while True:
      buf = proc.stdout.read(1)
      if buf == '\r':
        buf = '\n'
        last_was_cr = True
      elif last_was_cr:
        last_was_cr = False
        if buf == '\n':
          continue
      if not buf:
        break
      sys.stdout.write(buf)
      out.write(buf)
    code = proc.wait()
    elapsed_time = ((time.time() - start_time) / 60.0)
    outval = out.getvalue()
    result = result_fn(code, outval)
    if result in (FAIL, RETRY):
      print '===Failed in %.1f mins===' % elapsed_time
      print
    else:
      print '===Succeeded in %.1f mins===' % elapsed_time
      print
      return outval
    if result is FAIL:
      break

  raise SubprocessFailed('%s failed with code %d in %s after %d attempts.' %
                         (' '.join(args), code, cwd, attempt),
                         code, outval)


def git(*args, **kwargs):
  """Wrapper around call specifically for Git commands."""
  if args and args[0] == 'cache':
    # Rewrite "git cache" calls into "python git_cache.py".
    cmd = (sys.executable, '-u', GIT_CACHE_PATH) + args[1:]
  else:
    git_executable = 'git'
    # On windows, subprocess doesn't fuzzy-match 'git' to 'git.bat', so we
    # have to do it explicitly. This is better than passing shell=True.
    if sys.platform.startswith('win'):
      git_executable += '.bat'
    cmd = (git_executable,) + args
  return call(*cmd, **kwargs)


def get_gclient_spec(solutions, target_os, target_os_only):
  return GCLIENT_TEMPLATE % {
      'solutions': pprint.pformat(solutions, indent=4),
      'cache_dir': '"%s"' % CACHE_DIR,
      'target_os': ('\ntarget_os=%s' % target_os) if target_os else '',
      'target_os_only': '\ntarget_os_only=%s' % target_os_only
  }


def check_enabled(master, builder, slave):
  if master in ENABLED_MASTERS:
    return True
  builder_list = ENABLED_BUILDERS.get(master)
  if builder_list and builder in builder_list:
    return True
  slave_list = ENABLED_SLAVES.get(master)
  if slave_list and slave in slave_list:
    return True
  return False


def check_disabled(master, builder, slave):
  """Returns True if disabled, False if not disabled."""
  builder_list = DISABLED_BUILDERS.get(master)
  if builder_list and builder in builder_list:
    return True
  slave_list = DISABLED_SLAVES.get(master)
  if slave_list and slave in slave_list:
    return True
  return False


def check_valid_host(master, builder, slave):
  return (check_enabled(master, builder, slave)
          and not check_disabled(master, builder, slave))


def solutions_printer(solutions):
  """Prints gclient solution to stdout."""
  print 'Gclient Solutions'
  print '================='
  for solution in solutions:
    name = solution.get('name')
    url = solution.get('url')
    print '%s (%s)' % (name, url)
    if solution.get('deps_file'):
      print '  Dependencies file is %s' % solution['deps_file']
    if 'managed' in solution:
      print '  Managed mode is %s' % ('ON' if solution['managed'] else 'OFF')
    custom_vars = solution.get('custom_vars')
    if custom_vars:
      print '  Custom Variables:'
      for var_name, var_value in sorted(custom_vars.iteritems()):
        print '    %s = %s' % (var_name, var_value)
    custom_deps = solution.get('custom_deps')
    if 'custom_deps' in solution:
      print '  Custom Dependencies:'
      for deps_name, deps_value in sorted(custom_deps.iteritems()):
        if deps_value:
          print '    %s -> %s' % (deps_name, deps_value)
        else:
          print '    %s: Ignore' % deps_name
    for k, v in solution.iteritems():
      # Print out all the keys we don't know about.
      if k in ['name', 'url', 'deps_file', 'custom_vars', 'custom_deps',
               'managed']:
        continue
      print '  %s is %s' % (k, v)
    print


def solutions_to_git(input_solutions):
  """Modifies urls in solutions to point at Git repos.

  returns: (git solution, svn root of first solution) tuple.
  """
  warnings = []
  assert input_solutions
  solutions = copy.deepcopy(input_solutions)
  first_solution = True
  buildspec_name = False
  for solution in solutions:
    original_url = solution['url']
    parsed_url = urlparse.urlparse(original_url)
    parsed_path = parsed_url.path

    # Rewrite SVN urls into Git urls.
    buildspec_m = re.match(BUILDSPEC_RE, parsed_path)
    if first_solution and buildspec_m:
      solution['url'] = GIT_BUILDSPEC_PATH
      buildspec_name = buildspec_m.group(1)
      solution['deps_file'] = path.join('build', buildspec_name, 'DEPS')
    elif parsed_path in RECOGNIZED_PATHS:
      solution['url'] = RECOGNIZED_PATHS[parsed_path]
    else:
      warnings.append('path %r not recognized' % parsed_path)
      print 'Warning: %s' % (warnings[-1],)

    # Point .DEPS.git is the git version of the DEPS file.
    if not FLAG_DAY:
      solution['deps_file'] = '.DEPS.git'

    if first_solution:
      root = parsed_path
      first_solution = False

    solution['managed'] = False
    # We don't want gclient to be using a safesync URL. Instead it should
    # using the lkgr/lkcr branch/tags.
    if 'safesync_url' in solution:
      print 'Removing safesync url %s from %s' % (solution['safesync_url'],
                                                  parsed_path)
      del solution['safesync_url']
  return solutions, root, buildspec_name, warnings


def remove(target):
  """Remove a target by moving it into build.dead."""
  dead_folder = path.join(BUILDER_DIR, 'build.dead')
  if not path.exists(dead_folder):
    os.makedirs(dead_folder)
  os.rename(target, path.join(dead_folder, uuid.uuid4().hex))


def ensure_no_checkout(dir_names, scm_dirname):
  """Ensure that there is no undesired checkout under build/.

  If there is an incorrect checkout under build/, then
  move build/ to build.dead/
  This function will check each directory in dir_names.

  scm_dirname is expected to be either ['.svn', '.git']
  """
  assert scm_dirname in ['.svn', '.git', '*']
  has_checkout = any(map(lambda dir_name: path.exists(
      path.join(os.getcwd(), dir_name, scm_dirname)), dir_names))

  if has_checkout or scm_dirname == '*':
    build_dir = os.getcwd()
    prefix = ''
    if scm_dirname != '*':
      prefix = '%s detected in checkout, ' % scm_dirname

    for filename in os.listdir(build_dir):
      deletion_target = path.join(build_dir, filename)
      print '%sdeleting %s...' % (prefix, deletion_target),
      remove(deletion_target)
      print 'done'


def gclient_configure(solutions, target_os, target_os_only):
  """Should do the same thing as gclient --spec='...'."""
  with codecs.open('.gclient', mode='w', encoding='utf-8') as f:
    f.write(get_gclient_spec(solutions, target_os, target_os_only))


def gclient_sync(buildspec_name, shallow):
  # We just need to allocate a filename.
  fd, gclient_output_file = tempfile.mkstemp(suffix='.json')
  os.close(fd)
  gclient_bin = 'gclient.bat' if sys.platform.startswith('win') else 'gclient'
  cmd = [gclient_bin, 'sync', '--verbose', '--reset', '--force',
         '--output-json', gclient_output_file , '--nohooks', '--noprehooks']
  if buildspec_name:
    cmd += ['--with_branch_heads']
  if shallow:
    cmd += ['--shallow']

  try:
    call(*cmd)
  except SubprocessFailed as e:
    # Throw a GclientSyncFailed exception so we can catch this independently.
    raise GclientSyncFailed(e.message, e.code, e.output)
  else:
    with open(gclient_output_file) as f:
      return json.load(f)
  finally:
    os.remove(gclient_output_file)


def gclient_runhooks(gyp_envs):
  gclient_bin = 'gclient.bat' if sys.platform.startswith('win') else 'gclient'
  env = dict([env_var.split('=', 1) for env_var in gyp_envs])
  call(gclient_bin, 'runhooks', env=env)


def get_svn_rev(git_hash, dir_name):
  pattern = r'^\s*git-svn-id: [^ ]*@(\d+) '
  log = git('log', '-1', git_hash, cwd=dir_name)
  match = re.search(pattern, log, re.M)
  if not match:
    return None
  return int(match.group(1))


def get_git_hash(revision, branch, sln_dir):
  """We want to search for the SVN revision on the git-svn branch.

  Note that git will search backwards from origin/master.
  """
  match = "^git-svn-id: [^ ]*@%s " % revision
  cmd = ['log', '-E', '--grep', match, '--format=%H', '--max-count=1',
         'origin/%s' % branch]
  result = git(*cmd, cwd=sln_dir).strip()
  if result:
    return result
  raise SVNRevisionNotFound('We can\'t resolve svn r%s into a git hash in %s' %
                            (revision, sln_dir))


def _last_commit_for_file(filename, repo_base):
  cmd = ['log', '--format=%H', '--max-count=1', '--', filename]
  return git(*cmd, cwd=repo_base).strip()


def need_to_run_deps2git(repo_base, deps_file, deps_git_file):
  """Checks to see if we need to run deps2git.

  Returns True if there was a DEPS change after the last .DEPS.git update
  or if DEPS has local modifications.
  """
  print 'Checking if %s exists' % deps_git_file
  if not path.isfile(deps_git_file):
    # .DEPS.git doesn't exist but DEPS does?  Generate one (unless we're past
    # migration day, in which case we don't need .DEPS.git.
    print 'it doesn\'t exist!'
    return not FLAG_DAY

  # See if DEPS is dirty
  deps_file_status = git(
      'status', '--porcelain', deps_file, cwd=repo_base).strip()
  if deps_file_status and deps_file_status.startswith('M '):
    return True

  last_known_deps_ref = _last_commit_for_file(deps_file, repo_base)
  last_known_deps_git_ref = _last_commit_for_file(deps_git_file, repo_base)
  merge_base_ref = git('merge-base', last_known_deps_ref,
                       last_known_deps_git_ref, cwd=repo_base).strip()

  # If the merge base of the last DEPS and last .DEPS.git file is not
  # equivilent to the hash of the last DEPS file, that means the DEPS file
  # was committed after the last .DEPS.git file.
  return last_known_deps_ref != merge_base_ref


def get_git_buildspec(version):
  """Get the git buildspec of a version, return its contents.

  The contents are returned instead of the file so that we can check the
  repository into a temp directory and confine the cleanup logic here.
  """
  git('cache', 'populate', '-v', '--cache-dir', CACHE_DIR, GIT_BUILDSPEC_REPO)
  mirror_dir = git(
      'cache', 'exists', '--quiet', '--cache-dir', CACHE_DIR,
      GIT_BUILDSPEC_REPO).strip()
  TOTAL_TRIES = 30
  for tries in range(TOTAL_TRIES):
    try:
      return git('show', 'master:%s/DEPS' % version, cwd=mirror_dir)
    except SubprocessFailed:
      if tries < TOTAL_TRIES - 1:
        print 'Buildspec for %s not committed yet, waiting 5 seconds...'
        time.sleep(5)
        git('cache', 'populate', '-v', '--cache-dir',
            CACHE_DIR, GIT_BUILDSPEC_REPO)
      else:
        print >> sys.stderr, '%s not found, ' % version,
        print >> sys.stderr, 'the buildspec2git cron job probably is not ',
        print >> sys.stderr, 'running correctly, please contact mmoss@.'
        raise


def buildspecs2git(sln_dir, buildspec_name):
  """This is like deps2git, but for buildspecs.

  Because buildspecs are vastly different than normal DEPS files, we cannot
  use deps2git.py to generate git versions of the git DEPS.  Fortunately
  we don't have buildspec trybots, and there is already a service that
  generates git DEPS for every buildspec commit already, so we can leverage
  that service so that we don't need to run buildspec2git.py serially.

  This checks the commit message of the current DEPS file for the release
  number, waits in a busy loop for the coorisponding .DEPS.git file to be
  committed into the git_buildspecs repository.
  """
  repo_base = path.join(os.getcwd(), sln_dir)
  deps_file = path.join(repo_base, 'build', buildspec_name, 'DEPS')
  deps_git_file = path.join(repo_base, 'build', buildspec_name, '.DEPS.git')
  deps_log = git('log', '-1', '--format=%B', deps_file, cwd=repo_base)
  m = re.search(r'Buildspec for\s+version (\d+\.\d+\.\d+\.\d+)', deps_log)
  version = m.group(1)
  git_buildspec = get_git_buildspec(version)
  with open(deps_git_file, 'wb') as f:
    f.write(git_buildspec)


def ensure_deps2git(solution, shallow):
  repo_base = path.join(os.getcwd(), solution['name'])
  deps_file = path.join(repo_base, 'DEPS')
  deps_git_file = path.join(repo_base, '.DEPS.git')
  if not git('ls-files', '.DEPS.git', cwd=repo_base).strip():
    return

  print 'Checking if %s is newer than %s' % (deps_file, deps_git_file)
  if not need_to_run_deps2git(repo_base, deps_file, deps_git_file):
    return

  print '===DEPS file modified, need to run deps2git==='
  cmd = [sys.executable, DEPS2GIT_PATH,
         '--cache_dir', CACHE_DIR,
         '--deps', deps_file,
         '--out', deps_git_file]
  if 'chrome-internal.googlesource' in solution['url']:
    cmd.extend(['--extra-rules', S2G_INTERNAL_PATH])
  if shallow:
    cmd.append('--shallow')
  call(*cmd)


def emit_log_lines(name, lines):
  for line in lines.splitlines():
    print '@@@STEP_LOG_LINE@%s@%s@@@' % (name, line)
  print '@@@STEP_LOG_END@%s@@@' % name


def emit_properties(properties):
  for property_name, property_value in properties.iteritems():
    print '@@@SET_BUILD_PROPERTY@%s@"%s"@@@' % (property_name, property_value)


# Derived from:
# http://code.activestate.com/recipes/577972-disk-usage/?in=user-4178764
def get_total_disk_space():
  cwd = os.getcwd()
  # Windows is the only platform that doesn't support os.statvfs, so
  # we need to special case this.
  if sys.platform.startswith('win'):
    _, total, free = (ctypes.c_ulonglong(), ctypes.c_ulonglong(), \
                      ctypes.c_ulonglong())
    if sys.version_info >= (3,) or isinstance(cwd, unicode):
      fn = ctypes.windll.kernel32.GetDiskFreeSpaceExW
    else:
      fn = ctypes.windll.kernel32.GetDiskFreeSpaceExA
    ret = fn(cwd, ctypes.byref(_), ctypes.byref(total), ctypes.byref(free))
    if ret == 0:
      # WinError() will fetch the last error code.
      raise ctypes.WinError()
    return (total.value, free.value)

  else:
    st = os.statvfs(cwd)
    free = st.f_bavail * st.f_frsize
    total = st.f_blocks * st.f_frsize
    return (total, free)


def get_target_revision(folder_name, git_url, revisions):
  normalized_name = folder_name.strip('/')
  if normalized_name in revisions:
    return revisions[normalized_name]
  if git_url in revisions:
    return revisions[git_url]
  return None


def force_revision(folder_name, revision, git_svn=False):
  split_revision = revision.split(':', 1)
  branch = 'master'
  if len(split_revision) == 2:
    # Support for "branch:revision" syntax.
    branch, revision = split_revision

  if revision and revision.upper() != 'HEAD':
    if revision and revision.isdigit() and len(revision) < 40:
      # rev_num is really a svn revision number, convert it into a git hash.
      git_ref = get_git_hash(int(revision), branch, folder_name)
    else:
      # rev_num is actually a git hash or ref, we can just use it.
      git_ref = revision
    git('checkout', '--force', git_ref, cwd=folder_name)
  else:
    git('checkout', '--force', 'origin/%s' % branch, cwd=folder_name)

def git_checkout(solutions, revisions, shallow):
  build_dir = os.getcwd()
  # Before we do anything, break all git_cache locks.
  if path.isdir(CACHE_DIR):
    git('cache', 'unlock', '-vv', '--force', '--all', '--cache-dir', CACHE_DIR)
    for item in os.listdir(CACHE_DIR):
      filename = os.path.join(CACHE_DIR, item)
      if item.endswith('.lock'):
        raise Exception('%s exists after cache unlock' % filename)
  first_solution = True
  for sln in solutions:
    # This is so we can loop back and try again if we need to wait for the
    # git mirrors to update from SVN.
    done = False
    tries_left = 60
    while not done:
      name = sln['name']
      url = sln['url']
      if url == CHROMIUM_SRC_URL or url + '.git' == CHROMIUM_SRC_URL:
        # Experiments show there's little to be gained from
        # a shallow clone of src.
        shallow = False
      sln_dir = path.join(build_dir, name)
      s = ['--shallow'] if shallow else []
      populate_cmd = (['cache', 'populate', '-v', '--cache-dir', CACHE_DIR]
                      + s + [url])
      git(*populate_cmd)
      mirror_dir = git(
          'cache', 'exists', '--quiet', '--cache-dir', CACHE_DIR, url).strip()
      clone_cmd = (
          'clone', '--no-checkout', '--local', '--shared', mirror_dir, sln_dir)
      if not path.isdir(sln_dir):
        git(*clone_cmd)
      else:
        git('fetch', 'origin', cwd=sln_dir)

      revision = get_target_revision(name, url, revisions) or 'HEAD'
      try:
        force_revision(sln_dir, revision, url==CHROMIUM_SRC_URL)
        done = True
      except SubprocessFailed:
        # Exited abnormally, theres probably something wrong.
        # Lets wipe the checkout and try again.
        remove(sln_dir)
        git(*clone_cmd)
      except SVNRevisionNotFound:
        tries_left -= 1
        if tries_left > 0:
          # If we don't have the correct revision, wait and try again.
          print 'We can\'t find revision %s.' % revision
          print 'The svn to git replicator is probably falling behind.'
          print 'waiting 5 seconds and trying again...'
          time.sleep(5)
        else:
          raise

    git('clean', '-df', cwd=sln_dir)

    if first_solution:
      git_ref = git('log', '--format=%H', '--max-count=1',
                    cwd=sln_dir).strip()
    first_solution = False
  return git_ref


def _download(url):
  """Fetch url and return content, with retries for flake."""
  for attempt in xrange(RETRIES):
    try:
      return urllib2.urlopen(url).read()
    except Exception:
      if attempt == RETRIES - 1:
        raise


def parse_diff(diff):
  """Takes a unified diff and returns a list of diffed files and their diffs.

  The return format is a list of pairs of:
    (<filename>, <diff contents>)
  <diff contents> is inclusive of the diff line.
  """
  result = []
  current_diff = ''
  current_header = None
  for line in diff.splitlines():
    # "diff" is for git style patches, and "Index: " is for SVN style patches.
    if line.startswith('diff') or line.startswith('Index: '):
      if current_header:
        # If we are in a diff portion, then save the diff.
        result.append((current_header, '%s\n' % current_diff))
      git_header_match = re.match(r'diff (?:--git )?(\S+) (\S+)', line)
      svn_header_match = re.match(r'Index: (.*)', line)

      if git_header_match:
        # First, see if its a git style header.
        from_file = git_header_match.group(1)
        to_file = git_header_match.group(2)
        if from_file != to_file and from_file.startswith('a/'):
          # Sometimes git prepends 'a/' and 'b/' in front of file paths.
          from_file = from_file[2:]
        current_header = from_file

      elif svn_header_match:
        # Otherwise, check if its an SVN style header.
        current_header = svn_header_match.group(1)

      else:
        # Otherwise... I'm not really sure what to do with this.
        raise InvalidDiff('Can\'t process header: %s\nFull diff:\n%s' %
                          (line, diff))

      current_diff = ''
    current_diff += '%s\n' % line
  if current_header:
    # We hit EOF, gotta save the last diff.
    result.append((current_header, current_diff))
  return result


def get_svn_patch(patch_url):
  """Fetch patch from patch_url, return list of (filename, diff)"""
  svn_exe = 'svn.bat' if sys.platform.startswith('win') else 'svn'
  patch_data = call(svn_exe, 'cat', patch_url)
  return parse_diff(patch_data)


def apply_svn_patch(patch_root, patches, whitelist=None, blacklist=None):
  """Expects a list of (filename, diff), applies it on top of patch_root."""
  if whitelist:
    patches = [(name, diff) for name, diff in patches if name in whitelist]
  elif blacklist:
    patches = [(name, diff) for name, diff in patches if name not in blacklist]
  diffs = [diff for _, diff in patches]
  patch = ''.join(diffs)

  if patch:
    print '===Patching files==='
    for filename, _ in patches:
      print 'Patching %s' % filename
    try:
      call(PATCH_TOOL, '-p0', '--remove-empty-files', '--force', '--forward',
          stdin_data=patch, cwd=patch_root, tries=1)
      for filename, _ in patches:
        full_filename = path.abspath(path.join(patch_root, filename))
        git('add', full_filename, cwd=path.dirname(full_filename))
    except SubprocessFailed as e:
      raise PatchFailed(e.message, e.code, e.output)

def apply_rietveld_issue(issue, patchset, root, server, _rev_map, _revision,
                         whitelist=None, blacklist=None):
  apply_issue_bin = ('apply_issue.bat' if sys.platform.startswith('win')
                     else 'apply_issue')
  cmd = [apply_issue_bin,
         # The patch will be applied on top of this directory.
         '--root_dir', root,
         # Tell apply_issue how to fetch the patch.
         '--issue', issue,
         '--no-auth',
         '--server', server,
         # Always run apply_issue.py, otherwise it would see update.flag
         # and then bail out.
         '--force',
         # Don't run gclient sync when it sees a DEPS change.
         '--ignore_deps',
  ]
  if patchset:
    cmd.extend(['--patchset', patchset])
  if whitelist:
    for item in whitelist:
      cmd.extend(['--whitelist', item])
  elif blacklist:
    for item in blacklist:
      cmd.extend(['--blacklist', item])

  # Only try once, since subsequent failures hide the real failure.
  try:
    call(*cmd, tries=1)
  except SubprocessFailed as e:
    raise PatchFailed(e.message, e.code, e.output)


def check_flag(flag_file):
  """Returns True if the flag file is present."""
  return os.path.isfile(flag_file)


def delete_flag(flag_file):
  """Remove bot update flag."""
  if os.path.isfile(flag_file):
    os.remove(flag_file)


def emit_flag(flag_file):
  """Deposit a bot update flag on the system to tell gclient not to run."""
  print 'Emitting flag file at %s' % flag_file
  with open(flag_file, 'wb') as f:
    f.write('Success!')


def parse_got_revision(gclient_output, got_revision_mapping, use_svn_revs):
  """Translate git gclient revision mapping to build properties.

  If use_svn_revs is True, then translate git hashes in the revision mapping
  to svn revision numbers.
  """
  properties = {}
  solutions_output = {
      # Make sure path always ends with a single slash.
      '%s/' % path.rstrip('/') : solution_output for path, solution_output
      in gclient_output['solutions'].iteritems()
  }
  for dir_name, property_name in got_revision_mapping.iteritems():
    # Make sure dir_name always ends with a single slash.
    dir_name = '%s/' % dir_name.rstrip('/')
    if dir_name not in solutions_output:
      continue
    solution_output = solutions_output[dir_name]
    if solution_output.get('scm') is None:
      # This is an ignored DEPS, so the output got_revision should be 'None'.
      git_revision = revision = None
    else:
      # Since we are using .DEPS.git, everything had better be git.
      assert solution_output.get('scm') == 'git'
      git_revision = git('rev-parse', 'HEAD', cwd=dir_name).strip()
      if use_svn_revs:
        revision = get_svn_rev(git_revision, dir_name)
        if not revision:
          revision = git_revision
      else:
        revision = git_revision

    properties[property_name] = revision
    if revision != git_revision:
      properties['%s_git' % property_name] = git_revision

  return properties


def emit_json(out_file, did_run, gclient_output=None, **kwargs):
  """Write run information into a JSON file."""
  output = {}
  output.update(gclient_output if gclient_output else {})
  output.update({'did_run': did_run})
  output.update(kwargs)
  with open(out_file, 'wb') as f:
    f.write(json.dumps(output))


def ensure_deps_revisions(deps_url_mapping, solutions, revisions):
  """Ensure correct DEPS revisions, ignores solutions."""
  for deps_name, deps_data in sorted(deps_url_mapping.items()):
    if deps_name.strip('/') in solutions:
      # This has already been forced to the correct solution by git_checkout().
      continue
    revision = get_target_revision(deps_name, deps_data.get('url', None),
                                   revisions)
    if not revision:
      continue
    # TODO(hinoka): Catch SVNRevisionNotFound error maybe?
    git('fetch', 'origin', cwd=deps_name)
    force_revision(deps_name, revision)


def ensure_checkout(solutions, revisions, first_sln, target_os, target_os_only,
                    patch_root, issue, patchset, patch_url, rietveld_server,
                    revision_mapping, buildspec_name, gyp_env, shallow):
  # Get a checkout of each solution, without DEPS or hooks.
  # Calling git directly because there is no way to run Gclient without
  # invoking DEPS.
  print 'Fetching Git checkout'
  git_ref = git_checkout(solutions, revisions, shallow)

  patches = None
  if patch_url:
    patches = get_svn_patch(patch_url)

  for solution in solutions:
    # At first, only patch top-level DEPS.
    if patch_root == solution['name']:
      if patches:
        apply_svn_patch(patch_root, patches, whitelist=['DEPS'])
      elif issue:
        apply_rietveld_issue(issue, patchset, patch_root, rietveld_server,
                            revision_mapping, git_ref, whitelist=['DEPS'])
      break

  if buildspec_name:
    buildspecs2git(first_sln, buildspec_name)
  else:
    # Run deps2git if there is a DEPS change after the last .DEPS.git commit.
    for solution in solutions:
      ensure_deps2git(solution, shallow)

  # Ensure our build/ directory is set up with the correct .gclient file.
  gclient_configure(solutions, target_os, target_os_only)

  # Let gclient do the DEPS syncing.
  gclient_output = gclient_sync(buildspec_name, shallow)

  # Now that gclient_sync has finished, we should revert any .DEPS.git so that
  # presubmit doesn't complain about it being modified.
  if (not buildspec_name and
      git('ls-files', '.DEPS.git', cwd=first_sln).strip()):
    git('checkout', 'HEAD', '--', '.DEPS.git', cwd=first_sln)

  if buildspec_name:
    # Run gclient runhooks if we're on an official builder.
    # TODO(hinoka): Remove this when the official builders run their own
    #               runhooks step.
    gclient_runhooks(gyp_env)

  # Finally, ensure that all DEPS are pinned to the correct revision.
  dir_names = [sln['name'] for sln in solutions]
  ensure_deps_revisions(gclient_output.get('solutions', {}),
                        dir_names, revisions)
  # Apply the rest of the patch here (sans DEPS)
  if patches:
    apply_svn_patch(patch_root, patches, blacklist=['DEPS'])
  elif issue:
    apply_rietveld_issue(issue, patchset, patch_root, rietveld_server,
                         revision_mapping, git_ref, blacklist=['DEPS'])

  return gclient_output


class UploadTelemetryThread(threading.Thread):
  def __init__(self, prefix, master, builder, slave, kwargs):
    super(UploadTelemetryThread, self).__init__()
    self.master = master
    self.builder = builder
    self.slave = slave
    self.prefix = prefix
    self.kwargs = kwargs or {}

  def url(self, name=None):
    return 'gs://%s/%s/%s/%s/%s.json' % (
        GS_BUCKET, self.master, self.builder, self.slave, name or self.prefix)

  @staticmethod
  def _gsutil(*args, **kwargs):
    fail_gs_codes = kwargs.pop('fail_gs_codes', ())
    fail_gs_msgs = kwargs.pop('fail_gs_msgs', ())
    def gs_ok_fn(code, out):
      if not code:
        return OK
      if not fail_gs_msgs and not fail_gs_codes:
        return RETRY

      lines = out.splitlines()
      if fail_gs_codes:
        status = re.match('GSResponseError.*status=(\d+)', lines[-1])
        if status and int(status.group(1)) in fail_gs_codes:
          return FAIL

      if fail_gs_msgs:
        if any(m in lines[0] for m in fail_gs_msgs):
          return FAIL

      return RETRY
    kwargs.setdefault('result_fn', gs_ok_fn)

    return call(sys.executable, '-u', GSUTIL_BIN, *args, **kwargs)

  def run(self):
    if not UPLOAD_TELEMETRY:
      return

    if self.prefix == 'start':
      try:
        self._gsutil('rm', self.url('start_old'), self.url('end_old'),
                     fail_gs_codes={404})
      except Exception as e:
        print 'INFO: Could not rm start_old, end_old. %r' % e

      try:
        self._gsutil('mv', self.url('start'), self.url('start_old'),
                     fail_gs_msgs={'InvalidUriError'})
      except Exception as e:
        print 'INFO: Could not move start -> start_old. %r' % e

      try:
        self._gsutil('mv', self.url('end'), self.url('end_old'),
                     fail_gs_msgs={'InvalidUriError'})
      except Exception as e:
        print 'INFO: Could not move end -> end_old. %r' % e

    # Disk space Code duplicated here to get it out of the critical path
    # when bot_update is not activated.
    data = {
        'prefix': self.prefix,
        'master': self.master,
        'builder': self.builder,
        'slave': self.slave,
    }
    data.update(self.kwargs)
    try:
      total_disk_space, free_disk_space = get_total_disk_space()
      total_disk_space_gb = int(total_disk_space / (1024 * 1024 * 1024))
      used_disk_space_gb = int((total_disk_space - free_disk_space)
                              / (1024 * 1024 * 1024))
      percent_used = int(used_disk_space_gb * 100 / total_disk_space_gb)
      data['disk'] = {
          'total': total_disk_space_gb,
          'used': used_disk_space_gb,
          'percent': percent_used,
          'status': 'OK',
          'small': total_disk_space < SHALLOW_CLONE_THRESHOLD,
      }
    except Exception as e:
      data['disk'] = {
          'status': 'EXCEPTION',
          'message': str(e),
      }

    try:
      self._gsutil('cp', '-', self.url(), stdin_data=json.dumps(data))
    except Exception:
      print 'Telemetry upload failed.'


def upload_telemetry(prefix, master, builder, slave, **kwargs):
  thr = UploadTelemetryThread(prefix, master, builder, slave, kwargs)
  thr.daemon = True
  thr.start()
  return thr


def parse_revisions(revisions, root):
  """Turn a list of revision specs into a nice dictionary.

  We will always return a dict with {root: something}.  By default if root
  is unspecified, or if revisions is [], then revision will be assigned 'HEAD'
  """
  results = {root.strip('/'): 'HEAD'}
  for revision in revisions:
    split_revision = revision.split('@')
    if len(split_revision) == 1:
      # This is just a plain revision, set it as the revision for root.
      results[root] = split_revision[0]
    elif len(split_revision) == 2:
      # This is an alt_root@revision argument.
      current_root, current_rev = split_revision

      # We want to normalize svn/git urls into .git urls.
      parsed_root = urlparse.urlparse(current_root)
      if parsed_root.scheme == 'svn':
        if parsed_root.path in RECOGNIZED_PATHS:
          normalized_root = RECOGNIZED_PATHS[parsed_root.path]
        else:
          print 'WARNING: SVN path %s not recognized, ignoring' % current_root
          continue
      elif parsed_root.scheme in ['http', 'https']:
        normalized_root = 'https://%s/%s' % (parsed_root.netloc,
                                             parsed_root.path)
        if not normalized_root.endswith('.git'):
          normalized_root = '%s.git' % normalized_root
      elif parsed_root.scheme:
        print 'WARNING: Unrecognized scheme %s, ignoring' % parsed_root.scheme
        continue
      else:
        # This is probably a local path.
        normalized_root = current_root.strip('/')

      results[normalized_root] = current_rev
    else:
      print ('WARNING: %r is not recognized as a valid revision specification,'
             'skipping' % revision)
  return results


def parse_args():
  parse = optparse.OptionParser()

  parse.add_option('--issue', help='Issue number to patch from.')
  parse.add_option('--patchset',
                   help='Patchset from issue to patch from, if applicable.')
  parse.add_option('--patch_url', help='Optional URL to SVN patch.')
  parse.add_option('--root', dest='patch_root',
                   help='DEPRECATED: Use --patch_root.')
  parse.add_option('--patch_root', help='Directory to patch on top of.')
  parse.add_option('--rietveld_server',
                   default='codereview.chromium.org',
                   help='Rietveld server.')
  parse.add_option('--specs', help='Gcilent spec.')
  parse.add_option('--master', help='Master name.')
  parse.add_option('-f', '--force', action='store_true',
                   help='Bypass check to see if we want to be run. '
                        'Should ONLY be used locally or by smart recipes.')
  parse.add_option('--revision_mapping',
                   help='{"path/to/repo/": "property_name"}')
  parse.add_option('--revision_mapping_file',
                   help=('Same as revision_mapping, except its a path to a json'
                         ' file containing that format.'))
  parse.add_option('--revision-mapping', # Backwards compatability.
                   help='DEPRECATED, use "revision_mapping" instead')
  parse.add_option('--revision', action='append', default=[],
                   help='Revision to check out. Can be an SVN revision number, '
                        'git hash, or any form of git ref.  Can prepend '
                        'root@<rev> to specify which repository, where root '
                        'is either a filesystem path, git https url, or '
                        'svn url. To specify Tip of Tree, set rev to HEAD.'
                        'To specify a git branch and an SVN rev, <rev> can be '
                        'set to <branch>:<revision>.')
  parse.add_option('--slave_name', default=socket.getfqdn().split('.')[0],
                   help='Hostname of the current machine, '
                   'used for determining whether or not to activate.')
  parse.add_option('--builder_name', help='Name of the builder, '
                   'used for determining whether or not to activate.')
  parse.add_option('--build_dir', default=os.getcwd())
  parse.add_option('--flag_file', default=path.join(os.getcwd(),
                                                    'update.flag'))
  parse.add_option('--shallow', action='store_true',
                   help='Use shallow clones for cache repositories.')
  parse.add_option('--gyp_env', action='append', default=[],
                   help='Environment variables to pass into gclient runhooks.')
  parse.add_option('--clobber', action='store_true',
                   help='Delete checkout first, always')
  parse.add_option('--bot_update_clobber', action='store_true', dest='clobber',
                   help='(synonym for --clobber)')
  parse.add_option('-o', '--output_json',
                   help='Output JSON information into a specified file')
  parse.add_option('--post-flag-day', action='store_true',
                   help='Behave as if the chromium git migration has already '
                   'happened')


  options, args = parse.parse_args()

  if options.post_flag_day:
    global FLAG_DAY
    FLAG_DAY = True

  try:
    if options.revision_mapping_file:
      if options.revision_mapping:
        print ('WARNING: Ignoring --revision_mapping: --revision_mapping_file '
               'was set at the same time as --revision_mapping?')
      with open(options.revision_mapping_file, 'r') as f:
        options.revision_mapping = json.load(f)
    elif options.revision_mapping:
      options.revision_mapping = json.loads(options.revision_mapping)
  except Exception as e:
    print (
        'WARNING: Caught execption while parsing revision_mapping*: %s'
        % (str(e),)
    )

  return options, args


def main():
  # Get inputs.
  options, _ = parse_args()
  builder = options.builder_name
  slave = options.slave_name
  master = options.master

  # Check if this script should activate or not.
  active = check_valid_host(master, builder, slave) or options.force or False

  # Print helpful messages to tell devs whats going on.
  if options.force and options.output_json:
    recipe_force = 'Forced on by recipes'
  elif active and options.output_json:
    recipe_force = 'Off by recipes, but forced on by bot update'
  elif not active and options.output_json:
    recipe_force = 'Forced off by recipes'
  else:
    recipe_force = 'N/A. Was not called by recipes'

  print BOT_UPDATE_MESSAGE % {
    'master': master or 'Not specified',
    'builder': builder or 'Not specified',
    'slave': slave or 'Not specified',
    'recipe': recipe_force,
  },
  # Print to stderr so that it shows up red on win/mac.
  print ACTIVATED_MESSAGE if active else NOT_ACTIVATED_MESSAGE

  # Parse, munipulate, and print the gclient solutions.
  specs = {}
  exec(options.specs, specs)
  svn_solutions = specs.get('solutions', [])
  git_slns, svn_root, buildspec_name, warnings = solutions_to_git(svn_solutions)
  solutions_printer(git_slns)

  # Lets send some telemetry data about bot_update here. This returns a thread
  # object so we can join on it later.
  all_threads = []
  run_id = uuid.uuid4().hex
  thr = upload_telemetry(
      active=active,
      builder=builder,
      conversion_warnings=warnings,
      git_solutions=git_slns,
      master=master,
      prefix='start',
      run_id=run_id,
      slave=slave,
      solutions=specs.get('solutions', []),
      specs=options.specs,
      unix_time=time.time(),
  )
  all_threads.append(thr)

  dir_names = [sln.get('name') for sln in svn_solutions if 'name' in sln]
  # If we're active now, but the flag file doesn't exist (we weren't active last
  # run) or vice versa, blow away all checkouts.
  if bool(active) != bool(check_flag(options.flag_file)):
    ensure_no_checkout(dir_names, '*')
  if options.output_json:
    # Make sure we tell recipes that we didn't run if the script exits here.
    emit_json(options.output_json, did_run=active)
  if active:
    if options.clobber:
      ensure_no_checkout(dir_names, '*')
    else:
      ensure_no_checkout(dir_names, '.svn')
    emit_flag(options.flag_file)
  else:
    delete_flag(options.flag_file)
    thr.join()
    return

  # Do a shallow checkout if the disk is less than 100GB.
  total_disk_space, free_disk_space = get_total_disk_space()
  total_disk_space_gb = int(total_disk_space / (1024 * 1024 * 1024))
  used_disk_space_gb = int((total_disk_space - free_disk_space)
                           / (1024 * 1024 * 1024))
  percent_used = int(used_disk_space_gb * 100 / total_disk_space_gb)
  step_text = '[%dGB/%dGB used (%d%%)]' % (used_disk_space_gb,
                                           total_disk_space_gb,
                                           percent_used)
  if not options.output_json:
    print '@@@STEP_TEXT@%s@@@' % step_text
  if not options.shallow:
    options.shallow = total_disk_space < SHALLOW_CLONE_THRESHOLD

  # The first solution is where the primary DEPS file resides.
  first_sln = dir_names[0]

  # Split all the revision specifications into a nice dict.
  print 'Revisions: %s' % options.revision
  revisions = parse_revisions(options.revision, first_sln)
  # This is meant to be just an alias to the revision of the main solution.
  root_revision = revisions[first_sln]
  print 'Fetching Git checkout at %s@%s' % (first_sln, root_revision)

  try:
    # Outer try is for catching patch failures and exiting gracefully.
    # Inner try is for catching gclient failures and retrying gracefully.
    try:
      checkout_parameters = dict(
          # First, pass in the base of what we want to check out.
          solutions=git_slns,
          revisions=revisions,
          first_sln=first_sln,

          # Also, target os variables for gclient.
          target_os=specs.get('target_os', []),
          target_os_only=specs.get('target_os_only', False),

          # Then, pass in information about how to patch on top of the checkout.
          patch_root=options.patch_root,
          issue=options.issue,
          patchset=options.patchset,
          patch_url=options.patch_url,
          rietveld_server=options.rietveld_server,
          revision_mapping=options.revision_mapping,

          # For official builders.
          buildspec_name=buildspec_name,
          gyp_env=options.gyp_env,

          # Finally, extra configurations such as shallowness of the clone.
          shallow=options.shallow)
      gclient_output = ensure_checkout(**checkout_parameters)
    except GclientSyncFailed:
      print 'We failed gclient sync, lets delete the checkout and retry.'
      ensure_no_checkout(dir_names, '*')
      gclient_output = ensure_checkout(**checkout_parameters)
  except PatchFailed as e:
    if options.output_json:
      # Tell recipes information such as root, got_revision, etc.
      emit_json(options.output_json,
                did_run=True,
                root=first_sln,
                log_lines=[('patch error', e.output),],
                patch_root=options.patch_root,
                step_text='%s PATCH FAILED' % step_text)
    else:
      # If we're not on recipes, tell annotator about our got_revisions.
      emit_log_lines('patch error', e.output)
      print '@@@STEP_TEXT@%s PATCH FAILED@@@' % step_text
    raise

  # Revision is an svn revision, unless its a git master or past flag day.
  use_svn_rev = master not in GIT_MASTERS and not FLAG_DAY
  # Take care of got_revisions outputs.
  revision_mapping = dict(GOT_REVISION_MAPPINGS.get(svn_root, {}))
  if options.revision_mapping:
    revision_mapping.update(options.revision_mapping)

  got_revisions = parse_got_revision(gclient_output, revision_mapping,
                                     use_svn_rev)

  if options.output_json:
    # Tell recipes information such as root, got_revision, etc.
    emit_json(options.output_json,
              did_run=True,
              root=first_sln,
              patch_root=options.patch_root,
              step_text=step_text,
              properties=got_revisions)
  else:
    # If we're not on recipes, tell annotator about our got_revisions.
    emit_properties(got_revisions)

  thr = upload_telemetry(
      active=active,
      builder=builder,
      conversion_warnings=warnings,
      did_run=True,
      gclient_output=gclient_output,
      git_solutions=git_slns,
      got_revision=got_revisions,
      master=master,
      patch_root=options.patch_root,
      prefix='end',
      run_id=run_id,
      slave=slave,
      solutions=specs['solutions'],
      specs=options.specs,
      unix_time=time.time(),
  )
  all_threads.append(thr)

  # Sort of wait for all telemetry threads to finish.
  for thr in all_threads:
    thr.join(5)


if __name__ == '__main__':
  sys.exit(main())
