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

#import "chrome/browser/ui/cocoa/facebook_chat/facebook_bubble_view.h"

#include "ui/gfx/scoped_ns_graphics_context_save_gstate_mac.h"

@interface NSBezierPath(Popups)
- (void)appendBezierPathWithRoundedRectangle:(NSRect)aRect topLeftRadius:(float)topLeftRadius topRightRadius:(float)topRightRadius bottomLeftRadius:(float)bottomLeftRadius bottomRightRadius:(float)bottomRightRadius arrowLocation:(fb_bubble::BubbleArrowLocation)arrowLocation;
@end

@implementation NSBezierPath(Popups)
- (void)appendBezierPathWithRoundedRectangle:(NSRect)aRect topLeftRadius:(float)topLeftRadius topRightRadius:(float)topRightRadius bottomLeftRadius:(float)bottomLeftRadius bottomRightRadius:(float)bottomRightRadius arrowLocation:(fb_bubble::BubbleArrowLocation)arrowLocation
{
	float maxRadius =  0.5 * MIN(aRect.size.width, aRect.size.height);

	topLeftRadius = MIN(topLeftRadius, maxRadius);
	bottomLeftRadius = MIN(bottomLeftRadius, maxRadius);
	topRightRadius = MIN(topRightRadius, maxRadius);
	bottomRightRadius = MIN(bottomRightRadius, maxRadius);

    NSPoint topMid = NSMakePoint(NSMidX(aRect), NSMaxY(aRect));
    NSPoint leftMid = NSMakePoint(NSMinX(aRect), NSMidY(aRect));
    NSPoint rightMid = NSMakePoint(NSMaxX(aRect), NSMidY(aRect));
    //NSPoint bottomMid = NSMakePoint(NSMidX(aRect), NSMinY(aRect));
    NSPoint topLeft = NSMakePoint(NSMinX(aRect), NSMaxY(aRect));
    NSPoint topRight = NSMakePoint(NSMaxX(aRect), NSMaxY(aRect));
    NSPoint bottomRight = NSMakePoint(NSMaxX(aRect), NSMinY(aRect));
	NSPoint bottomLeft = NSMakePoint(NSMinX(aRect), NSMinY(aRect));

    [self moveToPoint:topMid];
    [self appendBezierPathWithArcFromPoint:topLeft
                                   toPoint:leftMid
                                    radius:topLeftRadius];

  CGFloat dX = (arrowLocation == fb_bubble::kBottomLeft) ?
      fb_bubble::kBubbleArrowXOffset :
      NSMidX(aRect) - NSMinX(aRect) - fb_bubble::kBubbleArrowWidth / 2;

  NSPoint arrowStart = NSMakePoint(NSMinX(aRect), NSMinY(aRect));
  arrowStart.x += dX;

	[self appendBezierPathWithArcFromPoint:bottomLeft
								   toPoint:arrowStart
                   radius:bottomLeftRadius];

  [self lineToPoint:arrowStart];
  [self lineToPoint:NSMakePoint(arrowStart.x +
      fb_bubble::kBubbleArrowWidth / 2,
      arrowStart.y - fb_bubble::kBubbleArrowHeight)];
  [self lineToPoint:NSMakePoint(arrowStart.x +
      fb_bubble::kBubbleArrowWidth,
      arrowStart.y)];

	[self appendBezierPathWithArcFromPoint:bottomRight
                                   toPoint:rightMid
                                    radius:bottomRightRadius];

	[self appendBezierPathWithArcFromPoint:topRight
								   toPoint:topMid
                                    radius:topRightRadius];
    [self closePath];
}
@end

@implementation FacebookBubbleView

@synthesize arrowLocation=arrowLocation_;

- (id)initWithFrame:(NSRect)frameRect {
  if ((self = [super initWithFrame:frameRect])) {
    // do member initialization here
    arrowLocation_ = fb_bubble::kBottomLeft;
    [self setBackgroundColor:[NSColor whiteColor]];
  }
  return self;
}

- (void)drawRect:(NSRect)rect {
  gfx::ScopedNSGraphicsContextSaveGState scopedGState;

  NSRect bounds = NSInsetRect([self bounds], 0.5, 0.5);

  bounds.size.height -= fb_bubble::kBubbleArrowHeight;
  // we will only support bottom left arrow positioning as for now
  bounds.origin.y += fb_bubble::kBubbleArrowHeight;

  NSBezierPath *bezier = [NSBezierPath bezierPath];
  // Start with a rounded rectangle.
  [bezier appendBezierPathWithRoundedRectangle:bounds
                                 topLeftRadius:fb_bubble::kBubbleCornerRadius
                                topRightRadius:fb_bubble::kBubbleCornerRadius
                              bottomLeftRadius:fb_bubble::kBubbleCornerRadius
                             bottomRightRadius:fb_bubble::kBubbleCornerRadius
                                 arrowLocation:arrowLocation_];

  // drawing an arrow at bottom left
  /*
  NSBezierPath* arrowPath = [NSBezierPath bezierPath];
  CGFloat dX = (arrowLocation_ == fb_bubble::kBottomLeft) ?
      fb_bubble::kBubbleArrowXOffset :
      NSMidX(bounds) - NSMinX(bounds) - fb_bubble::kBubbleArrowWidth / 2;

  NSPoint arrowStart = NSMakePoint(NSMinX(bounds), NSMinY(bounds));
  arrowStart.x += dX;
  [arrowPath moveToPoint:arrowStart];
  [arrowPath lineToPoint:NSMakePoint(arrowStart.x +
      fb_bubble::kBubbleArrowWidth / 2,
      arrowStart.y - fb_bubble::kBubbleArrowHeight)];
  [arrowPath lineToPoint:NSMakePoint(arrowStart.x +
      fb_bubble::kBubbleArrowWidth,
      arrowStart.y)];
  [arrowPath closePath];
  */

  // draw border showing up from bottom layer
  NSColor* borderColor = [NSColor colorWithCalibratedWhite:(100.0/255.0)
                                                     alpha:1.0];

  [backgroundColor_ set];
  [bezier fill];

  [bezier setLineWidth: 1.0];
  //[arrowPath setLineWidth: 1.5];
  [borderColor set];
  //[[bezier bezierPathByReversingPath] setClip];
  //[arrowPath stroke];
  //[[arrowPath bezierPathByReversingPath] setClip];
  [bezier stroke];
}

- (NSPoint)arrowTip {
  NSRect bounds = [self bounds];
  NSPoint tip = NSMakePoint((arrowLocation_ == fb_bubble::kBottomLeft) ?
      NSMinX(bounds) + fb_bubble::kBubbleArrowXOffset +
        fb_bubble::kBubbleArrowWidth / 2 :
      NSMidX(bounds),
      NSMinY(bounds));
  return tip;
}

- (void)setBackgroundColor:(NSColor*)bgrColor {
  backgroundColor_.reset([bgrColor retain]);
}

@end
