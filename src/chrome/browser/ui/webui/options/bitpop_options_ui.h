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

#ifndef CHROME_BROWSER_UI_WEBUI_OPTIONS_BITPOP_OPTIONS_UI_H_
#define CHROME_BROWSER_UI_WEBUI_OPTIONS_BITPOP_OPTIONS_UI_H_

#include <string>
#include <vector>

#include "base/compiler_specific.h"
#include "base/memory/scoped_ptr.h"
#include "chrome/browser/ui/webui/chrome_url_data_manager.h"
#include "content/public/browser/notification_observer.h"
#include "content/public/browser/notification_registrar.h"
#include "content/public/browser/notification_types.h"
#include "content/public/browser/web_ui_controller.h"
#include "content/public/browser/web_ui_message_handler.h"
#include "ui/base/layout.h"

class AutocompleteResult;

namespace base {
class DictionaryValue;
class ListValue;
}

namespace options {

// The base class handler of Javascript messages of options pages.
class BitpopOptionsPageUIHandler : public content::WebUIMessageHandler,
                                   public content::NotificationObserver {
 public:
  // Key for identifying the Settings App localized_strings in loadTimeData.
  static const char kSettingsAppKey[];

  BitpopOptionsPageUIHandler();
  virtual ~BitpopOptionsPageUIHandler();

  // Is this handler enabled?
  virtual bool IsEnabled();

  // Collects localized strings for options page.
  virtual void GetLocalizedValues(base::DictionaryValue* localized_strings) = 0;

  virtual void PageLoadStarted() {}

  // Will be called only once in the life time of the handler. Generally used to
  // add observers, initializes preferences, or start asynchronous calls from
  // various services.
  virtual void InitializeHandler() {}

  // Initialize the page. Called once the DOM is available for manipulation.
  // This will be called when a RenderView is re-used (when navigated to with
  // back/forward or session restored in some cases) or when created.
  virtual void InitializePage() {}

  // Uninitializes the page.  Called just before the object is destructed.
  virtual void Uninitialize() {}

  // WebUIMessageHandler implementation.
  virtual void RegisterMessages() OVERRIDE {}

  // content::NotificationObserver implementation.
  virtual void Observe(int type,
                       const content::NotificationSource& source,
                       const content::NotificationDetails& details) OVERRIDE {}

 protected:
  struct OptionsStringResource {
    // The name of the resource in templateData.
    const char* name;
    // The .grd ID for the resource (IDS_*).
    int id;
    // The .grd ID of the string to replace $1 in |id|'s string. If zero or
    // omitted (default initialized), no substitution is attempted.
    int substitution_id;
  };

  // A helper to simplify string registration in WebUI for strings which do not
  // change at runtime and optionally contain a single substitution.
  static void RegisterStrings(base::DictionaryValue* localized_strings,
                              const OptionsStringResource* resources,
                              size_t length);

  // Registers string resources for a page's header and tab title.
  static void RegisterTitle(base::DictionaryValue* localized_strings,
                            const std::string& variable_name,
                            int title_id);

  content::NotificationRegistrar registrar_;

 private:
  DISALLOW_COPY_AND_ASSIGN(BitpopOptionsPageUIHandler);
};

// An interface for common operations that a host of OptionsPageUIHandlers
// should provide.
class BitpopOptionsPageUIHandlerHost {
 public:
  virtual void InitializeHandlers() = 0;

 protected:
  virtual ~BitpopOptionsPageUIHandlerHost() {}
};

// The WebUI for chrome:bitpop-settings-frame.
class BitpopOptionsUI : public content::WebUIController,
               			public BitpopOptionsPageUIHandlerHost {
 public:
  explicit BitpopOptionsUI(content::WebUI* web_ui);
  virtual ~BitpopOptionsUI();

  static base::RefCountedMemory* GetFaviconResourceBytes(
      ui::ScaleFactor scale_factor);

  // Overridden from OptionsPageUIHandlerHost:
  virtual void InitializeHandlers() OVERRIDE;

  // Overridden from content::WebUIController:
  virtual void RenderViewCreated(content::RenderViewHost* render_view_host)
      OVERRIDE;
  virtual void RenderViewReused(content::RenderViewHost* render_view_host)
      OVERRIDE;

 private:
  // Adds OptionsPageUiHandler to the handlers list if handler is enabled.
  void AddOptionsPageUIHandler(base::DictionaryValue* localized_strings,
                               BitpopOptionsPageUIHandler* handler);

  bool initialized_handlers_;

  std::vector<BitpopOptionsPageUIHandler*> handlers_;

  DISALLOW_COPY_AND_ASSIGN(BitpopOptionsUI);
};

}  // namespace options

#endif  // CHROME_BROWSER_UI_WEBUI_OPTIONS_BITPOP_OPTIONS_UI_H_
