# -*- test-case-name: buildbot.test.test_status_push -*-

import re
import os

try:
    import simplejson as json
except ImportError:
    import json

from twisted.internet import defer, reactor
from twisted.python import log
from twisted.trial import unittest
from twisted.web import server, resource
from twisted.web.error import Error
from zope.interface import implements, Interface

from buildbot import master
from buildbot.changes import changes
from buildbot.slave import bot
from buildbot.status import status_push
from buildbot.status.persistent_queue import IQueue, ReadFile
from buildbot.test.runutils import RunMixin
from buildbot.test.status_push_server import EventsHandler


config_base = """
from buildbot.process import factory
from buildbot.buildslave import BuildSlave
from buildbot.config import BuilderConfig
from buildbot.scheduler import Scheduler
from buildbot.status.persistent_queue import IQueue
from buildbot.status.status_push import StatusPush, HttpStatusPush
from buildbot.steps import dummy

BuildmasterConfig = c = {}

c['slaves'] = [BuildSlave('bot1', 'sekrit')]
c['schedulers'] = [Scheduler('dummy', None, 120, ['dummy'])]

f1 = factory.QuickBuildFactory('fakerep', 'cvsmodule', configure=None)
c['builders'] = [
    BuilderConfig(name='dummy', slavename='bot1', factory=f1,
        builddir='quickdir', slavebuilddir='slavequickdir'),
]
c['slavePortnum'] = 0
c['projectUrl'] = 'example.com/yay'
c['projectName'] = 'Pouet'
c['buildbotURL'] = 'build.example.com/yo'

def doNothing(self):
    # Creates self.fake_queue to store the object.
    assert IQueue.providedBy(self.queue)
    if not hasattr(self, 'fake_queue'):
        self.fake_queue = []
    items = self.queue.popChunk()
    self.fake_queue.extend(items)
    self.queueNextServerPush()
"""

config_no_http = (config_base + """
c['status'] = [StatusPush(serverPushCb=doNothing)]
""")

config_http = (config_base + """
c['status'] = [HttpStatusPush('http://127.0.0.1:<PORT>/receiver')]
""")

config_no_http_no_filter = (config_base + """
c['status'] = [StatusPush(serverPushCb=doNothing, filter=False)]
""")

config_http_no_filter = (config_base + """
c['status'] = [HttpStatusPush('http://127.0.0.1:<PORT>/receiver', filter=False)]
""")

EXPECTED = [
    {
        'event': 'builderAdded',
        'payload': {
            'builder': {
                "category": None,
                "cachedBuilds": [],
                "basedir": "quickdir",
                "pendingBuilds": [],
                "state": "offline",
                "slaves": ["bot1"],
                "currentBuilds": []
            },
            'builderName': 'dummy',
        }
    },
    {
        "event": "builderChangedState",
        "payload": {
            'state': 'offline',
            'builderName': 'dummy'
        }
    },
    {
        "event": "start",
        "payload": {
            'status': {
                "buildbotURL": 'build.example.com/yo',
                "projectName": 'Pouet',
                'projectURL': None,
            }
        }
    },
    {
        'event': 'slaveConnected',
        'payload': {
            'slave': {
                'access_uri': None,
                'admin': 'one',
                'connected': True,
                'host': None,
                'name': 'bot1',
                'runningBuilds': [],
                'version': '0.7.12'
            }
        }
    },
    {
        'event': 'builderChangedState',
        'payload': {
            'state': 'idle',
            'builderName': 'dummy'
        },
    },
    {
        "event": "changeAdded",
        "payload": {
            'change': {
                "category": None,
                "files": ["Makefile", "foo/bar.c"],
                "who": "bob",
                "when": "n0w",
                "number": 1,
                "comments": "changed stuff",
                "branch": None,
                "revlink": "",
                "properties": [],
                "revision": None
            }
        }
    },
    {
        'event': 'requestSubmitted',
        'payload': {
            'request': {
                'builderName': 'test_builder',
                'builds': [],
                'source': {
                    'branch': None,
                    'changes': [],
                    'hasPatch': False,
                    'revision': None
                },
                'submittedAt': 'yesterday',
            }
        }
    },
    {
        'event': 'builderChangedState',
        'payload': {
            'state': 'building',
            'builderName': 'dummy'
        }
    },
    {
        'event': 'buildStarted',
        'payload': {
            'build': {
                'blame': [],
                'builderName': 'dummy',
                'changes': [],
                'currentStep': None,
                'eta': None,
                'number': 0,
                'properties': [
                    ['branch', None, 'Build'],
                    ['buildername', 'dummy', 'Build'],
                    ['buildnumber', 0, 'Build'],
                    ['revision', None, 'Build'],
                    ['slavename', 'bot1', 'BuildSlave']
                ],
                'reason': 'forced build',
                'requests': [
                    {
                        'builderName': 'test_builder',
                        'builds': [],
                        'source': {
                            'branch': None,
                            'changes': [],
                            'hasPatch': False,
                            'revision': None
                        },
                        'submittedAt': 'yesterday'
                    }
                ],
                'results': None,
                'slave': 'bot1',
                'sourceStamp': {
                    'branch': None,
                    'hasPatch': False,
                    'changes': [],
                    'revision': None
                },
                'steps': [
                    {
                        'eta': None,
                        'expectations': [],
                        'isFinished': False,
                        'isStarted': False,
                        'name': 'cvs',
                        'results': [[None, []], []],
                        'statistics': {},
                        'text': ['updating'],
                        'times': [None, None],
                        'urls': {}
                    },
                    {
                        'eta': None,
                        'expectations': [],
                        'isFinished': False,
                        'isStarted': False,
                        'name': 'compile',
                        'results': [[None, []], []],
                        'statistics': {},
                        'text': ['compiling'],
                        'times': [None, None],
                        'urls': {}
                    },
                    {
                        'eta': None,
                        'expectations': [],
                        'isFinished': False,
                        'isStarted': False,
                        'name': 'test',
                        'results': [[None, []], []],
                        'statistics': {},
                        'text': ['testing'],
                        'times': [None, None],
                        'urls': {}
                    }
                ],
                'text': [],
                'times': [123, None]
            }
        }
    },
    {
        'event': 'stepStarted',
        'payload': {
            'step': {
                'eta': None,
                'expectations': [],
                'isFinished': False,
                'isStarted': True,
                'name': 'cvs',
                'results': [[None, []], []],
                'statistics': {},
                'text': ['updating'],
                'times': [123, None],
                'urls': {}
            },
            'properties': [
                ['branch', None, 'Build'],
                ['buildername', 'dummy', 'Build'],
                ['buildnumber', 0, 'Build'],
                ['revision', None, 'Build'],
                ['slavename', 'bot1', 'BuildSlave']
            ],
        }
    },
    {
        'event': 'stepFinished',
        'payload': {
            'step': {
                'eta': None,
                'expectations': [],
                'isFinished': True,
                'isStarted': True,
                'name': 'cvs',
                'results': [2, ['cvs']],
                'statistics': {},
                'text': ['update', 'failed'],
                'times': [123, None],
                'urls': {}
            },
            'properties': [
                ['branch', None, 'Build'],
                ['buildername', 'dummy', 'Build'],
                ['buildnumber', 0, 'Build'],
                ['revision', None, 'Build'],
                ['slavename', 'bot1', 'BuildSlave']
            ],
        }
    },
    {
        'event': 'buildFinished',
        'payload': {
            'build': {
                'blame': [],
                'builderName': 'dummy',
                'changes': [],
                'currentStep': None,
                'eta': None,
                'number': 0,
                'properties': [
                    ['branch', None, 'Build'],
                    ['buildername', 'dummy', 'Build'],
                    ['buildnumber', 0, 'Build'],
                    ['revision', None, 'Build'],
                    ['slavename', 'bot1', 'BuildSlave']
                ],
                'reason': 'forced build',
                'requests': [
                    {
                        'builderName': 'test_builder',
                        'builds': [0],
                        'source': {
                            'branch': None,
                            'hasPatch': False,
                            'changes': [],
                            'revision': None},
                        'submittedAt': 'yesterday'
                    }
                ],
                'results': 2,
                'slave': 'bot1',
                'sourceStamp': {
                    'branch': None,
                    'changes': [],
                    'hasPatch': False,
                    'revision': None
                },
                'steps': [
                    {
                        'eta': None,
                        'expectations': [],
                        'isFinished': True,
                        'isStarted': True,
                        'name': 'cvs',
                        'results': [2, ['cvs']],
                        'statistics': {},
                        'text': ['update', 'failed'],
                        'times': [345, None],
                        'urls': {}
                    },
                    {
                        'eta': None,
                        'expectations': [],
                        'isFinished': False,
                        'isStarted': False,
                        'name': 'compile',
                        'results': [[None, []], []],
                        'statistics': {},
                        'text': ['compiling'],
                        'times': [345, None],
                        'urls': {}
                    },
                    {
                        'eta': None,
                        'expectations': [],
                        'isFinished': False,
                        'isStarted': False,
                        'name': 'test',
                        'results': [[None, []], []],
                        'statistics': {},
                        'text': ['testing'],
                        'times': [345, None],
                        'urls': {}
                    }
                ],
                'text': ['failed', 'cvs'],
                'times': [123, None]
            },
        }
    },
    {
        'event': 'builderChangedState',
        'payload': {
            'state': 'idle',
            'builderName': 'dummy'
        }
    },
    {
        'event': 'slaveDisconnected',
        'payload': {
            'slavename': 'bot1'
        }
    },
    {
        'event': 'builderChangedState',
        'payload': {
            'state': 'offline',
            'builderName': 'dummy',
        }
    },
    {
        "event": "shutdown",
        "payload": {
            'status': {
                "buildbotURL": 'build.example.com/yo',
                "projectName": 'Pouet',
                'projectURL': None,
            }
        }
    },
]

EXPECTED_SHORT = [
    {
        'event': 'builderAdded',
        'payload': {
            'builder': {
                "basedir": "quickdir",
                "state": "offline",
                "slaves": ["bot1"],
            },
            'builderName': 'dummy',
        }
    },
    {
        "event": "builderChangedState",
        "payload": {
            'state': 'offline',
            'builderName': 'dummy'
        }
    },
    {
        "event": "start",
        "payload": {
            'status': {
                "buildbotURL": 'build.example.com/yo',
                "projectName": 'Pouet',
            }
        }
    },
    {
        'event': 'slaveConnected',
        'payload': {
            'slave': {
                'admin': 'one',
                'connected': True,
                'name': 'bot1',
                'version': '0.7.12'
            }
        }
    },
    {
        'event': 'builderChangedState',
        'payload': {
            'state': 'idle',
            'builderName': 'dummy'
        },
    },
    {
        "event": "changeAdded",
        "payload": {
            'change': {
                "files": ["Makefile", "foo/bar.c"],
                "who": "bob",
                "when": "n0w",
                "number": 1,
                "comments": "changed stuff",
            }
        }
    },
    {
        'event': 'requestSubmitted',
        'payload': {
            'request': {
                'builderName': 'test_builder',
                'submittedAt': 'yesterday',
            }
        }
    },
    {
        'event': 'builderChangedState',
        'payload': {
            'state': 'building',
            'builderName': 'dummy'
        }
    },
    {
        'event': 'buildStarted',
        'payload': {
            'build': {
                'builderName': 'dummy',
                'properties': [
                    ['branch', None, 'Build'],
                    ['buildername', 'dummy', 'Build'],
                    ['buildnumber', 0, 'Build'],
                    ['revision', None, 'Build'],
                    ['slavename', 'bot1', 'BuildSlave']
                ],
                'reason': 'forced build',
                'requests': [
                    {
                        'builderName': 'test_builder',
                        'submittedAt': 'yesterday'
                    }
                ],
                'slave': 'bot1',
                'steps': [
                    {
                        'name': 'cvs',
                        'text': ['updating'],
                    },
                    {
                        'name': 'compile',
                        'text': ['compiling'],
                    },
                    {
                        'name': 'test',
                        'text': ['testing'],
                    }
                ],
                'times': [123, None]
            }
        }
    },
    {
        'event': 'stepStarted',
        'payload': {
            'step': {
                'isStarted': True,
                'name': 'cvs',
                'text': ['updating'],
                'times': [123, None],
            },
            'properties': [
                ['branch', None, 'Build'],
                ['buildername', 'dummy', 'Build'],
                ['buildnumber', 0, 'Build'],
                ['revision', None, 'Build'],
                ['slavename', 'bot1', 'BuildSlave']
            ],
        }
    },
    {
        'event': 'stepFinished',
        'payload': {
            'step': {
                'isFinished': True,
                'isStarted': True,
                'name': 'cvs',
                'results': [2, ['cvs']],
                'text': ['update', 'failed'],
                'times': [123, None],
            },
            'properties': [
                ['branch', None, 'Build'],
                ['buildername', 'dummy', 'Build'],
                ['buildnumber', 0, 'Build'],
                ['revision', None, 'Build'],
                ['slavename', 'bot1', 'BuildSlave']
            ],
        }
    },
    {
        'event': 'buildFinished',
        'payload': {
            'build': {
                'builderName': 'dummy',
                'properties': [
                    ['branch', None, 'Build'],
                    ['buildername', 'dummy', 'Build'],
                    ['buildnumber', 0, 'Build'],
                    ['revision', None, 'Build'],
                    ['slavename', 'bot1', 'BuildSlave']
                ],
                'reason': 'forced build',
                'requests': [
                    {
                        'builderName': 'test_builder',
                        'submittedAt': 'yesterday'
                    }
                ],
                'results': 2,
                'slave': 'bot1',
                'steps': [
                    {
                        'isFinished': True,
                        'isStarted': True,
                        'name': 'cvs',
                        'results': [2, ['cvs']],
                        'text': ['update', 'failed'],
                        'times': [345, None],
                    },
                    {
                        'name': 'compile',
                        'text': ['compiling'],
                    },
                    {
                        'name': 'test',
                        'text': ['testing'],
                    }
                ],
                'text': ['failed', 'cvs'],
                'times': [123, None]
            },
        }
    },
    {
        'event': 'builderChangedState',
        'payload': {
            'state': 'idle',
            'builderName': 'dummy'
        }
    },
    {
        'event': 'slaveDisconnected',
        'payload': {
            'slavename': 'bot1'
        }
    },
    {
        'event': 'builderChangedState',
        'payload': {
            'state': 'offline',
            'builderName': 'dummy',
        }
    },
    {
        "event": "shutdown",
        "payload": {
            'status': {
                "buildbotURL": 'build.example.com/yo',
                "projectName": 'Pouet',
            }
        }
    },
]

class Receiver(resource.Resource):
    isLeaf = True
    def __init__(self):
        self.packets = []

    def render_POST(self, request):
        for packet in request.args['packets']:
            data = json.loads(packet)
            for p in data:
                self.packets.append(p)
        return "ok"


class StatusPushTestBase(RunMixin, unittest.TestCase):
    def getStatusPush(self):
        for i in self.master.services:
            if isinstance(i, status_push.StatusPush):
                return i

    def init(self, config):
        # The master.
        self.master.loadConfig(config)
        self.master.readConfig = True
        self.assertTrue(self.getStatusPush())
        self.master.startService()

    def tearDown(self):
        """Similar to RunMixin.tearDown but skip over if self.master is None
        since we do test stopService."""
        log.msg("doing tearDown")
        if self.master:
            d = self.shutdownAllSlaves()
            d.addCallback(self._tearDown_1)
            d.addCallback(self._tearDown_2)
            return d
        else:
            return defer.succeed(None)

    def verifyItems(self, items, expected):
        def QuickFix(item, *args):
            """Strips time-specific values.

            None means an array.
            Anything else is a key to a dict."""
            args = list(args)
            value = args.pop()

            def Loop(item, value, *args):
                args = list(args)
                arg = args.pop(0)
                if isinstance(item, list) and arg is None:
                    for i in item:
                        Loop(i, value, *args)
                elif isinstance(item, dict):
                    if len(args) == 0 and arg in item:
                        item[arg] = value
                    elif arg in item:
                        Loop(item[arg], value, *args)

            Loop(item, value, *args)

        def FindItem(items, event, *args):
            for i in items:
                if i['event'] == event:
                    QuickFix(i, *args)

        # Cleanup time dependent values. It'd be nice to mock datetime instead.
        for i in range(len(items)):
            item = items[i]
            del item['started']
            del item['timestamp']
            self.assertEqual('Pouet', item.pop('project'))
            self.assertEqual(i + 1, item.pop('id'))

        FindItem(items, 'changeAdded', 'payload', 'change', 'when',
                'n0w')
        FindItem(items, 'requestSubmitted', 'payload', 'request',
                'submittedAt', 'yesterday')

        FindItem(items, 'buildStarted', 'payload', 'build', 'requests',
                None, 'submittedAt', 'yesterday')
        FindItem(items, 'stepStarted', 'payload', 'build', 'requests',
                None, 'submittedAt', 'yesterday')
        FindItem(items, 'stepFinished', 'payload', 'build', 'requests',
                None, 'submittedAt', 'yesterday')
        FindItem(items, 'buildFinished', 'payload', 'build', 'requests',
                None, 'submittedAt', 'yesterday')

        FindItem(items, 'buildStarted', 'payload', 'build', 'times',
                [123, None])
        FindItem(items, 'stepStarted', 'payload', 'build', 'times',
                [123, None])
        FindItem(items, 'stepStarted', 'payload', 'step', 'times',
                [123, None])
        FindItem(items, 'stepFinished', 'payload', 'build', 'times',
                [123, None])
        FindItem(items, 'stepFinished', 'payload', 'step', 'times',
                [123, None])
        FindItem(items, 'buildFinished', 'payload', 'build', 'times',
                [123, None])

        FindItem(items, 'stepStarted', 'payload', 'build',
                'current_step', 'times', [234, None])
        FindItem(items, 'stepFinished', 'payload', 'build',
                'current_step', 'times', [234, None])
        FindItem(items, 'buildFinished', 'payload', 'build',
                'current_step', 'times', [234, None])

        FindItem(items, 'stepStarted', 'payload', 'build', 'steps', None,
                'times', [345, None])
        FindItem(items, 'stepFinished', 'payload', 'build', 'steps',
                None, 'times', [345, None])
        FindItem(items, 'buildFinished', 'payload', 'build', 'steps',
                None, 'times', [345, None])

        for i in range(min(len(expected), len(items))):
            self.assertEqual(expected[i], items[i], str(i))
        self.assertEqual(len(expected), len(items))


class StatusPushTest(StatusPushTestBase):
    def testNotFiltered(self):
        self.expected = EXPECTED
        self.init(config_no_http_no_filter)
        d = self.connectSlave()
        d.addCallbacks(self._testPhase1)
        return d

    def testFiltered(self):
        self.expected = EXPECTED_SHORT
        self.init(config_no_http)
        d = self.connectSlave()
        d.addCallbacks(self._testPhase1)
        return d

    def _testPhase1(self, d):
        # Now the slave is connected, trigger a change.
        cm = self.master.change_svc
        c = changes.Change("bob", ["Makefile", "foo/bar.c"], "changed stuff")
        cm.addChange(c)
        d = self.requestBuild("dummy")
        d.addCallback(self._testPhase2)
        return d

    def _testPhase2(self, d):
        d = self.shutdownAllSlaves()
        d.addCallback(lambda x: self.master.stopService())
        d.addCallback(self._testPhase3)
        return d

    def _testPhase3(self, d):
        def TupleToList(items):
            if isinstance(items, (list, tuple)):
                return [TupleToList(i) for i in items]
            if isinstance(items, dict):
                return dict([(k, TupleToList(v))
                             for (k, v) in items.iteritems()])
            else:
                return items
        self.assertEqual(0, self.getStatusPush().queue.nbItems())
        # Grabs fake_queue created in DoNothing().
        self.verifyItems(TupleToList(self.getStatusPush().fake_queue),
                         self.expected)
        self.master = None


class HttpStatusPushTest(StatusPushTestBase):
    def setUp(self):
        StatusPushTestBase.setUp(self)
        self.server = None

    def tearDown(self):
        StatusPushTestBase.tearDown(self)
        state_path = os.path.join(self.path, 'state')
        state = json.loads(ReadFile(state_path))
        del state['started']
        self.assertEqual({"last_id_pushed": 0, "next_id": 17, }, state)
        os.remove(state_path)
        self.assertEqual([], os.listdir(self.path))

    def testNotFiltered(self):
        self.expected = EXPECTED
        path = os.path.join(os.path.dirname(__file__), 'status_push_server.py')
        self.site = server.Site(Receiver())
        self.server = reactor.listenTCP(0, self.site)
        self.port = self.server.getHost().port
        self.init(config_http_no_filter.replace('<PORT>', str(self.port)))
        d = self.connectSlave()
        d.addCallbacks(self._testPhase1)
        return d

    def testFiltered(self):
        self.expected = EXPECTED_SHORT
        path = os.path.join(os.path.dirname(__file__), 'status_push_server.py')
        self.site = server.Site(Receiver())
        self.server = reactor.listenTCP(0, self.site)
        self.port = self.server.getHost().port
        self.init(config_http.replace('<PORT>', str(self.port)))
        d = self.connectSlave()
        d.addCallbacks(self._testPhase1)
        return d

    def _testPhase1(self, d):
        g = self.getStatusPush()
        self.path = g.path
        # Now the slave is connected, trigger a change.
        cm = self.master.change_svc
        c = changes.Change("bob", ["Makefile", "foo/bar.c"], "changed stuff")
        cm.addChange(c)
        d = self.requestBuild("dummy")
        d.addCallback(self._testPhase2)
        return d

    def _testPhase2(self, d):
        d = self.shutdownAllSlaves()
        d.addCallback(lambda x: self.master.stopService())
        d.addCallback(self._testPhase3)
        d.addCallback(lambda x: self.server.stopListening())
        return d

    def _testPhase3(self, d):
        g = self.getStatusPush()
        # Assert all the items were pushed.
        self.assertEqual(0, g.queue.nbItems())
        self.verifyItems(self.site.resource.packets, self.expected)
        self.master = None

# vim: set ts=4 sts=4 sw=4 et:
