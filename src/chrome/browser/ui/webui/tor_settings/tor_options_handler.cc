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

#include "chrome/browser/ui/webui/tor_settings/tor_options_handler.h"

#include <string>

#include "base/bind.h"
#include "base/json/json_reader.h"
#include "base/prefs/pref_service.h"
#include "base/run_loop.h"
#include "base/strings/utf_string_conversions.h"
#include "base/values.h"
#include "chrome/browser/chrome_notification_types.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/ui/webui/favicon_source.h"
#include "chrome/common/extensions/extension_constants.h"
#include "chrome/common/pref_names.h"
#include "chrome/grit/chromium_strings.h"
#include "chrome/grit/generated_resources.h"
#include "chrome/grit/locale_settings.h"
#include "content/public/browser/dom_operation_notification_details.h"
#include "content/public/browser/notification_details.h"
#include "content/public/browser/notification_service.h"
#include "content/public/browser/notification_source.h"
#include "content/public/browser/notification_types.h"
#include "content/public/browser/render_frame_host.h"
#include "content/public/browser/render_view_host.h"
#include "content/public/browser/url_data_source.h"
#include "content/public/browser/web_contents.h"
#include "content/public/browser/web_contents_observer.h"
#include "extensions/browser/extension_host.h"
#include "extensions/browser/extension_system.h"
#include "extensions/browser/process_manager.h"
#include "ui/base/l10n/l10n_util.h"

namespace {

void ExecuteScriptInBackgroundPage(Profile* profile,
                                   const std::string& extension_id,
                                   const std::string& script) {
  extensions::ProcessManager* manager =
      extensions::ExtensionSystem::Get(profile)->process_manager();
  extensions::ExtensionHost* host =
      manager->GetBackgroundHostForExtension(extension_id);
  if (host == NULL) {
    DLOG(ERROR) << "Extension " << extension_id << " has no background page.";
    return;
  }
  // std::string script2 =
  //     "window.domAutomationController.setAutomationId(0);" + script;
  host->render_view_host()->GetMainFrame()->
      ExecuteJavaScriptForTests(base::UTF8ToUTF16(script));
}

} // namespace

namespace tor_settings {

TorOptionsHandler::TorOptionsHandler()
    : page_initialized_(false),
      weak_ptr_factory_(this) {
}

TorOptionsHandler::~TorOptionsHandler() {
}

void TorOptionsHandler::GetLocalizedValues(base::DictionaryValue* values) {
  DCHECK(values);

  static OptionsStringResource resources[] = {
    { "torSettingsTitle", IDS_TOR_SETTINGS_TITLE },
    { "sectionTitleTorProxy", IDS_TOR_SETTINGS_SECTION_TITLE_PROXY },
    { "proxyShowProxySection", IDS_TOR_SETTINGS_SHOW_PROXY_SECTION },
    { "torsettings_useProxy_type", IDS_TOR_SETTINGS_USEPROXY_TYPE },
    { "torsettings_useProxy_type_socks4",
        IDS_TOR_SETTINGS_USEPROXY_TYPE_SOCKS4 },
    { "torsettings_useProxy_type_socks5",
        IDS_TOR_SETTINGS_USEPROXY_TYPE_SOCKS5 },
    { "torsettings_useProxy_type_http", IDS_TOR_SETTINGS_USEPROXY_TYPE_HTTP },
    { "torsettings_useProxy_address", IDS_TOR_SETTINGS_USEPROXY_ADDRESS },
    { "torsettings_useProxy_address_placeholder",
        IDS_TOR_SETTINGS_USEPROXY_ADDRESS_PLACEHOLDER },
    { "torsettings_useProxy_port", IDS_TOR_SETTINGS_USEPROXY_PORT },
    { "torsettings_useProxy_username", IDS_TOR_SETTINGS_USEPROXY_USERNAME },
    { "torsettings_optional", IDS_TOR_SETTINGS_OPTIONAL },
    { "torsettings_useProxy_password", IDS_TOR_SETTINGS_USEPROXY_PASSWORD },
    { "sectionTitleTorFirewall", IDS_TOR_SETTINGS_SECTION_TITLE_FIREWALL },
    { "firewallShowFirewallSection", IDS_TOR_SETTINGS_SHOW_FIREWALL_SECTION },
    { "torsettings_useFirewall_allowedPorts", IDS_TOR_SETTINGS_USEFIREWALL_ALLOWED_PORTS },
    { "sectionTitleTorISPBlock", IDS_TOR_SETTINGS_SECTION_TITLE_ISP_BLOCK },
    { "ispBlockShowISPBlockSection", IDS_TOR_SETTINGS_SHOW_ISP_BLOCK_SECTION },
    { "torsettings_useBridges_default", IDS_TOR_SETTINGS_USEBRIDGES_DEFAULT },
    { "torsettings_useBridges_type", IDS_TOR_SETTINGS_USEBRIDGES_TYPE },
    { "torsettings_useBridges_custom", IDS_TOR_SETTINGS_USEBRIDGES_CUSTOM },
    { "torsettings_useBridges_label", IDS_TOR_SETTINGS_USEBRIDGES_LABEL },
    { "torsettings_useBridges_placeholder",
        IDS_TOR_SETTINGS_USEBRIDGES_PLACEHOLDER },

    { "extensionControlled", IDS_OPTIONS_TAB_EXTENSION_CONTROLLED },
    { "extensionDisable", IDS_OPTIONS_TAB_EXTENSION_CONTROLLED_DISABLE },
  };

  OptionsPageUIHandlerStaticContainer::RegisterStrings(values, resources, arraysize(resources));

  // values->SetBoolean("usingNewProfilesUI", switches::IsNewAvatarMenu());
  values->SetBoolean("profileIsGuest",
                     Profile::FromWebUI(web_ui())->IsOffTheRecord());

  values->SetBoolean("profileIsSupervised",
                     Profile::FromWebUI(web_ui())->IsSupervised());
}

void TorOptionsHandler::RegisterMessages() {
  // web_ui()->RegisterMessageCallback(
  //     "becomeDefaultBrowser",
  //     base::Bind(&TorOptionsHandler::BecomeDefaultBrowser,
  //                base::Unretained(this)));
}

void TorOptionsHandler::Uninitialize() {
  registrar_.RemoveAll();
}

void TorOptionsHandler::PageLoadStarted() {
  page_initialized_ = false;
}

void TorOptionsHandler::InitializeHandler() {
  Profile* profile = Profile::FromWebUI(web_ui());
  PrefService* prefs = profile->GetPrefs();

    // Create our favicon data source.
  content::URLDataSource::Add(
      profile, new FaviconSource(profile, FaviconSource::FAVICON));

  // No preferences below this point may be modified by guest profiles.
  if (Profile::FromWebUI(web_ui())->IsGuestSession())
    return;

  profile_pref_registrar_.Init(prefs);
  // profile_pref_registrar_.Add(
  //     prefs::kNetworkPredictionOptions,
  //     base::Bind(&TorOptionsHandler::SetupNetworkPredictionControl,
  //                base::Unretained(this)));
}

void TorOptionsHandler::InitializePage() {
  page_initialized_ = true;

  Profile* profile = Profile::FromWebUI(web_ui());

  registrar_.Add(this,
                 chrome::NOTIFICATION_TOR_NETWORK_SETTINGS_READY,
                 content::Source<Profile>(profile));

  std::string script = "torlauncher.getTorNetworkSettingsForBrowserNative();";
  ExecuteScriptInBackgroundPage(profile,
                                extension_misc::kTorLauncherAppId,
                                script);
}

void TorOptionsHandler::Observe(
    int type,
    const content::NotificationSource& source,
    const content::NotificationDetails& details) {
  // Notifications are used to update the UI dynamically when settings change in
  // the background. If the UI is currently being loaded, no dynamic updates are
  // possible (as the DOM and JS are not fully loaded) or necessary (as
  // InitializePage() will update the UI at the end of the load).
  if (!page_initialized_)
    return;

  switch (type) {
    case chrome::NOTIFICATION_TOR_NETWORK_SETTINGS_READY: {
      scoped_ptr<base::Value> settings = make_scoped_ptr(
             content::Details<base::Value>(details).ptr());
      DLOG(INFO) << "NOTIFICATION_TOR_NETWORK_SETTINGS_READY: " <<
          "settings.get() == " << reinterpret_cast<int>(settings.get()) <<
          ", " <<
          "*settings.get() == " << *settings.get();

      web_ui()->CallJavascriptFunction("TorOptions.initializePageUIWithData",
                                      *settings.get());
    }
    break;

    default:
      DLOG(ERROR) << "Unexpected notification in TorOptionsHandler::Observe";
      break;
  }
}

} // namespace tor_settings
