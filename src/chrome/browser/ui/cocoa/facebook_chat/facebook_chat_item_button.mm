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

#import "chrome/browser/ui/cocoa/facebook_chat/facebook_chat_item_button.h"

#import <Cocoa/Cocoa.h>

#include "base/memory/scoped_nsobject.h"
#import "chrome/browser/ui/cocoa/facebook_chat/facebook_chat_item_controller.h"
#include "chrome/browser/facebook_chat/facebook_chat_item.h"
#include "ui/gfx/scoped_ns_graphics_context_save_gstate_mac.h"

namespace {
  static const CGFloat kDefaultCornerRadius = 3;
  const CGFloat kRightDecorationDim = 16;
}

@implementation FacebookChatItemCell

- (void)drawWithFrame:(NSRect)cellFrame inView:(NSView *)controlView {
  NSRect hlBounds = NSInsetRect(cellFrame, 10, 5.5);

  if (controlView && [controlView isKindOfClass:[FacebookChatItemButton class]]) {
    FacebookChatItemButton* buttonControl = (FacebookChatItemButton*)controlView;
    FacebookChatItemController* controller = buttonControl.fbController;

    if (controller && [controller chatItem] &&
        [controller chatItem]->num_notifications() != 0) {
      NSRect hlBounds2 = NSInsetRect(hlBounds, 0.5, 2.5);
      hlBounds2.size.height -= 2;

      gfx::ScopedNSGraphicsContextSaveGState scopedGState;
      scoped_nsobject<NSShadow> shadow([[NSShadow alloc] init]);
      [shadow.get() setShadowOffset:NSMakeSize(1, 1)];
      [shadow setShadowBlurRadius:8];
      [shadow setShadowColor:[NSColor colorWithCalibratedRed: 0.0
                                                       green: 0.6
                                                        blue: 1.0
                                                       alpha: 1.0]];
      NSBezierPath *shadowPath =
          [NSBezierPath bezierPathWithRoundedRect:hlBounds2
                                          xRadius:kDefaultCornerRadius
                                          yRadius:kDefaultCornerRadius];
      [[NSColor whiteColor] set];

      [shadow set];

      [shadowPath fill];
    }
  }

  [super drawWithFrame:hlBounds inView:controlView];
}

- (NSRect)drawTitle:(NSAttributedString *)title withFrame:(NSRect)frame inView:(NSView *)controlView {
  frame.size.width -= kRightDecorationDim;
  return [super drawTitle:title withFrame:frame inView:controlView];
}
@end

@implementation FacebookChatItemButton

@synthesize fbController=controller_;

+ (Class)cellClass {
  return [FacebookChatItemCell class];
}

@end

