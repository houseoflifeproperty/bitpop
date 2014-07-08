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

#include "chrome/browser/facebook_chat/facebook_bitpop_notification_service_factory.h"

#include "chrome/browser/facebook_chat/facebook_bitpop_notification.h"
#include "chrome/browser/profiles/profile.h"
#include "components/keyed_service/content/browser_context_dependency_manager.h"

#if defined(OS_WIN)
#include "chrome/browser/ui/views/facebook_chat/facebook_bitpop_notification_win.h"
#elif defined (OS_MACOSX)
#include "chrome/browser/ui/cocoa/facebook_chat/facebook_bitpop_notification_mac.h"
#endif

// static
FacebookBitpopNotification* FacebookBitpopNotificationServiceFactory::GetForProfile(Profile* profile) {
  return static_cast<FacebookBitpopNotification*>(
      GetInstance()->GetServiceForBrowserContext(profile, true));
}

// static
FacebookBitpopNotificationServiceFactory* FacebookBitpopNotificationServiceFactory::GetInstance() {
  return Singleton<FacebookBitpopNotificationServiceFactory>::get();
}

FacebookBitpopNotificationServiceFactory::FacebookBitpopNotificationServiceFactory()
    : BrowserContextKeyedServiceFactory("facebook_bitpop_notification",
    									BrowserContextDependencyManager::GetInstance()) {
}

FacebookBitpopNotificationServiceFactory::~FacebookBitpopNotificationServiceFactory() {
}

KeyedService* FacebookBitpopNotificationServiceFactory::BuildServiceInstanceFor(
    content::BrowserContext* profile) const {
#if defined(OS_WIN)
  return new FacebookBitpopNotificationWin(static_cast<Profile*>(profile));
#elif defined (OS_MACOSX)
  return new FacebookBitpopNotificationMac(static_cast<Profile*>(profile));
#else
  return NULL;
#endif
}

