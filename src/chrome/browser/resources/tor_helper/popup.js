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

window.onload = function () {
  var menuLaunch = document.getElementById('launch_tor_browser');
  var menuAbout = document.getElementById('about_protected_mode');
  var menuNetworkSettings = document.getElementById('network_settings');

  // const kLaunchTorMenuState_Disabled = 0;
  // const kLaunchTorMenuState_LaunchTor = 1;
  // const kLaunchTorMenuState_OpenNewWindow = 2;

  // gLaunchTorMenuState = kLaunchTorMenuState_Disabled;
  const kTorLauncherAppId = "gedbhlplmladiedjcndlndakofpdibcb";

  if (menuLaunch)
    menuLaunch.addEventListener('click', function (e) {
      chrome.torlauncher.launchTorBrowser({});
      return false;
    }, false);

  if (menuAbout)
    menuAbout.addEventListener('click', function (e) {
      chrome.runtime.sendMessage(kTorLauncherAppId, { kind: "TorOpenAboutProtectedModeDialog" });
      return false;
    }, false);

  if (menuNetworkSettings)
    menuNetworkSettings.addEventListener('click', function (e) {
      //chrome.runtime.sendMessage(kTorLauncherAppId, { kind: "TorOpenNetworkSettingsDialog" });
      chrome.torlauncher.launchTorBrowser({ open_tor_settings: true })
      return false;
    }, false);
};
