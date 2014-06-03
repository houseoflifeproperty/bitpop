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

Chat.Views.SidebarLogin = Ember.View.extend({
  controller: Chat.Controllers.sidebarLoginController,
  template: Em.Handlebars.compile(
      '<div id="login-centered">'
    +   '<img src="images/facebook_login_bitpop.png" alt="Facebook chat login" />'
    +   '<p class="promo">Chat with your friends<br>while surfing</p>'
    +   '{{#unless connectionInProgress}}'
    +     '<button id="login-button" class="btn" {{action "login"}}>Login</button>'
    +   '{{/unless}}'
    +   '{{#if showErrorBox}}'
    +     '<p class="error">{{errorStatus}}</p>'
    +   '{{/if}}'
    +   '{{#if showSyncControl}}'
    +     '<p id="sync-para">'
    +       '<label {{bindAttr for="view.enableSyncCheck.elementId"}}>'
    +         '{{input type="checkbox" viewName="enableSyncCheck" checkedBinding="enableSync" disabledBinding="syncControlUIDisabled"}}'
    +         'Synchronize browser data using your Facebook account'
    +       '</label>'
    +     '</p>'
    +   '{{/if}}'
    +   '{{#if connectionInProgress}}'
    +     '<div id="spinner-content">'
    +       '<p>{{spinnerStatus}}</p>'
    +       '<div id="spinner"></div>'  
    +     '</div>'
    +   '{{/if}}'
    + '</div>'
  ),

  
  didInsertElement: function () {
    $(window).load(function () {
      chrome.extension.sendMessage({
        'kind': 'rosterViewLoaded'
      });
    });
  }

});