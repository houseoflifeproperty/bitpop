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

class TorlauncherStartTorFunction : public UIThreadExtensionFunction {
  virtual ~TorlauncherStartTorFunction() {}
  virtual ResponseAction Run() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION("torlauncher.startTor", TORLAUNCHER_STARTTOR)
};
class TorlauncherInitiateAppQuitFunction : public UIThreadExtensionFunction {
  virtual ~TorlauncherInitiateAppQuitFunction() {}
  virtual ResponseAction Run() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION("torlauncher.initiateAppQuit",
                             TORLAUNCHER_INITIATEAPPQUIT)
};
class TorlauncherGetTorProcessStatusFunction : public UIThreadExtensionFunction {
  virtual ~TorlauncherGetTorProcessStatusFunction() {}
  virtual ResponseAction Run() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION("torlauncher.getTorProcessStatus",
                             TORLAUNCHER_GETTORPROCESSSTATUS)
};
class TorlauncherSetTorStatusRunningFunction : public UIThreadExtensionFunction {
  virtual ~TorlauncherSetTorStatusRunningFunction() {}
  virtual ResponseAction Run() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION("torlauncher.setTorStatusRunning",
                             TORLAUNCHER_SETTORSTATUSRUNNING)
};
class TorlauncherGetTorServiceSettingsFunction : public UIThreadExtensionFunction {
  virtual ~TorlauncherGetTorServiceSettingsFunction() {}
  virtual ResponseAction Run() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION("torlauncher.getTorServiceSettings",
                             TORLAUNCHER_GETTORSERVICESETTINGS)
};
class TorlauncherEnvExistsFunction : public UIThreadExtensionFunction {
  virtual ~TorlauncherEnvExistsFunction() {}
  virtual ResponseAction Run() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION("torlauncher.envExists",
                             TORLAUNCHER_ENVEXISTS)
};
class TorlauncherEnvGetFunction : public UIThreadExtensionFunction {
  virtual ~TorlauncherEnvGetFunction() {}
  virtual ResponseAction Run() OVERRIDE;
  DECLARE_EXTENSION_FUNCTION("torlauncher.envGet",
                             TORLAUNCHER_ENVGET)
};
} // namespace extensions

#endif // CHROME_BROWSER_EXTENSIONS_API_TORLAUNCHER_TORLAUNCHER_API_H_
