# BitPop browser. Tor Launcher integration part.
# Copyright (C) 2014 BitPop AS
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

{
  'targets': [
    {
      # GN version: //components/torlauncher
      'target_name': 'torlauncher',
      'type': 'static_library',
      'include_dirs': [
        '..',
      ],
      'dependencies': [
        '../base/base.gyp:base',
        '../base/base.gyp:base_prefs',
        '../crypto/crypto.gyp:crypto',
        '../ui/base/ui_base.gyp:ui_base',
        'components.gyp:keyed_service_core',
        'components.gyp:pref_registry',
        'components_strings.gyp:components_strings',
      ],
      'sources': [
        'torlauncher/torlauncher_pref_names.cc',
        'torlauncher/torlauncher_pref_names.h',
        'torlauncher/torlauncher_service.cc',
        'torlauncher/torlauncher_service.h',
      ],
      'copies': [
        {
          'destination': '<(PRODUCT_DIR)/torlauncher',
          'conditions': [
            ['OS=="win"', {
              'files': [
                '../third_party/tor/win/Data',
                '../third_party/tor/win/Tor',
              ],
            }],
            ['OS=="mac"', {
              'files': [
                '../third_party/tor/mac/Data',
                '../third_party/tor/mac/Tor',
              ],
            }],
          ],
        }
      ],
    },
  ],
}
