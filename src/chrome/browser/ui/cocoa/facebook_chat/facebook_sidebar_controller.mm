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

#import "chrome/browser/ui/cocoa/facebook_chat/facebook_sidebar_controller.h"

#include <Cocoa/Cocoa.h>

#include "base/logging.h"
#include "base/mac/scoped_nsobject.h"
#include "base/prefs/pref_service.h"
#include "chrome/browser/browser_process.h"
#include "chrome/browser/chrome_notification_types.h"
#include "chrome/browser/extensions/extension_service.h"
#include "chrome/browser/extensions/extension_view_host.h"
#include "chrome/browser/extensions/extension_view_host_factory.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/ui/browser.h"
#include "chrome/browser/ui/cocoa/extensions/extension_view_mac.h"
#import "chrome/browser/ui/cocoa/view_id_util.h"
#include "chrome/common/chrome_constants.h"
#include "chrome/common/pref_names.h"
#include "content/public/browser/notification_details.h"
#include "content/public/browser/notification_observer.h"
#include "content/public/browser/notification_source.h"
#include "content/public/browser/web_contents.h"
#include "extensions/common/extension.h"
#include "extensions/browser/extension_registry.h"
#include "extensions/browser/extension_registry_observer.h"
#include "extensions/browser/extension_system.h"
#include "extensions/browser/runtime_data.h"

using content::WebContents;
using extensions::Extension;
using extensions::ExtensionSystem;
using extensions::UnloadedExtensionInfo;

namespace {

// Width of the facebook friends sidebar is constant and cannot be manipulated
// by user. When time comes we may change this decision.
const int kFriendsSidebarWidth = 186;
}  // end namespace

@interface FacebookSidebarController (Private)
- (void)showSidebarContents:(WebContents*)sidebarContents;
- (void)initializeExtensionHostWithExtensionLoaded:(BOOL)loaded;
- (void)sizeChanged;
- (void)onViewDidShow;
- (void)invalidateExtensionHost;
@end

@interface BackgroundSidebarView : NSView {}
@end

@implementation BackgroundSidebarView

- (void)drawRect:(NSRect)dirtyRect {
    // set any NSColor for filling, say white:
    [[NSColor grayColor] setFill];
    NSRectFill(dirtyRect);
}

@end

// NOTE: this class does nothing for now
class SidebarExtensionContainer : public ExtensionViewMac::Container {
 public:
  explicit SidebarExtensionContainer(FacebookSidebarController* controller)
       : controller_(controller) {
  }

  virtual void OnExtensionSizeChanged(ExtensionViewMac* view,
                                      const gfx::Size& new_size) OVERRIDE {}

  virtual void OnExtensionViewDidShow(ExtensionViewMac* view) OVERRIDE {
    [controller_ onViewDidShow];
  }

 private:
  FacebookSidebarController* controller_; // Weak; owns this.
};

class SidebarExtensionNotificationBridge : public content::NotificationObserver {
 public:
  explicit SidebarExtensionNotificationBridge(FacebookSidebarController* controller)
    : controller_(controller) {}

  virtual void Observe(int type,
               const content::NotificationSource& source,
               const content::NotificationDetails& details) OVERRIDE {
    switch (type) {
      case chrome::NOTIFICATION_EXTENSION_HOST_DID_STOP_LOADING: {
        if (content::Details<extensions::ExtensionHost>(
                [controller_ extension_view_host]) == details) {
          // ---
        }
        break;
      }

      case chrome::NOTIFICATION_EXTENSION_BACKGROUND_PAGE_READY: {
        [controller_ initializeExtensionHostWithExtensionLoaded:NO];
        break;
      }

      case chrome::NOTIFICATION_EXTENSION_HOST_VIEW_SHOULD_CLOSE: {
        if (content::Details<extensions::ExtensionHost>([controller_ extension_view_host]) == details) {
          [controller_ removeAllChildViews];
        }

        break;
      }

      default: {
        NOTREACHED() << "Received unexpected notification";
        break;
      }
    };
  }

 private:
  FacebookSidebarController* controller_;

};

class SidebarLoadedObserver : public extensions::ExtensionRegistryObserver {
 public:
  SidebarLoadedObserver(FacebookSidebarController* owner)
    : owner_(owner), processExtensionLoaded_(false) {}

  virtual void OnExtensionLoaded(
      content::BrowserContext* browser_context,
      const Extension* extension) OVERRIDE {
    if (processExtensionLoaded_) {
      if (extension->id() == chrome::kFacebookChatExtensionId) {
        [owner_ initializeExtensionHostWithExtensionLoaded:YES];
      }
    }
  }
  
  virtual void OnExtensionUnloaded(content::BrowserContext* browser_context,
                                   const Extension* extension,
                                   UnloadedExtensionInfo::Reason reason) OVERRIDE {
    if (extension->id() == chrome::kFacebookChatExtensionId) {
      [owner_ removeAllChildViews];
      [owner_ invalidateExtensionHost];
    }
  }

  void set_process_extension_loaded(bool process_extension_loaded) {
    processExtensionLoaded_ = process_extension_loaded;
  }

 private:
  FacebookSidebarController* owner_;
  bool processExtensionLoaded_;
};

@implementation FacebookSidebarController

@synthesize visible = sidebarVisible_;

- (id)initWithBrowser:(Browser*)browser {
  if ((self = [super initWithNibName:nil bundle:nil])) {
    browser_ = browser;
    sidebarVisible_ = NO;
    NSRect rc = [self view].frame;
    rc.size.width = kFriendsSidebarWidth;
    [[self view] setFrame:rc];

    view_id_util::SetID(
        [self view],
        VIEW_ID_FACEBOOK_FRIENDS_SIDE_BAR_CONTAINER);

    extension_container_.reset(new SidebarExtensionContainer(self));
    notification_bridge_.reset(new SidebarExtensionNotificationBridge(self));

    [[NSNotificationCenter defaultCenter]
        addObserver:self
        selector:@selector(sizeChanged)
        name:NSViewFrameDidChangeNotification
        object:[self view]
    ];

    sidebar_loaded_observer_.reset(new SidebarLoadedObserver(self));

    [self initializeExtensionHostWithExtensionLoaded:NO];
  }
  return self;
}

- (void)loadView {
  base::scoped_nsobject<NSView> view([[BackgroundSidebarView alloc] initWithFrame:NSZeroRect]);
  [view setAutoresizingMask:NSViewMinXMargin | NSViewHeightSizable];
  [view setAutoresizesSubviews:NO];
  [view setPostsFrameChangedNotifications:YES];

  [self setView:view];
}

- (void)dealloc {
  [[NSNotificationCenter defaultCenter] removeObserver:self];
  [super dealloc];
}

- (extensions::ExtensionViewHost*)extension_view_host {
  return extension_view_host_.get();
}

- (CGFloat)maxWidth {
  return kFriendsSidebarWidth;
}

- (void)initializeExtensionHostWithExtensionLoaded:(BOOL)loaded {
  Profile *profile = browser_->profile()->GetOriginalProfile();
  ExtensionService* service = profile->GetExtensionService();
  const Extension* sidebar_extension =
      service->extensions()->GetByID(chrome::kFacebookChatExtensionId);

  if (!sidebar_extension) {
    NOTREACHED() << "Empty extension.";
    return;
  }

  if (!ExtensionSystem::Get(profile)->runtime_data()->IsBackgroundPageReady(
      sidebar_extension)) {
    registrar_.RemoveAll();
    registrar_.Add(notification_bridge_.get(),
                   chrome::NOTIFICATION_EXTENSION_BACKGROUND_PAGE_READY,
                   content::Source<Extension>(sidebar_extension));
    extensions::ExtensionRegistry::Get(profile)->AddObserver(
        sidebar_loaded_observer_.get());
    if (!loaded)
      sidebar_loaded_observer_->set_process_extension_loaded(true);
    return;
  }

  std::string url = std::string("chrome-extension://") +
      std::string(chrome::kFacebookChatExtensionId) +
      std::string("/roster.html");
  
  extension_view_host_.reset(
    extensions::ExtensionViewHostFactory::CreatePopupHost(
      GURL(url), browser_));
  if (extension_view_host_.get()) {
    gfx::NativeView native_view = extension_view_host_->view()->native_view();
    NSRect container_bounds = [[self view] bounds];
    [native_view setFrame:container_bounds];
    [[self view] addSubview:native_view];
    extension_view_host_->view()->set_container(extension_container_.get());

    [native_view setNeedsDisplay:YES];

    // Wait to show the popup until the contained host finishes loading.
    registrar_.Add(notification_bridge_.get(),
                   chrome::NOTIFICATION_EXTENSION_HOST_DID_STOP_LOADING,
                   content::Source<extensions::ExtensionHost>(
                      extension_view_host_.get()));

    // Listen for the containing view calling window.close();
    registrar_.Add(notification_bridge_.get(),
                   chrome::NOTIFICATION_EXTENSION_HOST_VIEW_SHOULD_CLOSE,
                   content::Source<content::BrowserContext>(extension_view_host_->browser_context()));
  }
}

- (void)removeAllChildViews {
  NSMutableArray *viewsToRemove = [[NSMutableArray alloc] init];
  for (NSView* childView in [[self view] subviews])
    [viewsToRemove addObject:childView];
  [viewsToRemove makeObjectsPerformSelector:@selector(removeFromSuperview)];
  [viewsToRemove release];
}

- (void)setVisible:(BOOL)visible {
  sidebarVisible_ = visible;
  [[self view] setHidden:!visible];

  if (!extension_view_host_.get())
    return;

  gfx::NativeView native_view = extension_view_host_->view()->native_view();
  [native_view setNeedsDisplay:YES];
  [[self view] setNeedsDisplay:YES];
}

- (void)sizeChanged {
  if (!extension_view_host_.get())
    return;

  gfx::NativeView native_view = extension_view_host_->view()->native_view();
  NSRect container_bounds = [[self view] bounds];
  [native_view setFrame:container_bounds];

  [native_view setNeedsDisplay:YES];
  [[self view] setNeedsDisplay:YES];
}

- (void)onViewDidShow {
  [self sizeChanged];
}

- (void)invalidateExtensionHost {
  extension_view_host_.reset();
}

@end
