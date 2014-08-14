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

#include "chrome/browser/ui/cocoa/facebook_chat/facebook_bitpop_notification_mac.h"

#include "base/mac/mac_util.h"
#include "base/memory/scoped_ptr.h"
#include "chrome/browser/bitmap_fetcher.h"
#include "chrome/browser/profiles/profile.h"
#import  "chrome/browser/ui/cocoa/dock_icon.h"
#include "content/child/image_decoder.h"
#include "content/public/browser/browser_thread.h"
#include "net/base/load_flags.h"
#include "skia/ext/skia_utils_mac.h"
#include "third_party/skia/include/core/SkBitmap.h"
#include "url/gurl.h"

using content::BrowserThread;
using chrome::BitmapFetcher;

namespace {

static const char* kProfileImageURLPart1 = "http://graph.facebook.com/";
static const char* kProfileImageURLPart2 = "/picture?type=square";

class FacebookProfileBitmapFetcherDelegate : public chrome::BitmapFetcherDelegate {
public:
  FacebookProfileBitmapFetcherDelegate(int num_unread_to_set_on_callback)
    : num_unread_to_set_(num_unread_to_set_on_callback), fetcher_for_deletion_(NULL) {}

  void set_fetcher_for_deletion(BitmapFetcher* fetcher) {
    fetcher_for_deletion_ = fetcher;
  }

  virtual void OnFetchComplete(const GURL url, const SkBitmap* bitmap) OVERRIDE {
    DCHECK(BrowserThread::CurrentlyOn(BrowserThread::UI));

    if (bitmap) {
      CGColorSpaceRef color_space = base::mac::GetSystemColorSpace();
      NSImage* image = gfx::SkBitmapToNSImageWithColorSpace(*bitmap, color_space);

      [[DockIcon sharedDockIcon] setUnreadNumber:num_unread_to_set_
                                withProfileImage:image];
      [[DockIcon sharedDockIcon] updateIcon];

      [NSApp requestUserAttention:NSInformationalRequest];
    }

    if (fetcher_for_deletion_)
      delete fetcher_for_deletion_;

    delete this;
  }
private:
  int num_unread_to_set_;
  BitmapFetcher* fetcher_for_deletion_;
};

} // namespace

FacebookBitpopNotificationMac::FacebookBitpopNotificationMac(Profile *profile)
    : profile_(profile) {
}

FacebookBitpopNotificationMac::~FacebookBitpopNotificationMac() {
  // delegate_ should delete itself after url fetch finish
}

void FacebookBitpopNotificationMac::ClearNotification() {
  [[DockIcon sharedDockIcon] setUnreadNumber:0 withProfileImage:nil];
  [[DockIcon sharedDockIcon] updateIcon];
}

void FacebookBitpopNotificationMac::NotifyUnreadMessagesWithLastUser(
    int num_unread, const std::string& user_id) {
  DCHECK(profile_);

  if (![NSApp isActive]) {
    FacebookProfileBitmapFetcherDelegate* delegate =
        new FacebookProfileBitmapFetcherDelegate(num_unread);
    BitmapFetcher* fetcher = new BitmapFetcher(
        GURL(std::string(kProfileImageURLPart1) + user_id +
             std::string(kProfileImageURLPart2)),
        delegate);
    delegate->set_fetcher_for_deletion(fetcher);
    fetcher->Start(
        profile_->GetRequestContext(),
        std::string(),
        net::URLRequest::CLEAR_REFERRER_ON_TRANSITION_FROM_SECURE_TO_INSECURE,
        net::LOAD_NORMAL);
  }
}

