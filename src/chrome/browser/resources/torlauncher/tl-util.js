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

var torlauncher = torlauncher || {};

const kPropNamePrefix = "torlauncher.";

torlauncher.util = {
  translate: function(messageID, args) {
    return chrome.i18n.getMessage(messageID, args);
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
    var res = chrome.i18n.getMessage(key);

    return (res) ? res : aStringName;
  },

  // "torlauncher." is prepended to aStringName.
  getFormattedLocalizedString: function(aStringName, aArray, aLen) {
    if (!aStringName || !aArray || aLen > 9 || aLen <= 0)
      return aStringName;

    var key = kPropNamePrefix + aStringName;
    var res = chrome.i18n.getMessage(key, aArray.slice(0, aLen));

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

  envExistsWithPromise: function(env_name) {
    return new Promise(function (resolve, reject) {
      chrome.torlauncher.env.exists(env_name, resolve);
    });
  },

  envGetWithPromise: function(env_name) {
    return new Promise(function (resolve, reject) {
      chrome.torlauncher.env.get(env_name, resolve);
    });
  },

  prefGetWithPromise: function(pref_name) {
    return new Promise(function (resolve, reject) {
      chrome.torlauncher[pref_name].get({ incognito: true}, function (details) {
        resolve(details.value);
      });
    });
  },

  getShouldStartAndOwnTorWithPromise: function() {
    return new Promise(function (resolve, reject)) {
      const kEnvSkipLaunch = "TOR_SKIP_LAUNCH";
      const kPrefStartTor = "startTor";

      envExistsWithPromise(kEnvSkipLaunch).then(function (exists) {
        if (exists)
          envGetWithPromise(kEnvSkipLaunch).then(function(skip_launch) {
            resolve("1" != skip_launch);
          });
        else
          prefGetWithPromise(kPrefStartTor).then(function (pref_val) {
            resolve(pref_val);
          });
      });
    });
  },

  getShouldShowNetworkSettingsWithPromise: function()
  {
    return new Promise(function (resolve, reject) {
      const kEnvForceShowNetConfig = "TOR_FORCE_NET_CONFIG";
      const kPrefPromptAtStartup = "promptAtStartup";

      envExistsWithPromise(kEnvForceShowNetConfig).then(function (exists) {
        if (exists)
          envGetWithPromise(kEnvForceShowNetConfig).then(function(force_show) {
            resolve("1" == force_show);
          });
        else
          prefGetWithPromise(kPrefPromptAtStartup).then(function (pref_val) {
            resolve(pref_val);
          });
      });
    });
  },

  getShouldOnlyConfigureTorWithPromise: function()
  {
    return new Promise(function (resolve, reject) {
      const kEnvOnlyConfigureTor = "TOR_CONFIGURE_ONLY";
      const kPrefOnlyConfigureTor = "onlyConfigureTor";

      envExistsWithPromise(kEnvOnlyConfigureTor).then(function (exists) {
        if (exists)
          envGetWithPromise(kEnvOnlyConfigureTor).then(function(only_configure) {
            resolve("1" == only_configure);
          });
        else
          prefGetWithPromise(kPrefOnlyConfigureTor).then(function (pref_val) {
            resolve(pref_val);
          });
      });
    });
  },

  // ArrayBuffer conversions ---------------------------------
  // ---------------------------------------------------------
  ab2str: function (buf) {
    return String.fromCharCode.apply(null, new Uint8Array(buf));
  },

  str2ab: function (str) {
    var buf = new ArrayBuffer(str.length); // 2 bytes for each char
    var bufView = new Uint8rray(buf);
    for (var i=0, strLen=str.length; i < strLen; i++) {
      bufView[i] = str.charCodeAt(i);
    }
    return buf;
  }

};
