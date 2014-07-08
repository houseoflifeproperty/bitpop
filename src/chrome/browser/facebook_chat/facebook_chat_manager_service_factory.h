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

#include "base/compiler_specific.h"
#include "base/memory/singleton.h"
#include "components/keyed_service/content/browser_context_keyed_service_factory.h"

class FacebookChatManager;
class Profile;

class FacebookChatManagerServiceFactory : public BrowserContextKeyedServiceFactory {
 public:
  static FacebookChatManager* GetForProfile(Profile* profile);

  static FacebookChatManagerServiceFactory* GetInstance();

 private:
  friend struct DefaultSingletonTraits<FacebookChatManagerServiceFactory>;

  FacebookChatManagerServiceFactory();
  virtual ~FacebookChatManagerServiceFactory();

  // ProfileKeyedServiceFactory:
  virtual KeyedService* BuildServiceInstanceFor(
    content::BrowserContext* profile) const OVERRIDE;

  DISALLOW_COPY_AND_ASSIGN(FacebookChatManagerServiceFactory);
};

