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

#include "chrome/browser/ui/webui/tor_settings/core_options_handler.h"

#include "chrome/grit/generated_resources.h"
#include "ui/base/l10n/l10n_util.h"

namespace tor_settings {

CoreOptionsHandler::CoreOptionsHandler()
  : options::CoreOptionsHandler() {
}

CoreOptionsHandler::~CoreOptionsHandler() {

}

void CoreOptionsHandler::SetTitleString(
    base::DictionaryValue* localized_strings) {
  localized_strings->SetString("optionsPageTitle",
      l10n_util::GetStringUTF16(IDS_TOR_SETTINGS_TITLE));
}

} // namespace tor_settings
