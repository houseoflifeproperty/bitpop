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

Chat.Controllers.Application = Ember.Object.extend({
  debug: false,
  active_window_friend_id: null,
  active_window_tab_id: null,
  last_update_time_by_facebook_uid: {},
  chatAvailable: false,
  chatBlocked: true,
  chatIsIdle: false,
  self_uid: '1',
  retries: 0,

  init: function() {
    chrome.extension.onMessage.addListener(_.bind(this.processExtensionMessage, this));
    chrome.extension.onMessageExternal.addListener(_.bind(this.processExtensionMessageExternal, this));
  },

  processExtensionMessage: function(request, sender, sendResponse) {
    if (request.kind == '_onRoster') {
      this._onRoster(JSON.parse(request.friends));
    } else if (request.kind == '_onRosterChange') {
      this._onRosterChange(JSON.parse(request.friends));
    } else if (request.kind == 'setUserPresence') {
      this.setUserPresence(JSON.parse(request.presence), request.user_name);
    } else if (request.kind == 'windowReady') {
      var jid = Strophe.getBareJidFromJid(request.jid);
      if (jid == Strophe.getBareJidFromJid(this.user.get('jid')))
        this._onWindowReady(request.friend_jid, sender.tab.id);
    } else if (request.kind == 'updateTimesReady') {
      this.onUpdateTimesReady(request.data);
    } else if (request.kind == 'connectionInProgress') {
      this.setConnectionInProgress(request.desc);
    } else if (request.kind == 'connectionFailedWhileGettingFbPermissions') {
      this.onPermsConnFail();
    } else if (request.kind == 'stropheAuthFailed') {
      this.onStropheAuthFailed();
    } else if (request.kind == 'stropheConnectionFailed') {
      this.onStropheConnFailed();
    } else if (request.kind == 'stropheDisconnected') {
      this.onStropheDisconnected();
    } else if (request.kind == 'myUidAvailable') {
      this.onMyUidAvailable(request.uid);
    } else if (request.kind == '_onMessage') {
      this._onMessage(JSON.parse(request.message));
    } else if (request.kind == 'connectionNotAuthorized') {
      this.onNotAuthorized();
    } else if (request.kind == 'chatIsIdle') {
      this.onChatWentIdle();
    }
  },

  processExtensionMessageExternal: function (request, sender, sendResponse) {
    if (request.type == 'newInboxMessage') {
      var message = {
        id: "service",
        body: request.body,
        from: '-' + request.from + '@chat.facebook.com',
        createdAt: new Date(request.timestamp * 1000)
      };
      this._onMessage(message);
      return false;
    }
  },

  setUserPresence: function (presence, user_name) {
    if (!this.user) {
      this.user = Chat.Models.User.create({ jid: presence.from, name: user_name });
    } else {
      this.user.set('jid', presence.from);
      this.user.set('name', user_name);
    }
    this.set('self_uid', this.user.get('uid'));
    this.user.setPresence(presence);
  },

  _onRoster: function (friends) {
    var objects = _.map(friends, function (friend) {
      return Chat.Models.User.create(friend);
    });

    Chat.Controllers.roster.fillUsers(objects);
    this.mergeLastUpdateTimes();
    Chat.Controllers.localStorage.saveRoster(
      this.user.get('jid'),
      Chat.Controllers.roster.getAsJsonable()
    );
    this.set('retries', 0);
    this.set('chatBlocked', false);
    this.set('chatIsIdle', false);
    setTimeout(
      _.bind(function () {
        $.unblockUI({ fadeOut: 200 }); 
        this.set('chatAvailable', true); 

        _.bind(function () {
          if (this.get('chatAvailable')) 
            chrome.extension.sendMessage({
              kind: 'fqlQuery',
              query: 'SELECT uid, online_presence FROM user WHERE uid IN (SELECT uid2 FROM friend WHERE uid1=me())'
            }, function (data) {
              for (var i = 0; i < data.length; ++i) {
                var model = Chat.Controllers.roster.findUserByProperty('uid', data[i].uid.toString());
                if (model) {
                  model.setPresence(data[i].online_presence);
                }
              }
            });
          setTimeout(_.bind(arguments.callee, this), 30000);
        }, this)();
      }, this),
      0);
  },

  _onRosterChange: function (friends) {
    friends.forEach(function (friend) {
      var roster = Chat.Controllers.roster,
      model = roster.findUserByProperty('jid', friend.jid);

      if (friend.subscription === 'remove') {
        // Remove user from the roster
        // TODO: remove chat tab if present
        roster.removeUser(friend);

      } else {
        if (model) {
          // Update user in the roster
          // TODO: figure out Ember.Object#set for multiple properties
          model.beginPropertyChanges();
          Ember.keys(friend).forEach(function (key) {
            model.set(key, friend[key]);
          });
          model.endPropertyChanges();
        } else {
          // Add user to the roster
          model = Chat.Models.User.create(friend);
          roster.addUser(model);
        }
      }
    });
    Chat.Controller.localStorage.saveRoster(
      this.user.get('jid'),
      Chat.Controllers.roster.getAsJsonable()
    );
  },

  _onWindowReady: function (friend_jid, tab_id) {
    this.set('active_window_tab_id', tab_id);
    this.set('active_window_friend_jid', friend_jid);

    var roster = Chat.Controllers.roster,
    model = roster.findUserByProperty('jid', friend_jid);

    if (model)
      chrome.extension.sendMessage({
        'kind': 'initNames',
        'user_name': this.get('user.name'),
        'friend_name': model.get('name')
      });
  },

  mergeLastUpdateTimes: function () {
    Chat.Controllers.roster.forEach(_.bind(function (item, index, enumerable) {
      var sec = this.get('last_update_time_by_facebook_uid')[item.get('uid')] || 0;
      item.set('last_active_time', new Date(sec*1000));
    }, this));
  },

  onUpdateTimesReady: function (data) {
    this.set('last_update_time_by_facebook_uid', data);
    if (Chat.Controllers.roster.get('content').length)
      this.mergeLastUpdateTimes();
  },

  setConnectionInProgress: function (desc) {
    Chat.Controllers.sidebarLoginController.setInProgress(desc);
  },

  displayConnectionInterruptedMessage: function (loginScreenMessagePrefix) {
    // TODO: have it done by view method
    if (this.get('chatAvailable')) {
      if (this.get('retries') > 2) {
        Ember.run.scheduleOnce('afterRender', this, function () { $.unblockUI({ fadeOut: 200 }); });
        Chat.Controllers.sidebarLoginController.setError(
          loginScreenMessagePrefix
          + ' Please check your Internet connection and try to login again.'
        );
        this.set('chatAvailable', false);
        return;
      }
      var numSeconds = 5 * (this.get('retries') + 1);
      $.blockUI({
        message: '<span id="block-message">'
        +   'Connection to Facebook Chat interrupted. '
        +   '<span id="retrying-msg">'
        +     'Retrying in '
        +     '<span id="retry-in">' + numSeconds + '</span>'
        +     ' seconds...'
        +   '</span>'
        + '</span>',
        css: { left: '5px', right: '5px', width: '163px', padding: '5px 3px' }
      });

      var myInterval = setInterval(
        _.bind(function () {
          numSeconds--;
          $('#retry-in').text(numSeconds);
          if (numSeconds === 0) {
            clearInterval(myInterval);
            $('#retrying-msg').html('<br>Now connecting...');
            this.incrementProperty('retries');
            chrome.extension.sendMessage({
              'kind': 'retryApiConnection'
            });
          }
        }, this),
        1000);
    } else
      Chat.Controllers.sidebarLoginController.setError(
        loginScreenMessagePrefix
        + ' Please check your Internet connection and try to login again.'
      );
  },

  onPermsConnFail: function () {
    this.displayConnectionInterruptedMessage('Connection failed.');
  },

  onStropheAuthFailed: function () {
    Chat.Controllers.sidebarLoginController.setError(
      'Authentication for facebook chat failed.'
      + ' Please, try to login again.'
    );
    this.set('chatAvailable', false);
  },

  onStropheConnFailed: function () {
    Chat.Controllers.sidebarLoginController.setError(
      'Connection to facebook chat server failed.'
      + ' This may be the issue with facebook servers.'
      + ' Try to relogin later or in a few moments.'
    );
    this.set('chatAvailable', false);
  },

  onNotAuthorized: function () {
    Chat.Controllers.sidebarLoginController.setError(
      'Connection interrupted. Your authorization is required.'
      + ' This may be due to disabling or revoking permissions from the BitPop Facebook application.'
      + ' Also this can be due to the expiration of your session. Try to login again.'
    );
    this.set('chatAvailable', false);
  },

  onStropheDisconnected: function () {
    this.displayConnectionInterruptedMessage('Facebook chat disconnected without your intent.');
  },

  onChatAvailabilityChanges: function () {
    if (this.get('chatAvailable')) {
      chrome.extension.sendMessage({
        kind: 'graphApiRequest',
        path: '/me/statuses',
        params: { 'limit': '1' }
      }, _.bind(function (response) {
        if (response.error) {
          Chat.Controllers.sidebarMainUI.set('statusTitle', 'ERROR: Status fetch error.');
        } else if (response.data && response.data.length && response.data[0].message) {
          Chat.Controllers.sidebarMainUI.set('statusTitle', response.data[0].message);
        }
      }, this));
      Chat.Controllers.sidebarLoginController.onSlideToFriendsView();
    }
  }.observes('chatAvailable'),

  reconnect: function () {
    chrome.extension.sendMessage({
      'kind': 'reconnect'
    });
  },

  disconnect: function () {
    chrome.extension.sendMessage({
      'kind': 'disconnect'
    });
    this.set('chatBlocked', true);
  },

  onChatBlockChanged: function () {
    if (this.get('chatBlocked') || this.get('chatIsIdle')) {
      $('.box-wrap').block({ 
        message:
              this.get('chatIsIdle') ? (
                'Chat is idle.'
              + ' Move your mouse or press a keyboard button and wait for the chat to reconnect.'
              ) : (
                'Chat is unavailable at the moment.'
              + ' Change your status to "available" or wait for the connection to be established.'
              ),
        css: { left: '5px', right: '5px', width: '163px', padding: '5px 3px' },
        overlayCSS: { opacity: '0.4' }
      });
    } else {
      $('.box-wrap').unblock();
    }
  }.observes('chatBlocked', 'chatIsIdle'),

  onMyUidAvailable: function (uid) {
    this.set('chatAvailable', true);

    // temporary fix for user's jid, will be retrieved later, when chat is connected
    if (!this.user) {
      this.user = Chat.Models.User.create({ jid: uid + '@some.server', name: 'some-random-name' });
    }

    // localStorage controller parses out the facebook uid
    var roster = Chat.Controllers.localStorage.getSavedRoster(uid + '@some.server');
    var objects = _.map(roster, function (friend) {
      return Chat.Models.User.create(friend);
    });

    Chat.Controllers.roster.fillUsers(objects);
  },

  _onMessage: function (message) {
    var uid = Strophe.getNodeFromJid(message.from).substr(1);
    var user = Chat.Controllers.roster.findProperty('uid', uid);
    if (user && message.body) {
      // Do not post incoming message event if there's a view with that chat opened
      var views = chrome.extension.getViews();
      for (var i = 0; i < views.length; ++i) {
        if (views[i].location.hash.length && views[i].location.hash.indexOf(user.get('jid')) !== -1)
          return;
      }
      chrome.bitpop.facebookChat.newIncomingMessage(
                               message.id,
                               Strophe.getBareJidFromJid(user.get('jid')),
                               user.get('name'),
                               user.get('status'),
                               message.body);
    }
  },

  onChatWentIdle: function () {
    this.set('chatIsIdle', true);
  }
});

Chat.Controllers.application = Chat.Controllers.Application.create();