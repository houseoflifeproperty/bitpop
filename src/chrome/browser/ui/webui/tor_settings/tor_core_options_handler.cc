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

#include "chrome/browser/ui/webui/tor_settings/tor_core_options_handler.h"

#include "base/strings/string16.h"
#include "base/strings/utf_string_conversions.h"
#include "chrome/browser/ui/webui/tor_settings/tor_options_ui.h"
#include "chrome/common/chrome_switches.h"
#include "chrome/common/url_constants.h"
#include "chrome/grit/chromium_strings.h"
#include "chrome/grit/generated_resources.h"
#include "chrome/grit/locale_settings.h"
#include "grit/components_strings.h"
#include "ui/base/l10n/l10n_util.h"

namespace {

// Hack to re-use IDS_ABOUT, which is a menu item for the About page.
// Since it's a menu item, it may include a "&" to indicate a hotkey.
base::string16 GetAboutString() {
  if (!switches::AboutInSettingsEnabled())
    return base::string16();

  base::string16 str = l10n_util::GetStringUTF16(IDS_ABOUT);
  size_t start_pos = str.find(base::ASCIIToUTF16("&"));
  if (start_pos != base::string16::npos)
    str.erase(start_pos, 1);
  return str;
}

}

namespace tor_settings {

CoreOptionsHandler::CoreOptionsHandler()
  : options::CoreOptionsHandler() {
}

CoreOptionsHandler::~CoreOptionsHandler() {

}

void CoreOptionsHandler::GetLocalizedValues(
    base::DictionaryValue* localized_strings) {
  GetStaticLocalizedValues(localized_strings);
}

void CoreOptionsHandler::GetStaticLocalizedValues(
    base::DictionaryValue* localized_strings) {
  DCHECK(localized_strings);
  // Main
  localized_strings->SetString("optionsPageTitle",
      l10n_util::GetStringUTF16(IDS_TOR_SETTINGS_TITLE));

  // Controlled settings bubble.
  localized_strings->SetString("controlledSettingPolicy",
      l10n_util::GetStringUTF16(IDS_OPTIONS_CONTROLLED_SETTING_POLICY));
  localized_strings->SetString("controlledSettingExtension",
      l10n_util::GetStringUTF16(IDS_OPTIONS_CONTROLLED_SETTING_EXTENSION));
  localized_strings->SetString("controlledSettingExtensionWithName",
      l10n_util::GetStringUTF16(
          IDS_OPTIONS_CONTROLLED_SETTING_EXTENSION_WITH_NAME));
  localized_strings->SetString("controlledSettingManageExtension",
      l10n_util::GetStringUTF16(
          IDS_OPTIONS_CONTROLLED_SETTING_MANAGE_EXTENSION));
  localized_strings->SetString("controlledSettingDisableExtension",
      l10n_util::GetStringUTF16(IDS_EXTENSIONS_DISABLE));
  localized_strings->SetString("controlledSettingRecommended",
      l10n_util::GetStringUTF16(IDS_OPTIONS_CONTROLLED_SETTING_RECOMMENDED));
  localized_strings->SetString("controlledSettingHasRecommendation",
      l10n_util::GetStringUTF16(
          IDS_OPTIONS_CONTROLLED_SETTING_HAS_RECOMMENDATION));
  localized_strings->SetString("controlledSettingFollowRecommendation",
      l10n_util::GetStringUTF16(
          IDS_OPTIONS_CONTROLLED_SETTING_FOLLOW_RECOMMENDATION));
  localized_strings->SetString("controlledSettingsPolicy",
      l10n_util::GetStringUTF16(IDS_OPTIONS_CONTROLLED_SETTINGS_POLICY));
  localized_strings->SetString("controlledSettingsExtension",
      l10n_util::GetStringUTF16(IDS_OPTIONS_CONTROLLED_SETTINGS_EXTENSION));
  localized_strings->SetString("controlledSettingsExtensionWithName",
      l10n_util::GetStringUTF16(
          IDS_OPTIONS_CONTROLLED_SETTINGS_EXTENSION_WITH_NAME));

  // Search
  // BITPOP:
  OptionsPageUIHandlerStaticContainer::RegisterTitle(
      localized_strings, "searchPage", IDS_OPTIONS_SEARCH_PAGE_TITLE);
  // />
  localized_strings->SetString("searchPlaceholder",
      l10n_util::GetStringUTF16(IDS_OPTIONS_SEARCH_PLACEHOLDER));
  localized_strings->SetString("searchPageNoMatches",
      l10n_util::GetStringUTF16(IDS_OPTIONS_SEARCH_PAGE_NO_MATCHES));
  localized_strings->SetString("searchPageHelpLabel",
      l10n_util::GetStringUTF16(IDS_OPTIONS_SEARCH_PAGE_HELP_LABEL));
  localized_strings->SetString("searchPageHelpTitle",
      l10n_util::GetStringFUTF16(IDS_OPTIONS_SEARCH_PAGE_HELP_TITLE,
          l10n_util::GetStringUTF16(IDS_PRODUCT_NAME)));
  localized_strings->SetString("searchPageHelpURL",
                               chrome::kSettingsSearchHelpURL);

  // About
  localized_strings->SetBoolean("showAbout",
                                switches::AboutInSettingsEnabled());
  localized_strings->SetString("aboutButton", GetAboutString());

  // Common
  localized_strings->SetString("ok",
      l10n_util::GetStringUTF16(IDS_OK));
  localized_strings->SetString("cancel",
      l10n_util::GetStringUTF16(IDS_CANCEL));
  localized_strings->SetString("learnMore",
      l10n_util::GetStringUTF16(IDS_LEARN_MORE));
  localized_strings->SetString("close",
      l10n_util::GetStringUTF16(IDS_CLOSE));
  localized_strings->SetString("done",
      l10n_util::GetStringUTF16(IDS_DONE));
  localized_strings->SetString("deletableItemDeleteButtonTitle",
      l10n_util::GetStringUTF16(IDS_OPTIONS_DELETABLE_ITEM_DELETE_BUTTON));
}

} // namespace tor_settings
