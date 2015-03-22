// BitPop browser. Tor launcher integration part.
// Copyright (C) 2015 BitPop AS
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

#ifndef CHROME_BROWSER_TORLAUNCHER_TORLAUNCHER_SERVICE_FACTORY_H_
#define CHROME_BROWSER_TORLAUNCHER_TORLAUNCHER_SERVICE_FACTORY_H_

#include "base/memory/singleton.h"
#include "components/keyed_service/content/browser_context_keyed_service_factory.h"

class Profile;

namespace torlauncher {

class TorLauncherService;

// Singleton that owns all TorLauncherServices and associates them with
// Profiles.
class TorLauncherServiceFactory : public BrowserContextKeyedServiceFactory {
 public:
  // Returns the TorLauncherService for |profile|.
  static torlauncher::TorLauncherService* GetForProfile(Profile* profile);

  static TorLauncherServiceFactory* GetInstance();

 private:
  friend struct DefaultSingletonTraits<TorLauncherServiceFactory>;

  TorLauncherServiceFactory();
  virtual ~TorLauncherServiceFactory();

  // Overrides from BrowserContextKeyedServiceFactory:
  virtual content::BrowserContext* GetBrowserContextToUse(
      content::BrowserContext* context) const OVERRIDE;
  virtual KeyedService* BuildServiceInstanceFor(
      content::BrowserContext* profile) const OVERRIDE;
  virtual void RegisterProfilePrefs(
      user_prefs::PrefRegistrySyncable* registry) OVERRIDE;

  DISALLOW_COPY_AND_ASSIGN(TorLauncherServiceFactory);
};

}  // namespace torlauncher

#endif  // CHROME_BROWSER_TORLAUNCHER_TORLAUNCHER_SERVICE_FACTORY_H_
