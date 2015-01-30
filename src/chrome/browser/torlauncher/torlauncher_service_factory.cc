// BitPop browser. Facebook chat integration part.
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

#include "chrome/browser/torlauncher/torlauncher_service_factory.h"

#include "base/memory/scoped_ptr.h"
#include "base/prefs/pref_service.h"
#include "chrome/browser/profiles/incognito_helpers.h"
#include "chrome/browser/profiles/profile.h"
#include "components/keyed_service/content/browser_context_dependency_manager.h"
#include "components/pref_registry/pref_registry_syncable.h"
#include "components/torlauncher/torlauncher_service.h"
#include "content/public/browser/browser_context.h"

namespace torlauncher {

// static
TorLauncherService* TorLauncherServiceFactory::GetForProfile(Profile* profile) {
  return static_cast<TorLauncherService*>(
      GetInstance()->GetServiceForBrowserContext(profile, true));
}

// static
TorLauncherServiceFactory* TorLauncherServiceFactory::GetInstance() {
  return Singleton<TorLauncherServiceFactory>::get();
}

TorLauncherServiceFactory::TorLauncherServiceFactory()
    : BrowserContextKeyedServiceFactory(
          "TorLauncherService",
          BrowserContextDependencyManager::GetInstance()) {
  // No dependencies.
}

TorLauncherServiceFactory::~TorLauncherServiceFactory() {}

content::BrowserContext* TorLauncherServiceFactory::GetBrowserContextToUse(
    content::BrowserContext* context) const {
  return chrome::GetBrowserContextOwnInstanceInIncognito(context);
}

KeyedService* TorLauncherServiceFactory::BuildServiceInstanceFor(
    content::BrowserContext* profile) const {

  Profile* the_profile = static_cast<Profile*>(profile);

  return new TorLauncherService(the_profile->GetPrefs());
}

void TorLauncherServiceFactory::RegisterProfilePrefs(
    user_prefs::PrefRegistrySyncable* registry) {
  TorLauncherService::RegisterProfilePrefs(registry);
}

}  // namespace torlauncher
