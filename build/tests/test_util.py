#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import atexit
import os
import signal
import socket
import sys
import threading

from cStringIO import StringIO
from subprocess import check_call, Popen
from textwrap import dedent


def capture_terminal(f, *args, **kwargs):
  """Run f() with sys.stdout and sys.stderr reassigned to buffered pipes."""

  old_std = (sys.stdout, sys.stderr)
  (out_buf, err_buf) = (StringIO(), StringIO())
  (out_pipe, err_pipe) = (os.pipe(), os.pipe())
  def _thr_main(fd, buf):
    with os.fdopen(fd) as fh:
      buf.write(fh.read())
  (out_thread, err_thread) = (
      threading.Thread(target=_thr_main, args=(out_pipe[0], out_buf)),
      threading.Thread(target=_thr_main, args=(err_pipe[0], err_buf)))
  out_thread.start()
  err_thread.start()
  sys.stdout = os.fdopen(out_pipe[1], 'w')
  sys.stderr = os.fdopen(err_pipe[1], 'w')
  try:
    result = f(*args, **kwargs)
  except Exception as e:
    sys.excepthook(*sys.exc_info())
    result = e
  sys.stdout.close()
  sys.stderr.close()
  out_thread.join()
  err_thread.join()
  (sys.stdout, sys.stderr) = old_std
  return result, out_buf, err_buf


def find_free_port():
  """Find an avaible port on localhost."""
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.bind(('', 0))
  port = sock.getsockname()[1]
  sock.close()
  return port


class LocalGitServer(object):
  """A git server daemon running on localhost."""
  def __init__(self, root):
    self.root = root
    self.port = find_free_port()
    self.url = 'git://localhost:%s' % self.port
    self.devnull = open(os.devnull, 'w')
    os.makedirs(root)
    self.proc = Popen(
        ['git', 'daemon', '--export-all', '--reuseaddr', '--listen=localhost',
         '--port=%d' % self.port, '--base-path=%s' % root,  root],
        stdout=self.devnull, stderr=self.devnull)

  def stop(self):
    try:
      self.proc.terminate()
      self.devnull.close()
    except Exception:
      pass


class LocalSvnServer(object):
  """An svnserve daemon running on localhost."""
  def __init__(self, root):
    self.root = root
    self.pid_file = os.path.join(root, 'svnserve.pid')
    self.port = find_free_port()
    self.url = 'svn://localhost:%d/svn' % self.port
    self.devnull = open(os.devnull, 'w')
    os.makedirs(self.root)
    check_call(
        ['svnadmin', 'create', root], stdout=self.devnull, stderr=self.devnull)
    with open(os.path.join(root, 'conf', 'svnserve.conf'), 'w') as fh:
      fh.write(dedent('''\
          [general]
          anon-access = write
          '''))
    check_call(
        ['svnserve', '-d', '-r', self.root, '--listen-port=%d' % self.port,
         '--pid-file=%s' % self.pid_file],
        stdout=self.devnull, stderr=self.devnull)
    with open(self.pid_file) as fh:
      self.pid = int(fh.read().strip())
    atexit.register(self.stop)

  def stop(self):
    try:
      if self.pid:
        os.kill(self.pid, signal.SIGKILL)
        self.pid = None
      if self.devnull:
        self.devnull.close()
        self.devnull = None
    except Exception:
      pass
