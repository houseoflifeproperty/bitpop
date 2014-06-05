# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A buildbot command for running and interpreting the build_archive.sh script.
"""

from buildbot.steps import shell
from buildbot.process import buildstep

class ScriptObserver(buildstep.LogLineObserver):
  """This class knows how to understand archive_build/coverage/
  layout_test_results.py test output."""

  def __init__(self):
    buildstep.LogLineObserver.__init__(self)
    self.last_change = ''
    self.build_number = ''
    self.build_name = ''

  def outLineReceived(self, line):
    """This is called once with each line of the test log."""
    if line.startswith('last change: '):
      self.last_change = line.split(' ')[2]
    elif line.startswith('build number: '):
      self.build_number = line.split(' ')[2]
    elif line.startswith('build name: '):
      self.build_name = line.split(' ',  2)[2]

class ArchiveCommand(shell.ShellCommand):
  """Buildbot command that knows how to display archive_build/coverage/
  layout_test_results.py test output."""

  # 'parms' is used in buildbot.steps.shell.ShellCommand.__init__ to separate
  # kwargs that should be passed to the BuildStep constructor from kwargs
  # that should be passed to the RemoteShellCommand constructor.  It's
  # harmless to omit 'parms' in buildbot7, but in buildbot8, extra kwargs
  # that aren't listed in 'parms' will cause the RemoteShellCommand
  # constructor to throw an exception.
  parms = ['base_url',
           'link_text',
           'more_link_url',
           'more_link_text',
           'name',
           'index_suffix',
           'include_last_change']

  def __init__(self, **kwargs):
    shell.ShellCommand.__init__(self, **kwargs)
    self.script_observer = ScriptObserver()
    self.base_url = kwargs['base_url']
    self.link_text = kwargs['link_text']
    self.addLogObserver('stdio', self.script_observer)
    self.index_suffix = kwargs.get('index_suffix', '')
    self.include_last_change = kwargs.get('include_last_change', True)
    self.more_link_url = kwargs.get('more_link_url', '')
    self.more_link_text = kwargs.get('more_link_text', '')

  def createSummary(self, log):
    if (self.base_url and self.link_text):
      url_prefix = self.base_url % {
          'build_name': self.script_observer.build_name}

      if self.script_observer.build_number:
        url_prefix += '/' + self.script_observer.build_number
      if self.include_last_change:
        url_prefix += '/' + self.script_observer.last_change
      self.addURL(self.link_text, url_prefix + '/' + self.index_suffix)
      if self.more_link_url and self.more_link_text:
        self.addURL(self.more_link_text, url_prefix + '/' + self.more_link_url)
