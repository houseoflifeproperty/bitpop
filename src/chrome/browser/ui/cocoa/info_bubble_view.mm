// Copyright (c) 2012 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#import "chrome/browser/ui/cocoa/info_bubble_view.h"

#include "base/logging.h"
#include "base/memory/scoped_nsobject.h"
#import "third_party/GTM/AppKit/GTMNSBezierPath+RoundRect.h"

@implementation InfoBubbleView

@synthesize arrowLocation = arrowLocation_;
@synthesize alignment = alignment_;
@synthesize cornerFlags = cornerFlags_;

- (id)initWithFrame:(NSRect)frameRect {
  if ((self = [super initWithFrame:frameRect])) {
    arrowLocation_ = info_bubble::kTopLeft;
    alignment_ = info_bubble::kAlignArrowToAnchor;
    cornerFlags_ = info_bubble::kRoundedAllCorners;
    backgroundColor_.reset([[NSColor whiteColor] retain]);
  }
  return self;
}

- (void)drawRect:(NSRect)rect {
  // Make room for the border to be seen.
  NSRect bounds = [self bounds];
  if (arrowLocation_ == info_bubble::kBottomCenter) {
    bounds.origin.y += info_bubble::kBubbleArrowHeight;
  }
  if (arrowLocation_ != info_bubble::kNoArrow) {
    bounds.size.height -= info_bubble::kBubbleArrowHeight;
  }
  rect.size.height -= info_bubble::kBubbleArrowHeight;

  float topRadius = cornerFlags_ & info_bubble::kRoundedTopCorners ?
      info_bubble::kBubbleCornerRadius : 0;
  float bottomRadius = cornerFlags_ & info_bubble::kRoundedBottomCorners ?
      info_bubble::kBubbleCornerRadius : 0;

  NSBezierPath* bezier =
      [NSBezierPath gtm_bezierPathWithRoundRect:bounds
                            topLeftCornerRadius:topRadius
                           topRightCornerRadius:topRadius
                         bottomLeftCornerRadius:bottomRadius
                        bottomRightCornerRadius:bottomRadius];

  // Add the bubble arrow.
  CGFloat dX = 0;
  switch (arrowLocation_) {
    case info_bubble::kTopLeft:
      dX = info_bubble::kBubbleArrowXOffset;
      break;
    case info_bubble::kTopRight:
      dX = NSWidth(bounds) - info_bubble::kBubbleArrowXOffset -
          info_bubble::kBubbleArrowWidth;
      break;
    case info_bubble::kBottomCenter:
      dX = (NSWidth(bounds) - info_bubble::kBubbleArrowWidth) / 2;
      break;
    case info_bubble::kNoArrow:
      break;
    default:
      NOTREACHED();
      break;
  }
  NSPoint arrowStart =
      (arrowLocation_ != info_bubble::kBottomCenter) ?
          NSMakePoint(NSMinX(bounds), NSMaxY(bounds)) :
          NSMakePoint(NSMinX(bounds), NSMinY(bounds));

  arrowStart.x += dX;
  [bezier moveToPoint:NSMakePoint(arrowStart.x, arrowStart.y)];
  if (arrowLocation_ != info_bubble::kNoArrow) {
    [bezier lineToPoint:NSMakePoint(
        arrowStart.x +
            info_bubble::kBubbleArrowWidth / 2.0,
        arrowStart.y +
            ((arrowLocation_ != info_bubble::kBottomCenter) ? 1 : -1) *
            info_bubble::kBubbleArrowHeight)];
  }
  [bezier lineToPoint:NSMakePoint(arrowStart.x + info_bubble::kBubbleArrowWidth,
                                  arrowStart.y)];
  [bezier closePath];
  [backgroundColor_ set];
  [bezier fill];
}

- (NSPoint)arrowTip {
  NSRect bounds = [self bounds];
  CGFloat xOffset = 0;
  if (arrowLocation_ != info_bubble::kBottomCenter) {
    CGFloat tipXOffset =
        info_bubble::kBubbleArrowXOffset + info_bubble::kBubbleArrowWidth / 2.0;
    xOffset =
        (arrowLocation_ == info_bubble::kTopRight) ?
            NSMaxX(bounds) - tipXOffset :
            NSMinX(bounds) + tipXOffset;
  } else
    xOffset = NSMinX(bounds) + NSWidth(bounds) / 2;

  NSPoint arrowTip = NSMakePoint(xOffset,
      (arrowLocation_ == info_bubble::kBottomCenter) ? NSMinY(bounds) :
                                                       NSMaxY(bounds));
  return arrowTip;
}

- (NSColor*)backgroundColor {
  return backgroundColor_;
}

- (void)setBackgroundColor:(NSColor*)backgroundColor {
  backgroundColor_.reset([backgroundColor retain]);
}

@end
