#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Flashes attached unlocked devices with specified version of Android.

The script will download an image from google storage (see _GS_IMAGES_URL) and
flash that images on all attached (unlocked) devices. Before flashing, it will
check the radio image on the device, and if needed, will flash the radio image.
This part needs corp access as private radio images are not on google storage.
The script determines the URL for the specified build from three required
arguments, the android version (e.g. ics, jb), device type (e.g. yakju, sojus)
and the build number. Usage example:./flash_devices.py jb yakju userdebug 398337
The script will determine the URL for the specified image as the following URL:
gs://android-build/builds/git_jb-release-linux-yakju-userdebug/398337/
   25fe19bc6ad28374e73f84ffbcc4e02b12269371d53750e93d04ce5930483242/
   yakju-img-398337.zip

Because the build number is not as obvious as the other two arguments, the
script can be run with the -l option to list all builds for a particular android
version and device.  E.g. './flash_devices.py -l jb yakju userdebug' will list
all the userdebug builds for yakju on JB.

Note: The script assumes that gsutil is in the path, and the slave has set up
credentials for accessing Android builds:
https://developers.google.com/storage/docs/gsutil_install#authenticate
The script will not flash an image for the wrong device type and will skip
flashing devices that are already on the version being flashed to.

Example run:
/build/scripts/slave$ ./flash_devices.py jb yakju 411644
# 2012-08-28 10:08:12,820: Downloading factory image from gs.
# 2012-08-28 10:08:13,203: gsutil cp gs://android-build/builds/.../
                                       yakju-img-411644.zip yakju-img-411644.zip
# 2012-08-28 10:08:24,662: Rebooted device 016B7FFD11015007 into bootloader
# 2012-08-28 10:10:26,059: Flashed image yakju-....zip onto device 016B7...

The script will not flash if the device(s) already on build:
/build/scripts/slave$ ./flash_devices.py jb yakju 411644
No devices to flash.
Device(s) already on current build.
"""


import logging
import optparse
import os
import re
import subprocess
import sys
import time

import slave.gsutil_download
import slave.slave_utils


# Use tools from the third_party/android_tools/sdk directory
_ADB_TOOL = os.path.join(os.getenv('ANDROID_SDK_ROOT'),
                         'platform-tools', 'adb')
_SDK_FASTBOOT_TOOL = os.path.join(os.getenv('ANDROID_SDK_ROOT'),
                                  'platform-tools', 'fastboot')

# Google storage url for Android images
_GS_IMAGES_URL = 'gs://android-build/builds/'

# Number of times to try to find attached devices (via adb devices).
_INITIAL_WAIT_RETRIES = 3

# Number of seconds to wait between each retry for adb devices.
_INITIAL_WAIT_INTERVAL_SECS = 2


def RunCommand(args):
  """Execute a command and return stdout and stderr.

  Args:
    args: list of the command and the args to the command.

  Returns:
    (output, stderr): stdout and stderr
  """
  proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  output, stderr = proc.communicate()
  return (str(output).strip(), stderr)


def AdbCommand(args):
  """Execute an adb command and return stdout and stderr.

  Args:
    args: list of the args to the adb command.

  Returns:
    (output, stderr): stdout and stderr
  """
  return RunCommand([_ADB_TOOL] + args)


def FastbootCommand(args):
  """Execute an fastboot command and return stdout and stderr.

  Args:
    args: list of the args to the fastboot command.

  Returns:
    (output, stderr): stdout and stderr
  """
  return RunCommand([_SDK_FASTBOOT_TOOL] + args)


def GetAttachedDevices():
  """Returns a list of attached, online android devices.

  Example output:

    * daemon not running. starting it now on port 5037 *
    * daemon started successfully *
    List of devices attached
    027c10494100b4d7        device
    emulator-5554   offline

  Returns:
    list of attached online android devices.
  """
  re_device = re.compile('^([a-zA-Z0-9_:.-]+)\tdevice$', re.MULTILINE)
  output, stderr = AdbCommand(['devices'])
  if stderr:
    logging.critical(stderr)
    return []
  devices = re_device.findall(output)
  return devices


def GetAttachedFastbootDevices():
  """Returns a list of attached, online android devices in fastboot.

  Example output:
      016B75D60201600D   fastboot

  Returns:
    list of attached online android devices.
  """
  re_device = re.compile('^([a-zA-Z0-9_:.-]+)\tfastboot$', re.MULTILINE)
  output, stderr = FastbootCommand(['devices'])
  if stderr:
    logging.critical(stderr)
    return []
  devices = re_device.findall(output)
  return devices


def FlashDeviceStatus(device, android_version, device_type, build_number,
                      build_type):
  """Function to determine if the device can/needs to be flashed with image.

  Args:
    device: the device serial number.
    android_version: the android version being flashed to (e.g. jb, ics).
    device_type: the device type being flashed to.
    build_number: the build number being flashed to.
    build_type: the build type (e.g. userdebug) to flash to.

  Returns:
     (can_flash, needs_flash): can the device be flashed with the image and does
                               it need to be flashed to that image (i.e. is it
                               already on that image).
  """
  product_name, stderr1 = AdbCommand(['-s', device, 'shell', 'getprop',
                                      'ro.product.name'])
  device_android, stderr3 = AdbCommand(['-s', device, 'shell', 'getprop',
                                        'ro.build.id'])
  device_build_id, stderr2 = AdbCommand(['-s', device, 'shell', 'getprop',
                                         'ro.build.version.incremental'])
  device_build_type, stderr3 = AdbCommand(['-s', device, 'shell', 'getprop',
                                           'ro.build.type'])

  # Do not have appropriate information about the device.
  if stderr1 or stderr1 or stderr2 or stderr3:
    return False, False

  # Note(navabi): Is there a better way to determine if same android version.
  same_android = android_version[0].lower() == device_android[0].lower()

  if product_name != device_type:
    return False, False
  elif not same_android:
    return True, True
  elif device_build_type != build_type:
    return True, True
  elif device_build_id != build_number:
    return True, True
  return True, False


def GetBuildsDirectory(android_version, device_type, build_type):
  """Returns a string google storage path to the build directories.

  Args:
    android_version: the android version being flashed to (e.g. jb, ics).
    device_type: the device type for the image being flashed to.
    build_type: the build type (e.g. userdebug) to flash to.

  Returns:
    google storage path for builds.
  """
  gs_base = '%sgit_%s-release-linux-%s-%s' % (_GS_IMAGES_URL, android_version,
                                              device_type, build_type)
  return gs_base


def GSDownloadImage(android_version, device_type, build_number, build_type):
  """Download the specified image and return the name of it.

  Args:
    android_version: the android version being flashed to (e.g. jb, ics).
    device_type: yakju, soju, sojus, trygon, etc.
    build_number: the build number being flashed to.
    build_type: the build type (e.g. userdebug) to flash to.

  Returns:
    name of the downloaded image file.
  """
  # TODO(navabi): This requires gsutil.  Should be added to third_party as part
  # of the CL for this change.

  # First download the AOSP factory image from gsutil.
  logging.info('Downloading factory image from gs.')

  base_url = GetBuildsDirectory(android_version, device_type, build_type)
  file_name = '%s-img-%s.zip' % (device_type, build_number)

  try:
    slave.gsutil_download.DownloadLatestFile(base_url, file_name, file_name)
    return file_name
  except Exception:
    return None


def FlashSingleDeviceIfNecessary(device, image_file_name):
  """Flash image on a single device and reports any exception.

  Args:
    device: serial number to be flashed.
    image_file_name: name of the image file downloaded.

  Returns:
    true if successfully flashed, false otherwise.
  """
  # Reboot device into bootloader
  _, stderr = AdbCommand(['-s', device, 'reboot', 'bootloader'])
  if stderr:
    logging.info('ERROR flashing device: %s.', stderr)
    return False
  logging.info('Rebooted device %s into bootloader', device)

  for _ in xrange(_INITIAL_WAIT_RETRIES):
    devices = GetAttachedFastbootDevices()
    if devices:
      break
    time.sleep(_INITIAL_WAIT_INTERVAL_SECS)
  if not devices:
    print 'ERROR: There are no devices attached to fastboot.'
    return False

  # Flash the downloaded image onto the device.
  FastbootCommand(['-s', device, '-w', 'update', image_file_name])
  logging.info('Flashed image %s onto device %s.', image_file_name, device)

  return True


def ListBuildNumbers(android_version, device, build_type):
  """List all build numbers for the specified type of build.

  Args:
    android_version: e.g. ics, jb
    device: device type of build
    build_type: e.g. userdebug, debug, etc.

  Returns:
    number of build_numbers returned (-1 upon error)
  """
  # Example of gs_path: For './flash_device -l jb yakju userdebug,'
  # gsutil ls gs://android-build/builds/git_jb-release-linux-yakju-userdebug/*
  #                 /*/yakju-img-*.zip
  build_dir = GetBuildsDirectory(android_version, device,
                                 build_type).rstrip('/')
  gs_path = '%s/*/*/%s-img-*.zip' % (build_dir, device)

  # Get the list of all build numbers
  (status, output) = slave.slave_utils.GSUtilListBucket(gs_path, [])
  if status != 0:
    print 'Invalid android version and device type.'
    return -1

  # Format and print the list of all build numbers.
  def HasBuildNum(line):
    return line.find('%s-img-' % device) > -1

  build_lines = filter(HasBuildNum, output.split('\n'))

  def GetBuildNum(line):
    return line.split('/')[5]

  build_numbers = map(GetBuildNum, build_lines)
  print 'build numbers: %s' % str(build_numbers)
  return len(build_numbers)


def DownloadImageForDevices(android_version, device_type, build_type,
                            build_number):
  """Determine which devices need to be flashed and download image.

  If no devices that need to be flashed, the image will not be downloaded.

  Args:
    android_version: e.g. ics, jb
    device_type: device type of build
    build_type: e.g. userdebug, debug, etc.
    build_number: build number to download

  Raises:
    RuntimeError: if no devices of the right type for the image are attached

  Returns:
    name of image zip file downloaded (None if list of devices empty)
    list of devices that need to be flashed to the downloaded image
  """
  for _ in xrange(_INITIAL_WAIT_RETRIES):
    devices = GetAttachedDevices()
    if devices:
      break
    time.sleep(_INITIAL_WAIT_INTERVAL_SECS)
  if not devices:
    raise RuntimeError('ERROR: There are no devices attached.')

  # Make sure there is at least one phone that can be flashed with the build
  # that is not already on that build.
  devices_to_flash = []

  device_exists_to_flash = False
  device_exists_needs_flash = False

  for device in devices:
    can_flash, needs_flash = FlashDeviceStatus(device, android_version,
                                               device_type, build_number,
                                               build_type)
    if can_flash and needs_flash:
      devices_to_flash.append(device)
    device_exists_to_flash = device_exists_to_flash or can_flash
    device_exists_needs_flash = device_exists_needs_flash or needs_flash

  if not devices_to_flash:
    print 'No devices to flash.'
    if device_exists_to_flash:
      print 'Device(s) already on image build.'
      return (None, [])
    else:
      raise RuntimeError('ERROR: Devices are the wrong type for build.')

  # At least one phone to flash.  Download the image file from gs.
  img_zip = GSDownloadImage(android_version, device_type, build_number,
                            build_type)
  return (img_zip, devices_to_flash)


def FlashDevices(img_zip, devices_to_flash):
  """Flash build image on list of devices.

  Args:
    img_zip: image zip file
    devices_to_flash: device list to flash

  Returns:
    true if all devices successfully flashed with the image, false otherwise
  """
  all_succeed = True
  for device in devices_to_flash:
    success = FlashSingleDeviceIfNecessary(device, img_zip)
    if not success:
      all_succeed = False
      print 'ERROR: Failed to flash device %s.' % device
  return all_succeed


def main(argv):
  # Parse aguments after the python script
  args = argv[1:]
  opt_parser = optparse.OptionParser(description='Flash devices script.')
  opt_parser.add_option('--android-version',
                        help='Android version (e.g. jb, ics).')
  opt_parser.add_option('--device-type', help='Device type (e.g. yakju, soju).')
  opt_parser.add_option('--build-type', help='Build type (e.g. userdebug).')
  opt_parser.add_option('--build-number', help='Android image build number.')

  options, _ = opt_parser.parse_args(args)

  # If everything but build_num set, the user wants to see a list of the builds
  # for a specified android version and device type.
  if options.build_number is None:
    if options.android_version is None or options.device_type is None or \
       options.build_type is None:
      print 'Invalid number of arguments'
      print 'Usage (to show build numbers for userdebug yajku builds on JB):'
      print '  flash_devices.py --android-version=jb --device-type=yakju '
      print '                   --build-type=userdebug'
      print 'Usage (to show flash devices):'
      print 'e.g. --android-version=jb --device-type=yakju '
      print '     --build-type=userdebug --build_num=<n>'
      return 1

    # List the build numbers for the specified build and exit with 0.
    num_builds = ListBuildNumbers(options.android_version, options.device_type,
                                  options.build_type)
    if num_builds >= 0:
      return 0
    else:
      return 1
  elif options.android_version is None or options.device_type is None or \
       options.build_type is None or options.build_number is None:
    print 'Invalid number of arguments'
    print '  --android=jb --device=yakju --build_type=userdebug --build_num=<n>'
    return 1

  logging.basicConfig(level=logging.INFO,
                      format='# %(asctime)-15s: %(message)s')

  # Download build image and return the devices that need to be flashed to the
  # image. If no devices need to be flashed call will not download the image.
  (img_zip, devices_to_flash) = DownloadImageForDevices(options.android_version,
                                                        options.device_type,
                                                        options.build_type,
                                                        options.build_number)

  # If there are devices to flash but no build image, then error.
  if len(devices_to_flash) > 0 and not img_zip:
    invalid_specs = '%s %s %s' % (options.android_version, options.device_type,
                                  options.build_number)
    print 'Invalid Android factory image for: %s.' % invalid_specs
    return 1

  # TODO(navabi): Implement the following commented lines.
  # Flash radio images on devices that need to update radio for build image.
  # FlashRadioImage(img_zip, devices_to_flash)

  # Flash all devices that need to be flashed with image
  all_succeed = FlashDevices(img_zip, devices_to_flash)
  # Remove the img_zip file as it is no longer needed.
  os.remove(img_zip)

  if all_succeed:
    return 0
  else:
    return 1


if __name__ == '__main__':
  sys.exit(main(sys.argv))
