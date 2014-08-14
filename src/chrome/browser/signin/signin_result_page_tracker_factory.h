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

#ifndef CHROME_BROWSER_SIGNIN_SIGNIN_RESULT_PAGE_TRACKER_FACTORY_H_
#define CHROME_BROWSER_SIGNIN_SIGNIN_RESULT_PAGE_TRACKER_FACTORY_H_

#include "base/memory/singleton.h"
#include "chrome/browser/profiles/profile_keyed_service_factory.h"

class SigninResultPageTracker;
class Profile;

// Singleton that owns all SigninManagers and associates them with
// Profiles. Listens for the Profile's destruction notification and cleans up
// the associated SigninManager.
class SigninResultPageTrackerFactory : public ProfileKeyedServiceFactory {
 public:
  // Returns the instance of SigninManager associated with this profile
  // (creating one if none exists). Returns NULL if this profile cannot have a
  // SigninManager (for example, if |profile| is incognito).
  static SigninResultPageTracker* GetForProfile(Profile* profile);

  // Returns an instance of the SigninManagerFactory singleton.
  static SigninResultPageTrackerFactory* GetInstance();

 private:
  friend struct DefaultSingletonTraits<SigninResultPageTrackerFactory>;

  SigninResultPageTrackerFactory();
  virtual ~SigninResultPageTrackerFactory();

  // ProfileKeyedServiceFactory:
  virtual ProfileKeyedService* BuildServiceInstanceFor(
      Profile* profile) const OVERRIDE;
};

#endif  // CHROME_BROWSER_SIGNIN_SIGNIN_RESULT_PAGE_TRACKER_FACTORY_H_
