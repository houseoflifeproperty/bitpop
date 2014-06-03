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

#include "chrome/browser/signin/signin_result_page_tracker_factory.h"

#include "chrome/browser/profiles/profile_dependency_manager.h"
#include "chrome/browser/signin/signin_result_page_tracker.h"


SigninResultPageTrackerFactory::SigninResultPageTrackerFactory()
    : ProfileKeyedServiceFactory("SigninResultPageTracker",
                                 ProfileDependencyManager::GetInstance()) {
}

SigninResultPageTrackerFactory::~SigninResultPageTrackerFactory() {}

// static
SigninResultPageTracker* SigninResultPageTrackerFactory::GetForProfile(
	Profile* profile) {
  return static_cast<SigninResultPageTracker*>(
    GetInstance()->GetServiceForProfile(profile, true));
}

// static
SigninResultPageTrackerFactory* SigninResultPageTrackerFactory::GetInstance() {
  return Singleton<SigninResultPageTrackerFactory>::get();
}

ProfileKeyedService* SigninResultPageTrackerFactory::BuildServiceInstanceFor(
    Profile* profile) const {
  SigninResultPageTracker* service = new SigninResultPageTracker();
  service->Initialize(profile);
  return service;
}
