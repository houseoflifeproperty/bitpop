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

#import "chrome/browser/ui/cocoa/facebook_chat/facebook_chatbar_view.h"

#include "chrome/browser/themes/theme_properties.h"
#include "chrome/browser/themes/theme_service.h"
#import "chrome/browser/ui/cocoa/nsview_additions.h"
#import "chrome/browser/ui/cocoa/tabs/tab_strip_controller.h"
#import "chrome/browser/ui/cocoa/themed_window.h"
#import "chrome/browser/ui/cocoa/view_id_util.h"
#include "grit/theme_resources.h"
#import "ui/base/cocoa/nsgraphics_context_additions.h"
#include "ui/gfx/scoped_ns_graphics_context_save_gstate_mac.h"

@implementation FacebookChatbarView

// For programmatic instantiations in unit tests.
- (id)initWithFrame:(NSRect)frameRect {
  if ((self = [super initWithFrame:frameRect])) {
    [self setShowsDivider:NO];
  }
  return self;
}

// For nib instantiations in production.
- (id)initWithCoder:(NSCoder*)decoder {
  if ((self = [super initWithCoder:decoder])) {
    [self setShowsDivider:NO];
  }
  return self;
}

- (NSColor*)strokeColor {
  BOOL isActive = [[self window] isMainWindow];
  ui::ThemeProvider* themeProvider = [[self window] themeProvider];
  return themeProvider ? themeProvider->GetNSColor(
      isActive ? ThemeProperties::COLOR_TOOLBAR_STROKE :
                 ThemeProperties::COLOR_TOOLBAR_STROKE_INACTIVE) :
      [NSColor blackColor];
}

- (void)drawRect:(NSRect)rect {
  gfx::ScopedNSGraphicsContextSaveGState saveGState;

  // We want our backgrounds for the shelf to be phased from the upper
  // left hand corner of the view. Offset it by tab height so that the
  // background matches the toolbar background.
  CGFloat yOffset = NSMaxY([self frame]);
  NSPoint phase = NSMakePoint(
      0, yOffset + [TabStripController defaultTabHeight]);
  [[NSGraphicsContext currentContext] setPatternPhase:phase];
  [self drawBackgroundWithOpaque:YES];

  // Draw top stroke
  [[self strokeColor] set];
  NSRect borderRect, contentRect;
  NSDivideRect([self bounds], &borderRect, &contentRect, [self cr_lineWidth],
               NSMaxYEdge);
  NSRectFillUsingOperation(borderRect, NSCompositeSourceOver);

  // Draw the top highlight
  ThemeService* themeProvider =
      static_cast<ThemeService*>([[self window] themeProvider]);
  if (themeProvider) {
    int resourceName = themeProvider->UsingDefaultTheme() ?
        ThemeProperties::COLOR_TOOLBAR_BEZEL : ThemeProperties::COLOR_TOOLBAR;
    NSColor* highlightColor = themeProvider->GetNSColor(resourceName);
    if (highlightColor) {
      [highlightColor set];
      borderRect.origin.y -= [self cr_lineWidth];
      NSRectFillUsingOperation(borderRect, NSCompositeSourceOver);
    }
  }
}

// Mouse down events on the download shelf should not allow dragging the parent
// window around.
- (BOOL)mouseDownCanMoveWindow {
  return NO;
}

- (ViewID)viewID {
  return VIEW_ID_FACEBOOK_CHATBAR;
}

- (BOOL)isOpaque {
  return YES;
}

@end
