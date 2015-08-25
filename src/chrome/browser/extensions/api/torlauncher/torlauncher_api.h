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

#ifndef CHROME_BROWSER_EXTENSIONS_API_TORLAUNCHER_TORLAUNCHER_API_H_
#define CHROME_BROWSER_EXTENSIONS_API_TORLAUNCHER_TORLAUNCHER_API_H_

#include "extensions/browser/extension_function.h"

namespace extensions {

class TorlauncherLaunchTorBrowserFunction : public UIThreadExtensionFunction {
  ~TorlauncherLaunchTorBrowserFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.launchTorBrowser", TORLAUNCHER_LAUNCHTORBROWSER);
};

class TorlauncherStartTorFunction : public UIThreadExtensionFunction {
  ~TorlauncherStartTorFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.startTor", TORLAUNCHER_STARTTOR)
};
class TorlauncherInitiateAppQuitFunction : public UIThreadExtensionFunction {
  ~TorlauncherInitiateAppQuitFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.initiateAppQuit",
                             TORLAUNCHER_INITIATEAPPQUIT)
};
class TorlauncherGetTorProcessStatusFunction : public UIThreadExtensionFunction {
  ~TorlauncherGetTorProcessStatusFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.getTorProcessStatus",
                             TORLAUNCHER_GETTORPROCESSSTATUS)
};
class TorlauncherSetTorStatusRunningFunction : public UIThreadExtensionFunction {
  ~TorlauncherSetTorStatusRunningFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.setTorStatusRunning",
                             TORLAUNCHER_SETTORSTATUSRUNNING)
};
class TorlauncherGetTorServiceSettingsFunction : public UIThreadExtensionFunction {
  ~TorlauncherGetTorServiceSettingsFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.getTorServiceSettings",
                             TORLAUNCHER_GETTORSERVICESETTINGS)
};
class TorlauncherEnvExistsFunction : public UIThreadExtensionFunction {
  ~TorlauncherEnvExistsFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.envExists",
                             TORLAUNCHER_ENVEXISTS)
};
class TorlauncherEnvGetFunction : public UIThreadExtensionFunction {
  ~TorlauncherEnvGetFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.envGet",
                             TORLAUNCHER_ENVGET)
};
class TorlauncherReadAuthenticationCookieFunction:
    public UIThreadExtensionFunction {
  ~TorlauncherReadAuthenticationCookieFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.readAuthenticationCookie",
                             TORLAUNCHER_READAUTHENTICATIONCOOKIE)
};
class TorlauncherSendTorNetworkSettingsResultFunction:
    public UIThreadExtensionFunction {
  ~TorlauncherSendTorNetworkSettingsResultFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.sendTorNetworkSettingsResult",
                             TORLAUNCHER_SENDTORNETWORKSETTINGSRESULT)
};
class TorlauncherNotifyTorOpenControlConnectionSuccessFunction:
    public UIThreadExtensionFunction {
  ~TorlauncherNotifyTorOpenControlConnectionSuccessFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.notifyTorOpenControlConnectionSuccess",
                             TORLAUNCHER_NOTIFYTOROPENCONTROLCONNECTIONSUCCESS)
};
class TorlauncherNotifyTorCircuitsEstablishedFunction:
    public UIThreadExtensionFunction {
  ~TorlauncherNotifyTorCircuitsEstablishedFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.notifyTorCircuitsEstablished",
                             TORLAUNCHER_NOTIFYTORCIRCUITSESTABLISHED)
};
class TorlauncherNotifyTorSaveSettingsSuccessFunction:
    public UIThreadExtensionFunction {
  ~TorlauncherNotifyTorSaveSettingsSuccessFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.notifyTorSaveSettingsSuccess",
                             TORLAUNCHER_NOTIFYTORSAVESETTINGSSUCCESS)
};
class TorlauncherNotifyTorSaveSettingsErrorFunction:
    public UIThreadExtensionFunction {
  ~TorlauncherNotifyTorSaveSettingsErrorFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.notifyTorSaveSettingsError",
                             TORLAUNCHER_NOTIFYTORSAVESETTINGSERROR)
};
class TorlauncherSetTorProxyFunction:
    public UIThreadExtensionFunction {
  ~TorlauncherSetTorProxyFunction() override {}
  ResponseAction Run() override;
  DECLARE_EXTENSION_FUNCTION("torlauncher.setTorProxy",
                             TORLAUNCHER_SETTORPROXY)
};

} // namespace extensions

#endif // CHROME_BROWSER_EXTENSIONS_API_TORLAUNCHER_TORLAUNCHER_API_H_
