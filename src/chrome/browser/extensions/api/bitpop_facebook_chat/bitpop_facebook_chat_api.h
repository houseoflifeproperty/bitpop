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

#ifndef CHROME_BROWSER_EXTENSIONS_API_BITPOP_FACEBOOK_CHAT_BITPOP_FACEBOOK_CHAT_API_H_
#define CHROME_BROWSER_EXTENSIONS_API_BITPOP_FACEBOOK_CHAT_BITPOP_FACEBOOK_CHAT_API_H_

#include <string>
#include "chrome/browser/extensions/chrome_extension_function.h"

class TabContents;


class BitpopFacebookChatSetFriendsSidebarVisibleFunction : public ChromeSyncExtensionFunction {
  virtual ~BitpopFacebookChatSetFriendsSidebarVisibleFunction() {}
  virtual bool RunSync() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION("bitpop.facebookChat.setFriendsSidebarVisible",
    BITPOP_FACEBOOKCHAT_SETFRIENDSSIDEBARVISIBLE);
};

class BitpopFacebookChatGetFriendsSidebarVisibleFunction : public ChromeSyncExtensionFunction {
  virtual ~BitpopFacebookChatGetFriendsSidebarVisibleFunction() {}
  virtual bool RunSync() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION("bitpop.facebookChat.getFriendsSidebarVisible",
      BITPOP_FACEBOOKCHAT_GETFRIENDSSIDEBARVISIBLE);
};

class BitpopFacebookChatAddChatFunction : public ChromeSyncExtensionFunction {
  virtual ~BitpopFacebookChatAddChatFunction() {}
  virtual bool RunSync() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION("bitpop.facebookChat.addChat",
      BITPOP_FACEBOOKCHAT_ADDCHAT);
};

class BitpopFacebookChatNewIncomingMessageFunction : public ChromeSyncExtensionFunction {
  virtual ~BitpopFacebookChatNewIncomingMessageFunction() {}
  virtual bool RunSync() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION("bitpop.facebookChat.newIncomingMessage",
      BITPOP_FACEBOOKCHAT_NEWINCOMINGMESSAGE);
};

class BitpopFacebookChatLoggedOutFacebookSessionFunction : public ChromeSyncExtensionFunction {
  virtual ~BitpopFacebookChatLoggedOutFacebookSessionFunction() {}
  virtual bool RunSync() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION("bitpop.facebookChat.loggedOutFacebookSession",
      BITPOP_FACEBOOKCHAT_LOGGEDOUTFACEBOOKSESSION);
};

class BitpopFacebookChatLoggedInFacebookSessionFunction : public ChromeSyncExtensionFunction {
  virtual ~BitpopFacebookChatLoggedInFacebookSessionFunction() {}
  virtual bool RunSync() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION("bitpop.facebookChat.loggedInFacebookSession",
      BITPOP_FACEBOOKCHAT_LOGGEDINFACEBOOKSESSION);
};

class BitpopFacebookChatSetGlobalMyUidForProfileFunction : public ChromeSyncExtensionFunction {
  virtual ~BitpopFacebookChatSetGlobalMyUidForProfileFunction() {}
  virtual bool RunSync() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION("bitpop.facebookChat.setGlobalMyUidForProfile",
      BITPOP_FACEBOOKCHAT_SETGLOBALMYUIDFORPROFILE);
};

#endif  // CHROME_BROWSER_EXTENSIONS_API_BITPOP_FACEBOOK_CHAT_BITPOP_FACEBOOK_CHAT_API_H_

