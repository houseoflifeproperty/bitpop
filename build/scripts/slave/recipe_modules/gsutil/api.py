# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api
from slave import recipe_util

class GSUtilApi(recipe_api.RecipeApi):
  def __call__(self, cmd, name=None, use_retry_wrapper=True, **kwargs):
    """A step to run arbitrary gsutil commands.

    Note that this assumes that gsutil authentication environment variables
    (AWS_CREDENTIAL_FILE and BOTO_CONFIG) are already set, though if you want to
    set them to something else you can always do so using the env={} kwarg.

    Note also that gsutil does its own wildcard processing, so wildcards are
    valid in file-like portions of the cmd. See 'gsutil help wildcards'.

    Arguments:
      cmd: list of (string) arguments to pass to gsutil.
           Include gsutil-level options first (see 'gsutil help options').
      name: the (string) name of the step to use.
            Defaults to the first non-flag token in the cmd.
    """
    if not name:
      name = (t for t in cmd if not t.startswith('-')).next()
    full_name = 'gsutil ' + name

    gsutil_path = self.m.path['depot_tools'].join('third_party',
                                                  'gsutil',
                                                  'gsutil')
    cmd_prefix = []

    if use_retry_wrapper:
      # We pass the real gsutil_path to the wrapper so it doesn't have to do
      # brittle path logic.
      cmd_prefix = ['--', gsutil_path]
      gsutil_path = self.resource('gsutil_wrapper.py')

    return self.m.python(full_name, gsutil_path, cmd_prefix + cmd, **kwargs)

  def upload(self, source, bucket, dest, args=None, link_name='gsutil.upload',
             **kwargs):
    args = args or []
    full_dest = 'gs://%s/%s' % (bucket, dest)
    cmd = ['cp'] + args + [source, full_dest]
    name = kwargs.pop('name', 'upload')

    if link_name:
      @recipe_util.wrap_followup(kwargs)
      def inline_followup(step_result):
        step_result.presentation.links[link_name] = (
          'https://storage.cloud.google.com/%s/%s' % (bucket, dest)
        )

      kwargs['followup_fn'] = inline_followup

    return self(cmd, name, **kwargs)

  def download(self, bucket, source, dest, args=None, **kwargs):
    args = args or []
    full_source = 'gs://%s/%s' % (bucket, source)
    cmd = ['cp'] + args + [full_source, dest]
    name = kwargs.pop('name', 'download')
    return self(cmd, name, **kwargs)

  def download_url(self, url, dest, args=None, **kwargs):
    args = args or []
    url = url.replace('https://storage.cloud.google.com/', 'gs://')
    cmd = ['cp'] + args + [url, dest]
    name = kwargs.pop('name', 'download')
    return self(cmd, name, **kwargs)

  def copy(self, source_bucket, source, dest_bucket, dest, args=None,
           link_name='gsutil.copy', **kwargs):
    args = args or []
    full_source = 'gs://%s/%s' % (source_bucket, source)
    full_dest = 'gs://%s/%s' % (dest_bucket, dest)
    cmd = ['cp'] + args + [full_source, full_dest]
    name = kwargs.pop('name', 'copy')

    if link_name:
      @recipe_util.wrap_followup(kwargs)
      def inline_followup(step_result):
        step_result.presentation.links[link_name] = (
          'https://storage.cloud.google.com/%s/%s' % (dest_bucket, dest)
        )

      kwargs['followup_fn'] = inline_followup

    return self(cmd, name, **kwargs)
