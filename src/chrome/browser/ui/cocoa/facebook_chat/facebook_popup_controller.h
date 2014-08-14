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

#ifndef CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_POPUP_CONTROLLER_H_
#define CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_POPUP_CONTROLLER_H_

#import <Cocoa/Cocoa.h>

#include "base/memory/scoped_ptr.h"
#import "chrome/browser/ui/cocoa/base_bubble_controller.h"
#import "chrome/browser/ui/cocoa/info_bubble_view.h"
#include "url/gurl.h"


class Browser;
class FacebookExtensionPopupContainer;
class FacebookExtensionObserverBridge;

namespace extensions {
class ExtensionViewHost;
}

// This controller manages a single browser action popup that can appear once a
// user has clicked on a browser action button. It instantiates the extension
// popup view showing the content and resizes the window to accomodate any size
// changes as they occur.
//
// There can only be one browser action popup open at a time, so a static
// variable holds a reference to the current popup.
@interface FacebookPopupController : BaseBubbleController {
 @private
  // The native extension view retrieved from the extension host. Weak.
  NSView* extensionView_;

  // The current frame of the extension view. Cached to prevent setting the
  // frame if the size hasn't changed.
  NSRect extensionFrame_;

  scoped_ptr<FacebookExtensionObserverBridge> fbObserverBridge_;

  // The extension host object.
  scoped_ptr<extensions::ExtensionViewHost> host_;

  scoped_ptr<FacebookExtensionPopupContainer> container_;

  // There's an extra windowDidResignKey: notification right after a
  // ConstrainedWindow closes that should be ignored.
  BOOL ignoreWindowDidResignKey_;

  // The size once the ExtensionView has loaded.
  NSSize pendingSize_;
}

// Returns the ExtensionHost object associated with this popup.
- (extensions::ExtensionViewHost*)extensionViewHost;

// Starts the process of showing the given popup URL. Instantiates an
// ExtensionPopupController with the parent window retrieved from |browser|, a
// host for the popup created by the extension process manager specific to the
// browser profile and the remaining arguments |anchoredAt| and |arrowLocation|.
// |anchoredAt| is expected to be in the window's coordinates at the bottom
// center of the browser action button.
// The actual display of the popup is delayed until the page contents finish
// loading in order to minimize UI flashing and resizing.
// Passing YES to |devMode| will launch the webkit inspector for the popup,
// and prevent the popup from closing when focus is lost.  It will be closed
// after the inspector is closed, or another popup is opened.
+ (FacebookPopupController*)showURL:(GURL)url
                           inBrowser:(Browser*)browser
                          anchoredAt:(NSPoint)anchoredAt
                       arrowLocation:(info_bubble::BubbleArrowLocation)
                                         arrowLocation;

// Returns the controller used to display the popup being shown. If no popup is
// currently open, then nil is returned. Static because only one extension popup
// window can be open at a time.
+ (FacebookPopupController*)popup;

// Whether the popup is in the process of closing (via Core Animation).
- (BOOL)isClosing;

@end

#endif   // CHROME_BROWSER_UI_COCOA_FACEBOOK_CHAT_FACEBOOK_POPUP_CONTROLLER_H_
