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

#ifndef CHROME_BROWSER_UI_WEBUI_TOR_SERRINGS_TOR_OPTIONS_HANDLER_H_
#define CHROME_BROWSER_UI_WEBUI_TOR_SERRINGS_TOR_OPTIONS_HANDLER_H_


#include <vector>

#include "base/basictypes.h"
#include "base/compiler_specific.h"
#include "base/memory/ref_counted.h"
#include "base/memory/scoped_ptr.h"
#include "base/memory/weak_ptr.h"
#include "base/prefs/pref_change_registrar.h"
#include "base/prefs/pref_member.h"
#include "base/scoped_observer.h"
#include "base/values.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/shell_integration.h"
#include "chrome/browser/ui/host_desktop.h"
#include "chrome/browser/ui/webui/options/options_ui.h"
#include "chrome/browser/ui/webui/tor_settings/tor_options_ui.h"
#include "components/search_engines/template_url_service_observer.h"
#include "components/signin/core/browser/signin_manager_base.h"
#include "content/public/browser/notification_observer.h"
#include "content/public/browser/notification_registrar.h"
#include "extensions/browser/extension_registry_observer.h"
#include "google_apis/gaia/google_service_auth_error.h"
#include "ui/base/models/table_model_observer.h"
#include "ui/shell_dialogs/select_file_dialog.h"

namespace base {
class Value;
}

namespace tor_settings {

// Chrome browser options page UI handler.
class TorOptionsHandler
    : public options::OptionsPageUIHandler,
      public content::NotificationObserver {
 public:
  TorOptionsHandler();
  ~TorOptionsHandler() override;

  // OptionsPageUIHandler implementation.
  void GetLocalizedValues(base::DictionaryValue* values) override;
  void PageLoadStarted() override;
  void InitializeHandler() override;
  void InitializePage() override;
  void RegisterMessages() override;
  void Uninitialize() override;

 private:
  // content::NotificationObserver implementation.
  void Observe(int type,
                       const content::NotificationSource& source,
                       const content::NotificationDetails& details) override;

  // Updates the UI with the given state for the default browser.
  void SetDefaultBrowserUIString(int status_string_id);

  // C++ functions called from the tor settings page Javascript
  // void CancelTorSettingsChange(const base::ListValue *args);
  void SaveTorSettings(const base::ListValue* args);

  bool page_initialized_;

  PrefChangeRegistrar profile_pref_registrar_;

  // Used to get WeakPtr to self for use on the UI thread.
  base::WeakPtrFactory<TorOptionsHandler> weak_ptr_factory_;

  DISALLOW_COPY_AND_ASSIGN(TorOptionsHandler);
};

}  // namespace tor_settings

#endif  // CHROME_BROWSER_UI_WEBUI_TOR_SETTINGS_TOR_OPTIONS_HANDLER_H_
