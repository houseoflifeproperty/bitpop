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

#ifndef CHROME_BROWSER_FACEBOOK_CHAT_FACEBOOK_CHAT_ITEM_H_
#define CHROME_BROWSER_FACEBOOK_CHAT_FACEBOOK_CHAT_ITEM_H_
#pragma once

#include <string>
#include <list>

#include "base/observer_list.h"

class FacebookChatManager;

class FacebookChatItem {
  public:
    enum Status {
      AVAILABLE,
      IDLE,
      ERROR_STATUS,
      OFFLINE,
      COMPOSING
    };

    enum State {
      NORMAL = 0,
      REMOVING,
      ACTIVE_STATUS_CHANGED,
      HIGHLIGHT_STATUS_CHANGED,
      NUM_NOTIFICATIONS_CHANGED,
      STATUS_CHANGED
    };

    FacebookChatItem(FacebookChatManager *manager,
        const std::string &jid,
        const std::string &username,
        Status status);
    virtual ~FacebookChatItem();

    class Observer {
      public:
        virtual void OnChatUpdated(FacebookChatItem *source) = 0;
      protected:
        virtual ~Observer() {}
    };

    std::string jid() const;
    std::string username() const;
    Status status() const;
    unsigned int num_notifications() const;
    bool active() const;
    bool highlighted() const;
    State state() const;
    bool needs_activation() const;
    void set_needs_activation(bool value);

    void Remove();

    void AddNewUnreadMessage(const std::string &message);
    void ClearUnreadMessages();
    std::string GetMessageAtIndex(unsigned int index);

    void ChangeStatus(const std::string &status);

    void AddObserver(Observer* observer);
    void RemoveObserver(Observer* observer);
  private:
    friend class FacebookChatManager;

    void UpdateObservers();

    std::string jid_;
    std::string username_;
    Status status_;
    State state_;

    //unsigned int numNotifications_;
    std::vector<std::string> unreadMessages_;

    bool needsActivation_;

    // Our owning chat manager
    FacebookChatManager *manager_;

    ObserverList<Observer> observers_;
};

#endif  // CHROME_BROWSER_FACEBOOK_CHAT_FACEBOOK_CHAT_ITEM_H_

