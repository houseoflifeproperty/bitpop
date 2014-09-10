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
             metadata=None, **kwargs):
    args = [] if args is None else args[:]
    args += self._generate_metadata_args(metadata)
    full_dest = 'gs://%s/%s' % (bucket, dest)
    cmd = ['cp'] + args + [source, full_dest]
    name = kwargs.pop('name', 'upload')

    result = self(cmd, name, **kwargs)

    if link_name:
      result.presentation.links[link_name] = (
        'https://storage.cloud.google.com/%s/%s' % (bucket, dest)
      )

  def download(self, bucket, source, dest, args=None, **kwargs):
    args = [] if args is None else args[:]
    full_source = 'gs://%s/%s' % (bucket, source)
    cmd = ['cp'] + args + [full_source, dest]
    name = kwargs.pop('name', 'download')
    return self(cmd, name, **kwargs)

  def download_url(self, url, dest, args=None, **kwargs):
    args = args or []
    url = url.replace('https://storage.cloud.google.com/', 'gs://')
    cmd = ['cp'] + args + [url, dest]
    name = kwargs.pop('name', 'download')
    self(cmd, name, **kwargs)

  def copy(self, source_bucket, source, dest_bucket, dest, args=None,
           link_name='gsutil.copy', metadata=None, **kwargs):
    args = args or []
    args += self._generate_metadata_args(metadata)
    full_source = 'gs://%s/%s' % (source_bucket, source)
    full_dest = 'gs://%s/%s' % (dest_bucket, dest)
    cmd = ['cp'] + args + [full_source, full_dest]
    name = kwargs.pop('name', 'copy')

    result = self(cmd, name, **kwargs)

    if link_name:
      result.presentation.links[link_name] = (
        'https://storage.cloud.google.com/%s/%s' % (dest_bucket, dest)
      )

  def _generate_metadata_args(self, metadata):
    result = []
    if metadata:
      for k, v in sorted(metadata.iteritems(), key=lambda (k, _): k):
        field = self._get_metadata_field(k)
        param = (field) if v is None else ('%s:%s' % (field, v))
        result += ['-h', param]
    return result

  @staticmethod
  def _get_metadata_field(name, provider_prefix=None):
    """Returns: (str) the metadata field to use with Google Storage

    The Google Storage specification for metadata can be found at:
    https://developers.google.com/storage/docs/gsutil/addlhelp/WorkingWithObjectMetadata
    """
    # Already contains custom provider prefix
    if name.lower().startswith('x-'):
      return name

    # See if it's innately supported by Google Storage
    if name in (
        'Cache-Control',
        'Content-Disposition',
        'Content-Encoding',
        'Content-Language',
        'Content-MD5',
        'Content-Type',
    ):
      return name

    # Add provider prefix
    if not provider_prefix:
      provider_prefix = 'x-goog-meta'
    return '%s-%s' % (provider_prefix, name)
