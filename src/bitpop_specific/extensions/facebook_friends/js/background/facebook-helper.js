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

var FB = {
  APPLICATION_ID: "234959376616529",
  SUCCESS_URL: 'https://www.facebook.com/connect/login_success.html',
  LOGOUT_URL: 'https://www.facebook.com/logout.php',
  LOGOUT_NEXT_URL: 'https://sync.bitpop.com/sidebar/logout',
  GRAPH_API_URL: 'https://graph.facebook.com',
  FQL_API_URL: 'https://graph.facebook.com/fql',
  REST_API_URL: 'https://api.facebook.com/method/',
  TOKEN_EXCHANGE_URL: 'https://sync.bitpop.com/fb_exchange_token/',

  FRIEND_LIST_UPDATE_INTERVAL: 1000 * 60, // in milliseconds
  MACHINE_IDLE_INTERVAL: 60 * 10,  // in seconds

  PERMISSIONS: ['xmpp_login',
                'user_online_presence', 'friends_online_presence',
                'manage_notifications', 'read_mailbox', 'read_stream', 'user_status',
                'user_friends', 'publish_stream' ],

  // Facebook error codes
  FQL_ERROR: {
    API_EC_PARAM_ACCESS_TOKEN: 190
  },

  STATE: {
    DISCONNECTED: "disconnected",
    LOGIN_PENDING: "login_pending",
    PERMISSIONS_CHECK: "permissions_check",
    NEED_MORE_PERMISSIONS: "need_more_permissions",
    PERMISSIONS_CHECK_COMPLETE: "permissions_check_complete",
    GOT_ACCESS_TOKEN: "got_access_token",
    CONNECTED: "connected",
  } 
};

// Use accurately. Should be made Singleton
FB.Client = function (options) {

  // Should be made Singleton because of the following line
  FB.bindedTabUpdate = _.bind(this.onTabUpdated, this);

  $.subscribe("permissionCheckComplete", 
    _.bind(function(event, options) {
      if (options.newAccessToken) {
        //notifyObservingExtensions({ type: 'accessTokenAvailable',
        //                          accessToken: this.accessToken });
        this.getMyUid();
      } else if (options.hadAccessToken) {
        this.hadAccessTokenCallback();
      }
    }, this)
  );
  this.initializeAjax();
  if (!localStorage.accessToken) {
    this.accessToken = null;
    this.myUid = null;
    this.state = FB.STATE.DISCONNECTED;
  } else {
    this.accessToken = localStorage.accessToken;
    this.myUid = localStorage.myUid;
    this.checkForPermissions({ hadAccessToken: true });
  }
};

FB.Client.prototype.hadAccessTokenCallback = function () {
//  notifyObservingExtensions({ type: 'accessTokenAvailable',
//                       accessToken: localStorage.accessToken });

  $.publish('accessTokenAvailable.client.fb');
  if (this.myUid)
    this.onGotUid();
  else
    this.getMyUid();
}

FB.Client.prototype.initializeAjax = function () {
  this.offline_wait_timer = null;
  // Setup Ajax Error Handler
  $.ajaxSetup({
    error: _.bind(
      function (x, e) {
        var errorMsg = null;

        if (x.status === 0) {
          // Connection not available.
          errorMsg = 'You are offline. Please Check Your Network.';

          //this.notifyObservingExtensions({ type: 'wentOffline' });

          if (this.accessToken && this.offline_wait_timer === null) {
            this.offline_wait_timer = setTimeout(
              _.bind(function() {
                this.checkForPermissions({ hadAccessToken: true });
                this.offline_wait_timer = null;
              }, this),
              15000);
          }
        } else if (x.status === 400) {
          // Check for OAuth exception
          var response = JSON.parse(x.responseText);
          if (response.error && response.error.type == 'OAuthException' && !x.permission_request) {
              this.checkForPermissions({});

            errorMsg = response.error.message;
          } else {
            errorMsg = 'Not authorized.';
            console.log(x.responseText);
          }
        } else if (x.status === 404){
          errorMsg = 'Requested URL not found.' ;
        } else if (x.status === 500){
          errorMsg = 'Internal Server Error.';
        } else if (e === 'parsererror'){
          errorMsg = 'Parsing JSON Request failed.';
        } else if (e === 'timeout'){
          errorMsg = 'Request Time out.';
        } else {
          errorMsg = 'Unknown Error. Response was: "' + x.responseText + '"';
        }

        if (errorMsg) {
          x.callOnError && x.callOnError({ error: errorMsg });
          console.error(errorMsg);
        }
      }, this
    )
  });
};

FB.Client.prototype.login = function (permissions) {
  if (this.accessToken && this.state != FB.STATE.NEED_MORE_PERMISSIONS) {
    this.checkForPermissions({ hadAccessToken: true });
    return;
  }
  
  if (!chrome.tabs.onUpdated.hasListener(FB.bindedTabUpdate))
    chrome.tabs.onUpdated.addListener(FB.bindedTabUpdate);

  chrome.windows.onCreated.addListener(function (_window) {
    chrome.windows.onCreated.removeListener(arguments.callee);
    var winId = _window.id;
    chrome.windows.onRemoved.addListener(function (rmWindowId) {
      chrome.windows.onRemoved.removeListener(arguments.callee);
      if (rmWindowId == winId) {
        chrome.tabs.onUpdated.removeListener(FB.bindedTabUpdate);
      }
    });
  });

  var urlStart = "https://www.facebook.com/dialog/oauth?client_id=" +
      FB.APPLICATION_ID;
  var url = urlStart +
      "&response_type=token" +
      "&redirect_uri=" + FB.SUCCESS_URL +
      '&display=popup' +
      '&state=bitpop' +
      '&scope=' + permissions.join(',');
  var loginUrlStart = 'https://www.facebook.com/login.php?api_key=' +
      FB.APPLICATION_ID;

  // https://www.facebook.com/dialog/oauth?client_id=190635611002798&response_type=token&redirect_uri=https://www.facebook.com/connect/login_success.html&display=popup&scope=
  chrome.windows.getAll({ populate: true }, function (windows) {
    var found = false;
    for (var i = 0; i < windows.length; i++) {
      for (var j = 0; j < windows[i].tabs.length; j++) {
        if (windows[i].tabs[j].url.indexOf(urlStart) == 0 ||
            windows[i].tabs[j].url.indexOf(loginUrlStart) == 0) {
          chrome.tabs.update(windows[i].tabs[j].id, { selected: true, url: url });
          chrome.windows.update(windows[i].id, { focused: true });
          found = true;
          break;
        }
      }
      if (found)
        break;
    }
    if (!found) {
      var w = 620;
      var h = 400;
      var left = (screen.width/2)-(w/2);
      var top = (screen.height/2)-(h/2);

      window.open(url, "newwin", "height=" + h + ",width=" + w +
          ",left=" + left + ",top=" + top +
          ",toolbar=no,scrollbars=no,menubar=no,location=no,resizable=yes");
    }
  });
};

FB.Client.prototype.logout = function () {
  if (this.accessToken) {
    
    // Clear the access token in any case then continue
    var accessToken = this.accessToken;

    this.accessToken = null;
    this.state = FB.STATE.DISCONNECTED;
    localStorage.removeItem('accessToken');
    localStorage.removeItem('myUid');
    //notifyObservingExtensions({ type: 'loggedOut' });
    chrome.bitpopFacebookChat.loggedOutFacebookSession();

    var url = FB.LOGOUT_URL + '?next=' +
      FB.LOGOUT_NEXT_URL +
      '&access_token=' + accessToken +
      '&app_id=' + FB.APPLICATION_ID;
    // Logout by finding the focused window first,
    // placing the logout window below it
    // and listening for opened tab url change.
    // When url is changed, this means we can remove the window, and
    // regardless of the facebook result, we declare ourselves logged out.
    // The drawback of this approach is that when access token was already
    // invalid, we don't get a "login to facebook account" dialog in reaction
    // to clicking "Login" button in the sidebar.
    chrome.windows.getLastFocused(function (win) {
      if (!win || !win.width || !win.height)
        win = { "top": 0, "left": 0, "width": 50, "height": 50};

      var width = 50;
      var height = 50;
      var top = win.top + Math.floor((win.height - height) / 2);
      var left = win.left + Math.floor((win.width - width) / 2);

      chrome.windows.create(
        { "url": url, "type": "popup", "focused": false,
          "top": top, "left": left,
          "width": width, "height": height },
        function (wi) {
          if (win.id)
            chrome.windows.update(win.id, { "focused": true });

          chrome.windows.get(
            wi.id,
            { populate: true },
            function (w) {
              if (w.tabs.length !== 1)
                return;
              var logoutTabId = w.tabs[0].id;
              var removeLogoutTimeout = setTimeout(function () {
                chrome.tabs.onUpdated.removeListener(logoutTabUpdated);
                chrome.windows.remove(wi.id);
              }, 10000);

              var logoutTabUpdated = function (tabId, changeInfo, tab) {
                if (tabId == logoutTabId &&
                    tab.windowId == wi.id &&
                    changeInfo.url &&
                    changeInfo.url.indexOf(FB.LOGOUT_URL) !== 0) {
                  console.log('Logout confirmed.');
                  chrome.tabs.onUpdated.removeListener(arguments.callee);
                  chrome.windows.remove(wi.id);
                  clearTimeout(removeLogoutTimeout);
                }
              };

              chrome.tabs.onUpdated.addListener(logoutTabUpdated);
            }
          );
        }
      );
    });
  }
};

FB.Client.prototype.accessTokenFromSuccessURL = function (url) {
  var hashSplit = url.split('#');
  if (hashSplit.length > 1) {
    var paramsArray = hashSplit[1].split('&');
    for (var i = 0; i < paramsArray.length; i++) {
      var paramTuple = paramsArray[i].split('=');
      if (paramTuple.length > 1 && paramTuple[0] == 'access_token')
        return paramTuple[1];
    }
  }
  return null;
};

FB.Client.prototype.onTabUpdated = function (tabId, changeInfo, tab) {
  if (changeInfo.url && (changeInfo.url.indexOf(FB.SUCCESS_URL) === 0)) {
    if (!this.accessToken || this.state == FB.STATE.NEED_MORE_PERMISSIONS) {
      this.accessToken = this.accessTokenFromSuccessURL(changeInfo.url);
      if (!this.accessToken) {
        this.accessToken = null;
        localStorage.removeItem('accessToken');
        console.warn('Could not get an access token from url %s',
            changeInfo.url);
      } else {
        _gaq.push(['_trackEvent', 'login_success']);
        localStorage.setItem('accessToken', this.accessToken);
        this.extendAccessToken();
        this.checkForPermissions({ newAccessToken: true });
      }
    }

    chrome.tabs.remove(tabId);
    chrome.tabs.onUpdated.removeListener(FB.bindedTabUpdate);
  }
};

FB.Client.prototype.checkForPermissions = function (options) {
  $.publish('checkingPermissions.client.fb');
  this.state = FB.STATE.PERMISSIONS_CHECK;
  var xhr = $.ajax(FB.GRAPH_API_URL + '/me/permissions', {
    data: { access_token: this.accessToken }
  });
  xhr.permission_request = true;
  xhr.fail(
    // Logout if permission fetch raised an OAuthException on facebook side
    _.bind(function (jqxhr, textStatus) {
      if (jqxhr.status === 0) {
        $.publish('permissionsConnectionFailed.client.fb');
        // do not attempt further requests if network unavailable,
        // leave this task up to the roster UI controller
        clearTimeout(this.offline_wait_timer);
        this.offline_wait_timer = null;
      } else if (jqxhr.status === 400) {
        var response = JSON.parse(jqxhr.responseText);
        if (response.error && response.error.type == 'OAuthException') {
          $.publish('permissionsRequestNotAuthorized.client.fb');
          this.logout();
        }
      }
    }, this)
  ).done(
    _.bind(function (response, jqxhr, textStatus) {
      //var response = JSON.parse(jqxhr.responseText);
      var permsArray = response.data[0];

      var permsToPrompt = [];
      for (var i = 0; i < FB.PERMISSIONS.length; ++i) {
        if (permsArray[FB.PERMISSIONS[i]] == null) {
          permsToPrompt.push(FB.PERMISSIONS[i]);
        }
      }

      if (permsToPrompt.length > 0) {
        console.warn('Insufficient permissions. Requesting for more.');
        console.warn('Need permissions: ' + permsToPrompt.join(','));
        this.state = FB.STATE.NEED_MORE_PERMISSIONS;
        this.login(permsToPrompt);
      } else {
        this.state = FB.STATE.PERMISSIONS_CHECK_COMPLETE;
        $.publish('permissionCheckComplete', [ options ]);
      }
    }, this)
  );
};

FB.Client.prototype.getMyUid = function () {
  console.log('getMyUid() called');
  $.publish('retrievingUid.client.fb');
  this.graphApiRequest('/me', { fields: 'id' },
    _.bind(
      function(data) {
        console.log('/me success');
        if (data.id) {
          console.log('setting myUid...');
          this.myUid = data.id;
          localStorage.myUid = data.id;
        }
        this.onGotUid();
      }, this
    )
  );
};

FB.Client.prototype.onGotUid = function () {
  if (!this.myUid) {
    setTimeout(_.bind(this.getMyUid, this), 15000);
    return;
  }

  console.log('onGotUid() called');
  $.publish('myUidAvailable.client.fb');

  chrome.bitpopFacebookChat.loggedInFacebookSession();
  chrome.bitpopFacebookChat.setGlobalMyUidForProfile(this.myUid);
}

FB.Client.prototype.extendAccessToken = function () {
  if (!this.accessToken)
    return;

  $.publish('extendingToken.client.fb');
  var xhr = $.get(
      FB.TOKEN_EXCHANGE_URL + this.accessToken + '/', {},
      _.bind(
        function(data) {
          var at_prefix = "access_token=";
          if (data && data.indexOf(at_prefix) == 0) {
            var access_token = data.substring(at_prefix.length,
                                              data.indexOf('&'));
            if (access_token) {
              this.accessToken = access_token;
              localStorage.setItem('accessToken', this.accessToken);
              //notifyObservingExtensions({ type: 'accessTokenAvailable',
              //                            accessToken: this.accessToken });
              $.publish('accessTokenAvailable.client.fb', [ this.accessToken ]);

              console.log('Extend token success.')
            }
          }
        }, this),
    'html');
  xhr.callOnError = function (error) {
    console.error(error.error);
  };
}

FB.Client.prototype.graphApiRequest = function (path, params, callOnSuccess, callOnError) {
  if (!this.accessToken) {
    callOnError({ error: 'Facebook API unavailable.' });
    return;
  }

  params.access_token = this.accessToken;

  var xhr = $.get(FB.GRAPH_API_URL + path,
    params,
    function(pdata, textStatus, jqxhr) {
      if (pdata.error) {
        var errorMsg = 'Unable to fetch data from Facebook Graph API, url:' +
            path + ' . Error: ' + pdata.error.type +
            ': ' + pdata.error.message;

        console.error(errorMsg);

        errorMsg += '\nTry to logout and login once again.';

        jqxhr.callOnError && jqxhr.callOnError({ error: errorMsg });
        return;
      }
    },
    'json').done(callOnSuccess);

  if (callOnError) {
    xhr.callOnError = callOnError;
    xhr.fail(function (jqxhr, textStatus) { callOnError({ error: textStatus }); });
  }
}

FB.Client.prototype.graphApiPostRequest = function (path, params, callOnSuccess, callOnError) {
  if (!this.accessToken) {
    callOnError({ error: 'Facebook API unavailable.' });
    return;
  }

  console.log('graphApiRequest() token check: SUCCESS');
  params.access_token = this.accessToken;

  var xhr = $.post(FB.GRAPH_API_URL + path,
    params,
    function(pdata, textStatus, jqxhr) {
      console.log('graphApiRequest xhr fetch: SUCCESS');
      if (pdata.error) {
        var errorMsg = 'Unable to fetch data from Facebook Graph API, url:' +
            path + ' . Error: ' + pdata.error.type +
            ': ' + pdata.error.message;

        console.error(errorMsg);

        errorMsg += '\nTry to logout and login once again.';

        jqxhr.callOnError && jqxhr.callOnError({ error: errorMsg });
        return;
      }
    },
    'json').done(callOnSuccess);

  if (callOnError) {
    xhr.callOnError = callOnError;
    xhr.fail(function (jqxhr, textStatus) { callOnError({ error: textStatus }); });
  }
}

FB.Client.prototype.fqlRequest = function (query, callOnSuccess, callOnError) {
  if (!this.accessToken) {
    callOnError({ error: 'Facebook API unavailable.' });
    return;
  }

  xhr = $.get(FB.FQL_API_URL,
    {
      q: query,
      access_token: this.accessToken
    },
    function (pdata, textStatus, jqxhr) {
      if (pdata.error_code) {
        var errorMsg = 'Unable to fetch data from Facebook FQL API, query:' +
            query + '\nError: ' + pdata.error_code +
            ': ' + (pdata.error_msg ? pdata.error_msg : 'No message');
        console.error(errorMsg);
        errorMsg += '\nTry to logout and login once again.';
        jqxhr.callOnError || jqxhr.callOnError({ error: errorMsg });
        return;
      }
    },
    'json').done(function (pdata) { callOnSuccess(pdata.data); });

  if (callOnError) {
    xhr.callOnError = callOnError;
    xhr.fail(function (jqxhr, textStatus) { callOnError({ error: textStatus }); });
  }
}

FB.Client.prototype.restApiCall = function (method, params, onSuccess, onError) {
  params.format = 'json';
  params.access_token = localStorage.accessToken;

  var xhr = $.get(
      FB.REST_API_URL + method,
      params,
      function (data, textStatus, jqxhr) {
        if (data.error_code && onError) {
          var errorMsg = 'Unable to fetch data from Facebook REST API, method:' +
                method + '\nError: ' + data.error_code +
                ': ' + (data.error_msg ? data.error_msg : 'No message');
          jqxhr.onError && jqxhr.onError({ error: errorMsg });
        }
      },
      'json').done(function (data) { if (data === true) onSuccess({}); });
  if (onError) {
    xhr.callOnError = onError;
    xhr.fail(function (jqxhr, textStatus) { onError({ error: textStatus }); });
  }
}

FB.Client.prototype.setFacebookStatus = function (request, sendResponse) {
  if (!this.accessToken || !request.msg)
    return;

  var params = {};
  params.message = request.msg;
  var path = '/me/feed';

  function callOnSuccess() {
    sendResponse({ error: 'no' });
  }

  function callOnError() {
    sendResponse({ error: 'yes' });
  }

  this.graphApiPostRequest(path, params, callOnSuccess, callOnError);
};