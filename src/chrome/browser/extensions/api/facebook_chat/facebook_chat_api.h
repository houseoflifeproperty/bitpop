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

#ifndef CHROME_BROWSER_EXTENSIONS_EXTENSION_FACEBOOK_CHAT_API_H_
#define CHROME_BROWSER_EXTENSIONS_EXTENSION_FACEBOOK_CHAT_API_H_

#include <string>
#include "chrome/browser/extensions/extension_function.h"

class TabContents;

// Base class for facebook chat function APIs.
// class FacebookChatFunction : public SyncExtensionFunction {
//  public:
//   virtual bool RunImpl();
//  private:
//   virtual bool RunImpl(TabContents* tab,
//                        const std::string& content_id,
//                        const DictionaryValue& details) = 0;
// };

class SetFriendsSidebarVisibleFunction : public SyncExtensionFunction {
 public:
  virtual bool RunImpl() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION_NAME("bitpop.facebookChat.setFriendsSidebarVisible");
 protected:
  virtual ~SetFriendsSidebarVisibleFunction() {}
};

class GetFriendsSidebarVisibleFunction : public SyncExtensionFunction {
 public:
  virtual bool RunImpl() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION_NAME("bitpop.facebookChat.getFriendsSidebarVisible");
 protected:
  virtual ~GetFriendsSidebarVisibleFunction() {}
};

class AddChatFunction : public SyncExtensionFunction {
  public:
    virtual bool RunImpl() OVERRIDE;
    DECLARE_EXTENSION_FUNCTION_NAME("bitpop.facebookChat.addChat");
  protected:
    virtual ~AddChatFunction() {}
};

class NewIncomingMessageFunction: public SyncExtensionFunction {
  public:
    virtual bool RunImpl() OVERRIDE;
    DECLARE_EXTENSION_FUNCTION_NAME("bitpop.facebookChat.newIncomingMessage");
  protected:
    virtual ~NewIncomingMessageFunction() {}
};

class LoggedOutFacebookSessionFunction: public SyncExtensionFunction {
  public:
    virtual bool RunImpl() OVERRIDE;
    DECLARE_EXTENSION_FUNCTION_NAME("bitpop.facebookChat.loggedOutFacebookSession");
  protected:
    virtual ~LoggedOutFacebookSessionFunction() {}
};

class LoggedInFacebookSessionFunction: public SyncExtensionFunction {
  public:
    virtual bool RunImpl() OVERRIDE;
    DECLARE_EXTENSION_FUNCTION_NAME("bitpop.facebookChat.loggedInFacebookSession");
  protected:
    virtual ~LoggedInFacebookSessionFunction() {}

};

class SetGlobalMyUidForProfileFunction : public SyncExtensionFunction {
  public:
    virtual bool RunImpl() OVERRIDE;
    DECLARE_EXTENSION_FUNCTION_NAME("bitpop.facebookChat.setGlobalMyUidForProfile");
  protected:
    virtual ~SetGlobalMyUidForProfileFunction() {}
};

#endif  // CHROME_BROWSER_EXTENSIONS_EXTENSION_FACEBOOK_CHAT_API_H_

