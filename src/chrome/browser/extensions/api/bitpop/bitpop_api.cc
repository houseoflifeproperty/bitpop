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

#include "chrome/browser/extensions/api/bitpop/bitpop_api.h"

#include "base/values.h"
#include "chrome/browser/sync/profile_sync_service.h"
#include "chrome/browser/sync/profile_sync_service_factory.h"
#include "chrome/browser/ui/browser_navigator.h"

bool BitpopGetSyncStatusFunction::RunImpl() {
	ProfileSyncService* service =
			ProfileSyncServiceFactory::GetForProfile(profile());
	SetResult(base::Value::CreateBooleanValue(service && service->HasSyncSetupCompleted()));
	return true;
}

bool BitpopLaunchFacebookSyncFunction::RunImpl() {
	Browser *browser = GetCurrentBrowser();
	if (browser) {
		chrome::NavigateParams params(browser, GURL("chrome://signin/?fb_login=1"),
																	content::PAGE_TRANSITION_LINK);
		params.disposition = NEW_FOREGROUND_TAB;
		chrome::Navigate(&params);
		return true;
	}
	return false;
}
