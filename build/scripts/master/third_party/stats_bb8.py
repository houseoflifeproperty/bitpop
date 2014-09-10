import urllib

from buildbot.status import builder
from buildbot.status.web.base import HtmlResource

class StatsBuilderStatusResource(HtmlResource):
  def __init__(self, builder_status):
    HtmlResource.__init__(self)
    self.builder_status = builder_status

  def getBuilderVariables(self, cxt, maxBuilds):
    # 1. build time over <maxBuilds> builds
    # 2. pie chart, success failures
    # 3. pie chart, which steps fails the most
    # 4. 1 graph per step showing last <maxBuilds> builds
    # click on a graph makes it go bigger.
    buildTimes = []
    stepTimes = {}
    numberOfSuccess = 0
    numberOfFailures = 0
    failingSteps = {}

    for build in self.builder_status.generateFinishedBuilds(
        max_search=maxBuilds):
      buildNum = build.getNumber()
      if build.getResults() == builder.SUCCESS or \
         build.getResults() == builder.WARNINGS:
        (start, end) = build.getTimes()
        buildTimes.append((buildNum, float(end-start) / 60.0))
        numberOfSuccess += 1
      else:
        numberOfFailures += 1

      for step in build.getSteps():
        stepName = step.getName().translate(None, '- /[]{}():.,\'"%')
        stepTime = stepTimes.setdefault(stepName, [])
        failCount = failingSteps.setdefault(stepName, 0)
        (result, output) = step.getResults()
        if result == builder.SUCCESS or result == builder.WARNINGS:
          (start, end) = step.getTimes()
          elapsed = end - start
          stepTime.append((buildNum, elapsed))
        if result == builder.FAILURE:
          failingSteps[stepName] = failCount + 1

    # Put data in forward order
    buildTimes.reverse()
    map(list.reverse, stepTimes.values())

    slowest = reduce(
        max, [reduce(max, [y[1] for y in x], 0) for x in stepTimes.values()], 0)
    timeRange = slowest + 1
    yTicks = '[%s]' % ', '.join(["{v:%d}" % i for i in range(int(timeRange+1))])

    cxt['builder_status'] = self.builder_status
    cxt['buildTimes'] = buildTimes
    cxt['failingSteps'] = failingSteps
    cxt['stepTimes'] = stepTimes
    cxt['numberOfSuccess'] = numberOfSuccess
    cxt['numberOfFailures'] = numberOfFailures
    cxt['yTicks'] = yTicks
    cxt['timeRange'] = timeRange
    cxt['colorMap'] = { 'compile': 1, 'update': 1 };
    cxt['data_in_forward_order'] = '1'

  def content(self, request, cxt):
    maxBuilds = int(request.args.get(
        'max', [self.builder_status.buildCacheSize/2])[0])
    self.getBuilderVariables(cxt, maxBuilds)
    templates = request.site.buildbot_service.templates
    template = templates.get_template("builder_stats.html")
    return template.render(cxt)


class StatsStatusResource(HtmlResource):
  def __init__(self, allowForce=True, css=None):
    HtmlResource.__init__(self)

    self.status = None
    self.control = None
    self.changemaster = None
    self.allowForce = allowForce
    self.css = css

  def getMainVariables(self, status, cxt, maxBuilds=None):
    builderNames = []
    builderTimes = []
    builderFailures = []

    for builderName in status.getBuilderNames():
      builderNames.append(builderName)
      builderObj = status.getBuilder(builderName)
      if maxBuilds is None:
        builderMaxBuilds = builderObj.buildCacheSize/2
      else:
        builderMaxBuilds = maxBuilds

      goodCount = 0
      badCount = 0
      buildTimes = []

      for build in builderObj.generateFinishedBuilds(
          max_search=builderMaxBuilds):
        buildNum = build.getNumber()
        if (build.getResults() == builder.SUCCESS or
            build.getResults() == builder.WARNINGS):
          (start, end) = build.getTimes()
          buildTimes.append(end - start)
          goodCount += 1
        else:
          badCount += 1

      # Get the average time per build in minutes
      avg = float(sum(buildTimes)) / float(max(len(buildTimes), 1))
      builderTimes.append(avg / 60.0)

      # Get the proportion of failed builds.
      avg = float(badCount) / float(max(goodCount + badCount, 1))
      builderFailures.append(avg)

    cxt['builderNames'] = builderNames
    cxt['builderTimes'] = builderTimes
    cxt['builderFailures'] = builderFailures

  def content(self, request, cxt):
    try:
      maxBuilds = int(request.args.get('max')[0])
    except (TypeError, ValueError):
      maxBuilds = None
    self.getMainVariables(self.getStatus(request), cxt, maxBuilds=maxBuilds)
    templates = request.site.buildbot_service.templates
    template = templates.get_template('stats.html')
    return template.render(cxt)

  def getChild(self, path, req):
    return StatsBuilderStatusResource(self.getStatus(req).getBuilder(path))
