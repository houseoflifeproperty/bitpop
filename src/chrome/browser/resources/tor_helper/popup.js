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
  const kStatusUnknown = 0; // Tor process status.
  const kStatusStarting = 1;
  const kStatusRunning = 2;
  const kStatusExited = 3;  // Exited or failed to start.

  var menuLaunch = document.getElementById('launch_tor_browser');
  var menuAbout = document.getElementById('about_protected_mode');
  var menuNetworkSettings = document.getElementById('network_settings');
  var menuChangeTorCircuit = document.getElementById('change_tor_circuit');
  var changeCircuitBox = document.getElementById('change_circuit_message');
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
      chrome.torlauncher.launchTorBrowser({ open_tor_settings: true });
      //chrome.windows.create({ url: "chrome://tor-settings/", focused: true, incognito: false });
      return false;
    }, false);


  if (menuChangeTorCircuit)
    menuChangeTorCircuit.addEventListener('click', function (e) {
      chrome.runtime.sendMessage(
        { kind: chrome.extension.getBackgroundPage().kUpdateTorCircuits });
      changeCircuitBox.className = "box";
      setTimeout(function () {
        changeCircuitBox.className = "box hidden";
      }, 2000);
    }, false);

  var s = document.getElementsByClassName('country-link');
  if (s && s.length > 0) {
    for (var i = 0; i < s.length; ++i) {
      var obj = {
        id: s[i].id,
        onClick: function (e) {
          chrome.runtime.sendMessage(kTorLauncherAppId, {
            "kind": "changeExitNodeCountry",
            "ccode": this.id
          });
          return false;
        }
      }
      s[i].addEventListener('click', obj.onClick.bind(obj));
    }
  }

  // chrome.runtime.sendMessage(
  //   kTorLauncherAppId, { "kind": "getTorStatus" }, null,
  //   function (status) {
  //     if (status == kStatusRunning) {
  //       document.getElementById('not_protected_message').hidden = true;
  //       document.getElementById('tor_circuit').hidden = false;
  //     }
  //   }
  // );
};
