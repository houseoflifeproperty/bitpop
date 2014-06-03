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

#import "chrome/browser/ui/cocoa/facebook_chat/facebook_notification_view.h"

#include "base/logging.h"
#include "ui/gfx/scoped_ns_graphics_context_save_gstate_mac.h"


namespace {
  // Rockmelt-like blueish color used for notification window background
  const CGFloat kBgColorRed    = 0xc2 / 255.0;
  const CGFloat kBgColorGreen  = 0xec / 255.0;
  const CGFloat kBgColorBlue   = 0xfc / 255.0;
  const CGFloat kBgColorAlpha  = 255 / 255.0;

  const NSUInteger kMaxNotifications = 20;

  const int kPaddingTopBottom = 7;
  const int kPaddingLeftRight = 5;

  const CGFloat kDefaultWidth = 200;
  const CGFloat kContentWidth = kDefaultWidth - fb_bubble::kBubbleCornerRadius -
    2 * kPaddingLeftRight;
}

@interface FacebookNotificationView(Private)
- (CGFloat)heightForWidth:(CGFloat)width;
- (void)setFrameToFit;
- (NSString*)continuousContentString;
@end

@implementation FacebookNotificationView

- (id)initWithFrame:(NSRect)frameRect {
  if ((self = [super initWithFrame:frameRect])) {
    // do member initialization here
    [self setBackgroundColor:[NSColor colorWithCalibratedRed:kBgColorRed
                                                       green:kBgColorGreen
                                                        blue:kBgColorBlue
                                                       alpha:kBgColorAlpha]];
    [self setArrowLocation:fb_bubble::kBottomLeft];
    [self setPostsFrameChangedNotifications:YES];

    contentMessages_.reset([[NSMutableArray alloc] init]);

    textStorage_.reset([[NSTextStorage alloc] initWithString:@""]);
    layoutManager_ = [[NSLayoutManager alloc] init];
    textContainer_ = [[NSTextContainer alloc] init];
    [layoutManager_ addTextContainer:textContainer_];
    [textContainer_ release];
    [textStorage_ addLayoutManager:layoutManager_];
    [layoutManager_ release];
  }
  return self;
}

- (void)drawRect:(NSRect)rect {
  NSRect bounds = [self bounds];

  {
  gfx::ScopedNSGraphicsContextSaveGState scopedGState;

  NSAffineTransform* xform = [NSAffineTransform transform];
  [xform translateXBy:0.0 yBy:bounds.size.height];
  [xform scaleXBy:1.0 yBy:-1.0];
  [xform concat];

  // Draw the bubble
  [super drawRect:rect];
  }

  //CGContextRef ctx = (CGContextRef)[[NSGraphicsContext currentContext] graphicsPort];
  //CGContextSetTextMatrix(ctx, CGAffineTransformMakeScale(1, -1));

  bounds.origin.x += fb_bubble::kBubbleCornerRadius / 2 + kPaddingLeftRight;
  // TODO: check if the coordinates choice was right for origin.y
  bounds.origin.y += fb_bubble::kBubbleCornerRadius / 2 + kPaddingTopBottom;

  NSColor *textColor = [NSColor blackColor];

  // TODO: maybe add a text shadow attribute here too. display will be
  // better this way
  [textStorage_ addAttribute:NSForegroundColorAttributeName value:textColor
      range:NSMakeRange(0, [textStorage_ length])];

  NSRange glyphRange = [layoutManager_
    glyphRangeForTextContainer:textContainer_];
  [layoutManager_ drawGlyphsForGlyphRange:glyphRange atPoint:bounds.origin];
}

// The font used to display the content string
- (NSFont*)font {
  return [NSFont systemFontOfSize:[NSFont smallSystemFontSize]];
}

// - (CGFloat)defaultWidth {
//   return defaultWidth_;
// }
//
// - (void)setDefaultWidth:(CGFloat)width {
//   defaultWidth_ = width;
// }

- (CGFloat)heightForWidth:(CGFloat)width {
  [textContainer_ setContainerSize:NSMakeSize(width, FLT_MAX)];
  [[textStorage_ mutableString] setString:[self continuousContentString]];
  [textStorage_ addAttribute:NSFontAttributeName value:[self font]
      range:NSMakeRange(0, [textStorage_ length])];
  [textContainer_ setLineFragmentPadding:0.0];

  (void)[layoutManager_ glyphRangeForTextContainer:textContainer_];
  return [layoutManager_ usedRectForTextContainer:textContainer_].size.height;
}

- (void)setFrameToFit {
  NSRect frame = [self frame];
  frame.size.width = kDefaultWidth;
  frame.size.height = [self heightForWidth:kContentWidth] +
      2 * kPaddingTopBottom + fb_bubble::kBubbleCornerRadius +
      fb_bubble::kBubbleArrowHeight;
  [self setFrame:frame];
}

- (void)pushMessage:(NSString*)messageString {
  if ([contentMessages_ count] >= kMaxNotifications)
    [contentMessages_ removeObjectAtIndex:0];

  [contentMessages_ addObject:messageString];

  [self setFrameToFit];
  [self setNeedsDisplay:YES];
}

- (NSString*)popMessage {
  DCHECK([contentMessages_ count] > 1);

  NSString *ret = [contentMessages_ objectAtIndex:0];
  [contentMessages_ removeObjectAtIndex:0];

  [self setFrameToFit];
  [self setNeedsDisplay:YES];

  return ret;
}

- (NSUInteger)numMessagesRemaining {
  return [contentMessages_ count];
}

- (NSString*)continuousContentString {
  NSMutableString *res = [[[NSMutableString alloc] initWithString:@""]
                             autorelease];
  for (NSString *message in contentMessages_.get()) {
    [res appendString:message];
    if (message != [contentMessages_ lastObject])
      [res appendString:@"\n\n"];
  }
  return res;
}

- (BOOL)isFlipped {
  return YES;
}

@end

