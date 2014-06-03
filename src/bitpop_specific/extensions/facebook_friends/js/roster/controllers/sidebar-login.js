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

Chat.Controllers.SidebarLoginController = Ember.Controller.extend({
  spinnerStatus: 'Establishing Facebook Chat connection...',
  errorStatus: '',
  showErrorBox: false,
  showSyncControl: false,
  enableSync: true,
  connectionInProgress: false,
  loginClicked: false,

  actions: {
    login: function () {
        this.set('loginClicked', true);
        chrome.extension.sendMessage({ kind: "facebookLogin" });
        this.set('showErrorBox', false);
        _gaq.push(['_trackEvent', 'login_attempt', 'sync-' + (this.get('enableSync') ? 'on' : 'off')]);
    }
  },
  
  init: function () {
    // BITPOP
    chrome.bitpop.getSyncStatus(_.bind(this.toggleSyncMessage, this));
    chrome.bitpop.onSyncStatusChanged.addListener(_.bind(this.toggleSyncMessage, this));
    return this._super();
  },

  resetUI: function () {
    this.set('showErrorBox', false);
    this.set('connectionInProgress', false);
  },

  setError: function (status) {
    this.set('errorStatus', status);
    this.set('showErrorBox', true);
    this.set('connectionInProgress', false);
    this.set('loginClicked', false);
  },

  setInProgress: function (progressStatus) {
    this.set('showErrorBox', false);
    this.set('connectionInProgress', true);
    this.set('spinnerStatus', progressStatus);
  },

  toggleSyncMessage: function (params) {
    if (params && params === true) {
      this.set('showSyncControl', false);
      this.set('enableSync', false);
      $('#enable-sync').attr('disabled', true);
    } else {
      this.set('showSyncControl', true);
      this.set('enableSync', true);
      $('#enable-sync').attr('disabled', false);
    }
  },

  syncControlUIDisabled: function () {
    return !this.get('showSyncControl');
  }.property('showSyncControl'),

  onSlideToFriendsView: function () {
    if (this.get('enableSync') && this.get('loginClicked')) {
      this.toggleSyncMessage(true);
      chrome.bitpop.launchFacebookSync();
      this.set('loginClicked', false);
    }
  }
});

Chat.Controllers.sidebarLoginController = Chat.Controllers.SidebarLoginController.create();