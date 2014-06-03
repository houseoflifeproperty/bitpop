/**
 * File that contains all user configurable options. See chrome://extensions/
 * and http://code.google.com/chrome/extensions/options.html .
 */

// extend Storage API to set and get JS objects
Storage.prototype.setObject = function(key, value) {
    this.setItem(key, JSON.stringify(value));
};

Storage.prototype.getObject = function(key, def) {
    var value = this.getItem(key);
    var obj = window.JSON.parse(value);
    if (obj) {
      return obj;
    } else if (def) {
      return def;
    }
};

window.options = {

  init: function(debug) {
    for (var prop in options.defaults) {
      var stored = options.stored[prop];
      var debug_value = options.debug[prop];
      if (typeof stored !== 'undefined' && !(prop == 'controllerExtensionId' && stored.indexOf('igdd') === 0)) {
        options.current[prop] = stored;
      } else if (debug && typeof debug_value !== 'undefined') {
        options.current[prop] = debug_value;
      } else {
        options.current[prop] = options.defaults[prop];
      }
    }
    options.save();
    return options;
  },

  initDebug: function() {
    options.reset();
    return options.init(true);
  },

  save: function() {
    window.localStorage.setObject('options', window.options.current);
    return options;
  },

  reset: function() {
    options.stored = options.current = {};
    options.save();
    return options;
  },

  defaults: {
    popupEndpoint: '/desktop_notifications/popup.php',
    refreshTime: 30000,
    markAsRead: true,
    domain: 'www.facebook.com',
    protocol: 'https://',
    controllerExtensionId: "engefnlnhcgeegefndkhijjfdfbpbeah"
  },

  debug: {
    refreshTime: 5000,
    markAsRead: false,
    domain: 'www.dev.facebook.com',
    protocol: 'http://',
    controllerExtensionId: "engefnlnhcgeegefndkhijjfdfbpbeah"
  },

  stored: window.localStorage.getObject('options', {}),

  current: {}

};
