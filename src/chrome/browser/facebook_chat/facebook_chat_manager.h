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

#ifndef CHROME_BROWSER_FACEBOOK_CHAT_FACEBOOK_CHAT_MANAGER_H_
#define CHROME_BROWSER_FACEBOOK_CHAT_FACEBOOK_CHAT_MANAGER_H_
#pragma once

#include <string>
#include <set>

#include "base/basictypes.h"
#include "base/containers/hash_tables.h"
#include "base/observer_list.h"
#include "base/strings/string16.h"
#include "chrome/browser/facebook_chat/facebook_chat_item.h"
#include "chrome/browser/facebook_chat/facebook_chat_create_info.h"
#include "components/keyed_service/core/keyed_service.h"

class Browser;
class Profile;


class FacebookChatManager : public KeyedService {
  public:
    FacebookChatManager();

    virtual void Shutdown() OVERRIDE;

    FacebookChatItem* GetItem(const std::string &jid);

    FacebookChatItem* CreateFacebookChat(const FacebookChatCreateInfo &info);

    void RemoveItem(const std::string &jid);

    void AddNewUnreadMessage(const std::string &jid,
        const std::string &message);

    void ChangeItemStatus(const std::string &jid,
        const std::string &status);
    void DisplayChatNotificationBalloonIfNeeded(
        const base::string16& title,
        const base::string16& contents);

    class Observer {
      public:
        virtual void ModelChanged() = 0;

        virtual void ManagerIsGoingDown() {}
      private:
        virtual ~Observer() {}
    };

    // Allow objects to observe the download creation process.
    void AddObserver(Observer* observer);

    // Remove a download observer from ourself.
    void RemoveObserver(Observer* observer);

    // Returns true if initialized properly.
    bool Init(Profile *profile);

    int total_unread() const;
    std::string global_my_uid() const { return global_my_uid_; }
    void set_global_my_uid(const std::string& uid) { global_my_uid_ = uid; }

    bool has_message_id(const std::string& msg_id) const;
    void AddMessageId(const std::string& msg_id);

  protected:
    virtual ~FacebookChatManager();
  private:
    void NotifyModelChanged();

    typedef std::set<FacebookChatItem*> ChatSet;
    typedef base::hash_map<std::string, FacebookChatItem*> ChatMap;
    typedef std::set<std::string> MessageIdSet;

    std::string global_my_uid_;
    ChatSet chats_;
    ChatMap jid_chats_map_;
    // Set of message ids to account for duplicate message notifications
    // Different messages have different IDs
    MessageIdSet message_id_set_;

    Profile *profile_;

    bool shutdown_needed_;

    ObserverList<Observer> observers_;

    static int id_count_;

    DISALLOW_COPY_AND_ASSIGN(FacebookChatManager);
};

#endif  // CHROME_BROWSER_FACEBOOK_CHAT_FACEBOOK_CHAT_MANAGER_H_
