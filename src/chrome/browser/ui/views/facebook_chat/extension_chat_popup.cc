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

#include "chrome/browser/ui/views/facebook_chat/extension_chat_popup.h"

#include "base/bind.h"
#include "base/message_loop.h"
#include "chrome/browser/debugger/devtools_window.h"
#include "chrome/browser/extensions/extension_process_manager.h"
#include "chrome/browser/extensions/extension_system.h"
#include "chrome/browser/platform_util.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/ui/browser.h"
#include "chrome/browser/ui/browser_window.h"
#include "chrome/common/chrome_notification_types.h"
#include "content/public/browser/notification_details.h"
#include "content/public/browser/notification_source.h"
#include "content/public/browser/render_view_host.h"
#include "content/public/browser/web_contents.h"
#include "ui/gfx/insets.h"
#include "ui/views/layout/fill_layout.h"
#include "ui/views/widget/widget.h"

#if defined(USE_AURA)
#include "ui/aura/window.h"
#endif

#if defined(USE_ASH)
#include "ash/wm/window_animations.h"
#endif

using content::RenderViewHost;
using content::WebContents;

namespace {

// Returns true if |possible_parent| is a parent window of |child|.
bool IsParent(gfx::NativeView child, gfx::NativeView possible_parent) {
  if (!child)
    return false;
#if !defined(USE_AURA) && defined(OS_WIN)
  if (::GetWindow(child, GW_OWNER) == possible_parent)
    return true;
#endif
  gfx::NativeView parent = child;
  while ((parent = platform_util::GetParent(parent))) {
    if (possible_parent == parent)
      return true;
  }

  return false;
}

}  // namespace

// The minimum/maximum dimensions of the popup.
// The minimum is just a little larger than the size of the button itself.
// The maximum is an arbitrary number that should be smaller than most screens.
const int ExtensionChatPopup::kMinWidth = 25;
const int ExtensionChatPopup::kMinHeight = 25;
const int ExtensionChatPopup::kMaxWidth = 800;
const int ExtensionChatPopup::kMaxHeight = 600;

ExtensionChatPopup::ExtensionChatPopup(
    Browser* browser,
    extensions::ExtensionHost* host,
    views::View* anchor_view,
    views::BubbleBorder::ArrowLocation arrow_location)
    : BubbleDelegateView(anchor_view, arrow_location),
      extension_host_(host),
      inspect_with_devtools_(false),
      close_bubble_factory_(this) {
  // Adjust the margin so that contents fit better.
  const int margin = views::BubbleBorder::GetCornerRadius() / 2;
  set_margins(gfx::Insets(margin, margin, margin, margin));
  SetLayoutManager(new views::FillLayout());
  AddChildView(host->view());
  host->view()->SetContainer(this);
  // Use OnNativeFocusChange to check for child window activation on deactivate.
  set_close_on_deactivate(false);
  // Make the bubble move with its anchor (during inspection, etc.).
  set_move_with_anchor(true);

  // Wait to show the popup until the contained host finishes loading.
  registrar_.Add(this, content::NOTIFICATION_LOAD_COMPLETED_MAIN_FRAME,
                 content::Source<WebContents>(host->host_contents()));

  // Listen for the containing view calling window.close();
  registrar_.Add(this, chrome::NOTIFICATION_EXTENSION_HOST_VIEW_SHOULD_CLOSE,
                 content::Source<Profile>(host->profile()));

  // Listen for the dev tools opening on this popup, so we can stop it going
  // away when the dev tools get focus.
  registrar_.Add(this, content::NOTIFICATION_DEVTOOLS_AGENT_ATTACHED,
                 content::Source<Profile>(host->profile()));

  // Listen for the dev tools closing, so we can close this window if it is
  // being inspected and the inspector is closed.
  registrar_.Add(this, content::NOTIFICATION_DEVTOOLS_AGENT_DETACHED,
      content::Source<content::BrowserContext>(host->profile()));
}

ExtensionChatPopup::~ExtensionChatPopup() {
  views::WidgetFocusManager::GetInstance()->RemoveFocusChangeListener(this);
}

void ExtensionChatPopup::Observe(int type,
                             const content::NotificationSource& source,
                             const content::NotificationDetails& details) {
  switch (type) {
    case content::NOTIFICATION_LOAD_COMPLETED_MAIN_FRAME:
      DCHECK(content::Source<WebContents>(host()->host_contents()) == source);
      // Show when the content finishes loading and its width is computed.
      ShowBubble();
      break;
    case chrome::NOTIFICATION_EXTENSION_HOST_VIEW_SHOULD_CLOSE:
      // If we aren't the host of the popup, then disregard the notification.
      if (content::Details<extensions::ExtensionHost>(host()) == details)
        GetWidget()->Close();
      break;
    case content::NOTIFICATION_DEVTOOLS_AGENT_DETACHED:
      // Make sure it's the devtools window that inspecting our popup.
      // Widget::Close posts a task, which should give the devtools window a
      // chance to finish detaching from the inspected RenderViewHost.
      if (content::Details<RenderViewHost>(host()->render_view_host()) ==
          details) {
        GetWidget()->Close();
      }
      break;
    case content::NOTIFICATION_DEVTOOLS_AGENT_ATTACHED:
      // First check that the devtools are being opened on this popup.
      if (content::Details<RenderViewHost>(host()->render_view_host()) ==
          details) {
        // Set inspect_with_devtools_ so the popup will be kept open while
        // the devtools are open.
        inspect_with_devtools_ = true;
      }
      break;
    default:
      NOTREACHED() << L"Received unexpected notification";
  }
}

void ExtensionChatPopup::OnExtensionSizeChanged(ExtensionViewViews* view) {
  SizeToContents();
}

gfx::Size ExtensionChatPopup::GetPreferredSize() {
  // Constrain the size to popup min/max.
  gfx::Size sz = views::View::GetPreferredSize();
  sz.set_width(std::max(kMinWidth, std::min(kMaxWidth, sz.width())));
  sz.set_height(std::max(kMinHeight, std::min(kMaxHeight, sz.height())));
  return sz;
}

void ExtensionChatPopup::OnNativeFocusChange(gfx::NativeView focused_before,
                                         gfx::NativeView focused_now) {
  // Don't close if a child of this window is activated (only needed on Win).
  // ExtensionChatPopups can create Javascipt dialogs; see crbug.com/106723.
  gfx::NativeView this_window = GetWidget()->GetNativeView();
  if (inspect_with_devtools_ || focused_now == this_window ||
      IsParent(focused_now, this_window))
    return;
  // Delay closing the widget because on Aura, closing right away makes the
  // activation controller trigger another focus change before the current focus
  // change is complete.
  if (!close_bubble_factory_.HasWeakPtrs()) {
    MessageLoop::current()->PostTask(FROM_HERE,
        base::Bind(&ExtensionChatPopup::CloseBubble,
                   close_bubble_factory_.GetWeakPtr()));
  }
}

// static
ExtensionChatPopup* ExtensionChatPopup::ShowPopup(
    const GURL& url,
    Browser* browser,
    views::View* anchor_view,
    views::BubbleBorder::ArrowLocation arrow_location) {
  ExtensionProcessManager* manager =
      extensions::ExtensionSystem::Get(browser->profile())->process_manager();
  extensions::ExtensionHost* host = manager->CreatePopupHost(url, browser);
  ExtensionChatPopup* popup = new ExtensionChatPopup(browser, host, anchor_view,
      arrow_location);
  views::BubbleDelegateView::CreateBubble(popup);

#if defined(USE_ASH)
  gfx::NativeView native_view = popup->GetWidget()->GetNativeView();
  ash::SetWindowVisibilityAnimationType(
      native_view,
      ash::WINDOW_VISIBILITY_ANIMATION_TYPE_VERTICAL);
  ash::SetWindowVisibilityAnimationVerticalPosition(
      native_view,
      -3.0f);
#endif

  // If the host had somehow finished loading, then we'd miss the notification
  // and not show.  This seems to happen in single-process mode.
  if (host->did_stop_loading())
    popup->ShowBubble();

  return popup;
}

void ExtensionChatPopup::ShowBubble() {
  Show();

  // Focus on the host contents when the bubble is first shown.
  host()->host_contents()->Focus();

  // Listen for widget focus changes after showing (used for non-aura win).
  views::WidgetFocusManager::GetInstance()->AddFocusChangeListener(this);

  if (inspect_with_devtools_) {
    DevToolsWindow::ToggleDevToolsWindow(host()->render_view_host(),
        true,
        DEVTOOLS_TOGGLE_ACTION_SHOW_CONSOLE);
  }
}

void ExtensionChatPopup::CloseBubble() {
  GetWidget()->Close();
}
