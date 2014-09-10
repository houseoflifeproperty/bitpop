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

#ifndef CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_EXTENSION_CHAT_POPUP_H_
#define CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_EXTENSION_CHAT_POPUP_H_

#include "base/callback.h"
#include "base/compiler_specific.h"
#include "chrome/browser/ui/tabs/tab_strip_model_observer.h"
#include "chrome/browser/ui/views/extensions/extension_view_views.h"
#include "content/public/browser/notification_observer.h"
#include "content/public/browser/notification_registrar.h"
#include "ui/views/bubble/bubble_delegate.h"
#include "ui/views/focus/widget_focus_manager.h"
#include "url/gurl.h"

#if defined(USE_AURA)
#include "ui/wm/public/activation_change_observer.h"
#endif

class Browser;
namespace views {
class Widget;
}

namespace content {
class DevToolsAgentHost;
}

namespace extensions {
class ExtensionViewHost;
}

class ExtensionChatPopup : public views::BubbleDelegateView,
#if defined(USE_AURA)
                       public aura::client::ActivationChangeObserver,
#endif
                       public ExtensionViewViews::Container,
                       public content::NotificationObserver,
                       public TabStripModelObserver {
 public:
  virtual ~ExtensionChatPopup();

  // Create and show a popup with |url| positioned adjacent to |anchor_view|.
  // |browser| is the browser to which the pop-up will be attached.  NULL is a
  // valid parameter for pop-ups not associated with a browser.
  // The positioning of the pop-up is determined by |arrow| according to the
  // following logic:  The popup is anchored so that the corner indicated by the
  // value of |arrow| remains fixed during popup resizes.  If |arrow| is
  // BOTTOM_*, then the popup 'pops up', otherwise the popup 'drops down'.
  // The actual display of the popup is delayed until the page contents
  // finish loading in order to minimize UI flashing and resizing.
  static ExtensionChatPopup* ShowPopup(const GURL& url,
                                       Browser* browser,
                                       views::View* anchor_view,
                                       views::BubbleBorder::Arrow arrow);

  extensions::ExtensionViewHost* host() const { return host_.get(); }

  // content::NotificationObserver overrides.
  virtual void Observe(int type,
                       const content::NotificationSource& source,
                       const content::NotificationDetails& details) OVERRIDE;

  // ExtensionViewViews::Container overrides.
  virtual void OnExtensionSizeChanged(ExtensionViewViews* view) OVERRIDE;

  // views::View overrides.
  virtual gfx::Size GetPreferredSize() OVERRIDE;

  // views::BubbleDelegateView overrides.
  virtual void OnWidgetDestroying(views::Widget* widget) OVERRIDE;
  virtual void OnWidgetActivationChanged(views::Widget* widget,
                                         bool active) OVERRIDE;

#if defined(USE_AURA)
  // aura::client::ActivationChangeObserver overrides.
  virtual void OnWindowActivated(aura::Window* gained_active,
                                 aura::Window* lost_active) OVERRIDE;
#endif

  // TabStripModelObserver overrides.
  virtual void ActiveTabChanged(content::WebContents* old_contents,
                                content::WebContents* new_contents,
                                int index,
                                int reason) OVERRIDE;

  // The min/max height of popups.
  static const int kMinWidth;
  static const int kMinHeight;
  static const int kMaxWidth;
  static const int kMaxHeight;

 private:
  ExtensionChatPopup(extensions::ExtensionViewHost* host,
                 views::View* anchor_view,
                 views::BubbleBorder::Arrow arrow);

  // Show the bubble, focus on its content, and register listeners.
  void ShowBubble();

  // The contained host for the view.
  scoped_ptr<extensions::ExtensionViewHost> host_;

  content::NotificationRegistrar registrar_;

  DISALLOW_COPY_AND_ASSIGN(ExtensionPopup);
};

#include "base/compiler_specific.h"
#include "chrome/browser/extensions/extension_host.h"
#include "chrome/browser/ui/views/extensions/extension_view_views.h"
#include "content/public/browser/notification_observer.h"
#include "googleurl/src/gurl.h"
#include "ui/views/bubble/bubble_delegate.h"
#include "ui/views/focus/widget_focus_manager.h"

class Browser;

class ExtensionChatPopup : public views::BubbleDelegateView,
                       public ExtensionViewViews::Container,
                       public content::NotificationObserver,
                       public views::WidgetFocusChangeListener {
 public:
  virtual ~ExtensionChatPopup();

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
  static ExtensionChatPopup* ShowPopup(
      const GURL& url,
      Browser* browser,
      views::View* anchor_view,
      views::BubbleBorder::Arrow arrow_location);

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

 private:
  ExtensionChatPopup(Browser* browser,
                 extensions::ExtensionHost* host,
                 views::View* anchor_view,
                 views::BubbleBorder::Arrow arrow_location);

  // Show the bubble, focus on its content, and register listeners.
  void ShowBubble();
//public:
  void CloseBubble();
//private:
  // The contained host for the view.
  scoped_ptr<extensions::ExtensionHost> extension_host_;

  // Flag used to indicate if the pop-up should open a devtools window once
  // it is shown inspecting it.
  bool inspect_with_devtools_;

  content::NotificationRegistrar registrar_;

  base::WeakPtrFactory<ExtensionChatPopup> close_bubble_factory_;

  DISALLOW_COPY_AND_ASSIGN(ExtensionChatPopup);
};

#endif  // CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_EXTENSION_CHAT_POPUP_H_
