# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import base_flavor


"""Default flavor utils class, used for desktop builders."""


class DeviceDirs(object):
  def __init__(self,
               gm_actual_dir,
               gm_expected_dir,
               perf_data_dir,
               resource_dir,
               skimage_expected_dir,
               skimage_in_dir,
               skimage_out_dir,
               skp_dirs,
               skp_perf_dir,
               tmp_dir):
    self._gm_actual_dir = gm_actual_dir
    self._gm_expected_dir = gm_expected_dir
    self._perf_data_dir = perf_data_dir
    self._playback_actual_images_dir = skp_dirs.actual_images_dir
    self._playback_actual_summaries_dir = skp_dirs.actual_summaries_dir
    self._playback_expected_summaries_dir = skp_dirs.expected_summaries_dir
    self._resource_dir = resource_dir
    self._skimage_expected_dir = skimage_expected_dir
    self._skimage_in_dir = skimage_in_dir
    self._skimage_out_dir = skimage_out_dir
    self._skp_dir = skp_dirs.skp_dir()
    self._skp_perf_dir = skp_perf_dir
    self._tmp_dir = tmp_dir

  @property
  def gm_actual_dir(self):
    """Holds images and JSON summary written out by the 'gm' tool."""
    return self._gm_actual_dir

  @property
  def gm_expected_dir(self):
    """Holds expectations JSON summary read by the 'gm' tool."""
    return self._gm_expected_dir

  @property
  def perf_data_dir(self):
    return self._perf_data_dir

  @property
  def playback_actual_images_dir(self):
    """Holds image files written out by the 'render_pictures' tool."""
    return self._playback_actual_images_dir

  @property
  def playback_actual_summaries_dir(self):
    """Holds actual-result JSON summaries written by 'render_pictures' tool."""
    return self._playback_actual_summaries_dir

  @property
  def playback_expected_summaries_dir(self):
    """Holds expected-result JSON summaries read by 'render_pictures' tool."""
    return self._playback_expected_summaries_dir

  @property
  def resource_dir(self):
    return self._resource_dir

  @property
  def skimage_in_dir(self):
    return self._skimage_in_dir

  @property
  def skimage_expected_dir(self):
    return self._skimage_expected_dir

  @property
  def skimage_out_dir(self):
    return self._skimage_out_dir

  @property
  def skp_dir(self):
    """Holds SKP files that are consumed by RenderSKPs and BenchPictures."""
    return self._skp_dir

  @property
  def skp_perf_dir(self):
    return self._skp_perf_dir

  @property
  def tmp_dir(self):
    return self._tmp_dir


class DefaultFlavorUtils(base_flavor.BaseFlavorUtils):
  """Utilities to be used by build steps.

  The methods in this class define how certain high-level functions should
  work. Each build step flavor should correspond to a subclass of
  DefaultFlavorUtils which may override any of these functions as appropriate
  for that flavor.

  For example, the AndroidFlavorUtils will override the functions for
  copying files between the host and Android device, as well as the
  'step' function, so that commands may be run through ADB.
  """
  def __init__(self, *args, **kwargs):
    super(DefaultFlavorUtils, self).__init__(*args, **kwargs)
    self._chrome_path = None

  def step(self, name, cmd, **kwargs):
    """Wrapper for the Step API; runs a step as appropriate for this flavor."""
    path_to_app = self._skia_api.m.path['checkout'].join(
        'out', self._skia_api.c.configuration, cmd[0])
    if (self._skia_api.m.platform.is_linux and
        'x86_64' in self._skia_api.c.BUILDER_NAME and
        not 'TSAN' in self._skia_api.c.BUILDER_NAME):
      new_cmd = ['catchsegv', path_to_app]
    else:
      new_cmd = [path_to_app]
    new_cmd.extend(cmd[1:])
    return self._skia_api.m.step(name, new_cmd, **kwargs)

  @property
  def chrome_path(self):
    """Path to a checkout of Chrome on this machine."""
    if self._chrome_path is None:
      test_data = lambda: self._skia_api.m.raw_io.test_api.output(
          '/home/chrome-bot/src')
      self._chrome_path = self._skia_api.m.python.inline(
          'get CHROME_PATH',
          """
          import os
          import sys
          with open(sys.argv[1], 'w') as f:
            f.write(os.path.join(os.path.expanduser('~'), 'src'))
          """,
          args=[self._skia_api.m.raw_io.output()],
          step_test_data=test_data
      ).raw_io.output
    return self._chrome_path

  def compile(self, target):
    """Build the given target."""
    env = {}
    # The CHROME_PATH environment variable is needed for builders that use
    # toolchains downloaded by Chrome.
    env['CHROME_PATH'] = self.chrome_path
    env.update(self._skia_api.c.gyp_env.as_jsonish())
    make_cmd = 'make.bat' if self._skia_api.m.platform.is_win else 'make'
    cmd = [make_cmd, target, 'BUILDTYPE=%s' % self._skia_api.c.configuration]
    self._skia_api.m.step('build %s' % target, cmd, env=env,
                          cwd=self._skia_api.m.path['checkout'])

  def device_path_join(self, *args):
    """Like os.path.join(), but for paths on a connected device."""
    return self._skia_api.m.path.join(*args)

  def device_path_exists(self, path):
    """Like os.path.exists(), but for paths on a connected device."""
    return self._skia_api.m.path.exists(path)

  def copy_directory_to_device(self, host_dir, device_dir):
    """Like shutil.copytree(), but for copying to a connected device."""
    # For "normal" builders who don't have an attached device, we expect
    # host_dir and device_dir to be the same.
    if str(host_dir) != str(device_dir):
      raise ValueError('For builders who do not have attached devices, copying '
                       'from host to device is undefined and only allowed if '
                       'host_path and device_path are the same (%s vs %s).' % (
                       str(host_path), str(device_path)))

  def copy_directory_to_host(self, device_dir, host_dir):
    """Like shutil.copytree(), but for copying from a connected device."""
    # For "normal" builders who don't have an attached device, we expect
    # host_dir and device_dir to be the same.
    if str(host_dir) != str(device_dir):
      raise ValueError('For builders who do not have attached devices, copying '
                       'from device to host is undefined and only allowed if '
                       'host_path and device_path are the same (%s vs %s).' % (
                       str(host_path), str(device_path)))

  def copy_file_to_device(self, host_path, device_path):
    """Like shutil.copyfile, but for copying to a connected device."""
    # For "normal" builders who don't have an attached device, we expect
    # host_dir and device_dir to be the same.
    if str(host_path) != str(device_path):
      raise ValueError('For builders who do not have attached devices, copying '
                       'from host to device is undefined and only allowed if '
                       'host_path and device_path are the same (%s vs %s).' % (
                       str(host_path), str(device_path)))

  def create_clean_device_dir(self, path):
    """Like shutil.rmtree() + os.makedirs(), but on a connected device."""
    self.create_clean_host_dir(path)

  def create_clean_host_dir(self, path):
    """Convenience function for creating a clean directory."""
    self._skia_api.m.path.rmtree(str(path), path)
    self._skia_api.m.path.makedirs(str(path), path)

  def install(self):
    """Run device-specific installation steps."""
    pass

  def get_device_dirs(self):
    """ Set the directories which will be used by the build steps.

    These refer to paths on the same device where the test executables will
    run, for example, for Android bots these are paths on the Android device
    itself. For desktop bots, these are just local paths.
    """
    pardir = self._skia_api.m.path.pardir
    join = self._skia_api.m.path['slave_build'].join
    return DeviceDirs(
        gm_actual_dir=join('gm', 'actual'),
        gm_expected_dir=join('skia', 'expectations', 'gm'),
        perf_data_dir=self._skia_api.perf_data_dir,
        resource_dir=self._skia_api.resource_dir,
        skimage_expected_dir=join('skia', 'expectations', 'skimage'),
        skimage_in_dir=self._skia_api.skimage_in_dir,
        skimage_out_dir=self._skia_api.skimage_out_dir,
        skp_dirs=self._skia_api.local_skp_dirs,
        skp_perf_dir=self._skia_api.perf_data_dir,
        tmp_dir=join('tmp'))
