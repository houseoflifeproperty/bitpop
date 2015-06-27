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

var torlauncher = torlauncher || {};

const kPropNamePrefix = "torlauncher.";
var gUILanguage = chrome.i18n.getUILanguage();

torlauncher.util = {
  is_production: false,
  kNetworkSettingsWindowId: "torlauncher.window.network_settings",
  kAlertWindowId: "torlauncher.window.alert",

  kDefaultBridgePref: "defaultBridge",
  kDefaultBridgeTypePref: "defaultBridgeType",

  translate: function(messageID, args) {
    if (!torlauncher.messages[gUILanguage]) {
      if (gUILanguage == "en-US")
        gUILanguage = "en";
      else if (gUILanguage == "es-419")
        gUILanguage = "es";

      if (!torlauncher.messages[gUILanguage])
        return "";
    }

    var res = torlauncher.messages[gUILanguage][messageID];
    if (args && args.length) {
      for (var i = 1; i <= args.length; ++i) {
        res = res.replace('$' + i, args[i-1]);
      }
    }
    return res;
  },

  localizePage: function() {
    var translate = torlauncher.util.translate;
    //translate a page into the users language
    $("[i18n]:not(.i18n-replaced)").each(function() {
      $(this).html(translate($(this).attr("i18n")));
    });
    $("[i18n_value]:not(.i18n-replaced)").each(function() {
      $(this).val(translate($(this).attr("i18n_value")));
    });
    $("[i18n_title]:not(.i18n-replaced)").each(function() {
      $(this).attr("title", translate($(this).attr("i18n_title")));
    });
    $("[i18n_placeholder]:not(.i18n-replaced)").each(function() {
      $(this).attr("placeholder", translate($(this).attr("i18n_placeholder")));
    });
    $("[i18n_replacement_el]:not(.i18n-replaced)").each(function() {
      // Replace a dummy <a/> inside of localized text with a real element.
      // Give the real element the same text as the dummy link.
      var dummy_link = $("a", this);
      var text = dummy_link.text();
      var real_el = $("#" + $(this).attr("i18n_replacement_el"));
      real_el.text(text).val(text).replaceAll(dummy_link);
      // If localizePage is run again, don't let the [i18n] code above
      // clobber our work
      $(this).addClass("i18n-replaced");
    });
  },

  // "torlauncher." is prepended to aStringName.
  getLocalizedString: function(aStringName) {
    if (!aStringName)
      return aStringName;

    var key = kPropNamePrefix + aStringName;
    var res = torlauncher.util.translate(key);

    return (res) ? res : aStringName;
  },

  // "torlauncher." is prepended to aStringName.
  getFormattedLocalizedString: function(aStringName, aArray, aLen) {
    if (!aStringName || !aArray || aLen > 9 || aLen <= 0)
      return aStringName;

    var key = kPropNamePrefix + aStringName;
    var res = torlauncher.util.translate(key, aArray.slice(0, aLen));

    return (res) ? res : aStringName;
  },

  getLocalizedBootstrapStatus: function(aStatusObj, aKeyword)
  {
    if (!aStatusObj || !aKeyword)
      return "";

    var result;
    var fallbackStr;
    if (aStatusObj[aKeyword]) {
      var val = aStatusObj[aKeyword].toLowerCase();
      var key;
      if (aKeyword == "TAG") {
        if ("onehop_create" == val)
          val = "handshake_dir";
        else if ("circuit_create" == val)
          val = "handshake_or";

        key = "bootstrapStatus." + val;
        fallbackStr = aStatusObj.SUMMARY;
      } else if (aKeyword == "REASON") {
        if ("connectreset" == val)
          val = "connectrefused";

        key = "bootstrapWarning." + val;
        fallbackStr = aStatusObj.WARNING;
      }

      result = torlauncher.util.getLocalizedString(key);
      if (result == key)
        result = undefined;
    }

    if (!result)
      result = fallbackStr;

    return (result) ? result : "";
  },

  envExists: function(env_name) {
    return new Promise(function (resolve, reject) {
      chrome.torlauncher.envExists(env_name, resolve);
    });
  },

  envGet: function(env_name) {
    return new Promise(function (resolve, reject) {
      chrome.torlauncher.envGet(env_name, resolve);
    });
  },

  prefGet: function(pref_name) {
    return new Promise(function (resolve, reject) {
      chrome.torlauncher[pref_name].get(
        { incognito: true },
        function (details) {
          console.info('prefGet: ' + pref_name + ' == ' + details.value);
          var val = details.value;
          if (pref_name == 'defaultBridge')
            val = JSON.parse(val);
          resolve(val);
        }
      );
    });
  },

  setPref: function(pref_name, pref_value) {
    return new Promise(function (resolve, reject) {
      if (pref_name == "defaultBridge")
        pref_value = JSON.stringify(pref_value);
      chrome.torlauncher[pref_name].set({ value: pref_value,
                                          scope: "incognito_persistent"},
                                        resolve);
    });
  },

  shouldStartAndOwnTor: function *() {
    const kEnvSkipLaunch = "TOR_SKIP_LAUNCH";
    const kPrefStartTor = "startTorPref";

    try {
      var env_exists = yield this.envExists(kEnvSkipLaunch);
      if (env_exists) {
        var skip_launch = yield this.envGet(kEnvSkipLaunch);
        return ("1" != skip_launch);
      }
      return (yield this.prefGet(kPrefStartTor));

    } catch (e) {
      console.error('Runtime error: getShouldStartAndOwnTor()');
      throw e;
    }
  },

  shouldShowNetworkSettings: function *() {
    const kEnvForceShowNetConfig = "TOR_FORCE_NET_CONFIG";
    const kPrefPromptAtStartup = "promptAtStartup";

    try {
      var env_exists = yield this.envExists(kEnvForceShowNetConfig);
      if (env_exists) {
        var force_show = yield this.envGet(kEnvForceShowNetConfig);
        return ("1" == force_show);
      }
      return (yield this.prefGet(kPrefPromptAtStartup));

    } catch (e) {
      console.error('Runtime error: shouldShowNetworkSettings()');
      throw e;
    }
  },

  shouldOnlyConfigureTor: function *() {
    const kEnvOnlyConfigureTor = "TOR_CONFIGURE_ONLY";
    const kPrefOnlyConfigureTor = "onlyConfigureTor";

    try {
      var env_exists = yield this.envExists(kEnvOnlyConfigureTor);
      if (env_exists) {
        var only_configure = yield this.envGet(kEnvOnlyConfigureTor);
        return ("1" == only_configure);
      }
      return (yield this.prefGet(kPrefOnlyConfigureTor));

    } catch (e) {
      console.error(e);
      console.error('Runtime error: shouldOnlyConfigureTor()');
      throw e;
    }
  },

  // Error Reporting / Prompting
  showAlert: function(aParentWindow, aMsg) {
    const alertHtml =
      '<p>$1</p>' +
      '<div class="hbox">' +
        '<div class="spring flex1"></div>' +
        '<button id="alertOk" type="button" autofocus="true">OK</button>' +
        '<div class="spring flex1"></div>' +
      '</div>';

    return new Promise(function (resolve, reject) {
      if (!aParentWindow) {
        var w = chrome.app.window.get(torlauncher.util.kNetworkSettingsWindowId);
        if (w)
          aParentWindow = w.contentWindow;
      }

      var content = alertHtml.replace('$1', aMsg);
      if (!aParentWindow) {
        chrome.app.window.create('alert-dialog.html',
          {
            id: torlauncher.util.kAlertWindowId,
            state: "normal",
            alwaysOnTop: true,
            innerBounds: {
              left:      100,
              top:       100,
              width:     450,
              height:    250,
              minWidth:  450,
              minHeight: 250,
              maxWidth:  450,
              maxHeight: 250
            }
          },
          function (createdWindow) {
            var w = createdWindow.contentWindow;
            w.torlauncher = {
              alertWindowType: 'alert',
              alertContent: content,
              confirmButtonId: 'alertOk'
            };

            createdWindow.onClosed.addListener(resolve);
          }
        );
      } else {
        // FIXME:
        // when network settings window is closed with an alert modal dialog
        // opened - then what should we do?
        aParentWindow.modal.open({ content: content });
        aParentWindow.$("#alertOk").click(function (e) {
          aParentWindow.modal.close();
          resolve();
        });
      }
    });
  },

  // Returns true if user confirms; false if not.
  // Note that no prompt is shown (and false is returned) if the Network Settings
  // window is open.
  showConfirm: function(aParentWindow,
                        aMsg, aDefaultButtonLabel, aCancelButtonLabel) {
    const confirmHtml =
      '<p>$1</p>' +
      '<div class="hbox">' +
        '<div class="spring flex1"></div>' +
        '<button id="alertCancel" type="button">$3</button>' +
        '<button id="alertOk" type="button" autofocus="true">$2</button>' +
      '</div>';

    return new Promise(function (resolve, reject) {

      if (!aParentWindow) {
        var w = chrome.app.window.get(torlauncher.util.kNetworkSettingsWindowId);
        if (w) {
          reject();
          return;
        }
      }


      var content = confirmHtml.replace('$1', aMsg);
      content = content.replace('$2', aDefaultButtonLabel);
      content = content.replace('$3', aCancelButtonLabel);

      if (!aParentWindow) {
        chrome.app.window.create('alert-dialog.html',
          {
            id: torlauncher.util.kAlertWindowId,
            state: "normal",
            alwaysOnTop: true,
            innerBounds: {
              left:      100,
              top:       100,
              width:     450,
              height:    250,
              minWidth:  450,
              minHeight: 250,
              maxWidth:  450,
              maxHeight: 250
            }
          },
          function (createdWindow) {
            var w = createdWindow.contentWindow;
            w.torlauncher = {
              alertWindowType: 'confirm',
              alertContent: content,
              confirmButtonId: 'alertOk',
              cancelButtonId: 'alertCancel',
              resolveCallback: resolve,
              rejectCallback: reject
            };

            createdWindow.onClosed.addListener(reject);
          }
        );
      } else {
        // FIXME:
        // when network settings window is closed with an alert modal dialog
        // opened - then what should we do?
        aParentWindow.modal.open({ content: content });
        aParentWindow.$("#alertOk").click(function (e) {
          aParentWindow.modal.close();
          resolve();
        });
        aParentWindow.$("#alertCancel").click(function (e) {
          aParentWindow.modal.close();
          reject();
        });
      }
    });
  },

  showSaveSettingsAlert: function(aParentWindow, aDetails) {
    if (!aDetails)
      aDetails = torlauncher.util.getLocalizedString("ensure_tor_is_running");

    var s = torlauncher.util.getFormattedLocalizedString(
              "failed_to_save_settings", [aDetails], 1);
    return torlauncher.util.showAlert(aParentWindow, s);
  },

  // Returns an array of strings or undefined if none are available.
  defaultBridgeTypes: function *() {
      try {
        var defaultBridgeDict = yield this.prefGet(this.kDefaultBridgePref);
        // return sorted keys array of the dict
        return Object.keys(defaultBridgeDict).sort();
      } catch (e) {}

      return undefined;
  },

  // Returns an array of strings or undefined if none are available.
  // The list is filtered by the default_bridge_type pref value.
  defaultBridges: function *() {
    try {
      var filterType = yield this.prefGet(this.kDefaultBridgeTypePref);
      if (!filterType)
        return undefined;

      var defaultBridgeDict = yield this.prefGet(this.kDefaultBridgePref);
      var bridgeArray = [];
      for (var bridgeType in defaultBridgeDict) {
        if (bridgeType == filterType) {
          return defaultBridgeDict[bridgeType];
        }
      }
      return bridgeArray;

    } catch (e) {}

    return undefined;
  },

  // ArrayBuffer conversions ---------------------------------
  // ---------------------------------------------------------
  ab2str: function (buf) {
    return String.fromCharCode.apply(null, new Uint8Array(buf));
  },

  str2ab: function (str) {
    var buf = new ArrayBuffer(str.length); // 2 bytes for each char
    var bufView = new Uint8Array(buf);
    for (var i=0, strLen=str.length; i < strLen; i++) {
      bufView[i] = str.charCodeAt(i);
    }
    return buf;
  },

  pr_debug: function (message) {
    if (!torlauncher.util.is_production)
      console.log(message);
  },

  isGeneratorFunction: function (functionToCheck) {
    return (functionToCheck.constructor.name === "GeneratorFunction");
  },

  // run (async) a generator to completion
  runGenerator: function (g) {
      var it = g(), ret;

      // asynchronously iterate over generator
      (function iterate(val){
          ret = it.next( val );

          if (!ret.done) {
              // is it a Promise?
              if (Promise.prototype.isPrototypeOf(ret.value)) {
                  // wait on the promise
                  ret.value.then( iterate, function (e) { it.throw(e); } );
              }
              // immediate value: just send right back in
              else {
                  // avoid synchronous recursion
                  setTimeout( function(){
                      iterate( ret.value );
                  }, 0 );
              }
          }
      })();
  }
};
