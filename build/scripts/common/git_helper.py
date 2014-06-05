# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Helper to enable some svn-like operations on git repositories.

There are two operations in particular that are easy to do in SVN but hard to do
in Git:
  * Get the contents of a file at a particular revision
  * Get the relative ordering of a set of commits

The first is difficult because Git (as a distributed system) doesn't provide
'svn cat'-like functionality. In order to get the contents of a file, you must
have all of the repository objects cloned locally.

The second is difficult because Git (with its emphasis on branch workflows)
doesn't provide sequential monotonically increasing revision numbers. In order
to get a (weak) ordering on a set of commits, we must compute generation numbers
from the repository root and then compare those.

This file provides a lightweight way to perform both of these actions. It
provides a class that encapsulates checking out the necessary repository to a
temporary directory, gleaning the reqested information from that repo, and
cleaning up after itself.

  from git_helper import GitHelper
  repo = GitHelper('https://path.to/my/repo.git')

  # get the contents of a readme, ten revisions ago.
  file = repo.show('docs/README.md', 'master~10')

  # get the generation numbers of any number of commits
  commits = ['deadbeef', 'feedbead']
  ordering = repo.number(*commits)
  sorted_commits = [pair[1] for pair in sorted(zip(ordering, commits))]

  # clean up
  repo.destroy()

For super lightweight operations, GitHelper can be used as a context manager
that cleans up after itself.

  with GitHelper('https://path.to/my/repo.git') as g:
    g.show('VERSION')

Commit ordering is implemented via depot_tools/git-number, by iannucci@.
"""


import logging
import os
import shutil
import subprocess
import tempfile


class GitHelper(object):
  """Helper class for some common lightweight Git operations."""

  def __init__(self, url):
    """Creates the GitHelper object, pointed at the repo.

    Args:
      url: The url at which the repository lives. If this is an
           http(s):// url, the repository will be cloned into
           a local temporary directory. If this is a file:// url,
           the GitHelper simply assumes the on-disk repo is already
           in place and does nothing.
    """
    self.url = url
    if self.url.startswith('file://'):
      self.tmpdir = False
      self.dir = os.path.abspath(self.url.replace('file://', ''))
    else:
      self.tmpdir = True
      self.dir = tempfile.mkdtemp(prefix='git-tmp')
      self._retry(3, ['clone', '--mirror', self.url, self.dir])

  def __enter__(self):
    """Method called upon entering this object as a context manager."""
    return self

  def __exit__(self):
    """Method called when the context is exited."""
    self.destroy()

  def destroy(self):
    """Deletes the tmpdir holding the git objects."""
    if self.tmpdir:
      shutil.rmtree(self.dir)

  def _run(self, cmd, **kwargs):
    """Runs a git command and returns its output."""
    kwargs.setdefault('cwd', self.dir)
    cmd = ['git'] + map(str, cmd)
    logging.debug('Running %s', ' '.join(repr(tok) for tok in cmd))
    out = subprocess.check_output(
        cmd, stderr=subprocess.STDOUT, **kwargs)
    return out

  def _retry(self, tries, cmd, **kwargs):
    """Retries a call to _run |tries| times.

    Purposefully doesn't wrap last call in try/except,
    to expose the exception to the calling code.
    """
    while tries > 1:
      try:
        out = self._run(cmd, **kwargs)
        return out
      except subprocess.CalledProcessError:
        logging.debug('Failed to run command, retrying.')
        tries -= 1
        continue
    out = self._run(cmd, **kwargs)
    return out

  def show(self, path, ref):
    cmd = ['show', '%s:%s' % (ref, path)]
    return self._run(cmd)

  def number(self, *refs):
    cmd = ['number'] + list(refs)
    out = self._run(cmd)
    return map(int, out.splitlines())
