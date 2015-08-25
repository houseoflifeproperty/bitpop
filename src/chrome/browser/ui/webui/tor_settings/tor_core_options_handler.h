// BitPop browser. Tor launcher integration part.
// Copyright (C) 2015 BitPop AS
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

#ifndef CHROME_BROWSER_UI_WEBUI_TOR_SETTINGS_TOR_CORE_OPTIONS_HANDLER_H_
#define CHROME_BROWSER_UI_WEBUI_TOR_SETTINGS_TOR_CORE_OPTIONS_HANDLER_H_

#include "chrome/browser/ui/webui/options/core_options_handler.h"

namespace tor_settings {

class CoreOptionsHandler : public options::CoreOptionsHandler {
 public:
  CoreOptionsHandler();
  ~CoreOptionsHandler() override;

  // OptionsPageUIHandler implementation.
  void GetLocalizedValues(
      base::DictionaryValue* localized_strings) override;

  // Adds localized strings to |localized_strings|.
  static void GetStaticLocalizedValues(
      base::DictionaryValue* localized_strings);
};

} // namespace tor_settings

#endif // CHROME_BROWSER_UI_WEBUI_TOR_SETTINGS_TOR_CORE_OPTIONS_HANDLER_H_
