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

#ifndef CHROME_BROWSER_UI_COCOA_FACEBOOK_CHATBAR_CONTROLLER_H_
#define CHROME_BROWSER_UI_COCOA_FACEBOOK_CHATBAR_CONTROLLER_H_
#pragma once

#import <Foundation/Foundation.h>

#import "base/mac/cocoa_protocols.h"
#include "base/memory/scoped_nsobject.h"
#include "base/memory/scoped_ptr.h"
#import "chrome/browser/ui/cocoa/view_resizer.h"

@class HoverButton;
class FacebookChatbar;
class Browser;
class FacebookChatItem;
@class FacebookChatItemController;

@interface FacebookChatbarController : NSViewController<NSAnimationDelegate> {
 @private
  IBOutlet HoverButton *hoverCloseButton_;

  BOOL barIsVisible_;

  BOOL isFullscreen_;

  scoped_ptr<FacebookChatbar> bridge_;

  // Height of the shelf when it's fully visible.
  CGFloat maxBarHeight_;

  // The download items we have added to our shelf.
  scoped_nsobject<NSMutableArray> chatItemControllers_;

  // Delegate that handles resizing our view.
  id<ViewResizer> resizeDelegate_;

  scoped_nsobject<NSAnimation> addAnimation_;
  scoped_nsobject<NSAnimation> removeAnimation_;
  scoped_nsobject<NSAnimation> placeFirstAnimation_;

  FacebookChatItemController *lastAddedItem_;

  BOOL isRemovingAll_;

  Browser* browser_;
}

- (id)initWithBrowser:(Browser*)browser
       resizeDelegate:(id<ViewResizer>)resizeDelegate;

- (IBAction)show:(id)sender;
- (IBAction)hide:(id)sender;

- (FacebookChatbar*)bridge;

- (BOOL)isVisible;

- (void)addChatItem:(FacebookChatItem*)item;
- (void)activateItem:(FacebookChatItemController*)chatItem;
- (void)remove:(FacebookChatItemController*)chatItem;
- (void)removeAll;
- (void)placeFirstInOrder:(FacebookChatItemController*)chatItem;

- (void)layoutItems;

- (void)viewFrameDidChange:(NSNotification*)notification;

- (void)layoutItemsChildWindows;
- (void)closeAllChildrenPopups;
@end

#endif  // CHROME_BROWSER_UI_COCOA_FACEBOOK_CHATBAR_CONTROLLER_H_
