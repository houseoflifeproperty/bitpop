# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re

import buildbot
from buildbot import interfaces, util
from buildbot.buildslave import BuildSlave
from buildbot.status import mail
from buildbot.status.builder import BuildStatus
from buildbot.status.status_push import HttpStatusPush
from twisted.python import log
from zope.interface import implements

from master.autoreboot_buildslave import AutoRebootBuildSlave
from buildbot.status.web.authz import Authz
from buildbot.status.web.baseweb import WebStatus

import master.chromium_status_bb8 as chromium_status

from common import chromium_utils
import config


def HackMaxTime(maxTime=8*60*60):
  """Set maxTime default value to 8 hours. This function must be called before
  adding steps."""
  from buildbot.process.buildstep import RemoteShellCommand
  assert RemoteShellCommand.__init__.func_defaults == (None, 1, 1, 1200, None,
      {}, 'slave-config', True)
  RemoteShellCommand.__init__.im_func.func_defaults = (None, 1, 1, 1200,
      maxTime, {}, 'slave-config', True)
  assert RemoteShellCommand.__init__.func_defaults == (None, 1, 1, 1200,
      maxTime, {}, 'slave-config', True)

HackMaxTime()


def HackBuildStatus():
  """Adds a property to Build named 'blamelist' with the blamelist."""
  old_setBlamelist = BuildStatus.setBlamelist
  def setBlamelist(self, blamelist):
    self.setProperty('blamelist', blamelist, 'Build')
    old_setBlamelist(self, blamelist)
  BuildStatus.setBlamelist = setBlamelist

HackBuildStatus()


class InvalidConfig(Exception):
  """Used by VerifySetup."""
  pass


def AutoSetupSlaves(builders, bot_password, max_builds=1,
                    missing_recipients=None, missing_timeout=300):
  """Helper function for master.cfg to quickly setup c['slaves']."""
  slaves_dict = {}
  for builder in builders:
    auto_reboot = builder.get('auto_reboot', True)
    notify_on_missing = builder.get('notify_on_missing', False)
    slavenames = builder.get('slavenames', [])[:]
    if 'slavename' in builder:
      slavenames.append(builder['slavename'])
    for slavename in slavenames:
      slaves_dict[slavename] = (auto_reboot, notify_on_missing)
  slaves = []
  for (slavename, (auto_reboot, notify_on_missing)) in slaves_dict.iteritems():
    if auto_reboot:
      slave_class = AutoRebootBuildSlave
    else:
      slave_class = BuildSlave

    if notify_on_missing:
      slaves.append(slave_class(slavename, bot_password, max_builds=max_builds,
                                notify_on_missing=missing_recipients,
                                missing_timeout=missing_timeout))
    else:
      slaves.append(slave_class(slavename, bot_password, max_builds=max_builds))
  return slaves


def VerifySetup(c, slaves):
  """Verify all the available slaves in the slave configuration are used and
  that all the builders have a slave."""
  # Extract the list of slaves associated to a builder and make sure each
  # builder has its slaves connected.
  # Verify each builder has at least one slave.
  builders_slaves = set()
  slaves_name = [s.slavename for s in c['slaves']]
  for b in c['builders']:
    builder_slaves = set()
    slavename = b.get('slavename')
    if slavename:
      builder_slaves.add(slavename)
    slavenames = b.get('slavenames', [])
    for s in slavenames:
      builder_slaves.add(s)
    if not slavename and not slavenames:
      raise InvalidConfig('Builder %s has no slave' % b['name'])
    # Now test.
    for s in builder_slaves:
      if not s in slaves_name:
        raise InvalidConfig('Builder %s using undefined slave %s' % (b['name'],
                                                                     s))
    builders_slaves |= builder_slaves
  if len(builders_slaves) != len(slaves_name):
    raise InvalidConfig('Same slave defined multiple times')

  # Make sure each slave has their builder.
  builders_name = [b['name'] for b in c['builders']]
  for s in c['slaves']:
    name = s.slavename
    if not name in builders_slaves:
      raise InvalidConfig('Slave %s not associated with any builder' % name)

  # Make sure every defined slave is used.
  for s in slaves.GetSlaves():
    name = chromium_utils.EntryToSlaveName(s)
    if not name in slaves_name:
      raise InvalidConfig('Slave %s defined in your slaves_list is not '
                          'referenced at all' % name)
    builders = s.get('builder', [])
    if not isinstance(builders, (list, tuple)):
      builders = [builders]
    testers = s.get('testers', [])
    if not isinstance(testers, (list, tuple)):
      testers = [testers]
    builders.extend(testers)
    for b in builders:
      if not b in builders_name:
        raise InvalidConfig('Slave %s uses non-existent builder %s' % (name,
                                                                       b))

class UsersAreEmails(util.ComparableMixin):
  """Chromium already uses email addresses as user name so no need to do
  anything.
  """
  # Class has no __init__ method
  # pylint: disable=W0232
  implements(interfaces.IEmailLookup)

  @staticmethod
  def getAddress(name):
    return name


class FilterDomain(util.ComparableMixin):
  """Similar to buildbot.mail.Domain but permits filtering out people we don't
  want to spam.

  Also loads default values from chromium_config."""
  implements(interfaces.IEmailLookup)

  compare_attrs = ['domain', 'permitted_domains']


  def __init__(self, domain=None, permitted_domains=None):
    """domain is the default domain to append when only the naked username is
    available.
    permitted_domains is a whitelist of domains that emails will be sent to."""
    # pylint: disable=E1101
    self.domain = domain or config.Master.master_domain
    self.permitted_domains = (permitted_domains or
                              config.Master.permitted_domains)

  def getAddress(self, name):
    """If name is already an email address, pass it through."""
    result = name
    if self.domain and not '@' in result:
      result = '%s@%s' % (name, self.domain)
    if not '@' in result:
      log.msg('Invalid blame email address "%s"' % result)
      return None
    if self.permitted_domains:
      for p in self.permitted_domains:
        if result.endswith(p):
          return result
      return None
    return result


def CreateWebStatus(port, templates=None, tagComparator=None, **kwargs):
  webstatus = WebStatus(port, **kwargs)
  if templates:
    # Manipulate the search path for jinja templates
    # pylint: disable=F0401
    import jinja2
    # pylint: disable=E1101
    old_loaders = webstatus.templates.loader.loaders
    # pylint: disable=E1101
    new_loaders = old_loaders[:1]
    new_loaders.extend([jinja2.FileSystemLoader(x) for x in templates])
    new_loaders.extend(old_loaders[1:])
    webstatus.templates.loader.loaders = new_loaders
  chromium_status.SetupChromiumPages(webstatus, tagComparator)
  return webstatus


def GetMastername():
  # Get the master name from the directory name. Remove leading "master.".
  return re.sub('^master.', '', os.path.basename(os.getcwd()))


def AutoSetupMaster(c, active_master, mail_notifier=False,
                    mail_notifier_mode=None,
                    public_html=None, templates=None,
                    order_console_by_time=False,
                    tagComparator=None,
                    enable_http_status_push=False):
  """Add common settings and status services to a master.

  If you wonder what all these mean, PLEASE go check the official doc!
  http://buildbot.net/buildbot/docs/0.7.12/ or
  http://buildbot.net/buildbot/docs/latest/full.html

  - Default number of logs to keep
  - WebStatus and MailNotifier
  - Debug ssh port. Just add a file named .manhole beside master.cfg and
    simply include one line containing 'port = 10101', then you can
    'ssh localhost -p' and you can access your buildbot from the inside."""
  c['slavePortnum'] = active_master.slave_port
  c['projectName'] = active_master.project_name
  c['projectURL'] = config.Master.project_url

  c['properties'] = {'mastername': GetMastername()}
  if 'buildbotURL' in c:
    c['properties']['buildbotURL'] = c['buildbotURL']

  # 'status' is a list of Status Targets. The results of each build will be
  # pushed to these targets. buildbot/status/*.py has a variety to choose from,
  # including web pages, email senders, and IRC bots.
  c.setdefault('status', [])
  if mail_notifier:
    # pylint: disable=E1101
    c['status'].append(mail.MailNotifier(
        fromaddr=active_master.from_address,
        mode=mail_notifier_mode or 'problem',
        relayhost=config.Master.smtp,
        lookup=FilterDomain()))

  # For all production masters, notify our health-monitoring webapp.
  if enable_http_status_push:
    blacklist = (
        'buildETAUpdate',
        #'buildFinished',
        'buildStarted',
        'buildedRemoved',
        'builderAdded',
        'builderChangedState',
        'buildsetSubmitted',
        'changeAdded',
        'logFinished',
        'logStarted',
        'requestCancelled',
        'requestSubmitted',
        'slaveConnected',
        'slaveDisconnected',
        'stepETAUpdate',
        'stepFinished',
        'stepStarted',
        'stepText2Changed',
        'stepTextChanged',
    )
    c['status'].append(HttpStatusPush(
        'https://chromium-build-logs.appspot.com/status_receiver',
        blackList=blacklist))

  kwargs = {}
  if public_html:
    kwargs['public_html'] = public_html
  kwargs['order_console_by_time'] = order_console_by_time
  # In Buildbot 0.8.4p1, pass provide_feeds as a list to signal what extra
  # services Buildbot should be able to provide over HTTP.
  if buildbot.version == '0.8.4p1':
    kwargs['provide_feeds'] = ['json']
  if active_master.master_port:
    # Actions we want to allow must be explicitly listed here.
    # Deliberately omitted are:
    #   - gracefulShutdown
    #   - cleanShutdown
    authz = Authz(forceBuild=True,
                  forceAllBuilds=True,
                  pingBuilder=True,
                  stopBuild=True,
                  stopAllBuilds=True,
                  cancelPendingBuild=True)
    c['status'].append(CreateWebStatus(active_master.master_port,
                                       tagComparator=tagComparator,
                                       authz=authz,
                                       num_events_max=3000,
                                       templates=templates,
                                       **kwargs))
  if active_master.master_port_alt:
    c['status'].append(CreateWebStatus(active_master.master_port_alt,
                                       tagComparator=tagComparator,
                                       num_events_max=3000,
                                       templates=templates,
                                       **kwargs))

  # Keep last build logs, the default is too low.
  c['buildHorizon'] = 1000
  c['logHorizon'] = 500
  # Must be at least 2x the number of slaves.
  c['eventHorizon'] = 200
  # Tune cache sizes to speed up web UI.
  c['caches'] = {
    'BuildRequests': 1000,
    'Changes': 1000,
    'SourceStamps': 1000,
    'chdicts': 1000,
    'ssdicts': 1000,
  }
  # Must be at least 2x the number of on-going builds.
  c['buildCacheSize'] = 200

  # See http://buildbot.net/buildbot/docs/0.8.1/Debug-Options.html for more
  # details.
  if os.path.isfile('.manhole'):
    try:
      from buildbot import manhole
    except ImportError:
      log.msg('Using manhole has an implicit dependency on Crypto.Cipher. You '
              'need to install it manually:\n'
              '  sudo apt-get install python-crypto\n'
              'on ubuntu or run:\n'
              '  pip install --user pycrypto\n'
              '  pip install --user pyasn1\n')
      raise

    # If 'port' is defined, it uses the same valid keys as the current user.
    values = {}
    execfile('.manhole', values)
    if 'debugPassword' in values:
      c['debugPassword'] = values['debugPassword']
    interface = 'tcp:%s:interface=127.0.0.1' % values.get('port', 0)
    if 'port' in values and 'user' in values and 'password' in values:
      c['manhole'] = manhole.PasswordManhole(interface, values['user'],
                                            values['password'])
    elif 'port' in values:
      c['manhole'] = manhole.AuthorizedKeysManhole(interface,
          os.path.expanduser("~/.ssh/authorized_keys"))

def DumpSetup(c, important=None, filename='config.current.txt'):
  """Writes a flattened version of the setup to a text file.
     Some interesting classes are exploded with their variables
     exposed,  by default the BuildFactories and Schedulers.
     Newlines and indentation are sprinkled through the representation,
     to make the output more easily broken up and groked with grep or diff.

     Note that the heuristics of how to find classes that you want expanded
     is not too hard to fool, but it seems to handle it usefully for
     normal master configs.

     c         The config: same as the rest of the utilities here.
     important Array of classes to also expand.
     filename  Where to write this ill-defined but useful information.
  """
  from buildbot.schedulers.base import BaseScheduler
  from buildbot.process.factory import BuildFactory

  def hacky_repr(obj, name, indent, important):
    def hacky_repr_class(obj, indent, subdent, important):
      r = '%s {\n' % obj.__class__.__name__
      for (n, v) in vars(obj).iteritems():
        if not n.startswith('_'):
          r += hacky_repr(v, "%s: " % n, indent + subdent, important) + ',\n'
      r += indent + '}'
      return r

    if isinstance(obj, list):
      r = '[' + ', '.join(hacky_repr(o, '', '', important) for o in obj) + ']'
    elif isinstance(obj, tuple):
      r = '(' + ', '.join(hacky_repr(o, '', '', important) for o in obj) + ')'
    else:
      r = repr(obj)
      if not isinstance(obj, basestring):
        r = re.sub(' at 0x[0-9a-fA-F]*>', '>', r)

    subdent = '  '
    if any(isinstance(obj, c) for c in important):
      r = hacky_repr_class(obj, indent, subdent, important)
    elif len(r) > max(30, 76-len(indent)-len(name)) and \
        not isinstance(obj, basestring):
      if isinstance(obj, list):
        r = '[\n'
        for o in obj:
          r += hacky_repr(o, '', indent + subdent, important) + ',\n'
        r += indent + ']'
      elif isinstance(obj, tuple):
        r = '(\n'
        for o in obj:
          r += hacky_repr(o, '', indent + subdent, important) + ',\n'
        r += indent + ')'
      elif isinstance(obj, dict):
        r = '{\n'
        for (n, v) in sorted(obj.iteritems(), key=lambda x: x[0]):
          if not n.startswith('_'):
            r += hacky_repr(v, "'%s': " % n, indent + subdent, important)
            r += ',\n'
        r += indent + '}'
    return "%s%s%s" % (indent, name, r)

  important = (important or []) + [BaseScheduler, BuildFactory]

  with open(filename, 'w') as f:
    print >> f, hacky_repr(c, 'config = ', '', important)


def Partition(item_tuples, num_partitions):
  """Divides |item_tuples| into |num_partitions| separate lists.

  Perfect partitioning is NP hard, this is a "good enough" estimate.

  Args:
    item_tuples: tuple in the format (weight, item_name).
    num_partitions: int number of partitions to generate.

  Returns:
    A list of lists of item_names with as close to equal weight as possible.
  """
  assert num_partitions > 0, 'Must pass a positive number of partitions'
  assert len(item_tuples) >= num_partitions, 'Need more items than partitions'
  partitions = [[] for _ in xrange(num_partitions)]
  def GetLowestSumPartition():
    return sorted(partitions, key=lambda x: sum([i[0] for i in x]))[0]
  for item in sorted(item_tuples, reverse=True):
    GetLowestSumPartition().append(item)
  return sorted([sorted([name for _, name in p]) for p in partitions])
