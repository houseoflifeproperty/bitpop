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

#ifndef CHROME_BROWSER_UI_WEBUI_OPTIONS_BITPOP_OPTIONS_HANDLER_H_
#define CHROME_BROWSER_UI_WEBUI_OPTIONS_BITPOP_OPTIONS_HANDLER_H_

#include "base/prefs/pref_member.h"
#include "chrome/browser/ui/webui/options/bitpop_options_ui.h"

namespace options {

// Chrome browser options page UI handler.
class BitpopOptionsHandler
    : public BitpopOptionsPageUIHandler {
 public:
  BitpopOptionsHandler();
  virtual ~BitpopOptionsHandler();

  // OptionsPageUIHandler implementation.
  virtual void GetLocalizedValues(base::DictionaryValue* values) OVERRIDE;
  virtual void PageLoadStarted() OVERRIDE;
  virtual void InitializeHandler() OVERRIDE;
  virtual void InitializePage() OVERRIDE;
  virtual void RegisterMessages() OVERRIDE;

 private:
  void OpenFacebookNotificationsOptions(const base::ListValue * params);

  bool page_initialized_;

  DISALLOW_COPY_AND_ASSIGN(BitpopOptionsHandler);
};

}  // namespace options

#endif  // CHROME_BROWSER_UI_WEBUI_OPTIONS_BITPOP_OPTIONS_HANDLER_H_
