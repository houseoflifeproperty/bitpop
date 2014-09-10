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

#ifndef CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_CHAT_NOTIFICATION_POPUP_H_
#define CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_CHAT_NOTIFICATION_POPUP_H_
#pragma once

#include <deque>
#include <string>

#include "ui/views/bubble/bubble_delegate.h"
#include "ui/views/controls/button/button.h"
#include "ui/views/controls/label.h"
#include "ui/views/focus/widget_focus_manager.h"

namespace views {
  class ImageButton;
}

class NotificationContainerView;

using views::BubbleDelegateView;
using views::BubbleBorder;

class ChatNotificationPopup : public BubbleDelegateView,
                              public views::ButtonListener {
public:
  static ChatNotificationPopup* Show(views::View* anchor_view,
      BubbleBorder::Arrow arrow_location);

  void PushMessage(const std::string& message);
  std::string PopMessage();
  int num_messages_remaining() const { return messages_.size(); }

  typedef std::deque<std::string> MessageContainer;
  const MessageContainer& GetMessages();

  // views::ButtonListener protocol
  virtual void ButtonPressed(views::Button* sender, const ui::Event& event) OVERRIDE;

  // views::View overrides
  virtual gfx::Size GetPreferredSize() OVERRIDE;

  // views::WidgetDelegateView overrides
  // virtual bool ShouldShowCloseButton() const OVERRIDE;
  // virtual bool ShouldShowWindowTitle() const OVERRIDE;
  // virtual base::string16 GetWindowTitle() const OVERRIDE;

  views::View* container_view();

private:

  ChatNotificationPopup(views::View* anchor_view,
                        BubbleBorder::Arrow arrow_location);

  MessageContainer messages_;
  NotificationContainerView* container_view_;
};

#endif  // CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_CHAT_NOTIFICATION_POPUP_H_
