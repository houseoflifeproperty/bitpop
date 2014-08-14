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

Chat.Controllers.SidebarMainUI = Ember.Controller.extend({
  statusTitle: 'Set your status here.',
  
  actions: {
    logoutClicked: function () {
      chrome.extension.sendMessage({ kind: "logoutFacebook" });
      Chat.Controllers.application.set('chatAvailable', false);
      Chat.Controllers.sidebarLoginController.resetUI();
    }
  }
});

Chat.Controllers.sidebarMainUI = Chat.Controllers.SidebarMainUI.create();