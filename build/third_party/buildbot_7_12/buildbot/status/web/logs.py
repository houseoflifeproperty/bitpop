
from zope.interface import implements
from twisted.python import components
from twisted.spread import pb
from twisted.web import html, server
from twisted.web.resource import Resource
from twisted.web.error import NoResource

from buildbot import interfaces
from buildbot.status import builder
from buildbot.status.web.base import IHTMLLog, HtmlResource
from buildbot.status.web.ansi2html import Ansi2HTML


textlog_stylesheet = """
<style type="text/css">
 div.data {
  font-family: "Courier New", courier, monotype;
 }
 span.stdout {
  font-family: "Courier New", courier, monotype;
 }
 span.stderr {
  font-family: "Courier New", courier, monotype;
  color: red;
 }
 span.header {
  font-family: "Courier New", courier, monotype;
  color: blue;
 }
</style>
"""

class ChunkConsumer:
    implements(interfaces.IStatusLogConsumer)

    def __init__(self, original, textlog):
        self.original = original
        self.textlog = textlog
    def registerProducer(self, producer, streaming):
        self.producer = producer
        self.original.registerProducer(producer, streaming)
    def unregisterProducer(self):
        self.original.unregisterProducer()
    def writeChunk(self, chunk):
        formatted = self.textlog.content([chunk])
        try:
            if isinstance(formatted, unicode):
                formatted = formatted.encode('utf-8')
            self.original.write(formatted)
        except pb.DeadReferenceError:
            self.producing.stopProducing()
    def finish(self):
        self.textlog.finished()


# /builders/$builder/builds/$buildnum/steps/$stepname/logs/$logname
class TextLog(Resource):
    # a new instance of this Resource is created for each client who views
    # it, so we can afford to track the request in the Resource.
    implements(IHTMLLog)

    printAs = "html"
    subscribed = False

    def __init__(self, original):
        Resource.__init__(self)
        self.original = original

    def getChild(self, path, req):
        if path == "ansi":
            self.ansiParser = Ansi2HTML()

        if path == "text" or path == "ansi":
            self.printAs = path
            return self

        return HtmlResource.getChild(self, path, req)

    def htmlHeader(self, request):
        title = "Log File contents"
        data = "<html>\n<head><title>" + title + "</title>\n"
        data += textlog_stylesheet
        data += "</head>\n"
        data += "<body vlink=\"#800080\">\n"
        texturl = request.childLink("text")
        data += '<a href="%s">(view as text)</a><br />\n' % texturl
        ansiurl = request.childLink("ansi")
        data += '<a href="%s">(view as ansi)</a><br />\n' % ansiurl
        data += "<pre>\n"
        return data

    def content(self, entries):
        spanfmt = '<span class="%s">%s</span>'
        data = ""
        for type, entry in entries:
            if type >= len(builder.ChunkTypes) or type < 0:
                # non-std channel, don't display
                continue
            if self.printAs == "text":
                if type != builder.HEADER:
                    data += entry
            elif self.printAs == "ansi":
                if type != builder.HEADER:
                    data += self.ansiParser.parseBlock(entry)
            else:
                data += spanfmt % (builder.ChunkTypes[type],
                                   html.escape(entry))
        return data

    def htmlFooter(self):
        data = "</pre>\n"
        data += "</body></html>\n"
        return data

    def render_HEAD(self, request):
        if self.printAs == "text":
            request.setHeader("content-type", "text/plain")
        else:
            request.setHeader("content-type", "text/html")

        # vague approximation, ignores markup
        request.setHeader("content-length", self.original.length)
        return ''

    def render_GET(self, req):
        self.req = req

        if self.printAs == "text":
            req.setHeader("content-type", "text/plain")
        else:
            req.setHeader("content-type", "text/html")

        if self.printAs == "html":
            req.write(self.htmlHeader(req))
        if self.printAs == "ansi":
            req.write(self.ansiParser.printHtmlHeader("Log File Contents"))
            req.write(self.ansiParser.printHeader())

        self.original.subscribeConsumer(ChunkConsumer(req, self))
        return server.NOT_DONE_YET

    def finished(self):
        if not self.req:
            return
        try:
            if self.printAs == "html":
                self.req.write(self.htmlFooter())
            if self.printAs == "ansi":
                self.req.write(self.ansiParser.printFooter())
                self.req.write(self.ansiParser.printHtmlFooter())
            self.req.finish()
        except pb.DeadReferenceError:
            pass
        # break the cycle, the Request's .notifications list includes the
        # Deferred (from req.notifyFinish) that's pointing at us.
        self.req = None

components.registerAdapter(TextLog, interfaces.IStatusLog, IHTMLLog)


class HTMLLog(Resource):
    implements(IHTMLLog)

    def __init__(self, original):
        Resource.__init__(self)
        self.original = original

    def render(self, request):
        request.setHeader("content-type", "text/html")
        return self.original.html

components.registerAdapter(HTMLLog, builder.HTMLLogFile, IHTMLLog)


class LogsResource(HtmlResource):
    addSlash = True

    def __init__(self, step_status):
        HtmlResource.__init__(self)
        self.step_status = step_status

    def getChild(self, path, req):
        for log in self.step_status.getLogs():
            if path == log.getName():
                if log.hasContents():
                    return IHTMLLog(interfaces.IStatusLog(log))
                return NoResource("Empty Log '%s'" % path)
        return HtmlResource.getChild(self, path, req)
