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

#ifndef CHROME_BROWSER_UI_COCOA_FACEBOOK_CHATBAR_MAC_H_
#define CHROME_BROWSER_UI_COCOA_FACEBOOK_CHATBAR_MAC_H_
#pragma once

#import <Cocoa/Cocoa.h>

#include "base/compiler_specific.h"
#include "chrome/browser/facebook_chat/facebook_chatbar.h"
#include "chrome/browser/facebook_chat/facebook_chat_manager.h"

@class FacebookChatbarController;
class Browser;

class FacebookChatbarMac : public FacebookChatbar {
  public:
    explicit FacebookChatbarMac(Browser *browser,
                                FacebookChatbarController *controller);
    virtual void AddChatItem(FacebookChatItem *chat_item) OVERRIDE;
    virtual void RemoveAll() OVERRIDE;

    virtual void Show() OVERRIDE;
    virtual void Hide() OVERRIDE;

    virtual Browser *browser() const OVERRIDE;

  private:
    Browser *browser_;

    FacebookChatbarController *controller_;
};

#endif  // CHROME_BROWSER_UI_COCOA_FACEBOOK_CHATBAR_MAC_H_

