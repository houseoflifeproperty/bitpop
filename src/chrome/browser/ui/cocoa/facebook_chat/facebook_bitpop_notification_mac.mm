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
#include "chrome/browser/profiles/profile.h"
#import  "chrome/browser/ui/cocoa/dock_icon.h"
#include "content/child/image_decoder.h"
#include "content/public/browser/browser_thread.h"
#include "net/url_request/url_fetcher_impl.h"
#include "net/url_request/url_fetcher.h"
#include "net/url_request/url_fetcher_delegate.h"
#include "net/url_request/url_fetcher_factory.h"
#include "net/http/http_response_headers.h"
#include "net/url_request/url_request_status.h"
#include "skia/ext/skia_utils_mac.h"
#include "third_party/skia/include/core/SkBitmap.h"
#include "url/gurl.h"

using content::BrowserThread;
using net::URLFetcher;

static const char* kProfileImageURLPart1 = "http://graph.facebook.com/";
static const char* kProfileImageURLPart2 = "/picture?type=square";


class FacebookProfileImageFetcherDelegate : public net::URLFetcherDelegate {
public:
  FacebookProfileImageFetcherDelegate(Profile* profile,
      const std::string &uid, int num_unread_to_set_on_callback);

  virtual void OnURLFetchComplete(const URLFetcher* source) OVERRIDE;

private:
  scoped_ptr<URLFetcher> url_fetcher_;
  Profile* profile_;
  int num_unread_to_set_;
};

FacebookProfileImageFetcherDelegate::FacebookProfileImageFetcherDelegate(
    Profile* profile, const std::string &uid, int num_unread_to_set_on_callback)
 :
  profile_(profile),
  num_unread_to_set_(num_unread_to_set_on_callback) {

  url_fetcher_.reset(new net::URLFetcherImpl(
      GURL(std::string(kProfileImageURLPart1) + uid +
              std::string(kProfileImageURLPart2)),
          URLFetcher::GET,
          this)
  );
  url_fetcher_->SetRequestContext(profile_->GetRequestContext());
  url_fetcher_->Start();
}

void FacebookProfileImageFetcherDelegate::OnURLFetchComplete(const URLFetcher* source) {
  DCHECK(BrowserThread::CurrentlyOn(BrowserThread::UI));

  if (source->GetStatus().is_success() && (source->GetResponseCode() / 100 == 2)) {
    std::string mime_type;
    if (source->GetResponseHeaders()->GetMimeType(&mime_type) &&
        (mime_type == "image/gif" || mime_type == "image/png" ||
         mime_type == "image/jpeg")) {

      content::ImageDecoder decoder;

      std::string data;
      if (source->GetResponseAsString(&data)) {
        SkBitmap decoded = decoder.Decode(
            reinterpret_cast<const unsigned char*>(data.c_str()),
            data.length());

        CGColorSpaceRef color_space = base::mac::GetSystemColorSpace();
        NSImage* image = gfx::SkBitmapToNSImageWithColorSpace(decoded, color_space);

        [[DockIcon sharedDockIcon] setUnreadNumber:num_unread_to_set_
                                  withProfileImage:image];
        [[DockIcon sharedDockIcon] updateIcon];

        [NSApp requestUserAttention:NSInformationalRequest];
      }
    }
  }

  delete this;
}

// ---------------------------------------------------------------------------
FacebookBitpopNotificationMac::FacebookBitpopNotificationMac(Profile *profile)
  : profile_(profile), delegate_(NULL) {
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
  if (![NSApp isActive]) {
    delegate_ = new FacebookProfileImageFetcherDelegate(profile_, user_id,
        num_unread);
  }
}

