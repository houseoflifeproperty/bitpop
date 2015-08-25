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

const kTorHelperExtensionId = "nnldggpjfmmhhmjoekppejaejalbchbh";

chrome.app.runtime.onLaunched.addListener(function() {
  torlauncher.torProcessService.init();
});

chrome.runtime.onInstalled.addListener(function (details) {
  torlauncher.util.runGenerator(torlauncher.registerBridgePrefs);
});

chrome.runtime.onMessageExternal.addListener(function (message, sender, sendResponse) {
  console.info('sender.id: ' + sender.id);
  if (sender.id == kTorHelperExtensionId) {
    if (message.kind == "getTorStatus") {
      sendResponse(torlauncher.torProcessService.TorProcessStatus);
    } else if (message.kind == "changeExitNodeCountry") {
      if (message.ccode) {
        torlauncher.torProcessService.changeExitNodeCountry(message.ccode);
      }
    }
  }
});

const kTorConfKeyDisableNetwork = "DisableNetwork";
const kTorConfKeySocks4Proxy = "Socks4Proxy";
const kTorConfKeySocks5Proxy = "Socks5Proxy";
const kTorConfKeySocks5ProxyUsername = "Socks5ProxyUsername";
const kTorConfKeySocks5ProxyPassword = "Socks5ProxyPassword";
const kTorConfKeyHTTPSProxy = "HTTPSProxy";
const kTorConfKeyHTTPSProxyAuthenticator = "HTTPSProxyAuthenticator";
const kTorConfKeyReachableAddresses = "ReachableAddresses";
const kTorConfKeyUseBridges = "UseBridges";
const kTorConfKeyBridgeList = "Bridge";

function createColonStr(aStr1, aStr2) {
  var rv = aStr1;
  if (aStr2)
  {
    if (!rv)
      rv = "";
    rv += ':' + aStr2;
  }

  return rv;
}

// Separate aStr at the first colon.  Always return a two-element array.
function parseColonStr(aStr) {
  var rv = ["", ""];
  if (!aStr)
    return rv;

  var idx = aStr.indexOf(":");
  if (idx >= 0)
  {
    if (idx > 0)
      rv[0] = aStr.substring(0, idx);
    rv[1] = aStr.substring(idx + 1);
  }
  else
    rv[0] = aStr;

  return rv;
}

// Returns true if successful.
function *initProxySettings(proxySettingsOut) {
  var proxyType, proxyAddrPort, proxyUsername, proxyPassword;

  var reply = yield* torlauncher.protocolService.TorGetConfStr(
      kTorConfKeySocks4Proxy, null);
  if (!torlauncher.protocolService.TorCommandSucceeded(reply))
    return false;

  if (reply.retVal) {
    proxyType = "SOCKS4";
    proxyAddrPort = reply.retVal;
  }
  else {
    var reply = yield* torlauncher.protocolService.TorGetConfStr(
        kTorConfKeySocks5Proxy, null);
    if (!torlauncher.protocolService.TorCommandSucceeded(reply))
      return false;

    if (reply.retVal) {
      proxyType = "SOCKS5";
      proxyAddrPort = reply.retVal;
      var reply = yield* torlauncher.protocolService.TorGetConfStr(
          kTorConfKeySocks5ProxyUsername, null);
      if (!torlauncher.protocolService.TorCommandSucceeded(reply))
        return false;

      proxyUsername = reply.retVal;
      var reply = yield* torlauncher.protocolService.TorGetConfStr(
          kTorConfKeySocks5ProxyPassword, null);
      if (!torlauncher.protocolService.TorCommandSucceeded(reply))
        return false;

      proxyPassword = reply.retVal;
    }
    else {
      var reply = yield* torlauncher.protocolService.TorGetConfStr(
          kTorConfKeyHTTPSProxy, null);
      if (!torlauncher.protocolService.TorCommandSucceeded(reply))
        return false;

      if (reply.retVal) {
        proxyType = "HTTP";
        proxyAddrPort = reply.retVal;
        var reply = yield* torlauncher.protocolService.TorGetConfStr(
                                   kTorConfKeyHTTPSProxyAuthenticator, null);
        if (!torlauncher.protocolService.TorCommandSucceeded(reply))
          return false;

        var values = parseColonStr(reply.retVal);
        proxyUsername = values[0];
        proxyPassword = values[1];
      }
    }
  }

  proxySettingsOut.haveProxy = (proxyType != undefined);
  proxySettingsOut.proxyType = proxyType;
  if (proxyAddrPort) {
    var values = parseColonStr(proxyAddrPort);
    proxySettingsOut.proxyAddr = values[0];
    proxySettingsOut.proxyPort = values[1];
  }

  proxySettingsOut.proxyUsername = proxyUsername;
  proxySettingsOut.proxyPassword = proxyPassword;

  return true;
} // initProxySettings


// Returns true if successful.
function *initFirewallSettings(firewallSettingsOut) {
  const kTorConfKeyReachableAddresses = "ReachableAddresses";

  var allowedPorts;
  var reply = yield* torlauncher.protocolService.TorGetConfStr(
      kTorConfKeyReachableAddresses, null);
  if (!torlauncher.protocolService.TorCommandSucceeded(reply))
    return false;

  if (reply.retVal) {
    var portStrArray = reply.retVal.split(',');
    for (var i = 0; i < portStrArray.length; i++) {
      var values = parseColonStr(portStrArray[i]);
      if (values[1]) {
        if (allowedPorts)
          allowedPorts += ',' + values[1];
        else
          allowedPorts = values[1];
      }
    }
  }

  var haveFirewall = (allowedPorts != undefined);
  firewallSettingsOut.haveFirewall = haveFirewall;
  if (allowedPorts)
    firewallSettingsOut.allowedPorts = allowedPorts;

  return true;
}

function setBridgeListElemValue(aBridgeArray) {
  // To be consistent with bridges.torproject.org, pre-pend "bridge" to
  // each line as it is displayed in the UI.
  var bridgeList = [];
  if (aBridgeArray)
  {
    for (var i = 0; i < aBridgeArray.length; ++i)
    {
      var s = aBridgeArray[i].trim();
      if (s.length > 0)
      {
        if (s.toLowerCase().indexOf("bridge") !== 0)
          s = "bridge " + s;
        bridgeList.push(s);
      }
    }
  }

  return bridgeList;
}

// Returns true if successful.
function *initBridgeSettings(bridgeSettingsOut) {
  const kTorConfKeyUseBridges = "UseBridges";
  const kTorConfKeyBridgeList = "Bridge";

  const kPrefDefaultBridgeType = "defaultBridgeType";
  const kPrefDefaultBridgeRecommendedType = "defaultBridgeRecommendedType";

  var typeList = yield *torlauncher.util.defaultBridgeTypes();
  var canUseDefaultBridges = (typeList && (typeList.length > 0));
  var defaultType = yield torlauncher.util.prefGet(kPrefDefaultBridgeType);
  var useDefault = canUseDefaultBridges && !!defaultType;

  // If not configured to use a default set of bridges, get UseBridges setting
  // from tor.
  var useBridges = useDefault;
  var bridgeList = null;
  if (!useDefault) {
    var reply = yield* torlauncher.protocolService.TorGetConfBool(
        kTorConfKeyUseBridges, false);
    if (!torlauncher.protocolService.TorCommandSucceeded(reply))
      return false;

    useBridges = reply.retVal;

    // Get bridge list from tor.
    var bridgeReply = yield* torlauncher.protocolService.TorGetConf(
        kTorConfKeyBridgeList);
    if (!torlauncher.protocolService.TorCommandSucceeded(bridgeReply))
      return false;

    bridgeList = setBridgeListElemValue(bridgeReply.lineArray);
    if (!(bridgeList.length > 0)) {
      if (canUseDefaultBridges)
        useDefault = true;  // We have no custom values... back to default.
      else
        useBridges = false; // No custom or default bridges are available.
    }
  }

  bridgeSettingsOut.useBridges = useBridges;
  bridgeSettingsOut.canUseDefaultBridges = canUseDefaultBridges;
  bridgeSettingsOut.useDefault = useDefault;
  if (typeList && (typeList.length > 0)) {
    bridgeSettingsOut.typeList = typeList;
  }
  if (!!defaultType)
    bridgeSettingsOut.defaultType = defaultType;
  bridgeSettingsOut.recommendedType =
      yield torlauncher.util.prefGet(kPrefDefaultBridgeRecommendedType);
  const key = "recommended_bridge";
  bridgeSettingsOut.recommendedBridgeMenuItemLabelSuffix =
      torlauncher.util.getLocalizedString(key);
  if (bridgeList && bridgeList.length > 0)
    bridgeSettingsOut.bridgeList = bridgeList;

  return true;
}

torlauncher.readTorSettings = function* () {
  var didSucceed = false;
  var proxySettings = {};
  var firewallSettings = {};
  var bridgeSettings = {};

  try {
    // TODO: retrieve > 1 key at one time inside initProxySettings() et al.
    didSucceed = (yield *initProxySettings(proxySettings)) &&
                 (yield *initFirewallSettings(firewallSettings)) &&
                 (yield *initBridgeSettings(bridgeSettings));
  }
  catch (e) { console.info("Error in bgPage torlauncher.readTorSettings: " + e + '\n' + e.stack); }

  console.info('torlauncher.readTorSettings*(): didSucceed == ' + (didSucceed ? 'true +++' : 'false !!!'));
  chrome.torlauncher.sendTorNetworkSettingsResult(
      didSucceed ? JSON.stringify(
        { 'proxySettings': proxySettings,
          'firewallSettings': firewallSettings,
          'bridgeSettings': bridgeSettings }) : '{}');
}

torlauncher.getTorNetworkSettingsForBrowserNative = function () {
  torlauncher.util.runGenerator(torlauncher.readTorSettings);
};

// Returns true if settings were successfully applied.
function *applyProxySettings(proxySettings)
{
  var settings = yield *getAndValidateProxySettings(proxySettings);
  if (!settings) {
    return false;
  }

  return (yield *setConfAndReportErrors(settings));
}


// Return a settings object if successful and null if not.
function *getAndValidateProxySettings(proxySettings) {
  // TODO: validate user-entered data.  See Vidalia's NetworkPage::save()

  var settings = {};
  settings[kTorConfKeySocks4Proxy] = null;
  settings[kTorConfKeySocks5Proxy] = null;
  settings[kTorConfKeySocks5ProxyUsername] = null;
  settings[kTorConfKeySocks5ProxyPassword] = null;
  settings[kTorConfKeyHTTPSProxy] = null;
  settings[kTorConfKeyHTTPSProxyAuthenticator] = null;

  if (!proxySettings)
    return settings;

  var proxyType, proxyAddrPort, proxyUsername, proxyPassword;
  if (proxySettings.haveProxy) {
    proxyAddrPort = createColonStr(proxySettings.proxyAddr,
                                   proxySettings.proxyPort);
    if (!proxyAddrPort) {
      console.info('!proxyAddrPort');
      reportValidationError("error_proxy_addr_missing");
      return null;
    }

    console.info(proxyAddrPort);

    proxyType = proxySettings.proxyType;
    console.info('proxyType: ' + proxyType);
    if (!proxyType) {
      reportValidationError("error_proxy_type_missing");
      return null;
    }

    if ("SOCKS4" != proxyType) {
      proxyUsername = proxySettings.proxyUsername;
      proxyPassword = proxySettings.proxyPassword;
    }
  }

  if ("SOCKS4" == proxyType) {
    settings[kTorConfKeySocks4Proxy] = proxyAddrPort;
  }
  else if ("SOCKS5" == proxyType) {
    settings[kTorConfKeySocks5Proxy] = proxyAddrPort;
    settings[kTorConfKeySocks5ProxyUsername] = proxyUsername;
    settings[kTorConfKeySocks5ProxyPassword] = proxyPassword;
  }
  else if ("HTTP" == proxyType) {
    settings[kTorConfKeyHTTPSProxy] = proxyAddrPort;
    // TODO: Does any escaping need to be done?
    settings[kTorConfKeyHTTPSProxyAuthenticator] =
                                  createColonStr(proxyUsername, proxyPassword);
  }

  console.info(JSON.stringify(settings));
  return settings;
} // getAndValidateProxySettings

// Returns true if settings were successfully applied.
function *applyFirewallSettings(firewallSettings) {
  var settings = getAndValidateFirewallSettings(firewallSettings);
  if (!settings)
    return false;

  return (yield *setConfAndReportErrors(settings));
}


// Return a settings object if successful and null if not.
// Not used for the wizard.
function getAndValidateFirewallSettings(firewallSettings) {
  // TODO: validate user-entered data.  See Vidalia's NetworkPage::save()

  var settings = {};
  settings[kTorConfKeyReachableAddresses] = null;

  if (!firewallSettings)
      return settings;

  var allowedPorts = firewallSettings.firewallAllowedPorts;

  return constructFirewallSettings(allowedPorts);
}

function constructFirewallSettings(aAllowedPorts) {
  var settings = {};
  settings[kTorConfKeyReachableAddresses] = null;

  if (aAllowedPorts) {
    var portsConfStr;;
    var portsArray = aAllowedPorts.split(',');
    for (var i = 0; i < portsArray.length; ++i) {
      var s = portsArray[i].trim();
      if (s.length > 0) {
        if (!portsConfStr)
          portsConfStr = "*:" + s;
        else
          portsConfStr += ",*:" + s;
      }
    }

    if (portsConfStr)
      settings[kTorConfKeyReachableAddresses] = portsConfStr;
  }

  return settings;
}

// Returns true if settings were successfully applied.
function *applyBridgeSettings(bridgeSettings) {
  var settings = yield *getAndValidateBridgeSettings(bridgeSettings);
  if (!settings)
    return false;

  return (yield *setConfAndReportErrors(settings));
}


// Return a settings object if successful and null if not.
function *getAndValidateBridgeSettings(bridgeSettings) {
  var settings = {};
  settings[kTorConfKeyUseBridges] = null;
  settings[kTorConfKeyBridgeList] = null;

  if (!bridgeSettings)
    return settings;

  var useBridges = bridgeSettings.useBridges;
  var defaultBridgeType;
  var bridgeList;
  if (useBridges) {
    var useCustom = !bridgeSettings.useDefault;
    if (useCustom) {
      var bridgeStr = bridgeSettings.bridgeList;
      bridgeList = parseAndValidateBridges(bridgeStr);
      if (!bridgeList) {
        reportValidationError("error_bridges_missing");
        return null;
      }
    }
    else {
      defaultBridgeType = bridgeSettings.defaultType;
      if (!defaultBridgeType) {
        reportValidationError("error_default_bridges_type_missing");
        return null;
      }
    }
  }

  // Since it returns a filterd list of bridges, TorLauncherUtil.defaultBridges
  // must be called after setting the kPrefDefaultBridgeType pref.
  yield torlauncher.util.setPref('defaultBridgeType', defaultBridgeType || "");
  if (defaultBridgeType)
    bridgeList = yield *torlauncher.util.defaultBridges();

  if (useBridges && bridgeList) {
    settings[kTorConfKeyUseBridges] = true;
    settings[kTorConfKeyBridgeList] = bridgeList;
  }

  return settings;
}

// Returns an array or null.
function parseAndValidateBridges(aStr) {
  if (!aStr)
    return null;

  var resultStr = aStr;
  resultStr = resultStr.replace(/bridge/gi, ""); // Remove "bridge" everywhere.
  resultStr = resultStr.replace(/\r\n/g, "\n");  // Convert \r\n pairs into \n.
  resultStr = resultStr.replace(/\r/g, "\n");    // Convert \r into \n.
  resultStr = resultStr.replace(/\n\n/g, "\n");  // Condense blank lines.

  var resultArray = new Array;
  var tmpArray = resultStr.split('\n');
  for (var i = 0; i < tmpArray.length; i++) {
    var s = tmpArray[i].trim(); // Remove extraneous whitespace.
    resultArray.push(s);
  }

  return (0 === resultArray.length) ? null : resultArray;
}


// Returns true if successful.
// aShowOnErrorPanelID is only used when displaying the wizard.
function *setConfAndReportErrors(aSettingsObj) {
  var errObj = {};
  var didSucceed = yield *torlauncher.protocolService.TorSetConfWithReply(
      aSettingsObj, errObj);
  if (!didSucceed) {
    showSaveSettingsAlert(errObj.details);
  }

  return didSucceed;
}

function showSaveSettingsAlert(aDetails) {
  if (!aDetails)
    aDetails = torlauncher.util.getLocalizedString("ensure_tor_is_running");

  var s = torlauncher.util.getFormattedLocalizedString(
            "failed_to_save_settings", [aDetails], 1);

  chrome.torlauncher.notifyTorSaveSettingsError(s);
}

function reportValidationError(aStrKey) {
  showSaveSettingsAlert(torlauncher.util.getLocalizedString(aStrKey));
}

function *useSettings(callbackAfter) {
  var settings = {};
  settings[kTorConfKeyDisableNetwork] = false;
  try {
    var unusedSuccess = yield *setConfAndReportErrors(settings);
    console.info('Before SAVECONF ------------------------------------------');
    //torlauncher.util.pr_debug('network-settings.useSettings: after setConfAnd...');
    var reply = torlauncher.protocolService.TorSendCommand("SAVECONF");
    torlauncher.torProcessService.TorClearBootstrapError();

    gIsBootstrapComplete = torlauncher.torProcessService.TorIsBootstrapDone;
    if (!gIsBootstrapComplete) {
      yield openProgressDialog();
      if (!gIsBootstrapComplete) {
        chrome.torlauncher.notifyTorSaveSettingsError("Failed to run the bootstrap process.");
      } else {
        chrome.torlauncher.notifyTorSaveSettingsSuccess();
      }
    }

  } catch (e) {
    chrome.torlauncher.notifyTorSaveSettingsError(e.message);
  }
}

function openProgressDialog()
{
  return new Promise(function (resolve, reject) {
    var chromeURL = "progress.html";

    chrome.app.window.create(chromeURL, {
      id: torlauncher.torProcessService.kProgressDialogWindowId,
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
    }, function (createdWindow) {
      // pass window creation arguments
      createdWindow.contentWindow.windowArgs = {
        isBrowserStartup: false,
        openerCallbackFunc: onProgressDialogClose
      };

      createdWindow.onClosed.addListener(function () {
        resolve();
      });
    });
  });
}


function onProgressDialogClose(aBootstrapCompleted) {
  gIsBootstrapComplete = aBootstrapCompleted;
}

torlauncher.saveTorSettings = function* () {
  var didSucceed = false;
  try {
    didSucceed = (yield *applyProxySettings(gSettingsToSave.proxySettings)) &&
                 (yield *applyFirewallSettings(gSettingsToSave.firewallSettings)) &&
                 (yield *applyBridgeSettings(gSettingsToSave.bridgeSettings));
  }
  catch (e) { console.info("Error in applySettings: " + e + '\n' + e.stack); }
  if (didSucceed)
    yield *useSettings();

  gIsSaving = false;
};

gIsSaving = false;
gSettingsToSave = null;

torlauncher.saveNetworkSettings = function (settings_json_string) {
  if (!gIsSaving) {
    gSettingsToSave = JSON.parse(settings_json_string);
    console.info('===========================================');
    console.info('= gSettingsToSave:');
    console.info(JSON.stringify(gSettingsToSave));
    console.info('===========================================');
    gIsSaving = true;
    torlauncher.util.runGenerator(torlauncher.saveTorSettings);
  }
};
