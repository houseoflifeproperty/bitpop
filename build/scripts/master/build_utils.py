# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Mixed bag of anything."""

import re
import urllib

from twisted.python import log
from twisted.web import html
import buildbot
from buildbot.status.web.base import build_get_class
from buildbot.status.web.base import IBox
from buildbot.steps import trigger
from buildbot.steps.transfer import FileUpload
from buildbot.status.builder import SUCCESS


def getAllRevisions(build):
  """Helper method to extract all revisions associated to a build.

  Args:
    build: The build we want to extract the revisions of.

  Returns:
    A list of revision numbers.
  """
  source_stamp = build.getSourceStamp()
  if source_stamp and source_stamp.changes:
    return [change.revision for change in source_stamp.changes]
  try:
    return [build.getProperty('got_revision')]
  except KeyError:
    pass
  try:
    return [build.getProperty('revision')]
  except KeyError:
    pass


def getLatestRevision(build, git_repo=None):
  """Helper method to extract the latest revision associated to a build.

  Args:
    build: The build we want to extract the latest revision of.
    git_repo: The GitHelper object associated with build's respository.
        If passed, the VCS is assumed to be Git.

  Returns:
    The latest revision of that build, or None, if none.
  """
  revisions = getAllRevisions(build)
  if not revisions:
    return None

  if git_repo:
    with_numbers = zip(revisions, git_repo.number(*revisions))
    return max(with_numbers, lambda t: t[1])[0][0]
  else:
    return max(revisions)


def SplitPath(projects, path):
  """Common method to split SVN path into branch and filename sections.

  Since we have multiple projects, we announce project name as a branch
  so that schedulers can be configured to kick off builds based on project
  names.

  Args:
    projects: array containing modules we are interested in. It should
      be mapping to first directory of the change file.
    path: Base SVN path we will be polling.

  More details can be found at:
    http://buildbot.net/repos/release/docs/buildbot.html#SVNPoller.
  """
  pieces = path.split('/')
  if pieces[0] in projects:
    # announce project name as a branch
    branch = pieces.pop(0)
    return (branch, '/'.join(pieces))
  # not in projects, ignore
  return None


def GetStepsByName(build_status, step_names):
  steps = []
  for step in build_status.getSteps():
    if step.getName() in step_names:
      steps.append(step)
  return steps


# Extracted from
# http://src.chromium.org/svn/trunk/tools/buildbot/master.chromium/public_html/buildbot.css
DEFAULT_STYLES = {
  'BuildStep': '',
  'start': ('color: #666666; background-color: #fffc6c;'
            'border-color: #C5C56D;'),
  'success': ('color: #FFFFFF; background-color: #8fdf5f; '
              'border-color: #4F8530;'),
  'failure': ('color: #FFFFFF; background-color: #e98080; '
              'border-color: #A77272;'),
  'warnings': ('color: #FFFFFF; background-color: #ffc343; '
               'border-color: #C29D46;'),
  'exception': ('color: #FFFFFF; background-color: #e0b0ff; '
                'border-color: #ACA0B3;'),
  'offline': ('color: #FFFFFF; background-color: #e0b0ff; '
              'border-color: #ACA0B3;'),
}

def EmailableBuildTable(build_status, waterfall_url, styles=None):
  """Convert a build_status into a html table that can be sent by email.
  That means the CSS style must be inline."""

  if int(buildbot.version.split('.')[1]) > 7:
    return EmailableBuildTable_bb8(build_status, waterfall_url, styles)

  class DummyObject(object):
    prepath = None

  def GenBox(item):
    """Generates a box for one build step."""
    # Fix the url root.
    box_text = IBox(item).getBox(request).td(align='center').replace(
                   'href="builders/',
                   'href="' + waterfall_url + 'builders/')
    # Convert CSS classes to inline style.
    match = re.search(r"class=\"([^\"]*)\"", box_text)
    if match:
      css_class_text = match.group(1)
      css_classes = css_class_text.split()
      not_found = [c for c in css_classes if c not in styles]
      css_classes = [c for c in css_classes if c in styles]
      if len(not_found):
        log.msg('CSS classes couldn\'t be converted in inline style in '
                'email: %s' % str(not_found))
      inline_styles = ' '.join([styles[c] for c in css_classes])
      box_text = box_text.replace('class="%s"' % css_class_text,
                                  'style="%s"' % inline_styles)
    else:
      log.msg('Couldn\'t find the class attribute')
    return '<tr>%s</tr>\n' % box_text

  styles = styles or DEFAULT_STYLES
  request = DummyObject()

  # With a hack to fix the url root.
  build_boxes = [GenBox(build_status)]
  build_boxes.extend([GenBox(step) for step in build_status.getSteps()
                      if step.isStarted() and step.getText()])
  table_content = ''.join(build_boxes)
  return (('<table style="border-spacing: 1px 1px; font-weight: bold; '
           'padding: 3px 0px 3px 0px; text-align: center; font-size: 10px; '
           'font-family: Verdana, Cursor; ">\n') +
          table_content +
          '</table>\n')


def EmailableBuildTable_bb8(build_status, waterfall_url, styles=None,
                            step_names=None):
  """Uses new web reporting API in buildbot8."""

  styles = styles or DEFAULT_STYLES

  def GenBuildBox(buildstatus):
    """Generates a box for one build."""
    class_ = build_get_class(buildstatus)
    style = ''
    if class_ and class_ in styles:
      style = styles[class_]
    reason = html.escape(buildstatus.getReason())
    url = '%sbuilders/%s/builds/%d' % (
        waterfall_url,
        urllib.quote(buildstatus.getBuilder().getName(), safe=''),
        buildstatus.getNumber())
    fmt = ('<tr><td style="%s"><a title="Reason: %s" href="%s">'
           'Build %d'
           '</a></td></tr>')
    return fmt % (style, reason, url, buildstatus.getNumber())

  def GenStepBox(stepstatus):
    """Generates a box for one step."""
    class_ = build_get_class(stepstatus)
    style = ''
    if class_ and class_ in styles:
      style = styles[class_]
    stepname = stepstatus.getName()
    text = stepstatus.getText() or []
    text = text[:]
    base_url = '%sbuilders/%s/builds/%d/steps' % (
        waterfall_url,
        urllib.quote(stepstatus.getBuild().getBuilder().getName(), safe=''),
        stepstatus.getBuild().getNumber())
    for steplog in stepstatus.getLogs():
      name = steplog.getName()
      log.msg('name = %s' % name)
      url = '%s/%s/logs/%s' % (
          base_url,
          urllib.quote(stepname, safe=''),
          urllib.quote(name))
      text.append('<a href="%s">%s</a>' % (url, html.escape(name)))
    for name, target in stepstatus.getURLs().iteritems():
      text.append('<a href="%s">%s</a>' % (target, html.escape(name)))
    fmt = '<tr><td style="%s">%s</td></tr>'
    return fmt % (style, '<br/>'.join(text))

  build_boxes = [GenBuildBox(build_status)]
  if step_names:
    steps = GetStepsByName(build_status, step_names)
  else:
    steps = [step for step in build_status.getSteps()
             if step.isStarted() and step.getText()]
  build_boxes.extend(
      [GenStepBox(step) for step in steps if not step.isHidden()])
  table_content = ''.join(build_boxes)
  return (('<table style="border-spacing: 1px 1px; font-weight: bold; '
           'padding: 3px 0px 3px 0px; text-align: center; font-size: 10px; '
           'font-family: Verdana, Cursor; ">\n') +
          table_content +
          '</table>\n')


class FakeBuild(object):
  """Fake build object which spits back a canned set of properties.

  Used to allow digestion of all steps from a set of factories.
  """

  def __init__(self, properties):
    self.properties = properties

  def getProperty(self, key):
    return self.properties[key]

  def getProperties(self):
    return self

  def asDict(self):
    # The dictionary returned from a Properties object is in the form:
    #   {'name': (value, 'source')}
    ret = {}
    for k, v in self.properties.iteritems():
      ret[k] = (v, 'FakeBuild')
    return ret

  def render(self, words):
    # pylint: disable=R0201
    return words


def ExtractFactoriesSteps(factories):
  """Extract a dictionary mapping factory names to all steps (minus triggers).

  Arguments:
    factories: a list of pairs of buildbot (name, factory) pairs.
  Returns:
    A dictionary mapping factory names to steps.
  """
  builder_steps = {}
  for f in factories:
    name = f[0]
    steps = []
    for s in f[1].steps:
      # BuildFactory.steps is a list of pairs of BuildStep + constructor args.
      # Invoke the constructor (with the supplied args) for each step.
      nstep = s[0](**s[1])
      nstep.build = FakeBuild({'got_revision': '???'})
      # Skip triggers and FileUpload steps.
      if (nstep.__class__ == trigger.Trigger
          or nstep.__class__ == FileUpload):
        continue
      step_name = nstep.getText('', SUCCESS)[0]
      steps.append(step_name)
    builder_steps[name] = steps

  return builder_steps

def AllFactoriesSteps(factories):
  """Extract a list of all unique step names.

  Arguments:
    factories: a list of pairs of buildbot (name, factory) pairs.
  Returns:
    A list of unique step names.
  """
  builder_steps = ExtractFactoriesSteps(factories)
  # For each value (build step name) under each factory name, pull out that
  # element. ['factory1_step1', 'factory1_step2', 'factory2_step1' ... ]
  all_steps = [item for sublist in builder_steps.values() for item in sublist]
  # Eliminate duplicates.
  return list(set(all_steps))
