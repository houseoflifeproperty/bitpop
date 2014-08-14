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

#include "chrome/browser/facebook_chat/facebook_chat_manager_service_factory.h"

#include "chrome/browser/facebook_chat/facebook_chat_manager.h"
#include "chrome/browser/profiles/profile.h"
#include "components/keyed_service/content/browser_context_dependency_manager.h"

// static
FacebookChatManager* FacebookChatManagerServiceFactory::GetForProfile(Profile* profile) {
  return static_cast<FacebookChatManager*>(
      GetInstance()->GetServiceForBrowserContext(profile, true));
}

// static
FacebookChatManagerServiceFactory* FacebookChatManagerServiceFactory::GetInstance() {
  return Singleton<FacebookChatManagerServiceFactory>::get();
}

FacebookChatManagerServiceFactory::FacebookChatManagerServiceFactory()
    : BrowserContextKeyedServiceFactory("facebook_chat_manager",
    							 BrowserContextDependencyManager::GetInstance()) {
}

FacebookChatManagerServiceFactory::~FacebookChatManagerServiceFactory() {
}

KeyedService* FacebookChatManagerServiceFactory::BuildServiceInstanceFor(
    content::BrowserContext* profile) const {
  return new FacebookChatManager();
}

