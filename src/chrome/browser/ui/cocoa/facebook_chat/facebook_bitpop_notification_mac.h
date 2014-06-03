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

#ifndef CHROME_BROWSER_UI_COCOA_FACEBOK_CHAT_FACEBOOK_BITPOP_NOTIFICATION_MAC_H_
#define CHROME_BROWSER_UI_COCOA_FACEBOK_CHAT_FACEBOOK_BITPOP_NOTIFICATION_MAC_H_

#pragma once

#include "base/compiler_specific.h"
#include "chrome/browser/facebook_chat/facebook_bitpop_notification.h"

class FacebookProfileImageFetcherDelegate;
class Profile;

class FacebookBitpopNotificationMac : public FacebookBitpopNotification {
public:
  FacebookBitpopNotificationMac(Profile *profile);
  virtual ~FacebookBitpopNotificationMac();

  Profile* profile() const { return profile_; }

  virtual void ClearNotification() OVERRIDE;
  virtual void NotifyUnreadMessagesWithLastUser(int num_unread,
                                                const std::string& user_id) OVERRIDE;

private:
  Profile* const profile_;
  FacebookProfileImageFetcherDelegate *delegate_;
};

#endif  // CHROME_BROWSER_UI_COCOA_FACEBOK_CHAT_FACEBOOK_BITPOP_NOTIFICATION_MAC_H_
