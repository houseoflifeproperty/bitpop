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

#ifndef CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_CHAT_POPUP_H_
#define CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_CHAT_POPUP_H_
#pragma once

#include "base/compiler_specific.h"
#include "chrome/browser/extensions/extension_host.h"
#include "chrome/browser/ui/views/extensions/extension_view_views.h"
#include "ui/views/bubble/bubble_delegate.h"
#include "content/public/browser/notification_observer.h"
#include "googleurl/src/gurl.h"
#include "ui/views/focus/widget_focus_manager.h"

class Browser;

using views::BubbleDelegateView;
using views::BubbleBorder;

class ChatPopup : public BubbleDelegateView,
                  public ExtensionViewViews::Container,
                  public content::NotificationObserver,
                  public views::WidgetFocusChangeListener {
 public:
  virtual ~ChatPopup();

  // Create and show a popup with |url| positioned adjacent to |anchor_view|.
  // |browser| is the browser to which the pop-up will be attached.  NULL is a
  // valid parameter for pop-ups not associated with a browser.
  // The positioning of the pop-up is determined by |arrow_location| according
  // to the following logic:  The popup is anchored so that the corner indicated
  // by value of |arrow_location| remains fixed during popup resizes.
  // If |arrow_location| is BOTTOM_*, then the popup 'pops up', otherwise
  // the popup 'drops down'.
  // The actual display of the popup is delayed until the page contents
  // finish loading in order to minimize UI flashing and resizing.
  static ChatPopup* ShowPopup(
      const GURL& url,
      Browser* browser,
      views::View* anchor_view,
      BubbleBorder::ArrowLocation arrow_location);

  extensions::ExtensionHost* host() const { return extension_host_.get(); }

  // content::NotificationObserver overrides.
  virtual void Observe(int type,
                       const content::NotificationSource& source,
                       const content::NotificationDetails& details) OVERRIDE;

  // ExtensionView::Container overrides.
  virtual void OnExtensionSizeChanged(ExtensionViewViews* view) OVERRIDE;

  // views::View overrides.
  virtual gfx::Size GetPreferredSize() OVERRIDE;

  // views::WidgetFocusChangeListener overrides.
  virtual void OnNativeFocusChange(gfx::NativeView focused_before,
                                   gfx::NativeView focused_now) OVERRIDE;

  // The min/max height of popups.
  static const int kMinWidth;
  static const int kMinHeight;
  static const int kMaxWidth;
  static const int kMaxHeight;

  // WidgetDelegate overrides:
  //virtual views::View* GetInitiallyFocusedView() OVERRIDE;

 private:
  ChatPopup(Browser* browser,
            extensions::ExtensionHost* host,
            views::View* anchor_view,
            BubbleBorder::ArrowLocation arrow_location);

  // Show the bubble, focus on its content, and register listeners.
  void ShowBubble();

  // The contained host for the view.
  scoped_ptr<extensions::ExtensionHost> extension_host_;

  content::NotificationRegistrar registrar_;

  DISALLOW_COPY_AND_ASSIGN(ChatPopup);
};

#endif  // CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_CHAT_POPUP_H_
