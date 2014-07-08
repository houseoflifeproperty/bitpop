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

#ifndef CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_NOTIFICATION_VIEW_H_
#define CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_NOTIFICATION_VIEW_H_
#pragma once

#import "base/mac/scoped_nsobject.h"
#import "chrome/browser/ui/cocoa/facebook_chat/facebook_bubble_view.h"

// Content view for a bubble with an arrow showing arbitrary content.
// This is where nonrectangular drawing happens.
@interface FacebookNotificationView : FacebookBubbleView {
 @private
//   CGFloat defaultWidth_;

   base::scoped_nsobject<NSTextStorage> textStorage_;
   NSLayoutManager *layoutManager_;
   NSTextContainer *textContainer_;

   base::scoped_nsobject<NSMutableArray> contentMessages_;
}

// The font used to display the content string
- (NSFont*)font;

//- (CGFloat)defaultWidth;
//- (void)setDefaultWidth:(CGFloat)width;

// Control the messages content as a queue
- (void)pushMessage:(NSString*)messageString;  // changes the view frame
- (NSString*)popMessage;                       // changes the view frame
- (NSUInteger)numMessagesRemaining;

@end


#endif // CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_NOTIFICATION_VIEW_H_
