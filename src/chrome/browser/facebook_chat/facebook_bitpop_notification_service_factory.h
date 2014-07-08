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

#ifndef CHROME_BROWSER_FACEBOOK_CHAT_FACEBOOK_BITPOP_NOTIFICATION_SERVICE_FACTORY_H_
#define CHROME_BROWSER_FACEBOOK_CHAT_FACEBOOK_BITPOP_NOTIFICATION_SERVICE_FACTORY_H_

#include "base/compiler_specific.h"
#include "base/memory/singleton.h"
#include "components/keyed_service/content/browser_context_keyed_service_factory.h"

class FacebookBitpopNotification;
class Profile;

// Singleton that owns all BackgroundContentsServices and associates them with
// Profiles. Listens for the Profile's destruction notification and cleans up
// the associated BackgroundContentsService.
class FacebookBitpopNotificationServiceFactory
    : public BrowserContextKeyedServiceFactory {
 public:
  static FacebookBitpopNotification* GetForProfile(Profile* profile);

  static FacebookBitpopNotificationServiceFactory* GetInstance();

 private:
  friend struct DefaultSingletonTraits<FacebookBitpopNotificationServiceFactory>;

  FacebookBitpopNotificationServiceFactory();
  virtual ~FacebookBitpopNotificationServiceFactory();

  // BrowserContextKeyedServiceFactory:
  virtual KeyedService* BuildServiceInstanceFor(
      content::BrowserContext* profile) const OVERRIDE;
};

#endif  // CHROME_BROWSER_FACEBOOK_CHAT_FACEBOOK_BITPOP_NOTIFICATION_SERVICE_FACTORY_H_

