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

Array.prototype.contains = function(obj) {
  var i = this.length;
  while (i--) {
    if (this[i] === obj) {
      return true;
    }
  }
  return false;
};

Object.size = function(obj) {
    var size = 0, key;
    for (key in obj) {
        if (obj.hasOwnProperty(key)) size++;
    }
    return size;
};

DesktopNotifications = {

  DEFAULT_FADEOUT_DELAY: 20000,
  CLOSE_ON_CLICK_DELAY: 300,
  // 250 is a good delay for a human-visible flash
  COUNTER_BLINK_DELAY: 250,

  // Collection of notifications currently on screen
  notifications: [],
  _timer: null,

  // The following values are supposed to be in window.webkitNotifications,
  // but they're not defined as of Chrome 9/Chromium 75753.
  PERMISSION_ALLOWED: 0,
  PERMISSION_NOT_ALLOWED: 1,
  PERMISSION_DENIED: 2,

  // These may be overridden by clients
  getEndpoint: '/desktop_notifications/get.php',
  countsEndpoint: '/desktop_notifications/counts.php',
  domain: '',
  protocol: '',

  // polling instance
  _interval: null,

  // These are used to short circuit data fetching on the server.
  // See flib/notifications/prepare/prepare.php
  _latest_notif: 0,
  _latest_read_notif: 0,

  // Unread counts, used for badge and fetching new HTML
  _num_unread_notif: 0,
  _num_unseen_inbox: 0,

  // We may obtain a CSRF token from the server to suppress click-jacking
  // protection on requests to HTML pages.
  fb_dtsg: '',

  received_cache: [],

  threads: [],
  time_chat_was_read_indexed_by_friend_uid: {},
  time_popup_opened_indexed_by_friend_uid: {},
  just_connected: false,

  //FIXME: should be merged with popup.js constant
  MAX_NOTIFICATIONS_TO_SHOW: 5,

  /**
   * Start polling for notifications. New notifications are displayed
   * immediately. This should called from clients off of facebook.com. On the
   * main site we have presence to do our polling for us.
   */
  start: function(refresh_time) {
    var self = DesktopNotifications;
    // Don't refresh faster than fade out
    if (refresh_time < self.DEFAULT_FADEOUT_DELAY) {
      refresh_time = self.DEFAULT_FADEOUT_DELAY;
    }

    self.stop();
    self.showActiveIcon();
    // fetch the current counts immediately
    self.fetchServerInfo(self.handleServerInfo, self.showInactiveIcon);

    self._interval = setInterval(function() {
      self.fetchServerInfo(
        function(serverInfo) {
          self.handleServerInfo(serverInfo);
          // set back to active in case of previous error
          self.showActiveIcon();
        },
        self.showInactiveIcon);
    }, refresh_time);
  },

  /**
   * Get the best popup type to show. See WebDesktopNotificationsBaseController
   */
  getPopupType: function() {
    return 'inbox';
  },

  /**
   * Stop polling.
   */
  stop: function() {
    clearInterval(DesktopNotifications._interval);
    DesktopNotifications.showInactiveIcon();
  },

  /**
   * Updates icon in Chrome extension to normal blue icon
   */
  showActiveIcon: function() {
    if (chrome && chrome.browserAction) {
      chrome.browserAction.setIcon({path: '/images/icon19.png'});
    }
  },

  /**
   * Updates icon in Chrome extension to gray icon and clears badge.
   */
  showInactiveIcon: function() {
    if (chrome && chrome.browserAction) {
      chrome.browserAction.setBadgeText({text: ''});
      chrome.browserAction.setIcon({path: '/images/icon-loggedout.png'});
    }
  },

  /**
   * Fetches metadata from the server on the current state of the user's
   * notifications and inbox.
   */
  fetchServerInfo: function(callback, errback, no_cache) {
    callback = callback || function(d) { console.log(d); };
    errback = errback || function(u, e) { console.error(u, e); };
    var self = DesktopNotifications;

    var query = "SELECT thread_id, unread, unseen, updated_time, recipients FROM thread WHERE folder_id=0 AND unseen > 0";
    chrome.extension.sendMessage(self.controllerExtensionId,
        { type: 'fqlQuery',
          query: query
        },
        function (response) {
          if (!response)
            return;

          if (response.error)
            errback(response.error, 'fqlQuery: ' + query);
          else
            callback(response);
        }
     );
  },

  _fetch: function(uri, callback, errback) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", uri, true);
    xhr.onreadystatechange = function() {
      if (xhr.readyState == 4) {
        try {
          if (xhr.status == 200) {
            return callback(xhr.responseText);
          } else {
            throw 'Status ' + xhr.status + ': ' + xhr.responseText;
          }
        } catch (e) {
          errback(e, uri);
        }
      }
    };
    xhr.send(null);
  },

  /**
   * Decides whether to fetch any items for display depending on data from
   * server on unread counts.
   */
  handleServerInfo: function(serverInfo0) {
    var self = DesktopNotifications;

    if (self.just_connected)
      localStorage.setCacheItem('connect_time', (new Date()).toString(),
                                { 'days': 21 });

    var p = {};
    p.data = serverInfo0;
    var serverInfo = p;

    serverInfo.summary = { unseen_count: 0, unread_count: 0 };
    var i = 0;
    for (; i < serverInfo0.length; ++i) {
      serverInfo.summary.unseen_count += serverInfo0[i].unseen;
      serverInfo.summary.unread_count += serverInfo0[i].unread;
    }

    var thread_ids_received = [];
    for (i = 0; i < serverInfo.data.length; i++)
      thread_ids_received.push(serverInfo.data[i].thread_id);

    if (serverInfo.summary.unseen_count !== 0) {
      var first_unseen_thread_index = -1;  // not set equivalent
      var local_unseen_count = 0;
      for (i = 0; i < serverInfo.data.length; i++) {
        var th_id = serverInfo.data[i].thread_id;
        var upd_time = serverInfo.data[i].updated_time;

        var recipients = serverInfo.data[i].recipients;
        if (recipients.length > 1) {
          var time_popup_opened =
              self.time_popup_opened_indexed_by_friend_uid[''+recipients[0]] ||
              self.time_popup_opened_indexed_by_friend_uid[''+recipients[1]];
          if (time_popup_opened && time_popup_opened > upd_time) {
            localStorage.setCacheItem('xx_' + th_id, ''+time_popup_opened,
              { 'days': 21 });
          }
        }

        var d = localStorage.getCacheItem('xx_' + th_id);
        if (!d) {
          d = '0';
        }
        var date = new Date(+d);

        if (self.just_connected ||
          date.getTime() <
            (new Date(upd_time * 1000)).getTime()) {

          self.threads.push(th_id);
          local_unseen_count++;

          if (first_unseen_thread_index === -1)
            first_unseen_thread_index = i;
        }
        if (self.just_connected) {
          localStorage.setCacheItem('xx_' + th_id, (new Date()).getTime(),
            { 'days': 21 });
        }
      }

      serverInfo.summary.unseen_count = local_unseen_count;

      // get message for last unseen thread
      if (first_unseen_thread_index !== -1) {

        var query_obj = {
          recipients: "SELECT thread_id, recipients FROM thread WHERE " +
                      "folder_id=0 AND thread_id IN ('" +
                      thread_ids_received.
                        slice(0, self.MAX_NOTIFICATIONS_TO_SHOW).join("','") +
                      "')",
          users: "SELECT uid, name FROM user WHERE uid IN (SELECT recipients FROM #recipients)"
        };

        var message_query_tmpl =
             "SELECT message_id, thread_id, author_id, body, created_time FROM message WHERE" +
             " thread_id='{{thread_id}}'" +
             " ORDER BY created_time DESC LIMIT 10";
        for (i = 0; i < thread_ids_received.length &&
                        i < self.MAX_NOTIFICATIONS_TO_SHOW; i++) {
          query_obj['message_'+thread_ids_received[i]] =
            message_query_tmpl.replace('{{thread_id}}', thread_ids_received[i]);
        }

        var query = JSON.stringify(query_obj);

        chrome.extension.sendMessage(self.controllerExtensionId,
          {
            type: 'fqlQuery',
            query: query
          },
          function (response) {
            if (response.error)
              self.showInactiveIcon();
            else {
              self._handleInboxInfo(serverInfo, response);
            }
          }
        );
      }
    }

    if (serverInfo.summary.unseen_count === 0) {
      self._num_unseen_inbox = 0;
      self.updateUnreadCounter();
    } else if (serverInfo.summary.unseen_count !== self._num_unseen_inbox) {
      self._num_unseen_inbox = serverInfo.summary.unseen_count; // actually 0
      self.updateUnreadCounter();
    }
  },

  _findResultSet: function(query_name, data) {
    for (var i = 0; i < data.length; ++i) {
      if (data[i].name == query_name)
        return data[i].fql_result_set;
    }
    return null;
  },

  _findFirstFriendInRecipientsList: function(recipientsList, thread_id, uid_self) {
    var res = [];
    for (var i = 0; i < recipientsList.length; ++i) {
      if (recipientsList[i].thread_id == thread_id) {
        res = recipientsList[i];
        break;
      }
    }
    return (res[0] != uid_self) ? res[0] : res[1];
  },

  _handleInboxInfo: function(threads, data) {
    var self = DesktopNotifications;

    var users = self._findResultSet('users', data);
    var recipients = self._findResultSet('recipients', data);
    var messages = {};
    for (var i = 0; i < threads.data.length &&
                    i < self.MAX_NOTIFICATIONS_TO_SHOW; i++) {
      var th_id = threads.data[i].thread_id;
      var rs = self._findResultSet('message_' + th_id, data);
      var msg = (rs && rs[0]) ? rs[0] : null;
      messages[th_id] = msg;

      if (!self.just_connected) {
        var d = localStorage.getCacheItem('xx_' + th_id) || "0";
        var date = new Date(+d);
        var counter = Math.min(rs.length, threads.data[i].unseen);
        var msgList = [];
        for (var j = 0; j < counter && rs[j].author_id != myUid; ++j) {
          msgList.unshift(rs[j]);
        }

        for (j = 0; j < msgList.length; ++j) {
          var time_read = self.time_chat_was_read_indexed_by_friend_uid[
              ''+msgList[j].author_id
            ];
          if (this.threads.indexOf(th_id) !== -1 &&
              (!time_read ||
                (time_read.getTime() < msgList[j].created_time * 1000 &&
                  (msgList[j].created_time * 1000 - time_read.getTime()) > 7000 * 1000)) &&

              date.getTime() < msgList[j].created_time * 1000) {
            // Send message to friends extension to add message to chats
            chrome.extension.sendMessage("engefnlnhcgeegefndkhijjfdfbpbeah",
              {
                "type": "newInboxMessage",
                "from": msgList[j].author_id,
                "body": msgList[j].body,
                "created_time": msgList[j].created_time
              });
            self.time_chat_was_read_indexed_by_friend_uid[
              ''+msgList[j].author_id] = new Date();
          }
        }
      }
    }

    if (threads.summary.unseen_count !== self._num_unseen_inbox) {
      if (threads.summary.unseen_count > self._num_unseen_inbox) {
        self._latest_data = {
          threads: threads.data.slice(0, self.MAX_NOTIFICATIONS_TO_SHOW),
          users: users,
          messages: messages
        };

        self.addNotificationByType('inbox');
      }
      self._num_unseen_inbox = threads.summary.unseen_count;
      self.updateUnreadCounter();
    }

    self.just_connected = false;
  },

  /**
   * Updates "badge" in Chrome extension toolbar icon.
   * See http://code.google.com/chrome/extensions/browserAction.html#badge
   */
  updateUnreadCounter: function() {
    var self = DesktopNotifications;
    if (chrome && chrome.browserAction) {
      // first set the counter to empty
      chrome.browserAction.setBadgeText({text: ''});
      // wait, then set it to new value
      setTimeout(function() {
          // don't show a zero
          var num = (self.getUnreadCount() || '') + '';
          chrome.browserAction.setBadgeText({text: num});
        },
        self.COUNTER_BLINK_DELAY,
        false // quickling eats timeouts otherwise
        );
    }
  },

  getUnreadCount: function() {
    var self = DesktopNotifications;
    return self._num_unread_notif + self._num_unseen_inbox;
  },

  _nameByUid: function(uid, users) {
    for (var i = 0; i < users.length; i++) {
      if (users[i].uid.toString() == uid.toString())
        return users[i].name;
    }
    return "{Unknown user}";
  },

  addNotificationByType: function(type) {
    var self = DesktopNotifications;
    if (self._latest_data) {
      var fromUid, body, name;

      if (Object.size(self._latest_data.messages) <= 0)
        return;

      for (var i = 0; i < self._latest_data.threads.length; i++) {
        var thread_id = self._latest_data.threads[i].thread_id;
        var lastComment = self._latest_data.messages[thread_id];

        if (localStorage.getCacheItem(lastComment.message_id) == 1)
          continue;

        fromUid = lastComment.author_id;
        name = self._nameByUid(lastComment.author_id, self._latest_data.users);
        body = lastComment.body;

        localStorage.setCacheItem(lastComment.message_id, 1, { days: 21 });
      }
    }
  },

  /**
   * Adds a new notification to the queue.
   * After an expiration period, it is closed.
   */
  addNotification: function(alert_id, delay) {
  },

  showNotification: function(notification, delay) {
    notification.show();
    notification.onclick = function(e) {
      chrome.tabs.create({ url: this.clickHref });
      // Oddly, defer(0) still cancels the notification before the
      // click passes through.  Give it a little time before we
      // close the window.
      setTimeout(function() {
          e.srcElement.cancel();
        },
        DesktopNotifications.CLOSE_ON_CLICK_DELAY,
        false // quickling eats timeouts otherwise
        );
    };
    DesktopNotifications.notifications.push(notification);
    DesktopNotifications.restartTimer(delay);
  },

  expireNotifications: function() {
    DesktopNotifications.notifications.forEach(function(n) { n.cancel(); });
    DesktopNotifications.notifications = [];
    DesktopNotifications._timer = null;
  },

  restartTimer: function(extraTime) {
    if (DesktopNotifications._timer) {
      clearTimeout(DesktopNotifications._timer);
    }
    DesktopNotifications._timer = setTimeout(function() {
      DesktopNotifications.expireNotifications();
    }, extraTime);
  }
};
