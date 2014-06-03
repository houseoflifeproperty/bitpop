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

#ifndef CHROME_BROWSER_FACEBOOK_CHAT_FACEBOOK_UNREAD_MESSAGE_H_
#define CHROME_BROWSER_FACEBOOK_CHAT_FACEBOOK_UNREAD_MESSAGE_H_
#pragma once

#include <string>
#include "base/observer_list.h"
#include "base/timer.h"
#include "base/scoped_ptr.h"

class FacebookUnreadMessage {
  public:
    FacebookUnreadMessage(const std::string &message);
    ~FacebookUnreadMessage();

    std::string message() const;
    bool isVisible() const;

    void StartCountdown();

    virtual void Show() = 0;
    virtual void Hide() = 0;

    // class Observer {
    //   public:
    //     virtual ShouldHide(FacebookUnreadMessage *unread_message) = 0;
    // };

    // void AddObserver(Observer *observer);
    // void RemoveObserver(Observer *observer);

  private:
    std::string message_;
    bool isVisible_;

    OneShotTimer<FacebookUnreadMessage> timer_;
    // ObserverList<Observer> observers_;
};

#endif  // CHROME_BROWSER_FACEBOOK_CHAT_FACEBOOK_UNREAD_MESSAGE_H_
