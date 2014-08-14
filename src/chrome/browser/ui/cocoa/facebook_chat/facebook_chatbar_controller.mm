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

#import "chrome/browser/ui/cocoa/facebook_chat/facebook_chatbar_controller.h"

#include "base/mac/bundle_locations.h"
#include "base/mac/mac_util.h"
#import "chrome/browser/ui/cocoa/facebook_chat/facebook_chatbar_mac.h"
#import "chrome/browser/ui/cocoa/facebook_chat/facebook_chat_item_controller.h"
#include "chrome/browser/facebook_chat/facebook_chat_item.h"
#include "chrome/browser/ui/browser.h"
#include "chrome/browser/ui/browser_window.h"
#import "chrome/browser/ui/cocoa/hover_close_button.h"
#include "chrome/browser/ui/fullscreen/fullscreen_controller.h"
#include "chrome/browser/ui/tabs/tab_strip_model.h"

namespace {
// The size of the x button by default.
const NSSize kHoverCloseButtonDefaultSize = { 16, 16 };

const NSUInteger kMaxChatItemCount = 10;

const NSInteger kChatItemPadding = 2;

const NSInteger kChatItemsPaddingRight = 25;

const NSInteger kChatbarHeight = 36;

const NSTimeInterval kAddAnimationDuration = 0.6;
const NSTimeInterval kPlaceFirstAnimationDuration = 0.6;
}  // namespace

@interface LayoutChildWindowsAnimation : NSAnimation {
  FacebookChatbarController* chatbarController_;
}

@property (nonatomic, assign) FacebookChatbarController* chatbarController;

@end

@implementation LayoutChildWindowsAnimation

@synthesize chatbarController=chatbarController_;

- (void)setCurrentProgress:(NSAnimationProgress)progress {
  [super setCurrentProgress:progress];

  [chatbarController_ layoutItemsChildWindows];
}

@end

@interface FacebookChatbarController(Private)

- (void)layoutItems:(BOOL)skipFirst;
- (void)showChatbar:(BOOL)enable;
- (void)updateCloseButton;

@end

@implementation FacebookChatbarController

- (id)initWithBrowser:(Browser*)browser
       resizeDelegate:(id<ViewResizer>)resizeDelegate {
  if ((self = [super initWithNibName:@"FacebookChatbar"
                              bundle:base::mac::FrameworkBundle()])) {
    resizeDelegate_ = resizeDelegate;
    browser_ = browser;
    maxBarHeight_ = NSHeight([[self view] bounds]);

    if (browser && browser->window())
      isFullscreen_ = browser->window()->IsFullscreen();
    else
      isFullscreen_ = NO;

    // Reset the download shelf's frame height to zero.  It will be properly
    // positioned and sized the first time we try to set its height. (Just
    // setting the rect to NSZeroRect does not work: it confuses Cocoa's view
    // layout logic. If the shelf's width is too small, cocoa makes the download
    // item container view wider than the browser window).
    NSRect frame = [[self view] frame];
    frame.size.height = 0;
    [[self view] setFrame:frame];

    NSNotificationCenter* defaultCenter = [NSNotificationCenter defaultCenter];
    [[self view] setPostsFrameChangedNotifications:YES];
    [defaultCenter addObserver:self
                      selector:@selector(viewFrameDidChange:)
                          name:NSViewFrameDidChangeNotification
                        object:[self view]];

    chatItemControllers_.reset([[NSMutableArray alloc] init]);

    bridge_.reset(new FacebookChatbarMac(browser, self));
  }
  return self;
}

- (void)dealloc {
  [super dealloc];
}

- (BOOL)isVisible {
  return barIsVisible_;
}

- (void)showChatbar:(BOOL)enable {
  if ([self isVisible] == enable)
    return;

  if (enable)
    [resizeDelegate_ resizeView:self.view newHeight:maxBarHeight_];
  else
    [resizeDelegate_ resizeView:self.view newHeight:0];

  barIsVisible_ = enable;
  [self updateCloseButton];
}

- (void)show:(id)sender {
  [self showChatbar:YES];
}

- (void)hide:(id)sender {
  if (sender)
    bridge_->Hide();
  else
    [self showChatbar:NO];
}

- (FacebookChatbar*)bridge {
  return bridge_.get();
}

- (void)updateCloseButton {
  if (!barIsVisible_)
    return;

  NSRect selfBounds = [[self view] bounds];
  NSRect hoverFrame = [hoverCloseButton_ frame];
  NSRect bounds;

  if (browser_ && browser_->window() && browser_->window()->IsFullscreen()) {
    bounds = NSMakeRect(NSMinX(hoverFrame), 0,
                        selfBounds.size.width - NSMinX(hoverFrame),
                        selfBounds.size.height);
  } else {
    bounds.origin.x = NSMinX(hoverFrame);
    bounds.origin.y = NSMidY(hoverFrame) -
                      kHoverCloseButtonDefaultSize.height / 2.0;
    bounds.size = kHoverCloseButtonDefaultSize;
  }

  // Set the tracking off to create a new tracking area for the control.
  // When changing the bounds/frame on a HoverButton, the tracking isn't updated
  // correctly, it needs to be turned off and back on.
  [hoverCloseButton_ setTrackingEnabled:NO];
  [hoverCloseButton_ setFrame:bounds];
  [hoverCloseButton_ setTrackingEnabled:YES];
}

- (void)addChatItem:(FacebookChatItem*)item {
  DCHECK([NSThread isMainThread]);

  if (browser_ && browser_->fullscreen_controller()->IsFullscreenForTabOrPending(
                    browser_->tab_strip_model()->GetActiveWebContents())) {
    browser_->fullscreen_controller()->SetOpenChatbarOnNextFullscreenEvent();
  } else if (![self isVisible]) {
    [self show:nil];
  }

  // Do not place an item with existing jid to the chat item controllers
  for (FacebookChatItemController *contr in chatItemControllers_.get())
    if ([contr chatItem]->jid() == item->jid()) {
      if ([contr chatItem]->needs_activation())
        [self activateItem:contr];
      else
        [contr setDelayActivation:NO];
      return;
    }

  if (addAnimation_.get()) {
    [addAnimation_ stopAnimation];

    // if animation did not complete the animated frame may be in
    // intermediate state. following loop fixes that.
    for (FacebookChatItemController *itemController in chatItemControllers_.get()) {
      NSRect rc = [[itemController view] frame];
      rc.size = [itemController preferredSize];
      [[itemController view] setFrame:rc];
    }
  }

  addAnimation_.reset([[LayoutChildWindowsAnimation alloc]
      initWithDuration:kAddAnimationDuration
        animationCurve:NSAnimationEaseIn]);
  [addAnimation_ setAnimationBlockingMode:NSAnimationNonblocking];
  [addAnimation_ setDelegate:self];
  [(LayoutChildWindowsAnimation*)addAnimation_ setChatbarController:self];
  [addAnimation_ startAnimation];

  // Insert new item at the left.
  base::scoped_nsobject<FacebookChatItemController> controller(
      [[FacebookChatItemController alloc] initWithModel:item chatbar:self]);

  if (![controller chatItem]->needs_activation())
    [controller setDelayActivation:NO];

  // Adding at index 0 in NSMutableArrays is O(1).
  [chatItemControllers_ insertObject:controller.get() atIndex:0];

  [[self view] addSubview:[controller view]];

  NSRect rc = [[controller view] frame];
  rc.origin.x = [[self view] bounds].size.width - kChatItemsPaddingRight;
  rc.origin.y = kChatbarHeight / 2 - rc.size.height / 2;
  rc.size = [controller preferredSize];
  rc.size.width = 0;
  [[controller view] setFrame:rc];
  [[controller view] setAlphaValue:0.95];

  // Keep only a limited number of items in the shelf.
  if ([chatItemControllers_ count] > kMaxChatItemCount) {
    DCHECK(kMaxChatItemCount > 0);

    // Since no user will ever see the item being removed (needs a horizontal
    // screen resolution greater than 3200 at 16 items at 200 pixels each),
    // there's no point in animating the removal.
    [self remove:[chatItemControllers_ lastObject]];
  }

  lastAddedItem_ = controller;

  [self layoutItems:YES];
}

- (void)activateItem:(FacebookChatItemController*)chatItem {
  for (FacebookChatItemController *controller in chatItemControllers_.get()) {
    if (controller == chatItem && ![controller active]) {
      [controller setActive:YES];
    }
    else
      [controller setActive:NO];
  }
}

- (void)remove:(FacebookChatItemController*)chatItem {
  [[chatItem view] removeFromSuperview];

  [chatItemControllers_ removeObject:chatItem];

  if (isRemovingAll_) {
     if (removeAnimation_.get())
       [removeAnimation_ stopAnimation];

  }

  removeAnimation_.reset([[LayoutChildWindowsAnimation alloc]
      initWithDuration:kPlaceFirstAnimationDuration
        animationCurve:NSAnimationEaseOut]);
  [removeAnimation_ setAnimationBlockingMode:NSAnimationNonblocking];
  [removeAnimation_ setDelegate:self];
  [(LayoutChildWindowsAnimation*)removeAnimation_ setChatbarController:self];
  [removeAnimation_ startAnimation];

  [self layoutItems];

  // Check to see if we have any downloads remaining and if not, hide the shelf.
  if (![chatItemControllers_ count])
    [self showChatbar:NO];
}

- (void)removeAll {
  isRemovingAll_ = YES;
  for (int i = [chatItemControllers_ count]; i > 0; --i) {
    FacebookChatItemController *contr = [chatItemControllers_ objectAtIndex:0];
    [contr remove];  // it will call [self remove:] afterwards
  }
  isRemovingAll_ = NO;
}

- (void)placeFirstInOrder:(FacebookChatItemController*)chatItem {
  NSMutableArray *container = chatItemControllers_.get();

  if([container containsObject:chatItem] == NO ||
      [[chatItem view] isHidden] == NO) // if chat item is visible - no need to reorder items
    return;

  if (placeFirstAnimation_.get())
    [placeFirstAnimation_ stopAnimation];

  placeFirstAnimation_.reset([[LayoutChildWindowsAnimation alloc]
      initWithDuration:kPlaceFirstAnimationDuration
        animationCurve:NSAnimationEaseIn]);
  [placeFirstAnimation_ setAnimationBlockingMode:NSAnimationNonblocking];
  [placeFirstAnimation_ setDelegate:self];
  [(LayoutChildWindowsAnimation*)placeFirstAnimation_ setChatbarController:self];
  [placeFirstAnimation_ startAnimation];

  // find active item
  int activeItemIndex = -1;
  int i = 0;
  for (FacebookChatItemController* itemController
      in chatItemControllers_.get()) {
    if (![[itemController view] isHidden]) {
      if ([itemController active]) {
        activeItemIndex = i;
        break;
      }
    }
    else
      break;
    i++;
  }

  FacebookChatItemController* activeItem = nil;
  if (activeItemIndex != -1) {
    activeItem = [chatItemControllers_ objectAtIndex:activeItemIndex];
  }

  [chatItem retain];
  [container removeObjectIdenticalTo:chatItem];
  [container insertObject:chatItem atIndex:0];
  [chatItem release];

  if (activeItemIndex != -1) {
    DCHECK(activeItem != nil);

    [activeItem retain];
    [container removeObjectIdenticalTo:activeItem];
    [container insertObject:activeItem atIndex:activeItemIndex];
    [activeItem release];
  }

  [self layoutItems];
}

- (void)layoutItems:(BOOL)skipFirst {
  CGFloat currentX = 0;
  NSUInteger index = 0;
  NSUInteger lastVisibleIndex = -1;
  for (FacebookChatItemController* itemController
      in chatItemControllers_.get()) {
    NSRect frame = [[itemController view] frame];
    frame.origin.x = ([[self view] bounds].size.width - kChatItemsPaddingRight -
        [itemController preferredSize].width) - currentX;
    if (frame.origin.x < 10) {
      if ([itemController active] == YES) {
        FacebookChatItemController *lastVisibleItem = [chatItemControllers_
            objectAtIndex:lastVisibleIndex];
        [[lastVisibleItem view] setHidden:YES];
        [[itemController view] setFrame:[[lastVisibleItem view] frame]];
        [[itemController view] setHidden:NO];
      } else
        [[itemController view] setHidden:YES];
    } else if ([[itemController view] isHidden] == YES) {
      [[itemController view] setHidden:NO];
    }

    if (frame.origin.x >= 10) {
      lastVisibleIndex = index;
    }

    frame.size.width = [itemController preferredSize].width;
    [[[itemController view] animator] setFrame:frame];
    [[[itemController view] animator] setAlphaValue:1.0];
    [itemController layoutChildWindows];

    currentX += frame.size.width + kChatItemPadding;
    ++index;
  }

}

- (void)layoutItems {
  [self layoutItems:NO];
}

- (void)viewFrameDidChange:(NSNotification*)notification {
  [self layoutItems];
}

- (void)animationDidEnd:(NSAnimation *)animation {
  if (animation == addAnimation_.get()) {
    [lastAddedItem_ layedOutAfterAddingToChatbar];
    addAnimation_.reset();
  } else if (animation == removeAnimation_.get())
    removeAnimation_.reset();
  else if (animation == placeFirstAnimation_.get()) {
    placeFirstAnimation_.reset();
  }

  [self layoutItemsChildWindows];
}

- (void)layoutItemsChildWindows {
  for (FacebookChatItemController* controller in chatItemControllers_.get())
    [controller layoutChildWindows];
}

- (void)closeAllChildrenPopups {
  for (FacebookChatItemController* controller in chatItemControllers_.get())
    [controller closeAllPopups];
}

@end
