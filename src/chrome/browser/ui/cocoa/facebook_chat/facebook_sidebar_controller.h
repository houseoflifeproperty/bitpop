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

#ifndef CHROME_BROWSER_UI_COCOA_FACEBOOK_SIDEBAR_CONTROLLER_H_
#define CHROME_BROWSER_UI_COCOA_FACEBOOK_SIDEBAR_CONTROLLER_H_
#pragma once

#import <Cocoa/Cocoa.h>

#include "base/memory/scoped_ptr.h"
#include "content/public/browser/notification_registrar.h"

namespace extensions {
  class ExtensionViewHost;
}

class Browser;
class ExtensionHostPantry;
class SidebarExtensionContainer;
class SidebarExtensionNotificationBridge;
class SidebarLoadedObserver;


// A class that handles updates of the sidebar view within a browser window.
// It swaps in the relevant sidebar contents for a given TabContents or removes
// the vew, if there's no sidebar contents to show.
@interface FacebookSidebarController : NSViewController {
 @private
  BOOL sidebarVisible_;
  content::NotificationRegistrar registrar_;
  scoped_ptr<SidebarExtensionNotificationBridge> notification_bridge_;
  scoped_ptr<SidebarExtensionContainer> extension_container_;
  scoped_ptr<extensions::ExtensionViewHost> extension_view_host_;
  scoped_ptr<SidebarLoadedObserver> sidebar_loaded_observer_;
  Browser* browser_;
}

@property(nonatomic, assign) BOOL visible;

- (id)initWithBrowser:(Browser*)browser;

- (CGFloat)maxWidth;

- (void)removeAllChildViews;

- (extensions::ExtensionViewHost*)extension_view_host;

@end

#endif  // CHROME_BROWSER_UI_COCOA_FACEBOOK_SIDEBAR_CONTROLLER_H_
