# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.status import status_push

import urlparse


class TryServerHttpStatusPush(status_push.HttpStatusPush):
  """Status push used by try server.

  Rietveld listens to buildStarted and (step|build)Finished to know if a try
  job succeeeded or not.
  """
  def __init__(self, serverUrl, *args, **kwargs):
    # Appends the status listener to the base url.
    # TODO(csharp): Always add status_listener once all the configs are updated.
    if not serverUrl.endswith('status_listener'):
      serverUrl = urlparse.urljoin(serverUrl, 'status_listener')

    blackList = [
        'buildETAUpdate',
        #'buildFinished',
        #'buildStarted',
        'buildedRemoved',
        'builderAdded',
        'builderChangedState',
        'buildsetSubmitted',
        'changeAdded',
        'logFinished',
        'logStarted',
        'requestCancelled',
        'requestSubmitted',
        'shutdown',
        'slaveConnected',
        'slaveDisconnected',
        'start',
        'stepETAUpdate',
        #'stepFinished',
        'stepStarted',
        'stepText2Changed',
        'stepTextChanged',
    ]
    # Create the file with the password set into rietveld.
    pwd = open('.code_review_password').readline().strip()
    extra_post_params = { 'password': pwd }
    status_push.HttpStatusPush.__init__(
        self,
        *args,
        serverUrl=serverUrl,
        blackList=blackList,
        extra_post_params=extra_post_params,
        **kwargs)

  def setServiceParent(self, parent):
    """Adds the base_url property, it's not available to Rietveld otherwise."""
    self.extra_post_params['base_url'] = parent.buildbotURL
    status_push.HttpStatusPush.setServiceParent(self, parent)
