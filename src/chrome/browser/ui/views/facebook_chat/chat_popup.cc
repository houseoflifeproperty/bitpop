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

#include "chrome/browser/ui/views/facebook_chat/chat_popup.h"

#include "base/bind.h"
#include "base/message_loop.h"
#include "chrome/browser/extensions/extension_process_manager.h"
#include "chrome/browser/extensions/extension_system.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/ui/browser.h"
#include "chrome/browser/ui/browser_window.h"
#include "chrome/common/chrome_notification_types.h"
#include "content/public/browser/notification_details.h"
#include "content/public/browser/notification_source.h"
#include "content/public/browser/web_contents.h"
#include "ui/views/layout/fill_layout.h"
#include "ui/views/widget/widget.h"

using content::WebContents;
using extensions::ExtensionHost;

// The minimum/maximum dimensions of the popup.
// The minimum is just a little larger than the size of the button itself.
// The maximum is an arbitrary number that should be smaller than most screens.
const int ChatPopup::kMinWidth = 25;
const int ChatPopup::kMinHeight = 25;
const int ChatPopup::kMaxWidth = 270 + 4;
const int ChatPopup::kMaxHeight = 320 + 4 + 7;

ChatPopup::ChatPopup(
    Browser* browser,
    ExtensionHost* host,
    views::View* anchor_view,
    BubbleBorder::ArrowLocation arrow_location)
    : BubbleDelegateView(anchor_view, arrow_location),
      extension_host_(host) {
  // Adjust the margin so that contents fit better.
  int margin = BubbleBorder::GetCornerRadius() / 2;
  set_margins(gfx::Insets(margin, margin, margin, margin));
  SetLayoutManager(new views::FillLayout());
  AddChildView(host->view());
  host->view()->SetContainer(this);
#if defined(OS_WIN) && !defined(USE_AURA)
  // Use OnNativeFocusChange to check for child window activation on deactivate.
  set_close_on_deactivate(false);
#else
  set_close_on_deactivate(false); // it's actually the same, leaved to
                                  // preserve original source structure
#endif

  // Wait to show the popup until the contained host finishes loading.
  registrar_.Add(this, content::NOTIFICATION_LOAD_COMPLETED_MAIN_FRAME,
                 content::Source<WebContents>(host->host_contents()));

  // Listen for the containing view calling window.close();
  registrar_.Add(this, chrome::NOTIFICATION_EXTENSION_HOST_VIEW_SHOULD_CLOSE,
                 content::Source<Profile>(host->profile()));
}

ChatPopup::~ChatPopup() {
  views::WidgetFocusManager::GetInstance()->RemoveFocusChangeListener(this);
}

void ChatPopup::Observe(int type,
                             const content::NotificationSource& source,
                             const content::NotificationDetails& details) {
  switch (type) {
    case content::NOTIFICATION_LOAD_COMPLETED_MAIN_FRAME:
      DCHECK(content::Source<WebContents>(host()->host_contents()) == source);
      // Show when the content finishes loading and its width is computed.
      host()->host_contents()->Focus();
      break;
    case chrome::NOTIFICATION_EXTENSION_HOST_VIEW_SHOULD_CLOSE:
      // If we aren't the host of the popup, then disregard the notification.
      if (content::Details<ExtensionHost>(host()) == details)
        GetWidget()->Close();
      break;
    default:
      NOTREACHED() << L"Received unexpected notification";
  }
}

void ChatPopup::OnExtensionSizeChanged(ExtensionViewViews* view) {
  SizeToContents();
}

gfx::Size ChatPopup::GetPreferredSize() {
  // Constrain the size to popup min/max.
  gfx::Size sz = views::View::GetPreferredSize();
  sz.set_width(std::max(kMinWidth, std::min(kMaxWidth, sz.width())));
  sz.set_height(std::max(kMinHeight, std::min(kMaxHeight, sz.height())));
  return sz;
}

void ChatPopup::OnNativeFocusChange(gfx::NativeView focused_before,
                                         gfx::NativeView focused_now) {
  // TODO(msw): Implement something equivalent for Aura. See crbug.com/106958
#if defined(OS_WIN) && !defined(USE_AURA)
  // Don't close if a child of this window is activated (only needed on Win).
  // ChatPopups can create Javascipt dialogs; see crbug.com/106723.
  gfx::NativeView this_window = GetWidget()->GetNativeView();
  gfx::NativeView parent_window = anchor_view()->GetWidget()->GetNativeView();
  if (focused_now == this_window ||
      ::GetWindow(focused_now, GW_OWNER) == this_window) {
    return;
  }
  gfx::NativeView focused_parent = focused_now;
  while (focused_parent = ::GetParent(focused_parent)) {
    if (this_window == focused_parent)
      return;
    if (parent_window == focused_parent)
      GetWidget()->Close();
  }
  //GetWidget()->Close();
#endif
}

// static
ChatPopup* ChatPopup::ShowPopup(
    const GURL& url,
    Browser* browser,
    views::View* anchor_view,
    BubbleBorder::ArrowLocation arrow_location) {
  ExtensionProcessManager* manager =
      extensions::ExtensionSystem::Get(browser->profile())->process_manager();
  ExtensionHost* host = manager->CreatePopupHost(url, browser);
  ChatPopup* popup = new ChatPopup(browser, host, anchor_view,
      arrow_location);
  BubbleDelegateView::CreateBubble(popup);

  // If the host had somehow finished loading, then we'd miss the notification
  // and not show.  This seems to happen in single-process mode.
  //if (host->did_stop_loading())
  popup->ShowBubble();

  return popup;
}

void ChatPopup::ShowBubble() {
  Show();

  // Focus on the host contents when the bubble is first shown.

  // Listen for widget focus changes after showing (used for non-aura win).
  views::WidgetFocusManager::GetInstance()->AddFocusChangeListener(this);
}
