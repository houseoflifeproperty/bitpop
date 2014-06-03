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

#include "chrome/browser/ui/webui/options/bitpop_proxy_domain_settings_handler.h"

#include "base/bind.h"
#include "base/memory/scoped_ptr.h"
#include "base/string_number_conversions.h"
#include "base/utf_string_conversions.h"
#include "base/values.h"
#include "chrome/browser/extensions/event_router_forwarder.h"
#include "chrome/browser/extensions/extension_service.h"
#include "chrome/browser/prefs/pref_service.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/common/chrome_constants.h"
#include "chrome/common/extensions/extension.h"
#include "chrome/common/pref_names.h"
#include "chrome/common/url_constants.h"
#include "content/public/browser/web_ui.h"
#include "grit/generated_resources.h"
#include "grit/locale_settings.h"
#include "ui/base/l10n/l10n_util.h"

namespace {
  const char kOnUpdateProxyDomains[] = "bitpop.onProxyDomainsUpdate";
}

namespace options {

BitpopProxyDomainSettingsHandler::BitpopProxyDomainSettingsHandler() {
}

BitpopProxyDomainSettingsHandler::~BitpopProxyDomainSettingsHandler() {
}

void BitpopProxyDomainSettingsHandler::InitializeHandler() {
}

void BitpopProxyDomainSettingsHandler::InitializePage() {
  Profile* profile = Profile::FromWebUI(web_ui());
  PrefService* prefs = profile->GetPrefs();

  scoped_ptr<base::Value> siteList(base::Value::CreateStringValue(
      prefs->GetString(prefs::kBlockedSitesList)));
  scoped_ptr<base::Value> countryName(base::Value::CreateStringValue(
    prefs->GetString(prefs::kIPRecognitionCountryName)));

  web_ui()->CallJavascriptFunction(
      "BitpopProxyDomainSettingsOverlay.updateListFromPrefValue",
      *siteList);
  web_ui()->CallJavascriptFunction(
      "BitpopProxyDomainSettingsOverlay.updateCountryName",
      *countryName);
}

void BitpopProxyDomainSettingsHandler::GetLocalizedValues(
    base::DictionaryValue* localized_strings) {
  DCHECK(localized_strings);

  RegisterTitle(localized_strings, "uncensorBlockedSitesTitle",
                IDS_BITPOP_UNCENSOR_BLOCKED_SITES);
  localized_strings->SetString("aListOfSitesBlocked_start",
      l10n_util::GetStringUTF16(IDS_BITPOP_UNCENSOR_LIST_BLOCKED_SITES_START));
  localized_strings->SetString("aListOfSitesBlocked_end",
      l10n_util::GetStringUTF16(IDS_BITPOP_UNCENSOR_LIST_BLOCKED_SITES_END));
  localized_strings->SetString("updateDomainsButtonLabel",
      l10n_util::GetStringUTF16(IDS_BITPOP_UPDATE_DOMAINS_BUTTON_LABEL));
  localized_strings->SetString("useGlobalSettingDefaultOption",
      l10n_util::GetStringUTF16(IDS_BITPOP_USE_GLOBAL_SETTING));
}

void BitpopProxyDomainSettingsHandler::RegisterMessages() {
  web_ui()->RegisterMessageCallback(
      "updateDomains",
      base::Bind(&BitpopProxyDomainSettingsHandler::OnUpdateDomains,
                 base::Unretained(this)));
  web_ui()->RegisterMessageCallback(
      "proxySiteListChange",
      base::Bind(&BitpopProxyDomainSettingsHandler::ChangeSiteList,
                 base::Unretained(this)));
}

void BitpopProxyDomainSettingsHandler::OnUpdateDomains(
      const base::ListValue* params) {
  Profile* profile = Profile::FromWebUI(web_ui())->GetOriginalProfile();
  scoped_refptr<extensions::EventRouterForwarder> router_f(
      new extensions::EventRouterForwarder);
  scoped_ptr<base::ListValue> lv(new base::ListValue());
  router_f->DispatchEventToExtension(chrome::kUncensorISPExtensionId,
                                     kOnUpdateProxyDomains,
                                     lv.Pass(),
                                     profile,
                                     true,
                                     GURL()
                                     );
}

void BitpopProxyDomainSettingsHandler::ChangeSiteList(
      const base::ListValue* params) {

  std::string strValue;
  CHECK_EQ(params->GetSize(), 1U);
  CHECK(params->GetString(0, &strValue));

  Profile* profile = Profile::FromWebUI(web_ui());
  PrefService* pref_service = profile->GetPrefs();
  if (pref_service->IsUserModifiablePreference(prefs::kBlockedSitesList))
    pref_service->SetString(prefs::kBlockedSitesList, strValue);
  else {
    extensions::ExtensionPrefs* prefs =
        profile->GetExtensionService()->extension_prefs();
    prefs->SetExtensionControlledPref(
        chrome::kUncensorISPExtensionId,
        prefs::kBlockedSitesList,
        extensions::kExtensionPrefsScopeRegular,
        Value::CreateStringValue(strValue));
  }
}

}  // namespace options
