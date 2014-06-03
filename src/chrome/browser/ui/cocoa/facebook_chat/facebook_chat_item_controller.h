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

#ifndef CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_CHAT_ITEM_CONTROLLER_H_
#define CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_CHAT_ITEM_CONTROLLER_H_

#pragma once

#import <Cocoa/Cocoa.h>

#include "base/memory/scoped_ptr.h"
#include "base/memory/scoped_nsobject.h"
#include "chrome/browser/ui/cocoa/facebook_chat/facebook_chat_item_mac.h"

@class FacebookChatbarController;
@class FacebookNotificationController;
@class HoverButton;
class GURL;

@interface FacebookChatItemController : NSViewController {
@private
  IBOutlet NSButton* button_;
  IBOutlet HoverButton* hoverCloseButton_;

  scoped_nsobject<NSTrackingArea> buttonTrackingArea_;
  BOOL showMouseEntered_;

  scoped_ptr<FacebookChatItemMac> bridge_;
  scoped_nsobject<FacebookNotificationController> notificationController_;
  FacebookChatbarController *chatbarController_;

  NSImage *numNotificationsImage_;

  BOOL active_;
  BOOL delayActivation_;
}

// Takes ownership of |downloadModel|.
- (id)initWithModel:(FacebookChatItem*)downloadModel
            chatbar:(FacebookChatbarController*)chatbar;

- (IBAction)activateItemAction:(id)sender;
- (IBAction)removeAction:(id)sender;

- (void)openChatWindow;
- (void)chatWindowWillClose:(NSNotification*)notification;

- (NSSize)preferredSize;

- (NSPoint)popupPointForChatWindow;
- (NSPoint)popupPointForNotificationWindow;

- (GURL)getPopupURL;

- (FacebookChatItem*)chatItem;

//- (void)chatItemUpdated:(FacebookChatItem*)source;
- (void)remove;
- (void)setUnreadMessagesNumber:(int)number;
- (void)statusChanged;

- (BOOL)active;
- (void)setActive:(BOOL)active;

- (BOOL)delayActivation;
- (void)setDelayActivation:(BOOL)active;

- (void)layedOutAfterAddingToChatbar;

- (void)viewFrameDidChange:(NSNotification*)notification;

- (void)layoutChildWindows;

- (void)closeAllPopups;
@end

#endif    // CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_CHAT_ITEM_CONTROLLER_H_
