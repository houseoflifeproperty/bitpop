import urllib

from buildbot.status import builder
from buildbot.status.web.base import HtmlResource

HEAD = """
    <script type="text/javascript" src="%(path)s/mochikit/MochiKit.js"></script>
    <script type="text/javascript" src="%(path)s/plotkit/Base.js"></script>
    <script type="text/javascript" src="%(path)s/plotkit/Layout.js"></script>
    <script type="text/javascript" src="%(path)s/plotkit/Canvas.js"></script>
    <script type="text/javascript" src="%(path)s/plotkit/SweetCanvas.js"></script>
"""

def DisplayGraph(name, layout, width, height, color, data_variable, options):
    data = """
       <div><canvas id="canvas%s" height="%d" width="%d"></canvas></div>
        <script>
            var options%s = {
                "colorScheme": PlotKit.Base.palette(PlotKit.Base.baseColors()[%d]),
                %s
            }

            function draw%s() {
                var layout = new PlotKit.Layout("%s", options%s);
                layout.addDataset("data", %s);
                layout.evaluate();
                var canvas = MochiKit.DOM.getElement("canvas%s");
                var plotter = new PlotKit.SweetCanvasRenderer(canvas, layout, options%s);
                plotter.render();
            }

            MochiKit.DOM.addLoadEvent(draw%s);
        </script>
    """ % (name, height, width, name, color, options, name, layout, name, data_variable, name, name, name)

    return data


class StatsBuilderStatusResource(HtmlResource):
    def __init__(self, builder_status):
        HtmlResource.__init__(self)
        self.builder_status = builder_status

    def getBuilderVariables(self, builderObj):
        # 1. build time over 300 builds or average 5 weeks
        # 2. pie chart, success failures
        # 3. pie chart, which steps fails the most
        # 4. 1 graph per step showing last 300 builds timing, or average 5 weeks.
        # click on a graph makes it go bigger.
        buildTimes = []
        stepTimes = {}
        numberOfSuccess = 0
        numberOfFailures = 0
        failingSteps = {}
        slowestStep = 0

        build = builderObj.getBuild(-1) or builderObj.getBuild(-2)

        numberOfBuilds = 0
        while build and numberOfBuilds < 300:
            if build.isFinished():
                if build.getResults() == builder.SUCCESS or build.getResults() == builder.WARNINGS:
                    (start, end) = build.getTimes()
                    buildTimes.insert(0, end-start)
                    numberOfSuccess += 1
                else:
                    numberOfFailures += 1
                numberOfBuilds += 1

                for step in build.getSteps():
                    if not stepTimes.get(step.getName()):
                       stepTimes[step.getName()] = []
                    if not failingSteps.get(step.getName()):
                        failingSteps[step.getName()] = 0

                    (result, string) = step.getResults()
                    if result == builder.SUCCESS or result == builder.WARNINGS:
                        (start, end) = step.getTimes()
                        if end-start > slowestStep:
                            slowestStep = end-start
                        stepTimes[step.getName()].insert(0, end-start)
                    if result == builder.FAILURE:
                        failingSteps[step.getName()] += 1

            build = build.getPreviousBuild()

        buildId = 0
        buildTimesString = ""
        for buildTime in buildTimes:
            buildTimesString += "[%d, %f], " % (buildId, float(buildTime) / 60.0)
            buildId += 1

        buildId = 0
        failingStepsString = ""
        failingStepsLabel = ""
        for failingStepName in failingSteps:
            failingStepsString += "[%d, %d], " % (buildId, failingSteps[failingStepName])
            failingStepsLabel += "{v:%d, label:\"%s\"}," % (buildId, failingStepName)
            buildId += 1

        data = """
            var buildTimes = [%s];
            var failingSteps = [%s];
            var failingStepsLabel = [%s];
            var ratioSuccessFailures = [[0, %d], [1, %d]];
        """ % (buildTimesString, failingStepsString, failingStepsLabel, numberOfSuccess, numberOfFailures)

        stepsToIgnore = []
        for stepTimesBuilder in stepTimes:
            stepTimeString = ""
            stepId = 0
            over30secs = False
            for stepTime in stepTimes[stepTimesBuilder]:
                if stepTime > 30:
                    over30secs = True
                stepTimeString += "[%d, %.2f], " % (stepId, float(stepTime) / 60.0)
                stepId += 1
            if over30secs:
                data += """
                    var stepTimes%s = [%s];
                """ % (stepTimesBuilder.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(":", ""), stepTimeString)
            else:
                stepsToIgnore.append(stepTimesBuilder)

        for step in stepsToIgnore:
            stepTimes.pop(step)

        return (data, stepTimes, slowestStep)

    def head(self, request):
        return HEAD % {'path': '..'}

    def body(self, req):
        (variables, steps, slowestStep) = self.getBuilderVariables(self.builder_status)

        data = "<script type='text/javascript'>"
        data += variables
        data += "</script>"

        data += "<center>"
        data += "<h1> %s </h1><br>" % self.builder_status.getName()
        data += "<h2> Cycle time - Trend </h2>"
        cycleTimeOptions = """
            "drawXAxis": false,
        """
        data += DisplayGraph("cycleTimeBar", "line", 1200, 300, 0, "buildTimes", cycleTimeOptions)

        data += "<table><tr><td><h2>Ratio Success/Failures</h2><br>"
        ratioSuccessFailureOptions = """
            "xTicks": [{v:0, label:"Success"}, {v:1, label:"Failures"}],
        """
        data += DisplayGraph("ratioSuccessFailurePie", "pie", 570, 300, 4, "ratioSuccessFailures", ratioSuccessFailureOptions)

        data += "</td><td><h2>Failures by steps</h2><br>"
        stepsFailureOptions = """
            "xTicks": failingStepsLabel,
        """

        data += DisplayGraph("stepFailuresPie", "pie", 570, 300, 1, "failingSteps", stepsFailureOptions)
        data += "</td></tr></table>"

        slowestStep = (slowestStep / 60) + 1
        yTicks = ""
        for i in range(slowestStep + 1):
          yTicks += "{v:%d, label:'%d'}," % (i, i)

        stepsTimeOptions = """
            "drawXAxis": false,
            "yAxis": [0.00, %d.00],
            "yTicks": [%s],
        """ % (slowestStep, yTicks)

        data += "<table><tr>"
        stepId = 0
        for stepName in steps:
            if stepId % 3 == 0 and stepId != 0:
                data += "</tr><tr>"
            stepId += 1

            fixedName = stepName.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(":", "")
            graphName = "stepsTime%sLine" % fixedName

            data += "<td><h3>Cycle time: %s</h3><br>" % stepName
            variableName = "stepTimes%s" % fixedName
            color = 0
            if fixedName == "compile":
                color = 2
            if fixedName == "gclient":
                color = 5
            data += DisplayGraph(graphName, "line", 400, 300, color, variableName, stepsTimeOptions)
            data += "</td>"

        data += "</tr></table></center>"
        return data

class StatsStatusResource(HtmlResource):
    def __init__(self, allowForce=True, css=None):
        HtmlResource.__init__(self)

        self.status = None
        self.control = None
        self.changemaster = None
        self.allowForce = allowForce
        self.css = css

    def getTitle(self, request):
        status = self.getStatus(request)
        if hasattr(status, 'getTitle'):
          title = status.getTitle()
        else:
          title = status.getProjectName()
        if title:
            return "BuildBot: %s" % title
        else:
            return "BuildBot"

    def getChangemaster(self, request):
        return request.site.buildbot_service.parent.change_svc

    def head(self, request):
        return HEAD % {'path': '.'}

    def getMainVariables(self, status):
        averageTime = ""
        ratioFailures = ""
        nameMapping = ""

        builderNames = status.getBuilderNames()[:]
        builderId = 0
        for builderName in builderNames:
            if builderName == "Win Target Builds" or builderName == "Linux Target Builds":
              continue
            builderObj = status.getBuilder(builderName)
            build = builderObj.getBuild(-1) or builderObj.getBuild(-2)
            numberOfBuilds = 0
            numberOfSeconds = 0
            numberOfFailures = 0
            numberOfSuccess = 0
            while build and numberOfBuilds < 50:
                if build.isFinished():
                    if build.getResults() == builder.SUCCESS or build.getResults() == builder.WARNINGS:
                        (start, end) = build.getTimes()
                        numberOfSeconds += (end - start)
                        numberOfSuccess += 1
                    else:
                        numberOfFailures += 1
                    numberOfBuilds += 1
                build = build.getPreviousBuild()

            if numberOfSuccess:
                averageTime += "[%d, %f]," % (builderId, float(numberOfSeconds) / float(numberOfSuccess) / 60.0)
            else:
                averageTime += "[%d, 0.0]," % builderId

            if numberOfFailures:
                ratioFailures += "[%d, %f]," % (builderId, float(numberOfFailures) / float(numberOfBuilds) * 100.0)
            else:
                ratioFailures += "[%d, 0.00]," % builderId

            nameMapping += "{v:%d, label:A({href:\"./stats/%s\", text:\"aaa\"}, \"%s\")}," % (builderId,
                                                                                              urllib.quote(builderName),
                                                                                              builderName)
            builderId += 1

        data = """
            var averageTime = [%s];
            var ratioFailures = [%s];
            var nameMapping = [%s];
        """ % (averageTime, ratioFailures, nameMapping)

        return data

    def getChild(self, path, req):
        return StatsBuilderStatusResource(self.getStatus(req).getBuilder(path))

    def body(self, request):
        # and the data we want to render
        status = self.getStatus(request)

        # Get all revisions we can find.
        source = self.getChangemaster(request)

        data = "<script>"
        data += self.getMainVariables(status)
        data += "</script>"

        averageTimeOptions = """
            "xTicks": nameMapping,
            "barOrientation": "horizontal",
            "padding": {left: 200, right:5, top: 5, bottom: 10}
        """

        ratioFailuresOptions = """
            "yAxis": [0.00, 100.00],
            "yTicks": [{v:0, label:"0"},{v:10, label:"10"},{v:20, label:"20"},
                       {v:30, label:"30"},{v:40, label:"40"},{v:50, label:"50"},
                       {v:60, label:"60"},{v:70, label:"70"},{v:80, label:"80"},
                       {v:90, label:"90"},{v:100, label:"100"}],
            "drawYAxis": false,
            "barOrientation": "horizontal",
            "padding": {left: 2, right:20, top: 5, bottom: 10}
        """

        height = len(status.getBuilderNames()) * 15
        data += "<center><table><td width=200></td><td width=500><h2> Average time to cycle </h2></td><td width=500><h2> Percentage of failures </h2></td></table><table><tr><td>"
        data += DisplayGraph("averageTimeBar", "bar", 700, height, 0, "averageTime", averageTimeOptions)
        data += "</td><td>"
        data += DisplayGraph("ratioFailuresBar", "bar", 500, height, 1, "ratioFailures", ratioFailuresOptions)
        data += "</td></tr></table></center>"

        return data
