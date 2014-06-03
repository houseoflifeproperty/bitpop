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

#ifndef CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_NOTIFICATION_CONTROLLER_H_
#define CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_NOTIFICATION_CONTROLLER_H_

#pragma once

#import <Cocoa/Cocoa.h>

#import "base/mac/cocoa_protocols.h"
#include "base/memory/scoped_nsobject.h"

@class FacebookNotificationView;
@class HoverButton;

@interface FacebookNotificationController : NSWindowController<NSWindowDelegate> {
  NSWindow *parentWindow_;
  NSPoint anchor_;
  NSPoint oldAnchor_;

  scoped_nsobject<FacebookNotificationView> bubble_;
  scoped_nsobject<HoverButton> hoverCloseButton_;
}

@property (nonatomic, assign) NSPoint anchor;

- (id)initWithParentWindow:(NSWindow*)parentWindow
                anchoredAt:(NSPoint)anchorPoint;

- (void)messageReceived:(NSString*)message;

- (void)hideWindow;

- (BOOL)isClosing;

- (void)parentControllerWillDie;

@end

#endif  // CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_NOTIFICATION_CONTROLLER_H_
