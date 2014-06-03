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

#ifndef CHROME_BROWSER_UI_WEBUI_OPTIONS_BITPOP_UNCENSOR_FILTER_HANDLER_H_
#define CHROME_BROWSER_UI_WEBUI_OPTIONS_BITPOP_UNCENSOR_FILTER_HANDLER_H_

#include "chrome/browser/ui/webui/options/bitpop_options_ui.h"

class KeywordEditorController;

namespace extensions {
class Extension;
}

namespace base {
	class ListValue;
}

namespace options {

class BitpopUncensorFilterHandler : public BitpopOptionsPageUIHandler {
 public:
  BitpopUncensorFilterHandler();
  virtual ~BitpopUncensorFilterHandler();

  // OptionsPageUIHandler implementation.
  virtual void GetLocalizedValues(
      base::DictionaryValue* localized_strings) OVERRIDE;
  virtual void InitializeHandler() OVERRIDE;
  virtual void InitializePage() OVERRIDE;

  virtual void RegisterMessages() OVERRIDE;

 private:

 	void ChangeUncensorExceptions(const base::ListValue* params);

  DISALLOW_COPY_AND_ASSIGN(BitpopUncensorFilterHandler);
};

}  // namespace options

#endif  // CHROME_BROWSER_UI_WEBUI_OPTIONS_BITPOP_UNCENSOR_FILTER_HANDLER_H_
