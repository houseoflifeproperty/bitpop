# -*- python -*-
# ex: set syntax=python:

# Copyright (c) 2010 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Chrome Buildbot slave configuration

import os
import socket
import sys

from twisted.application import service
from buildslave.bot import BuildSlave

# Register the commands.
from slave import chromium_commands
# Load default settings.
import config

# config.Master.active_master and config.Master.active_slavename
# are set in run_slave.py
ActiveMaster = config.Master.active_master
slavename = config.Master.active_slavename

# Slave properties:
password = config.Master.GetBotPassword()
host = None
port = None
basedir = None
keepalive = 300
usepty = 0
umask = None


print 'Using slave name %s' % slavename

if password is None:
    print >> sys.stderr, '*** No password configured in %s.' % repr(__file__)
    sys.exit(1)

if host is None:
    host = os.environ.get('TESTING_MASTER_HOST', ActiveMaster.master_host)
print 'Using master host %s' % host

if port is None:
    port = ActiveMaster.slave_port
print 'Using master port %s' % port

if basedir is None:
    basedir = os.path.dirname(os.path.abspath(__file__))


application = service.Application('buildslave')
s = BuildSlave(host, port, slavename, password, basedir, keepalive, usepty,
               umask=umask, allow_shutdown='file')
s.setServiceParent(application)
