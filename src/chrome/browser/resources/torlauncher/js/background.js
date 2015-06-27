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

chrome.app.runtime.onLaunched.addListener(function() {
  torlauncher.torProcessService.init();
});

chrome.runtime.onInstalled.addListener(function (details) {
  torlauncher.util.runGenerator(torlauncher.registerBridgePrefs);
});

// Separate aStr at the first colon.  Always return a two-element array.
function parseColonStr(aStr)
{
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
  const kTorConfKeySocks4Proxy = "Socks4Proxy";
  const kTorConfKeySocks5Proxy = "Socks5Proxy";
  const kTorConfKeySocks5ProxyUsername = "Socks5ProxyUsername";
  const kTorConfKeySocks5ProxyPassword = "Socks5ProxyPassword";
  const kTorConfKeyHTTPSProxy = "HTTPSProxy";
  const kTorConfKeyHTTPSProxyAuthenticator = "HTTPSProxyAuthenticator";

  var proxyType, proxyAddrPort, proxyUsername, proxyPassword;

  var reply = yield* torlauncher.protocolService.TorGetConfStr(
      kTorConfKeySocks4Proxy, null);
  console.log('cp 1: ' + JSON.stringify(reply));
  if (!torlauncher.protocolService.TorCommandSucceeded(reply))
    return false;

  if (reply.retVal) {
    proxyType = "SOCKS4";
    proxyAddrPort = reply.retVal;
  }
  else {
    var reply = yield* torlauncher.protocolService.TorGetConfStr(
        kTorConfKeySocks5Proxy, null);
    console.log('cp 2');
    if (!torlauncher.protocolService.TorCommandSucceeded(reply))
      return false;

    if (reply.retVal) {
      proxyType = "SOCKS5";
      proxyAddrPort = reply.retVal;
      var reply = yield* torlauncher.protocolService.TorGetConfStr(
          kTorConfKeySocks5ProxyUsername, null);
      console.log('cp 3');
      if (!torlauncher.protocolService.TorCommandSucceeded(reply))
        return false;

      proxyUsername = reply.retVal;
      var reply = yield* torlauncher.protocolService.TorGetConfStr(
          kTorConfKeySocks5ProxyPassword, null);
      console.log('cp 4');
      if (!torlauncher.protocolService.TorCommandSucceeded(reply))
        return false;

      proxyPassword = reply.retVal;
    }
    else {
      var reply = yield* torlauncher.protocolService.TorGetConfStr(
          kTorConfKeyHTTPSProxy, null);
      console.log('cp 5');
      if (!torlauncher.protocolService.TorCommandSucceeded(reply))
        return false;

      if (reply.retVal) {
        proxyType = "HTTP";
        proxyAddrPort = reply.retVal;
        var reply = yield* torlauncher.protocolService.TorGetConfStr(
                                   kTorConfKeyHTTPSProxyAuthenticator, null);
        console.log('cp 6');
        if (!torlauncher.protocolService.TorCommandSucceeded(reply))
          return false;

        var values = parseColonStr(reply.retVal);
        proxyUsername = values[0];
        proxyPassword = values[1];
      }
    }
  }

  console.log('cp 7');
  proxySettingsOut.haveProxy = (proxyType != undefined);
  proxySettingsOut.proxyType = proxyType;
  if (proxyAddrPort) {
    var values = parseColonStr(proxyAddrPort);
    proxySettingsOut.proxyAddr = values[0];
    proxySettingsOut.proxyPort = values[1];
  }

  proxySettingsOut.proxyUsername = proxyUsername;
  proxySettingsOut.proxyPassword = proxyPassword;

  console.log('cp 8');

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
  catch (e) { console.log("Error in bgPage torlauncher.readTorSettings: " + e + '\n' + e.stack); }

  console.log('torlauncher.readTorSettings*(): didSucceed == ' + (didSucceed ? 'true +++' : 'false !!!'));
  chrome.torlauncher.sendTorNetworkSettingsResult(
      didSucceed ? JSON.stringify(
        { 'proxySettings': proxySettings,
          'firewallSettings': firewallSettings,
          'bridgeSettings': bridgeSettings }) : '{}');
}

torlauncher.getTorNetworkSettingsForBrowserNative = function () {
  torlauncher.util.runGenerator(torlauncher.readTorSettings);
}
