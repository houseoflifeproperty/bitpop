# Copyright (c) 2011 House of Life Property ltd.
# Copyright (c) 2011 Crystalnix <vgachkaylo@crystalnix.com>

{
  'conditions': [
    ['OS=="mac"', {
      'targets': [
        {
          'target_name': 'Sparkle',
          'type': 'shared_library',
          'dependencies': [
            'relaunch_tool',
          ],
          'configurations': {
            'Debug': {
              'xcode_config_file': 'Configurations/ConfigFrameworkDebug.xcconfig',
            },
            'Release': {
              'xcode_config_file': 'Configurations/ConfigFrameworkRelease.xcconfig',
              'xcode_settings': {
                'GCC_GENERATE_DEBUGGING_SYMBOLS': 'YES',
              },
            },
          },
          'product_name': 'Sparkle',
          'mac_bundle': 1,
          'xcode_settings': {
            'DYLIB_INSTALL_NAME_BASE': '@loader_path/Frameworks',
            'LD_DYLIB_INSTALL_NAME':
                '$(DYLIB_INSTALL_NAME_BASE:standardizepath)/$(WRAPPER_NAME)/$(PRODUCT_NAME)',
            'GCC_WARN_64_TO_32_BIT_CONVERSION': 'NO',
            'GCC_PREFIX_HEADER': 'Sparkle.pch',
            'GCC_PRECOMPILE_PREFIX_HEADER': 'YES',
          },
          'variables': {
            'sparkle_public_headers': [
              'Sparkle.h',
              'SUAppcast.h',
              'SUAppcastItem.h',
              'SUUpdater.h',
              'SUVersionComparisonProtocol.h',
            ],
            'sparkle_private_headers': [
              'SUPlainInstallerInternals.h',
              'SUUpdateAlert.h',
              'SUStatusController.h',
              'SUDSAVerifier.h',
              'SUConstants.h',
              'SUUnarchiver.h',
              'SUAutomaticUpdateAlert.h',
              'NTSynchronousTask.h',
              'SUStandardVersionComparator.h',
              'SUSystemProfiler.h',
              'SUUpdatePermissionPrompt.h',
              'SUWindowController.h',
              'SUInstaller.h',
              'SUPlainInstaller.h',
              'SUPackageInstaller.h',
              'SUBasicUpdateDriver.h',
              'SUUIBasedUpdateDriver.h',
              'SUAutomaticUpdateDriver.h',
              'SUScheduledUpdateDriver.h',
              'SUUpdateDriver.h',
              'SUProbingUpdateDriver.h',
              'SUUserInitiatedUpdateDriver.h',
              'SUDiskImageUnarchiver.h',
              'SUUnarchiver_Private.h',
              'SUPipedUnarchiver.h',
              'SUHost.h',
              'bspatch.h',
              'SUBinaryDeltaUnarchiver.h',
              'SUBinaryDeltaApply.h',
              'SUBinaryDeltaCommon.h',
            ],
          },
          'sources': [
            '<@(sparkle_public_headers)',
            '<@(sparkle_private_headers)',
            'SUUpdater.m',
            'SUPlainInstallerInternals.m',
            'SUAppcast.m',
            'SUAppcastItem.m',
            'SUUpdateAlert.m',
            'SUStatusController.m',
            'SUDSAVerifier.m',
            'SUConstants.m',
            'SUUnarchiver.m',
            'SUAutomaticUpdateAlert.m',
            'NTSynchronousTask.m',
            'SUStandardVersionComparator.m',
            'SUSystemProfiler.m',
            'SUUpdatePermissionPrompt.m',
            'SUWindowController.m',
            'SUInstaller.m',
            'SUPlainInstaller.m',
            'SUPackageInstaller.m',
            'SUBasicUpdateDriver.m',
            'SUUIBasedUpdateDriver.m',
            'SUAutomaticUpdateDriver.m',
            'SUScheduledUpdateDriver.m',
            'SUUpdateDriver.m',
            'SUProbingUpdateDriver.m',
            'SUUserInitiatedUpdateDriver.m',
            'SUDiskImageUnarchiver.m',
            'SUUnarchiver_Private.m',
            'SUPipedUnarchiver.m',
            'SUHost.m',
            'bspatch.c',
            'SUBinaryDeltaApply.m',
            'SUBinaryDeltaCommon.m',
            'SUBinaryDeltaUnarchiver.m',
          ],
          'mac_framework_headers': [
            '<@(sparkle_public_headers)',
          ],
          'mac_bundle_resources': [
            'License.txt',
            'Info.plist',
            'SUModelTranslation.plist',
            'SUStatus.nib',
            'cs.lproj',
            'da.lproj',
            'de.lproj',
            'en.lproj',
            'es.lproj',
            'fr.lproj',
            'is.lproj',
            'it.lproj',
            'ja.lproj',
            'nl.lproj',
            'pl.lproj',
            'pt_BR.lproj',
            'pt_PT.lproj',
            'ru.lproj',
            'sv.lproj',
            'tr.lproj',
            'zh_CN.lproj',
            'zh_TW.lproj',
            '<(PRODUCT_DIR)/relaunch',
          ],
          'include_dirs': [
            '.', '..',
          ],
          'link_settings': {
            'libraries': [
              '$(SDKROOT)/System/Library/Frameworks/Security.framework',
              '$(SDKROOT)/System/Library/Frameworks/WebKit.framework',
              '$(SDKROOT)/System/Library/Frameworks/IOKit.framework',
              '$(SDKROOT)/usr/lib/libbz2.dylib',
              '$(SDKROOT)/usr/lib/libxar.1.dylib',
              '$(SDKROOT)/usr/lib/libz.dylib',
              '$(SDKROOT)/usr/lib/libcrypto.dylib',
              '$(SDKROOT)/System/Library/Frameworks/Cocoa.framework',
            ],
          },
          'postbuilds': [
            {
              'postbuild_name': 'Link fr_CA to fr',
              'action': [
                '/usr/bin/env', 'ruby',
                '-e', 'resources = "#{ENV["BUILT_PRODUCTS_DIR"]}/#{ENV["WRAPPER_NAME"]}/Resources"',
                '-e', '`ln -sfh "fr.lproj" "#{resources}/fr_CA.lproj"`',
              ],
            },
            {
              'postbuild_name': 'Link pt to pt_BR',
              'action': [
                '/usr/bin/env', 'ruby',
                '-e', 'resources = "#{ENV["BUILT_PRODUCTS_DIR"]}/#{ENV["WRAPPER_NAME"]}/Resources"',
                '-e', '`ln -sfh "pt_BR.lproj" "#{resources}/pt.lproj"`',
              ],
            },
            {
              'postbuild_name': 'Create public Sparkle Framework headers dir',
              'action': [
                'mkdir', '-p', '$BUILT_PRODUCTS_DIR/$WRAPPER_NAME/Headers',
              ],
            },
            {
              'postbuild_name': 'Copy public Sparkle Framework Headers',
              'action': [
                'cp', '<@(sparkle_public_headers)', '$BUILT_PRODUCTS_DIR/$WRAPPER_NAME/Headers/',
              ],
            },
            {
              'postbuild_name': 'Fix permissions on relaunch tool for ninja builds',
              'action': [
                'chmod', '755', '$BUILT_PRODUCTS_DIR/$WRAPPER_NAME/Resources/relaunch',
              ],
            },
          ],
        },
        {
          'target_name': 'relaunch_tool',
          'type': 'executable',
          'product_name': 'relaunch',
          'configurations': {
            'Debug': {
              'xcode_config_file': 'Configurations/ConfigRelaunchDebug.xcconfig',
            },
            'Release': {
              'xcode_config_file': 'Configurations/ConfigRelaunchRelease.xcconfig',
            },
          },
          'sources': [
            'relaunch.m',
          ],
          'link_settings': {
            'libraries': [
              '$(SDKROOT)/System/Library/Frameworks/Cocoa.framework',
            ],
          },
        },
      ],
    }, ],
  ],
}
