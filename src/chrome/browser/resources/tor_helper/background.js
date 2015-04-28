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

(function () {

  const kOpenInitialTorSessionWindowMessage = 'open-initial-tor-session-window';
  const kInitialUrl = 'https://check.torproject.org/?lang=en_US';

  chrome.runtime.onMessageExternal.addListener(function (message, sender, sendResponse) {
    switch (message.kind) {
      case kOpenInitialTorSessionWindowMessage:
        chrome.windows.create({       url: kInitialUrl,
                                  focused: true,
                                incognito: true },
                              function (window) { /*sendResponse({ success: true });*/ });
        break;
      default:
        console.warn('Invalid message format: ' + JSON.stringify(message));
        /*sendResponse({ success: false });*/
    }
  });

})();
