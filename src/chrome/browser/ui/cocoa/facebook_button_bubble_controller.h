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

#import <Cocoa/Cocoa.h>

#import "chrome/browser/ui/cocoa/first_run_bubble_controller.h"

class Browser;
class Profile;

// Manages the facebook button bubble.
@interface FacebookButtonBubbleController : BaseBubbleController {
 @private
  IBOutlet NSTextField* header_;
  Browser* browser_;
  Profile* profile_;
  FirstRunBubbleController* other_;
}

// Creates and shows a facebook button bubble.
+ (FacebookButtonBubbleController*)
      showForParentWindow:(NSWindow*)parentWindow
              anchorPoint:(NSPoint)anchorPoint
                  browser:(Browser*)browser
                  profile:(Profile*)profile
                    other:(FirstRunBubbleController*)other;

@end
