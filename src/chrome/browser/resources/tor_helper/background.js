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


const kSOCKS5ProxyHost = "localhost";
// TODO: change the port number when release is right here
const kSOCKS5ProxyPort = 9150;
const kDefaultProxyUsername = "--Unknown--";
const kUpdateTorCircuits = "tor_helper.update-tor-circuits";

var tor_helper = {};

tor_helper.nonce = 0;

tor_helper.resetProxyServer = function () {
  chrome.torlauncher.proxy.set({ value: {
                                   mode: "fixed_servers",
                                   server: "socks5://" + kDefaultProxyUsername +
                                     ":" + tor_helper.nonce.toString() + "@" +
                                     "127.0.0.1:9150"
                                 },
                                 scope: "incognito_persistent"},
                                 function () {});
  // chrome.torlauncher.setTorProxy(kDefaultProxyUsername,
  //                                tor_helper.nonce.toString());
};

(function () {

  const kTorlauncherAppStartUp = "torlauncher-startup";
  const kOpenInitialTorSessionWindowMessage = 'open-initial-tor-session-window';

  const kInitialUrl = 'https://check.torproject.org/?lang=en_US';

  chrome.runtime.onMessageExternal.addListener(
      function (message, sender, sendResponse) {
    switch (message.kind) {
      case kTorlauncherAppStartUp: {
        tor_helper.resetProxyServer();
      }
      break;

      case kOpenInitialTorSessionWindowMessage:
        // chrome.windows.create({       url: kInitialUrl,
        //                           focused: true,
        //                         incognito: true },
        //                       function (window) { /*sendResponse({ success: true });*/ });
        break;
      default:
        console.warn('Invalid message format: ' + JSON.stringify(message));
        /*sendResponse({ success: false });*/
    }
  });

  chrome.runtime.onMessage.addListener(function (message, sender, sendResponse) {
    switch (message.kind) {
      case kUpdateTorCircuits:
        tor_helper.nonce++;
        tor_helper.resetProxyServer();
        break;
      default:
        console.warn('Invalid message format: ' + JSON.stringify(message));
        break;
    }
  });

})();
