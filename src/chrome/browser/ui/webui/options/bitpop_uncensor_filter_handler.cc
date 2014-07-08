// BitPop browser with features like Facebook chat and uncensored browsing. 
// Copyright (C) 2014 BitPop AS
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

#include "chrome/browser/ui/webui/options/bitpop_uncensor_filter_handler.h"

#include "base/bind.h"
#include "base/memory/scoped_ptr.h"
#include "base/prefs/pref_service.h"
#include "base/strings/string_number_conversions.h"
#include "base/strings/utf_string_conversions.h"
#include "base/values.h"
#include "chrome/browser/extensions/extension_service.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/common/chrome_constants.h"
#include "chrome/common/pref_names.h"
#include "chrome/common/url_constants.h"
#include "content/public/browser/web_ui.h"
#include "grit/generated_resources.h"
#include "grit/locale_settings.h"
#include "ui/base/l10n/l10n_util.h"

namespace options {

BitpopUncensorFilterHandler::BitpopUncensorFilterHandler() {
}

BitpopUncensorFilterHandler::~BitpopUncensorFilterHandler() {
}

void BitpopUncensorFilterHandler::InitializeHandler() {
}

void BitpopUncensorFilterHandler::InitializePage() {
  Profile* profile = Profile::FromWebUI(web_ui());
  PrefService* prefs = profile->GetPrefs();

  scoped_ptr<base::Value> filter(base::Value::CreateStringValue(
      prefs->GetString(prefs::kUncensorDomainFilter)));
  scoped_ptr<base::Value> exceptions(base::Value::CreateStringValue(
      prefs->GetString(prefs::kUncensorDomainExceptions)));

  web_ui()->CallJavascriptFunction("BitpopUncensorFilterOverlay.initLists",
    *filter, *exceptions);
}

void BitpopUncensorFilterHandler::GetLocalizedValues(
    base::DictionaryValue* localized_strings) {
  DCHECK(localized_strings);

  RegisterTitle(localized_strings, "uncensorFilterOverlayTitle",
                IDS_BITPOP_UNCENSOR_FILTER_OVERLAY_TITLE);
  localized_strings->SetString("uncensorTheFilter",
      l10n_util::GetStringUTF16(IDS_BITPOP_UNCENSOR_THE_FILTER));
  localized_strings->SetString("uncensorExceptions",
      l10n_util::GetStringUTF16(IDS_BITPOP_UNCENSOR_EXCEPTION));
  localized_strings->SetString("uncensorOriginalDomainHeader",
      l10n_util::GetStringUTF16(IDS_BITPOP_UNCENSOR_ORIGINAL_DOMAIN));
  localized_strings->SetString("uncensorNewLocationHeader",
      l10n_util::GetStringUTF16(IDS_BITPOP_UNCENSOR_NEW_LOCATION));
}

void BitpopUncensorFilterHandler::RegisterMessages() {
  web_ui()->RegisterMessageCallback(
      "changeUncensorExceptions",
      base::Bind(&BitpopUncensorFilterHandler::ChangeUncensorExceptions,
                 base::Unretained(this)));
}

void BitpopUncensorFilterHandler::ChangeUncensorExceptions(
      const base::ListValue* params) {

  std::string strValue;
  CHECK_EQ(params->GetSize(), 1U);
  CHECK(params->GetString(0, &strValue));

  Profile* profile = Profile::FromWebUI(web_ui());
  PrefService* pref_service = profile->GetPrefs();
  if (pref_service->IsUserModifiablePreference(prefs::kUncensorDomainExceptions))
    pref_service->SetString(prefs::kUncensorDomainExceptions, strValue);
  else {
    extensions::ExtensionPrefs* prefs = extensions::ExtensionPrefs::Get(profile);
    prefs->UpdateExtensionPref(
        chrome::kUncensorFilterExtensionId,
        prefs::kUncensorDomainExceptions,
        base::Value::CreateStringValue(strValue));
  }
}

}  // namespace options
