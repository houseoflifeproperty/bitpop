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

#ifndef CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_CHAT_ITEM_VIEW_H_
#define CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_CHAT_ITEM_VIEW_H_

#pragma once

#include <list>

#include "base/timer/timer.h"
#include "chrome/browser/facebook_chat/facebook_chat_item.h"
#include "ui/gfx/animation/animation_delegate.h"
#include "ui/views/controls/button/button.h"
#include "ui/views/mouse_watcher.h"
#include "ui/views/view.h"
#include "ui/views/widget/widget.h"
#include "ui/views/widget/widget_observer.h"

class ChatbarView;
class ChatNotificationPopup;
class ExtensionPopup;

namespace gfx {
class Bitmap;
class Image;
}

namespace views {
class TextButton;
class ImageButton;
}

class ChatItemView : public views::View,
                     public views::ButtonListener,
                     public FacebookChatItem::Observer,
                     public views::WidgetObserver,
                     public gfx::AnimationDelegate,
                     public views::MouseWatcherListener {
public:
  ChatItemView(FacebookChatItem *model, ChatbarView *chatbar);
  virtual ~ChatItemView();

  // views::ButtonListener protocol
  virtual void ButtonPressed(views::Button* sender, const ui::Event& event) OVERRIDE;

  // Overridden from views::View:
  virtual void Layout() OVERRIDE;
  virtual gfx::Size GetPreferredSize() OVERRIDE;

  // FacebookChatItem::Observer protocol
  virtual void OnChatUpdated(FacebookChatItem *source) OVERRIDE;

  // ui::AnimationDelegate implementation.
  virtual void AnimationProgressed(const gfx::Animation* animation) OVERRIDE;

  // Overridden from MouseWatcherListener
  virtual void MouseMovedOutOfHost() OVERRIDE;

  void Close(bool should_animate);

  void ActivateChat();
  void NotifyUnread();

  void ShowNotificationPopupIfNeeded();
  void CloseNotificationPopupIfNeeded();

  gfx::Rect RectForChatPopup();
  gfx::Rect RectForNotificationPopup();

  const FacebookChatItem* GetModel() const;

  SkBitmap* notification_icon() const { return notification_icon_; }

  int GetRightOffsetForText() const;

protected:
  // Overridden from views::View:
  virtual void OnPaint(gfx::Canvas* canvas) OVERRIDE;

  // views::Widget::Observer
  virtual void OnWidgetClosing(views::Widget* widget) OVERRIDE;

  virtual void UpdateNotificationIcon();

private:

  void StatusChanged();
  void TimerFired();

  FacebookChatItem *model_;

  ChatbarView *chatbar_;

  views::TextButton *openChatButton_;

  views::ImageButton *close_button_;

  SkColor close_button_bg_color_;

  ExtensionPopup *chat_popup_;
  ChatNotificationPopup* notification_popup_;

  typedef base::OneShotTimer<ChatItemView> ChatTimer;
  typedef std::list<ChatTimer*> TimerList;
  TimerList timers_;

  bool isMouseOverNotification_;

  SkBitmap *notification_icon_;

  scoped_ptr<views::MouseWatcher> mouse_watcher_;
};

#endif  // CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_CHAT_ITEM_VIEW_H_
