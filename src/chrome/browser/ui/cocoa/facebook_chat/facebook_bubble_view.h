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

#ifndef CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_BUBBLE_VIEW_H_
#define CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_BUBBLE_VIEW_H_
#pragma once

#import <Cocoa/Cocoa.h>

#include "base/memory/scoped_nsobject.h"

namespace fb_bubble {

const CGFloat kBubbleArrowHeight = 8.0;
const CGFloat kBubbleArrowWidth = 15.0;
const CGFloat kBubbleCornerRadius = 3.0;
const CGFloat kBubbleArrowXOffset = kBubbleArrowWidth + kBubbleCornerRadius;

enum BubbleArrowLocation {
  kBottomLeft,
  kBottomCenter,
};

}  // namespace info_bubble

// Content view for a bubble with an arrow showing arbitrary content.
// This is where nonrectangular drawing happens.
@interface FacebookBubbleView : NSView {
 @private
   fb_bubble::BubbleArrowLocation arrowLocation_;
   scoped_nsobject<NSColor> backgroundColor_;
}

@property(assign, nonatomic) fb_bubble::BubbleArrowLocation arrowLocation;

- (void)setBackgroundColor:(NSColor*)bgrColor;

// Returns the point location in view coordinates of the tip of the arrow.
- (NSPoint)arrowTip;

@end


#endif // CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_BUBBLE_VIEW_H_
