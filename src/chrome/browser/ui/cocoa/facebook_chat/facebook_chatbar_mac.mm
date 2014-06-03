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

#import "chrome/browser/ui/cocoa/facebook_chat/facebook_chatbar_mac.h"

#import "chrome/browser/ui/cocoa/facebook_chat/facebook_chatbar_controller.h"
#include "chrome/browser/ui/browser.h"
#include "chrome/browser/ui/fullscreen/fullscreen_controller.h"

FacebookChatbarMac::FacebookChatbarMac(Browser *browser,
                                       FacebookChatbarController *controller)
                                       : browser_(browser),
                                         controller_(controller) {
}

void FacebookChatbarMac::AddChatItem(FacebookChatItem *chat_item) {
  [controller_ addChatItem: chat_item];
  if (!browser_ || !browser_->fullscreen_controller()->IsFullscreenForTabOrPending())
    Show();
}

void FacebookChatbarMac::Show() {
  [controller_ show:nil];
}

void FacebookChatbarMac::Hide() {
  [controller_ hide:nil];
}

Browser *FacebookChatbarMac::browser() const {
  return browser_;
}

void FacebookChatbarMac::RemoveAll() {
  [controller_ removeAll];
  Hide();
}
