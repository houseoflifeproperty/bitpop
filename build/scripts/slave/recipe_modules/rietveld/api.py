# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import urlparse

from slave import recipe_api

class RietveldApi(recipe_api.RecipeApi):
  def calculate_issue_root(self):
    root = self.m.properties.get('root', '')
    # FIXME: Rietveld passes the blink path as src/third_party/WebKit
    #        so we have to strip the src bit off before passing to
    #        api.checkout_path. :(
    if root.startswith('src'):
      root = root[3:].lstrip('/')
    # Make remaining slashes platform independent.
    return self.m.path.join(*root.split('/'))

  def apply_issue(self, *root_pieces, **kwargs):
    """Call apply_issue from depot_tools.

    Args:
      root_pieces (strings): location where to run apply_issue, relative to the
        checkout root.
      authentication (string or None): authentication scheme to use. Can be None
        or 'oauth2'. See also apply_issue.py --help (-E and --no-auth options.)
    """
    # TODO(pgervais): replace *root_pieces by a single Path object.
    authentication = kwargs.get('authentication', None)
    rietveld_url = self.m.properties['rietveld']
    issue_number = self.m.properties['issue']

    if authentication == 'oauth2':
      step_result = self.m.python(
        'apply_issue',
        self.m.path['depot_tools'].join('apply_issue.py'), [
          '-r', self.m.path['checkout'].join(*root_pieces),
          '-i', issue_number,
          '-p', self.m.properties['patchset'],
          '-s', rietveld_url,
          '-E', self.m.path['build'].join('site_config',
                                          '.rietveld_client_email'),
          '-k', self.m.path['build'].join('site_config',
                                          '.rietveld_secret_key')
          ],
        )

    else:
      step_result = self.m.python(
        'apply_issue',
        self.m.path['depot_tools'].join('apply_issue.py'), [
          '-r', self.m.path['checkout'].join(*root_pieces),
          '-i', issue_number,
          '-p', self.m.properties['patchset'],
          '-s', rietveld_url,
          '--no-auth'],
        )
    step_result.presentation.links['Applied issue %s' % issue_number] = (
      urlparse.urljoin(rietveld_url, str(issue_number)))

