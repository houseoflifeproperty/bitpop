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
  timesRosterLoaded: 0,
  newMessageAudio: new Audio("mouth_pop.wav"),

  MACHINE_IDLE_INTERVAL: 60 * 10, // seconds

  init: function() {
    _gaq.push(['_trackPageview']);

    this.query_idle_timer = null;
    //this.manual_disconnect = false;
    this.prevIdleState = "active";

    // Setup browser action
    (function () {
      if (chrome.browserAction)
        chrome.browserAction.onClicked.addListener(function (tab) {
          chrome.bitpopFacebookChat.getFriendsSidebarVisible(function(is_visible) {
            chrome.bitpopFacebookChat.setFriendsSidebarVisible(!is_visible);
          });
        });
      else
        setTimeout(arguments.callee, 1000);
    })();

    this.facebookPrefsInit();

    chrome.extension.onMessage.addListener(
      _.bind(this.processExtensionMessage, this)
    );

    chrome.extension.onMessageExternal.addListener(_.bind(function (request, sender, sendResponse) {
      if (request.type == 'getMyUid') {
        sendResponse(this.fb_helper.myUid ? { id: this.fb_helper.myUid } : { error: "not connected" });
      } else if (request.type == 'fqlQuery') {
        this.fb_helper.fqlRequest(request.query, sendResponse, sendResponse);
        return true;
      } else if (request.type == 'restApiCall') {
        this.fb_helper.restApiCall(request.method, request.params, sendResponse, sendResponse);
        return true;
      }
    }, this));

    $.subscribe('accessTokenAvailable.client.fb', _.bind(this._accessTokenAvailable, this));
    $.subscribe('permissionsConnectionFailed.client.fb', _.bind(this._permsConnFail, this));
    $.subscribe('permissionsRequestNotAuthorized.client.fb', _.bind(this._permsNotAuthorized, this));
    $.subscribe('checkingPermissions.client.fb',
      _.bind(function () {
        chrome.extension.sendMessage({
          'kind': 'connectionInProgress',
          'desc': 'Checking Facebook permissions...'
        });
      }, this));
    $.subscribe('retrievingUid.client.fb',
      _.bind(function () {
        chrome.extension.sendMessage({
          'kind': 'connectionInProgress',
          'desc': 'Fetching current user Facebook uid...'
        });
      }, this));

    // Bindings for XMPP client events
    $.subscribe('authfail.client.im', _.bind(this._onAuthFail, this));
    $.subscribe('connfail.client.im', _.bind(this._onConnFail, this));
    $.subscribe('connected.client.im', _.bind(this._onConnected, this));
    $.subscribe('disconnecting.client.im', _.bind(this._onDisconnecting, this));
    $.subscribe('disconnected.client.im', _.bind(this._onDisconnected, this));
    $.subscribe('roster.client.im', _.bind(this._onRoster, this));
    $.subscribe('rosterChange.client.im', _.bind(this._onRosterChange, this));
    $.subscribe('presence.client.im', _.bind(this._onPresenceChange, this));
    $.subscribe('message.client.im', _.bind(this._onMessage, this));
    $.subscribe('typing.client.im', _.bind(this._onTyping, this));
    $.subscribe('clientJidAndNameDetermined.client.im', _.bind(this.setUserPresence, this));

    $.subscribe('connected.client.im',
      _.bind(function () {
        chrome.extension.sendMessage({
          'kind': 'connectionInProgress',
          'desc': 'Successfully connected to Facebook Chat. Fetching friend list...'
        });
      }, this));

    this.fb_helper = new FB.Client();
  },

  processExtensionMessage: function(request, sender, sendResponse) {
    if (request.kind == 'reconnect') {
        this.connectXMPPAndSendNotificationToRoster();
    } else if (request.kind == 'disconnect') {
        this.disconnect();
    } else if (request.kind == 'newOutgoingMessage') {
      this.sendMessage({
        'to': request.to,
        'body': request.body
      });
    } else if (request.kind == 'newTypingNotification') {
      this.client.sendTypingNotification(request.to, request.value);
    } else if (request.kind == 'facebookLogin') {
      this.login();
    } else if (request.kind == 'setFacebookStatus') {
      if (this.fb_helper) {
        this.fb_helper.setFacebookStatus(request, sendResponse);
        return true;
      }
    } else if (request.kind == 'logoutFacebook') {
      this.fb_helper && this.fb_helper.logout();
      this.client && this.client.connection && this.client.connection.connected && 
        this.disconnect();
      // Send to Messages extension
      chrome.extension.sendMessage('dhcejgafhmkdfanoalflifpjimaaijda',
        { type: 'loggedOut' } );
    } else if (request.kind == 'rosterViewLoaded') {
      // handle gracefully the roster page reload on various reasons
      this.incrementProperty('timesRosterLoaded');
      if (this.get('timesRosterLoaded') > 1 && 
          this.client && this.client.connection && this.client.connection.connected) {
        this.connectXMPPAndSendNotificationToRoster();
      }
    } else if (request.kind == 'retryApiConnection') {
      this.fb_helper.checkForPermissions({ hadAccessToken: true });
    } else if (request.kind == 'retryChatConnection') {
      this.connectXMPPAndSendNotificationToRoster();
    } else if (request.kind == 'fqlQuery') {
      this.fb_helper.fqlRequest(request.query, sendResponse, sendResponse);
      return true;
    } else if (request.kind == 'graphApiRequest') {
      this.fb_helper.graphApiRequest(request.path, request.params, sendResponse, sendResponse);
      return true;
    }
  },

  login: function () {
    this.gotToken = false;
    this.fb_helper.login(FB.PERMISSIONS);
  },

  _accessTokenAvailable: function () {
    this.gotToken = true;
    $.subscribe('myUidAvailable.client.fb', _.bind(this._myUidAvailable, this));
    this.fb_helper.getMyUid();
  },

  _myUidAvailable: function () {
    if (this.gotToken) {
      $.unsubscribe('myUidAvailable.client.fb');
      chrome.extension.sendMessage({
        'kind': 'myUidAvailable',
        'uid': this.fb_helper.myUid
      });
      chrome.extension.sendMessage('dhcejgafhmkdfanoalflifpjimaaijda',
        { 'type': 'myUidAvailable', 'myUid': this.fb_helper.myUid });
      chrome.extension.sendMessage('omkphklbdjafhafacohmepaahbofnkcp',
        { 'type': 'myUidAvailable', 'myUid': this.fb_helper.myUid });

      this.connectXMPPAndSendNotificationToRoster();
    }
  },

  connectXMPPAndSendNotificationToRoster: function () {
    this.fb_helper.fqlRequest(
      'SELECT recipients, updated_time FROM thread WHERE folder_id=0',
      _.bind(function (data) {
        var transformedData = {};
        for (var i = 0; i < data.length; i++) {
          var thread = data[i];
          if (thread.recipients.indexOf(+this.fb_helper.myUid) !== -1 &&
              thread.recipients.length == 2) {
            var myUidIndex = thread.recipients.indexOf(+this.fb_helper.myUid);
            transformedData[thread.recipients[1 - myUidIndex]] = thread.updated_time;
          }
        }

        chrome.extension.sendMessage({
          'kind': 'updateTimesReady',
          'data': transformedData
        });
      }, this)
    );

    chrome.extension.sendMessage({ kind: 'connectionInProgress', desc: 'Connecting to Facebook XMPP Chat...' });
    this.connectXMPP({ 
      jid: this.fb_helper.myUid + '@chat.facebook.com',
      access_token: this.fb_helper.accessToken,
      debug: true
    });
  },

  connectXMPP: function (options) {
    if (this.client && this.client.connection && this.client.connection.connected)
      this.client.disconnect();   // disconnect is async

    if (this.client)
      delete this.client;

    // TODO: raise an error if jid and password are not present
    options = options || {};

    this.debug = options.debug || this.debug;
    this.user = {
      jid: options.jid,
    };

    // Strophe.log = function (level, msg) {
    //   console.log("STROPHE:" + level + ': ' + msg);
    // };

    var BOSH_SERVER_URL = "http://tools.bitpop.com:5280/http-bind/";

    // XMPP client
    this.client = new IM.Client({
      host: BOSH_SERVER_URL,
      jid: options.jid,
      access_token: options.access_token,
      debug: this.debug
    });

    this.client.connect();
  },

  disconnect: function () {
    if (this.client && this.client.connection && this.client.connection.connected)
      this.client.disconnect();   // disconnect is async

    if (this.client)
      delete this.client;

    this.client = null;
  },

  setUserPresence: function (event, jid, name) {
    this.user.jid = Strophe.getBareJidFromJid(jid);
    this.user.name = name;
    chrome.extension.sendMessage({
      'kind': 'setUserPresence',
      'user_name': name,
      'presence': JSON.stringify({
        'from': jid,
        'type': 'available',
        'show': 'online',
        'status': 'online'
      })
    });
    chrome.extension.sendMessage('dhcejgafhmkdfanoalflifpjimaaijda',
      { type: 'chatIsAvailable'}
    );
    chrome.bitpopFacebookChat.setGlobalMyUidForProfile(jid);
  },

  _onRoster: function (event, friends) {
    chrome.extension.sendMessage({
      "kind": "_onRoster",
      "friends": JSON.stringify(friends)
    });
  },

  _onRosterChange: function (event, friends) {
    chrome.extension.sendMessage({
      "kind": "_onRosterChange",
      "friends": JSON.stringify(friends)
    });
  },

  _onPresenceChange: function (event, presence) {
    var fullJid = presence.from,
    bareJid = Strophe.getBareJidFromJid(fullJid);

    switch (presence.type) {
      case 'error':
      // do something
      break;
      case 'subscribe':
      // authorization request
      break;
      case 'unsubscribe':
      // deauthorization request
      break;
      case 'subscribed':
      // authorization confirmed
      break;
      case 'unsubscribed':
      // deauthorization confirmed
      break;
      default:
      // // Update user's or friend's presence status
      // if (this.user.jid !== bareJid) {
      //   chrome.extension.sendMessage({
      //     "kind": "_setFriendPresence",
      //     "presence": JSON.stringify(presence)
      //   });
      // }
    }
  },

  _onMessage: function (event, message) {
    if (message.body)
      this.get('newMessageAudio').play();

    chrome.extension.sendMessage({
      "kind": "_onMessage",
      "message": JSON.stringify(message)
    });

    chrome.extension.sendMessage('dhcejgafhmkdfanoalflifpjimaaijda',
        { 
          type: 'newMessage',
          from: Strophe.getNodeFromJid(message.from).substr(1),
          timestamp: (new Date()).getTime()
        } );
  },

  sendMessage: function (message) {
    this.client.message(message.to, message.body);
  },

  _onTyping: function (event, desc) {
    // Send typing event to browser
    // desc.is_typing
    // desc.from_jid

    var jid = Strophe.getBareJidFromJid(desc.from_jid);
    if (desc.is_typing) {
      chrome.bitpopFacebookChat.newIncomingMessage("service", jid, "", 'composing', "");
    } else {
      chrome.bitpopFacebookChat.newIncomingMessage("service", jid, "", 'online', "");
    }
  },

  _onAuthFail: function (event) {
    console.log('Authentication failed for given credentials.');
    chrome.extension.sendMessage({
      "kind": "stropheAuthFailed"
    });
  },

  _onConnFail: function (event) {
    console.log('Connection attempt failed.');
    chrome.extension.sendMessage({
      "kind": "stropheConnectionFailed"
    });
  },

  _onDisconnected: function (event, client) {
    if (client === this.client) {
      console.log('Disconnected XMPP chat without user intention.');
      chrome.extension.sendMessage({
        "kind": "stropheDisconnected"
      });
    }
  },

  _permsConnFail: function (event) {
    chrome.extension.sendMessage({
      'kind': 'connectionFailedWhileGettingFbPermissions'
    })
  },

  _permsNotAuthorized: function (event) {
    this.client && this.client.connection && this.client.connection.connected && 
      this.disconnect();
    // Send to Messages extension
    chrome.extension.sendMessage('dhcejgafhmkdfanoalflifpjimaaijda',
      { type: 'loggedOut' } );
    chrome.extension.sendMessage({
      'kind': 'connectionNotAuthorized'
    });
  },

  facebookPrefsInit: function () {
    var loggedIn = _.bind(function () { return this.fb_helper.myUid; }, this);
    // ********************************************************
    // facebook chat enable/disable functionality
    //
    // ********************************************************
    //
    // the list of tab ids which this extension is interested in.
    // Mostly facebook.com tabs
    var fbTabs = {};

    var TRACE = 0;
    var DEBUG = 1;
    var INFO  = 2;
    var logLevel = DEBUG;

    function myLog( ) {
        if(logLevel <= DEBUG) {
            console.log(arguments);
        }
    }

    chrome.tabs.onRemoved.addListener(
        function(tab)
        {
            delete fbTabs[tab];
        }
    );

    function sendResponseToContentScript(sender, data, status, response)
    {
        if (chrome.extension.lastError) {
            status = "error";
            response = chrome.extension.lastError;
        }
        myLog("Sending response ", data.action, data.id, status, response, response.stack);
        sender({
            action: data.action,
            id: data.id,
            status: status,
            response: response
        });
    }

    /**
     * extract the doman name from a URL
     */
    function getDomain(url) {
       return url.match(/:\/\/(.[^/]+)/)[1];
    }

    var ports = [];
    function addFbFunctionality( )
    {
        // add a listener to events coming from contentscript
        chrome.extension.onConnect.addListener(function(port) {
          ports.push(port);
          var port_ = port;
          port.onDisconnect.addListener(function() {
            console.assert(port_.name == 'my-port');
            if (port.name != 'my-port')
              return;
            var i = ports.indexOf(port_);
            if (i !== -1) {
              if (i === 0) {
                ports.shift();
              } else if (i === ports.length-1) {
                ports.pop();
              } else {
                ports = ports.slice(0, i).concat(ports.slice(i+1, ports.length));
              }
            }
          });

          console.assert(port.name == 'my-port');
          if (port.name != 'my-port')
            return;

          port.onMessage.addListener(
            function(request) {
                function sendResponse1(msg) {
                  port.postMessage(msg);
                }
                if (typeof request != 'string')
                  return false;
                myLog("Received request ", request);
                if(request) {
                    var data = JSON.parse(request);
                    try {
                        if(data.action === 'chat' && data.friendId !== undefined) {
                            // chat request event
                            //fbfeed.openChatWindow(data.friendId, function(a) {
                            //    sendResponseToContentScript(sendResponse, data, "ok", a);
                            //});
                        } else if(data.action === 'shouldEnableFbJewelsAndChat' &&
                            data.userId !== undefined) {
                            // save the id of the tabs which want the Jewel/Chat enable/disable
                            // so that they can be informed when quite mode changes
                            if(port.sender.tab.incognito) {
                                // if the broser is in incognito mode make a local decision
                                // no need to consult the native side.
                                var response =  {
                                        enableChat: true,
                                        enableJewels: true
                                    };
                                sendResponseToContentScript(sendResponse1, data, "ok", response);
                            } else {
                                //chrome.bitpopFacebookChat.getFriendsSidebarVisible(function(is_visible) {
                                chrome.bitpop.prefs.facebookShowChat.get({}, function(details) {
                                  var facebookShowChat = details.value;
                                  //chrome.bitpop.prefs.facebookShowJewels.get({}, function(details2) {
                                  //  var facebookShowJewels = details2.value;
                                  var response = null;
                                  if (loggedIn()) {
                                    response = {
                                      enableChat:   facebookShowChat,
                                      enableJewels: true
                                    };
                                  }
                                  else {
                                    response = { enableChat:true, enableJewels:true };
                                  }

                                  sendResponseToContentScript(sendResponse1, data,
                                                              "ok", response);
                                  //});
                                });
                                //});
                            }
                        }
                    } catch(e) {
                        sendResponseToContentScript(sendResponse1, data, "error", e);
                    }
                }
                return true;
              });
            });
    }

    function onSuppressChatChanged(details) {
      for(var i = 0; i < ports.length; i++) {
        ports[i].postMessage({});
      }
    }

    chrome.bitpop.prefs.facebookShowChat.onChange.addListener(onSuppressChatChanged);

    addFbFunctionality();
  },

  startChatAgain: function () {
    if (this.query_idle_timer === null)
      this.query_idle_timer = setInterval(_.bind(function() {
          chrome.idle.queryState(this.get('MACHINE_IDLE_INTERVAL'), _.bind(this.idleStateUpdate, this));
        }, this), 30 * 1000);  // every 30 seconds
    this.prevIdleState = 'active';
    this.client && this.client.connection && this.client.connection.reset();
    if (this.fb_helper.myUid && this.fb_helper.accessToken)
      this.connectXMPPAndSendNotificationToRoster();
  },

  enableIdleChatState: function (newState, shouldLaunchTimer) {
    clearInterval(this.query_idle_timer);
    this.query_idle_timer = null;
    if (this.client && this.client.connection && this.client.connection.connected) {
      if (shouldLaunchTimer)
        this.query_idle_timer = setInterval(_.bind(function() {
          chrome.idle.queryState(this.get('MACHINE_IDLE_INTERVAL'), _.bind(this.idleStateUpdate, this));
        }, this), 1 * 1000);  // every second

      this.prevIdleState = newState;
      this.disconnect();

      chrome.extension.sendMessage({
        'kind': 'chatIsIdle'
      });
      chrome.extension.sendMessage('dhcejgafhmkdfanoalflifpjimaaijda', 
        { type: 'chatIsIdle' });
     }
  },

  idleStateUpdate: function (newState) {
    if ((this.prevIdleState == "idle" || this.prevIdleState == "locked") &&
        newState == "active") {
      clearInterval(this.query_idle_timer);
      this.query_idle_timer = null;
      this.startChatAgain();
    } else if (this.prevIdleState == "active" &&
               (newState == "idle" || newState == "locked"))
      this.enableIdleChatState(newState, true);
  },

  _onConnected: function () {
    if (this.query_idle_timer === null)
      this.query_idle_timer = setInterval(_.bind(function() {
        chrome.idle.queryState(this.get('MACHINE_IDLE_INTERVAL'), _.bind(this.idleStateUpdate, this));
      }, this), 30 * 1000);  // every 30 seconds
  },

  _onDisconnecting: function () {
    if (!(this.prevIdleState == 'idle' || this.prevIdleState == 'locked')) {
      clearInterval(this.query_idle_timer);
      this.query_idle_timer = null;
    }
  }
});

Chat.Controllers.application = Chat.Controllers.Application.create();