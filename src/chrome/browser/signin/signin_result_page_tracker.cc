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

#include "chrome/browser/signin/signin_result_page_tracker.h"

#include "base/message_loop.h"
#include "chrome/browser/ui/browser.h"
#include "chrome/browser/ui/browser_finder.h"
#include "chrome/browser/ui/webui/signin/login_ui_service.h"
#include "chrome/browser/ui/webui/signin/login_ui_service_factory.h"
#include "chrome/common/url_constants.h"
#include "content/public/browser/navigation_controller.h"
#include "content/public/browser/navigation_entry.h"
#include "content/public/browser/notification_details.h"
#include "content/public/browser/notification_source.h"
#include "content/public/browser/page_navigator.h"
#include "content/public/browser/web_contents.h"
#include "net/base/escape.h"

#include <string>

using content::OpenURLParams;
using content::WebContents;
using content::NavigationController;

namespace {

enum ParseQueryState {
  START_STATE,
  KEYWORD_STATE,
  VALUE_STATE,
};

const char kHostToTrack[] = "sync.bitpop.com";
const char kAuthenticationSuccessPagePath[] = "/authentication_success/";
const char kAuthenticationErrorPagePath[] = "/login-error/";
const char kStateSetBySettingsPageIndicator = '1';
const char kStateSetBySigninPageIndicator = '2';

// Creates a string-to-string, keyword-value map from a parameter/query string
// that uses ampersand (&) to seperate paris and equals (=) to seperate
// keyword from value.
bool ParseQuery(const std::string& query,
                SigninResultPageTracker::Parameters* parameters_result) {
  std::string::const_iterator cursor;
  std::string keyword;
  std::string::const_iterator limit;
  SigninResultPageTracker::Parameters parameters;
  ParseQueryState state;
  std::string value;

  state = START_STATE;
  for (cursor = query.begin(), limit = query.end();
       cursor != limit;
       ++cursor) {
    char character = *cursor;
    switch (state) {
      case KEYWORD_STATE:
        switch (character) {
          case '&':
            parameters[keyword] = value;
            keyword = "";
            value = "";
            state = START_STATE;
            break;
          case '=':
            state = VALUE_STATE;
            break;
          default:
            keyword += character;
        }
        break;
      case START_STATE:
        switch (character) {
          case '&':  // Intentionally falling through
          case '=':
            return false;
          default:
            keyword += character;
            state = KEYWORD_STATE;
        }
        break;
      case VALUE_STATE:
        switch (character) {
          case '=':
            return false;
          case '&':
            parameters[keyword] = value;
            keyword = "";
            value = "";
            state = START_STATE;
            break;
          default:
            value += character;
        }
        break;
    }
  }
  switch (state) {
    case START_STATE:
      break;
    case KEYWORD_STATE:  // Intentionally falling through
    case VALUE_STATE:
      parameters[keyword] = value;
      break;
    default:
      NOTREACHED();
  }
  *parameters_result = parameters;
  return true;
}
}

SigninResultPageTracker::SigninResultPageTracker()
	: tracked_contents_(NULL),
		tracked_state_(),
		observer_(NULL) {
}

SigninResultPageTracker::~SigninResultPageTracker() {

}

void SigninResultPageTracker::Initialize(Profile* profile) {
	profile_ = profile;
}

void SigninResultPageTracker::Track(WebContents *contents,
																		const std::string& state,
																		Observer* observer) {
	if (tracked_contents_)
		UntrackCurrent();

	tracked_contents_ = contents;
	tracked_state_ = state;
	observer_ = observer;

	browser_ = chrome::FindBrowserWithWebContents(contents);
	if (browser_ && profile_ == browser_->profile()) {
		registrar_.Add(
	      this, content::NOTIFICATION_NAV_ENTRY_COMMITTED,
	      content::Source<NavigationController>(&contents->GetController()));
	  registrar_.Add(this, content::NOTIFICATION_WEB_CONTENTS_DESTROYED,
	                 content::Source<WebContents>(contents));
	}
}

void SigninResultPageTracker::UntrackCurrent() {
	if (!tracked_contents_)
		return;

  registrar_.Remove(this, content::NOTIFICATION_NAV_ENTRY_COMMITTED,
      content::Source<NavigationController>(&tracked_contents_->GetController()));
  registrar_.Remove(this, content::NOTIFICATION_WEB_CONTENTS_DESTROYED,
      content::Source<WebContents>(tracked_contents_));

  tracked_contents_ = NULL;
  tracked_state_.clear();
  observer_ = NULL;
}

void SigninResultPageTracker::FocusUI() {
	if (!tracked_contents_)
		return;
}

void SigninResultPageTracker::CloseUI() {
	PostCloseContents();
}

void SigninResultPageTracker::Observe(int type,
		const content::NotificationSource& source,
		const content::NotificationDetails& details) {

	switch (type) {
	case content::NOTIFICATION_NAV_ENTRY_COMMITTED: {
	    NavigationController* source_controller =
	      content::Source<NavigationController>(source).ptr();
	    DCHECK(source_controller->GetWebContents() == tracked_contents_);

	    GURL url(source_controller->GetLastCommittedEntry()->GetURL());

	    if (url.host() == kHostToTrack &&
	        url.has_path() && url.has_query() &&
	        (url.path() == kAuthenticationSuccessPagePath ||
	         url.path() == kAuthenticationErrorPagePath)) {

	    	Parameters params;
        ParseQuery(url.query(), &params);
        for (Parameters::iterator it = params.begin();
             it != params.end(); it++) {
          it->second = net::UnescapeURLComponent(it->second,
                                                 net::UnescapeRule::SPACES);
        }

        if (!params.count("state") || params["state"].empty() ||
        	  params["state"] != tracked_state_) {
        	PostCloseContents();
          return;
        }

        std::string state = params["state"];
        if (state[0] == kStateSetBySigninPageIndicator) {
        	GURL url2(std::string(chrome::kChromeUISyncPromoURL) +
        					 std::string("?") + url.query());
					OpenURLParams url_params(
          	url2, content::Referrer(), CURRENT_TAB, content::PAGE_TRANSITION_LINK, false);
      		tracked_contents_->OpenURL(url_params);
        } else if (state[0] == kStateSetBySettingsPageIndicator &&
        					 observer_ != NULL) {
        	if (params.count("email") && params.count("token") &&
        			params.count("type")) {
        		observer_->OnSigninCredentialsReady(params["email"],
        																				params["token"],
        																				params["type"]);
        	} else if (params.count("message")) {
        		observer_->OnSigninErrorOccurred(params["message"]);
        	}

        	PostCloseContents();
        }
	    }
		}
		break;

	case content::NOTIFICATION_WEB_CONTENTS_DESTROYED: {
			WebContents* contents = content::Source<WebContents>(source).ptr();
      DCHECK(contents == tracked_contents_);

      UntrackCurrent();
    }
    break;

  default:
  	NOTREACHED() << "Invalid notification received.";
	}
}

LoginUIService* SigninResultPageTracker::GetLoginUIService() const {
	if (!tracked_contents_)
		return NULL;

  return LoginUIServiceFactory::GetForProfile(GetProfile());
}

Profile* SigninResultPageTracker::GetProfile() const {
	if (!tracked_contents_)
		return NULL;

	return profile_;
}

void SigninResultPageTracker::PostCloseContents() {
	if (!tracked_contents_)
		return;

	MessageLoopForUI::current()->PostTask(
            FROM_HERE,
            base::Bind(&WebContents::Close,
                       base::Unretained(tracked_contents_))
          	);
}
