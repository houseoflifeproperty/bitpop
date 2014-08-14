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

#import "chrome/browser/ui/cocoa/facebook_chat/facebook_popup_controller.h"

#include <algorithm>

#include "base/callback.h"
#include "chrome/browser/chrome_notification_types.h"
#include "chrome/browser/extensions/extension_view_host.h"
#include "chrome/browser/extensions/extension_view_host_factory.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/ui/browser.h"
#import "chrome/browser/ui/cocoa/browser_window_cocoa.h"
#import "chrome/browser/ui/cocoa/extensions/extension_view_mac.h"
#import "chrome/browser/ui/cocoa/info_bubble_window.h"
#include "components/web_modal/web_contents_modal_dialog_manager.h"
#include "content/public/browser/notification_details.h"
#include "content/public/browser/notification_registrar.h"
#include "content/public/browser/notification_source.h"
#include "ui/base/cocoa/window_size_constants.h"

using content::BrowserContext;
using content::RenderViewHost;

namespace {
// The duration for any animations that might be invoked by this controller.
const NSTimeInterval kAnimationDuration = 0.2;

const CGFloat kPopupWidth = 270;
const CGFloat kPopupHeight = 320;

// There should only be one extension popup showing at one time. Keep a
// reference to it here.
static FacebookPopupController* gPopup;

// Given a value and a rage, clamp the value into the range.
CGFloat Clamp(CGFloat value, CGFloat min, CGFloat max) {
  return std::max(min, std::min(max, value));
}

}  // namespace

@interface FacebookPopupController(Private)
// Callers should be using the public static method for initialization.
// NOTE: This takes ownership of |host|.
- (id)initWithHost:(extensions::ExtensionViewHost*)host
      parentWindow:(NSWindow*)parentWindow
        anchoredAt:(NSPoint)anchoredAt
     arrowLocation:(info_bubble::BubbleArrowLocation)arrowLocation;

// Called when the extension's hosted NSView has been resized.
- (void)extensionViewFrameChanged;

// Called when the extension's size changes.
- (void)onSizeChanged:(NSSize)newSize;

// Called when the extension view is shown.
- (void)onViewDidShow;

- (void)parentWindowDidBecomeKey:(NSNotification*)notification;
@end

class FacebookExtensionPopupContainer : public ExtensionViewMac::Container {
 public:
  explicit FacebookExtensionPopupContainer(FacebookPopupController* controller)
      : controller_(controller) {
  }

  virtual void OnExtensionSizeChanged(
      ExtensionViewMac* view,
      const gfx::Size& new_size) OVERRIDE {
    [controller_ onSizeChanged:
        NSMakeSize(new_size.width(), new_size.height())];
  }

  virtual void OnExtensionViewDidShow(ExtensionViewMac* view) OVERRIDE {
    [controller_ onViewDidShow];
  }

 private:
  FacebookPopupController* controller_; // Weak; owns this.
};

class FacebookExtensionObserverBridge : public content::NotificationObserver {
 public:
  FacebookExtensionObserverBridge(FacebookPopupController* owner)
    : owner_(owner) {
    registrar_.Add(this, chrome::NOTIFICATION_EXTENSION_HOST_VIEW_SHOULD_CLOSE,
                   content::Source<BrowserContext>([owner_ extensionViewHost]->browser_context()));
  }

  // Overridden from content::NotificationObserver.
  virtual void Observe(int type,
               const content::NotificationSource& source,
               const content::NotificationDetails& details) OVERRIDE {
    switch (type) {
      case chrome::NOTIFICATION_EXTENSION_HOST_VIEW_SHOULD_CLOSE: {
        extensions::ExtensionHost* host =
            content::Details<extensions::ExtensionHost>(details).ptr();
        if (host == [owner_ extensionViewHost]) {
          FacebookPopupController* popup = [FacebookPopupController popup];
          if (popup && ![popup isClosing])
            [popup close];
        }

        break;
      }
    }
  }

 private:
  // The object we need to inform when we get a notification. Weak. Owns us.
  FacebookPopupController* owner_;

  // Used for registering to receive notifications and automatic clean up.
  content::NotificationRegistrar registrar_;

  DISALLOW_COPY_AND_ASSIGN(FacebookExtensionObserverBridge);
};

@implementation FacebookPopupController

- (id)initWithHost:(extensions::ExtensionViewHost*)host
      parentWindow:(NSWindow*)parentWindow
        anchoredAt:(NSPoint)anchoredAt
     arrowLocation:(info_bubble::BubbleArrowLocation)arrowLocation {
  if (arrowLocation != info_bubble::kBottomCenter)
    return nil;

  base::scoped_nsobject<InfoBubbleWindow> window(
      [[InfoBubbleWindow alloc]
          initWithContentRect:ui::kWindowSizeDeterminedLater
                    styleMask:NSBorderlessWindowMask
                      backing:NSBackingStoreBuffered
                        defer:YES]);
  if (!window.get())
    return nil;

  anchoredAt = [parentWindow convertBaseToScreen:anchoredAt];
  if ((self = [super initWithWindow:window
                       parentWindow:parentWindow
                         anchoredAt:anchoredAt])) {
    host_.reset(host);
    ignoreWindowDidResignKey_ = NO;

    InfoBubbleView* view = self.bubble;
    [view setArrowLocation:arrowLocation];

    extensionView_ = host->view()->native_view();
    container_.reset(new FacebookExtensionPopupContainer(self));
    host->view()->set_container(container_.get());

    NSNotificationCenter* center = [NSNotificationCenter defaultCenter];
    [center addObserver:self
               selector:@selector(extensionViewFrameChanged)
                   name:NSViewFrameDidChangeNotification
                 object:extensionView_];

    [center addObserver:self
               selector:@selector(parentWindowDidBecomeKey:)
                   name:NSWindowDidBecomeKeyNotification
                 object:parentWindow];

    [view addSubview:extensionView_];

    fbObserverBridge_.reset(new FacebookExtensionObserverBridge(self));
  }
  return self;
}

- (void)dealloc {
  [[NSNotificationCenter defaultCenter] removeObserver:self];
  [super dealloc];
}

- (void)close {
  // |windowWillClose:| could have already been called. http://crbug.com/279505
  if (host_) {
    web_modal::WebContentsModalDialogManager* modalDialogManager =
        web_modal::WebContentsModalDialogManager::FromWebContents(
            host_->host_contents());
    if (modalDialogManager &&
        modalDialogManager->IsDialogActive()) {
      return;
    }
  }
  [super close];
}

- (void)windowWillClose:(NSNotification *)notification {
  [super windowWillClose:notification];
  if (gPopup == self)
    gPopup = nil;
  if (host_->view())
    host_->view()->set_container(NULL);
  host_.reset();
}

- (void)windowDidResignKey:(NSNotification*)notification {
// |windowWillClose:| could have already been called. http://crbug.com/279505
  // --
  // -- Everything commented here to allow for a different app to be opened
  // -- while the popup is shown.
  // --
  // if (host_) {
  //   // When a modal dialog is opened on top of the popup and when it's closed,
  //   // it steals key-ness from the popup. Don't close the popup when this
  //   // happens. There's an extra windowDidResignKey: notification after the
  //   // modal dialog closes that should also be ignored.
  //   web_modal::WebContentsModalDialogManager* modalDialogManager =
  //       web_modal::WebContentsModalDialogManager::FromWebContents(
  //           host_->host_contents());
  //   if (modalDialogManager &&
  //       modalDialogManager->IsDialogActive()) {
  //     ignoreWindowDidResignKey_ = YES;
  //     return;
  //   }
  //   if (ignoreWindowDidResignKey_) {
  //     ignoreWindowDidResignKey_ = NO;
  //     return;
  //   }
  // }
  
  // [super windowDidResignKey:notification];
}

- (void)parentWindowDidBecomeKey:(NSNotification*)notification {
  NSWindow* window = [self window];
  if ([window isVisible])
    [self close];
}

- (BOOL)isClosing {
  return [static_cast<InfoBubbleWindow*>([self window]) isClosing];
}

- (extensions::ExtensionViewHost*)extensionViewHost {
  return host_.get();
}

+ (FacebookPopupController*)showURL:(GURL)url
                           inBrowser:(Browser*)browser
                          anchoredAt:(NSPoint)anchoredAt
                       arrowLocation:(info_bubble::BubbleArrowLocation)
                                         arrowLocation {
  DCHECK([NSThread isMainThread]);
  DCHECK(browser);
  if (!browser)
    return nil;

  extensions::ExtensionViewHost* host =
      extensions::ExtensionViewHostFactory::CreatePopupHost(url, browser);
  DCHECK(host);
  if (!host)
    return nil;

  [gPopup close];

  // Takes ownership of |host|. Also will autorelease itself when the popup is
  // closed, so no need to do that here.
  gPopup = [[FacebookPopupController alloc]
      initWithHost:host
      parentWindow:browser->window()->GetNativeWindow()
        anchoredAt:anchoredAt
     arrowLocation:arrowLocation];
  return gPopup;
}

+ (FacebookPopupController*)popup {
  return gPopup;
}

- (void)extensionViewFrameChanged {
  // If there are no changes in the width or height of the frame, then ignore.
  if (NSEqualSizes([extensionView_ frame].size, extensionFrame_.size))
    return;

  extensionFrame_ = [extensionView_ frame];
  // Constrain the size of the view.
  [extensionView_ setFrameSize:NSMakeSize(
      Clamp(NSWidth(extensionFrame_),
            ExtensionViewMac::kMinWidth, kPopupWidth),
      Clamp(NSHeight(extensionFrame_),
            ExtensionViewMac::kMinHeight, kPopupHeight))];

  // Pad the window by half of the rounded corner radius to prevent the
  // extension's view from bleeding out over the corners.
  CGFloat inset = info_bubble::kBubbleCornerRadius / 2.0;
  [extensionView_ setFrameOrigin:NSMakePoint(inset, inset +
      info_bubble::kBubbleArrowHeight)];

  NSRect frame = [extensionView_ frame];
  frame.origin.y -= info_bubble::kBubbleArrowHeight;
  frame.size.height += info_bubble::kBubbleArrowHeight +
                       info_bubble::kBubbleCornerRadius;
  frame.size.width += info_bubble::kBubbleCornerRadius;
  frame = [extensionView_ convertRect:frame toView:nil];
  // Adjust the origin according to the height and width so that the arrow is
  // positioned correctly at the middle and slightly down from the button.
  NSPoint windowOrigin = self.anchorPoint;
  windowOrigin.x -= NSWidth(frame) / 2;
  frame.origin = windowOrigin;

  // Is the window still animating in? If so, then cancel that and create a new
  // animation setting the opacity and new frame value. Otherwise the current
  // animation will continue after this frame is set, reverting the frame to
  // what it was when the animation started.
  NSWindow* window = [self window];
  id animator = [window animator];
  if ([window isVisible] &&
      ([animator alphaValue] < 1.0 ||
       !NSEqualRects([window frame], [animator frame]))) {
    [NSAnimationContext beginGrouping];
    [[NSAnimationContext currentContext] setDuration:kAnimationDuration];
    [animator setAlphaValue:1.0];
    [animator setFrame:frame display:YES];
    [NSAnimationContext endGrouping];
  } else {
    [window setFrame:frame display:YES];
  }

  // A NSViewFrameDidChangeNotification won't be sent until the extension view
  // content is loaded. The window is hidden on init, so show it the first time
  // the notification is fired (and consequently the view contents have loaded).
  if (![window isVisible]) {
    [self showWindow:self];
  }
}

- (void)onSizeChanged:(NSSize)newSize {
  // When we update the size, the window will become visible. Stay hidden until
  // the host is loaded.
  pendingSize_ = newSize;
  if (!host_->did_stop_loading())
    return;

  // No need to use CA here, our caller calls us repeatedly to animate the
  // resizing.
  NSRect frame = [extensionView_ frame];
  frame.size = newSize;

  // |new_size| is in pixels. Convert to view units.
  frame.size = [extensionView_ convertSize:frame.size fromView:nil];

  [extensionView_ setFrame:frame];
  [extensionView_ setNeedsDisplay:YES];
}

- (void)onViewDidShow {
  [self onSizeChanged:pendingSize_];
}

- (void)windowDidResize:(NSNotification*)notification {
  // Let the extension view know, so that it can tell plugins.
  if (host_->view())
    host_->view()->WindowFrameChanged();
}

- (void)windowDidMove:(NSNotification*)notification {
  // Let the extension view know, so that it can tell plugins.
  if (host_->view())
    host_->view()->WindowFrameChanged();
}

@end

