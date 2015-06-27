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

// Copyright (c) 2012 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef CHROME_BROWSER_UI_WEBUI_TOR_SETTINGS_TOR_OPTIONS_UI_H_
#define CHROME_BROWSER_UI_WEBUI_TOR_SETTINGS_TOR_OPTIONS_UI_H_

#include <string>
#include <vector>

#include "base/callback_list.h"
#include "base/compiler_specific.h"
#include "base/memory/scoped_ptr.h"
#include "chrome/browser/ui/webui/options/options_ui.h"
#include "content/public/browser/notification_registrar.h"
#include "content/public/browser/web_contents_observer.h"
#include "content/public/browser/web_ui_controller.h"
#include "content/public/browser/web_ui_message_handler.h"
#include "ui/base/layout.h"

class AutocompleteResult;

namespace base {
class DictionaryValue;
class ListValue;
class RefCountedMemory;
}

namespace user_prefs {
class PrefRegistrySyncable;
}

namespace tor_settings {

class OptionsPageUIHandlerStaticContainer {
 public:
  // Key for identifying the Settings App localized_strings in loadTimeData.
  static const char kSettingsAppKey[];

  // A helper to simplify string registration in WebUI for strings which do not
  // change at runtime and optionally contain a single substitution.
  static void RegisterStrings(base::DictionaryValue* localized_strings,
                              const options::OptionsPageUIHandler::OptionsStringResource* resources,
                              size_t length);

  // Registers string resources for a page's header and tab title.
  static void RegisterTitle(base::DictionaryValue* localized_strings,
                            const std::string& variable_name,
                            int title_id);
};

// The WebUI for chrome:tor-settings-frame.
class OptionsUI : public content::WebUIController,
                  public content::WebContentsObserver,
                  public options::OptionsPageUIHandlerHost {
 public:
  typedef base::CallbackList<void()> OnFinishedLoadingCallbackList;

  explicit OptionsUI(content::WebUI* web_ui);
  virtual ~OptionsUI();

  // Registers a callback to be called once the settings frame has finished
  // loading on the HTML/JS side.
  scoped_ptr<OnFinishedLoadingCallbackList::Subscription>
      RegisterOnFinishedLoadingCallback(const base::Closure& callback);

  // Takes the suggestions from |result| and adds them to |suggestions| so that
  // they can be passed to a JavaScript function.
  static void ProcessAutocompleteSuggestions(
      const AutocompleteResult& result,
      base::ListValue* const suggestions);

  static base::RefCountedMemory* GetFaviconResourceBytes(
      ui::ScaleFactor scale_factor);

  static void RegisterProfilePrefs(user_prefs::PrefRegistrySyncable* registry);

  // Overridden from content::WebContentsObserver:
  virtual void DidStartProvisionalLoadForFrame(
      content::RenderFrameHost* render_frame_host,
      const GURL& validated_url,
      bool is_error_page,
      bool is_iframe_srcdoc) OVERRIDE;

  // Overridden from OptionsPageUIHandlerHost:
  virtual void InitializeHandlers() OVERRIDE;
  virtual void OnFinishedLoading() OVERRIDE;

 private:
  // Adds OptionsPageUiHandler to the handlers list if handler is enabled.
  void AddOptionsPageUIHandler(base::DictionaryValue* localized_strings,
                               options::OptionsPageUIHandler* handler);

  bool initialized_handlers_;

  std::vector<options::OptionsPageUIHandler*> handlers_;
  OnFinishedLoadingCallbackList on_finished_loading_callbacks_;

  DISALLOW_COPY_AND_ASSIGN(OptionsUI);
};

} // namespace tor_settings

#endif // CHROME_BROWSER_UI_WEBUI_TOR_SETTINGS_TOR_OPTIONS_UI_H_
