// This file is packaged with the extension then re-fetched from the
// server for updates. Bitter experience has taught us that we can't depend on
// the server resource loading correctly.

/**
 * Copyright 2004-present Facebook. All Rights Reserved.
 *
 * Provides functions to get and display notifications in a desktop window.
 * Currently only Chrome supports the "web notifications" spec. Its
 * implementation is called webkitNotifications.
 *
 * Typically webkitNotifications is accessed from two distinct contexts:
 * 1) from a document on the host site
 * 2) from a Chrome extension that has permission to request data from the
 *    host site.
 *
 * This module supports both use cases. Some functions are Chrome-extension
 * only. A future refactoring may resolve to put them in a subclass, but
 * chances are higher we will eliminate support for 1) entirely.
 *
 * This module intentionally has no @requires dependencies so that it can
 * work in the extension context with a single <script> tag. The extension
 * may also load it as a haste resource via rscrx.php. Contact gdingle for
 * details.
 *
 * Web Notifications:
 *   http://dev.w3.org/2006/webapi/WebNotifications/publish/
 *   Chrome implementation: http://www.fburl.com/?key=1717695
 *
 * @provides desktop-notifications
 */
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
    var self = DesktopNotifications;

    var type = 'notifications';
    // if (self._num_unseen_inbox && !self._num_unread_notif) {
    //   type = 'inbox';
    // }
    return type;
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
    // var uri = self.protocol + self.domain + self.countsEndpoint +
    //   '?latest=' + self._latest_notif +
    //   '&latest_read=' + self._latest_read_notif;
    // if (no_cache) {
    //   uri += '&no_cache=1';
    // }
    // self._fetch(
    //   uri,
    //   function(json) {
    //     callback(JSON.parse(json));
    //   },
    //   errback
    // );

    var query = 'SELECT created_time, title_text,' +
                        'href, icon_url ' +
                 'FROM notification ' +
                 'WHERE recipient_id=me() AND is_unread = 1 AND is_hidden = 0'

    chrome.extension.sendMessage(self.controllerExtensionId,
        { type: 'fqlQuery',
          query: query
        },
        function (response) {
          if (!response)
            return;

          if (response.error)
            errback(response.error, query);
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
  handleServerInfo: function(serverInfo) {
    var self = DesktopNotifications;

    self._handleNotifInfo(serverInfo);
    // self._handleInboxInfo(serverInfo.inbox);
  },

  _handleNotifInfo: function(notifInfo) {
    var self = DesktopNotifications;

    if (self._num_unread_notif !== notifInfo.length) {
      if (notifInfo.length &&
          (self._latest_notif < notifInfo[0].created_time)) {
        self._latest_notif = notifInfo[0].created_time;
        self._latest_data = notifInfo[0];
        // self._latest_read_notif = notifInfo.latest_read;
        // see WebDesktopNotificationsBaseController::TYPE_NOTIFICATIONS
        self.addNotificationByType('notifications');
      }
      self._num_unread_notif = notifInfo.length;
      self.updateUnreadCounter();
    }
  },

  _handleInboxInfo: function(inboxInfo) {
    var self = DesktopNotifications;
    if (!inboxInfo) {
      return;
    }
    if (inboxInfo.unseen !== self._num_unseen_inbox) {
      if (inboxInfo.unseen > self._num_unseen_inbox) {
        // see WebDesktopNotificationsBaseController::TYPE_INBOX
        self.addNotificationByType('inbox');
      }
      self._num_unseen_inbox = inboxInfo.unseen;
      self.updateUnreadCounter();
    }
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

  addNotificationByType: function(type) {
    var self = DesktopNotifications;
    if (self._latest_data) {
      // var uri = self.protocol + self.domain + self.getEndpoint +
      //   '?type=' + (type || '');
      
      var notificationClickedCallback = function (notificationId) {
        if (notificationId == 'com.facebook.alert.notifications') {
          chrome.tabs.create({ url: self._latest_data.href });
          // Oddly, defer(0) still cancels the notification before the
          // click passes through.  Give it a little time before we
          // close the window.
          setTimeout(function() {
              chrome.notifications.clear("com.facebook.alert.notifications", 
                                         function () {});
            },
            DesktopNotifications.CLOSE_ON_CLICK_DELAY,
            false // quickling eats timeouts otherwise
          );
        }
      };

      chrome.notifications.create("com.facebook.alert.notifications", {
        type: "basic",
        iconUrl: self._latest_data.icon_url,
        title: 'Facebook Notification',
        message: self._latest_data.title_text,
        isClickable: true
      }, function (notificationId) {
        chrome.notifications.onClosed.addListener(function (notificationClosedId) {
          if (notificationClosedId == notificationId) {
            chrome.notifications.onClicked.removeListener(notificationClickedCallback);
            chrome.notifications.onClosed.removeListener(arguments.callee);
          }
        });
        chrome.notifications.onClicked.addListener(notificationClickedCallback);
      });
      DesktopNotifications.restartTimer(self.DEFAULT_FADEOUT_DELAY);
    }
  },

  /**
   * Adds a new notification to the queue.
   * After an expiration period, it is closed.
   */
  addNotification: function(alert_id, delay) {
    var self = DesktopNotifications;
    if (!window.webkitNotifications) {
      return;
    }

    if (typeof delay == 'undefined') {
      delay = self.DEFAULT_FADEOUT_DELAY;
    }
    var uri = self.protocol + self.domain + self.getEndpoint +
      '?alert_id=' + (alert_id || '') +
      '&latest=' + self._latest_notif +
      '&latest_read=' + self._latest_read_notif;
    var notification =
      window.webkitNotifications.createHTMLNotification(uri);

    // In case the user has multiple windows or tabs open, replace
    //// any existing windows for this alert with this one.
    notification.replaceId = 'com.facebook.alert.' + alert_id;

    self.showNotification(notification, delay);
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
    chrome.notifications.clear('com.facebook.alert.notifications', function () {});
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
