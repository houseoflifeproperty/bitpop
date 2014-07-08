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

#import "chrome/browser/ui/cocoa/facebook_chat/facebook_notification_controller.h"

#include "base/logging.h"
#include "base/mac/mac_util.h"
#include "base/timer/timer.h"
#include "grit/generated_resources.h"
#include "grit/theme_resources.h"
#include "grit/ui_resources.h"
#import "chrome/browser/ui/cocoa/facebook_chat/facebook_notification_view.h"
#import "chrome/browser/ui/cocoa/info_bubble_window.h"
#include "skia/ext/skia_utils_mac.h"
#import "ui/base/cocoa/hover_image_button.h"
#include "ui/base/cocoa/window_size_constants.h"
#include "ui/base/resource/resource_bundle.h"
#include "ui/gfx/image/image.h"

namespace {
const NSTimeInterval kBubbleMessageTimeoutSec = 10.0;
const NSTimeInterval kAnimationDuration = 0.2;

const CGFloat kCloseButtonDim = 16.0;
const CGFloat kCloseButtonRightXOffset = 4.0;
const CGFloat kCloseButtonTopYOffset = 7.0;

}

@interface FacebookNotificationController(Private)
- (void)bubbleMessageShowTimeout;
// Called when the bubble view has been resized.
- (void)updateOriginFromAnchor;
- (void)bubbleViewFrameChanged:(NSNotification*)notification;
@end

@implementation FacebookNotificationController

@synthesize anchor = anchor_;

- (id)initWithParentWindow:(NSWindow*)parentWindow
                anchoredAt:(NSPoint)anchorPoint {
  parentWindow_ = parentWindow;
  anchor_ = [parentWindow convertBaseToScreen:anchorPoint];

  bubble_.reset([[FacebookNotificationView alloc]
                    initWithFrame:NSZeroRect]);
  if (!bubble_.get())
    return nil;

  hoverCloseButton_.reset([[HoverImageButton alloc] initWithFrame:
      NSMakeRect(0, 0, kCloseButtonDim, kCloseButtonDim)]);
  [hoverCloseButton_ setAutoresizingMask:NSViewMinXMargin | NSViewMinYMargin];
  [hoverCloseButton_ setTarget:self];
  [hoverCloseButton_ setAction:@selector(close)];

  ResourceBundle& rb = ResourceBundle::GetSharedInstance();

  NSImage* defaultImage = rb.GetNativeImageNamed(IDR_CLOSE_DIALOG).ToNSImage();
  NSImage* hoverImage = rb.GetNativeImageNamed(IDR_CLOSE_DIALOG_H).ToNSImage();
  NSImage* pressedImage = rb.GetNativeImageNamed(IDR_CLOSE_DIALOG_P).ToNSImage();

  [(HoverImageButton*)hoverCloseButton_ setDefaultImage:defaultImage];
  [(HoverImageButton*)hoverCloseButton_ setHoverImage:hoverImage];
  [(HoverImageButton*)hoverCloseButton_ setPressedImage:pressedImage];

  [(HoverImageButton*)hoverCloseButton_ setBordered:NO];

  [bubble_ addSubview:hoverCloseButton_];

  base::scoped_nsobject<InfoBubbleWindow> window(
      [[InfoBubbleWindow alloc]
          initWithContentRect:(ui::kWindowSizeDeterminedLater)
                    styleMask:NSBorderlessWindowMask
                      backing:NSBackingStoreBuffered
                        defer:YES]);
  if (!window.get())
    return nil;
  [window setDelegate:self];
  [window setContentView:bubble_];
  [window setCanBecomeKeyWindow:NO];

  self = [super initWithWindow:window];

  [self setShouldCascadeWindows:NO];

  // Watch to see if the parent window closes, and if so, close this one.
  NSNotificationCenter* center = [NSNotificationCenter defaultCenter];
  [center addObserver:self
             selector:@selector(parentWindowWillClose:)
                 name:NSWindowWillCloseNotification
               object:parentWindow_];
  [center addObserver:self
             selector:@selector(bubbleViewFrameChanged:)
                 name:NSViewFrameDidChangeNotification
               object:bubble_.get()];

  return self;
}

- (void)messageReceived:(NSString*)message {
  [bubble_ pushMessage:message];
  [self showWindow:self];
  [self performSelector:@selector(bubbleMessageShowTimeout) withObject:nil
      afterDelay:kBubbleMessageTimeoutSec];
}

- (void)bubbleMessageShowTimeout {
  if ([bubble_ numMessagesRemaining] > 1) {
    (void)[bubble_ popMessage];
  } else {
    [self hideWindow];

    [self performSelector:@selector(bubbleMessageShowTimeout) withObject:nil
      afterDelay:kBubbleMessageTimeoutSec];
  }
}

- (void)parentControllerWillDie {
  [NSObject cancelPreviousPerformRequestsWithTarget:self];
}

- (void)dealloc {
  [[NSNotificationCenter defaultCenter] removeObserver:self];
  [super dealloc];
}

- (void)parentWindowWillClose:(NSNotification*)notification {
  [self close];
}

- (void)windowWillClose:(NSNotification *)notification {
  [[NSNotificationCenter defaultCenter] removeObserver:self];
}

// We want this to be a child of a browser window. addChildWindow: (called from
// this function) will bring the window on-screen; unfortunately,
// [NSWindowController showWindow:] will also bring it on-screen (but will cause
// unexpected changes to the window's position). We cannot have an
// addChildWindow: and a subsequent showWindow:. Thus, we have our own version.
- (void)showWindow:(id)sender {
  [parentWindow_ addChildWindow:[self window] ordered:NSWindowAbove];
  [self updateOriginFromAnchor];
  if ([parentWindow_ isVisible] && [parentWindow_ isMainWindow])
    [[self window] orderFront:self];
}

- (void)close {
  [parentWindow_ removeChildWindow:[self window]];

  // No longer have a parent window, so nil out the pointer and deregister for
  // notifications.
  NSNotificationCenter* center = [NSNotificationCenter defaultCenter];
  [center removeObserver:self
                    name:NSWindowWillCloseNotification
                  object:parentWindow_];
  parentWindow_ = nil;
  [super close];
}

- (BOOL)isClosing {
  return [static_cast<InfoBubbleWindow*>([self window]) isClosing];
}

- (void)hideWindow {
  [parentWindow_ removeChildWindow:[self window]];
  [[self window] orderOut:self];
}

// Takes the |anchor_| point and adjusts the window's origin accordingly.
- (void)updateOriginFromAnchor {
  NSWindow* window = [self window];
  NSPoint origin = anchor_;

  NSSize offsets = NSMakeSize(fb_bubble::kBubbleArrowXOffset +
                              fb_bubble::kBubbleArrowWidth / 2.0, 0);
  offsets = [[parentWindow_ contentView] convertSize:offsets toView:nil];
  origin.x -= offsets.width;

  // if ([window isVisible] && [[window animator] alphaValue] < 1.0) {
  //   [NSAnimationContext beginGrouping];
  //   [[NSAnimationContext currentContext] setDuration:kAnimationDuration];
  //   [[window animator] setFrameOrigin:origin];
  //   [NSAnimationContext endGrouping];
  // } else {
    [window setFrameOrigin:origin];
  // }
}

- (void)bubbleViewFrameChanged:(NSNotification*)notification {
  NSRect frame = [bubble_ frame];

  // position the close small button on top right of the bubble
  NSRect closeButtonFrame = [hoverCloseButton_ frame];
  closeButtonFrame.origin.x = NSWidth(frame) - kCloseButtonDim -
      kCloseButtonRightXOffset;
  closeButtonFrame.origin.y = kCloseButtonTopYOffset;
  [hoverCloseButton_ setFrame:closeButtonFrame];

  NSWindow* window = [self window];
  NSRect window_frame = [window frame];
  window_frame.size = frame.size;
  if ([window isVisible] && [[window animator] alphaValue] < 1.0) {
    [NSAnimationContext beginGrouping];
    [[NSAnimationContext currentContext] setDuration:kAnimationDuration];
    [[window animator] setFrame:window_frame display:YES];
    [NSAnimationContext endGrouping];
  } else {
    [window setFrame:window_frame display:YES];
  }
}

- (void)setAnchor:(NSPoint)anchorPoint {
  anchor_ = [parentWindow_ convertBaseToScreen:anchorPoint];
  [self updateOriginFromAnchor];
}

@end
