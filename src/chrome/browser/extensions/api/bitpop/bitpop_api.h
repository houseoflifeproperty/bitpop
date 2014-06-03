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

#ifndef CHROME_BROWSER_EXTENSIONS_API_BITPOP_BITPOP_API_H_
#define CHROME_BROWSER_EXTENSIONS_API_BITPOP_BITPOP_API_H_

#include <string>
#include "chrome/browser/extensions/extension_function.h"

class BitpopGetSyncStatusFunction : public SyncExtensionFunction {
 public:
  virtual bool RunImpl() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION_NAME("bitpop.getSyncStatus");
 protected:
  virtual ~BitpopGetSyncStatusFunction() {}
};

class BitpopLaunchFacebookSyncFunction : public SyncExtensionFunction {
 public:
  virtual bool RunImpl() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION_NAME("bitpop.launchFacebookSync");
 protected:
  virtual ~BitpopLaunchFacebookSyncFunction() {}
};

#endif	// CHROME_BROWSER_EXTENSIONS_API_BITPOP_BITPOP_API_H_
