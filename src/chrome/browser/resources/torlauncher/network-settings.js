// BitPop browser. Tor launcher integration part.
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

window.addEventListener(
  'load',
  function (ev) {
    initDialog();
  },
  false);

const kSupportAddr = "support@bitpop.com";

const kTorProcessReadyTopic = "TorProcessIsReady";
const kTorProcessExitedTopic = "TorProcessExited";
const kTorProcessDidNotStartTopic = "TorProcessDidNotStart";
const kTorOpenProgressTopic = "TorOpenProgressDialog";
const kTorBootstrapErrorTopic = "TorBootstrapError";
const kTorLogHasWarnOrErrTopic = "TorLogHasWarnOrErr";

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

var gProtocolSvc = null;
var gTorProcessService = null;
var gIsInitialBootstrap = false;
var gIsBootstrapComplete = false;
var gRestoreAfterHelpPanelID = null;
var gActiveTopics = [];  // Topics for which an observer is currently installed.

function initDialog()
{
  gDialogHelper = new torlauncher.UIHelper();

  //torlauncher.util.pr_debug("UI language: " + chrome.i18n.getUILanguage());
  torlauncher.util.localizePage();
  document.title = torlauncher.util.translate('torsettings.dialog.title');

  chrome.runtime.getPlatformInfo(function (info) {
    if (info.os == 'win')
      document.documentElement.setAttribute("class", "os-windows");

    var forAssistance = document.getElementById("forAssistance");
    if (forAssistance) {
      forAssistance.textContent = torlauncher.util.getFormattedLocalizedString(
                                          "forAssistance", [kSupportAddr], 1);
    }

    var cancelBtn = document.getElementById("cancelButton");
    gIsInitialBootstrap = window.windowArgs.isInitialBootstrap;

    var startAtPanel;
    if (window.windowArgs.startAtWizardPanel != undefined)
      startAtPanel = window.windowArgs.startAtWizardPanel;

    if (gIsInitialBootstrap) {
      if (cancelBtn) {
        if (info.os == 'win')
          cancelBtn.innerText = torlauncher.util.getLocalizedString("quit_win");
        else
          cancelBtn.innerText = torlauncher.util.getLocalizedString("quit");
      }

      var okBtn = document.getElementById("acceptButton");
      if (okBtn)
        okBtn.innerText = torlauncher.util.getLocalizedString("connect");
    }

    chrome.runtime.getBackgroundPage(function (backgroundPage) {
      //torlauncher.util.pr_debug('network-settings: Got background page.');
      gProtocolSvc = backgroundPage.torlauncher.protocolService;
      gProtocolSvc.initPromise.then(
        function () {
          //torlauncher.util.pr_debug('network-settings: gProtocolSvc.initPromise resolved');
          gTorProcessService = backgroundPage.torlauncher.torProcessService;

          var wizardElem = getWizard();
          var haveWizard = (wizardElem !== null);
          //torlauncher.util.pr_debug('network-settings: haveWizard == ' + (haveWizard ? 'true' : 'false'));
          if (haveWizard) {
            if (gDialogHelper.currentPage.pageid == "first") {
              showWizardNavButtons(false);
            }

            // Set "Copy Tor Log" label and move it after the Quit (cancel) button.
            var copyLogBtn = document.getElementById("extra2Button");
            if (copyLogBtn) {
              copyLogBtnTitle = wizardElem.getAttribute("buttonlabelextra2");
              copyLogBtn.innerHTML += copyLogBtnTitle;
            }

            if (gTorProcessService.TorBootstrapErrorOccurred ||
                gProtocolSvc.TorLogHasWarnOrErr) {
              showCopyLogButton(true);
            }

            // Use "Connect" as the finish button label (on the last wizard page)..
            var finishBtn = document.getElementById("finishButton");
            if (finishBtn)
              finishBtn.innerText = torlauncher.util.getLocalizedString("connect");

            // Add label and access key to Help button.
            var helpBtn = document.getElementById("helpButton");
            // if (helpBtn) {
              // TODO: make necessary changes for help button in the wizard
              // var strBundle = Cc["@mozilla.org/intl/stringbundle;1"]
              //               .getService(Ci.nsIStringBundleService)
              //               .createBundle("chrome://global/locale/dialog.properties");
              // helpBtn.setAttribute("label", strBundle.GetStringFromName("button-help"));
              // var accessKey = strBundle.GetStringFromName("accesskey-help");
              // if (accessKey)
              //   helpBtn.setAttribute("accesskey", accessKey);
            // }
          }

          // initDefaultBridgeTypeMenu();

          //torlauncher.util.pr_debug('network-settings: adding onMessage listener');
          chrome.runtime.onMessage.addListener(onMessage);

          //torlauncher.util.pr_debug("network-settings: adding observers");
          addObserver(kTorBootstrapErrorTopic);
          addObserver(kTorLogHasWarnOrErrTopic);
          addObserver(kTorProcessExitedTopic);
          addObserver(kTorOpenProgressTopic);

          //torlauncher.util.pr_debug("network-settings: adding 'click' event listeners");
          document.getElementById("acceptButton").addEventListener(
              'click', applySettings, false);
          document.getElementById("cancelButton").addEventListener(
              'click', onCancel, false);
          document.getElementById("restartTorButton").addEventListener(
              'click', onRestartTor, false);
          document.getElementById('connectButton').addEventListener(
              'click', useSettings, false);
          document.getElementById('extra2Button').addEventListener(
              'click', onCopyLog, false);

          var status = gTorProcessService.TorProcessStatus;
          //torlauncher.util.pr_debug("gTorProcessService.TorProcessStatus: " +
          //    JSON.stringify(gTorProcessService.TorProcessStatus));
          torlauncher.util.getShouldStartAndOwnTorWithPromise().then(
            function (shouldStartAndOwnTor) {
              //torlauncher.util.pr_debug("network=settings: shouldStartAndOwnTor: " +
              //    JSON.stringify(shouldStartAndOwnTor));
              if (shouldStartAndOwnTor &&
                 (status != gTorProcessService.kStatusRunning)) {
                if (status == gTorProcessService.kStatusExited)
                  showErrorMessage(true, null);
                else
                  showStartingTorPanel();

                //torlauncher.util.pr_debug(
                //    'network=settings: addObserver for TorProcessReady and TorProcessDidNotStart');
                addObserver(kTorProcessReadyTopic);
                addObserver(kTorProcessDidNotStartTopic);
              }
              else {
                readTorSettings();

                if (startAtPanel)
                  advanceToWizardPanel(startAtPanel);
                else
                  showPanel();
              }

              // Resize this window to fit content.  sizeToContent() alone will not do
              // the job (it has many limitations and it is buggy).
              // TODO: account for the following code
              // sizeToContent();
              // let w = maxWidthOfContent();
              // if (w)
              // {
              //   let windowFrameWidth = window.outerWidth - window.innerWidth;
              //   w += windowFrameWidth;

              //   if (w > window.outerWidth)
              //     window.resizeTo(w, window.outerHeight);
              // }

              console.info("initDialog done");
            }
          );
        }
      );
    });
  });
}

function getWizard()
{
  return gDialogHelper.WizardElem;
}

function showWizardNavButtons(aShowBtns)
{
  showOrHideButton("backButton", aShowBtns, false);
  showOrHideButton("nextButton", aShowBtns, false);
}

function onMessage(msg) {
  var aTopic = msg.kind;

  // do not execute observer handlers if removed
  if (gActiveTopics.indexOf(aTopic) < 0)
    return;

  if ((kTorBootstrapErrorTopic == aTopic) ||
       (kTorLogHasWarnOrErrTopic == aTopic)) {
    showCopyLogButton(true);
    return;
  }

  if (kTorProcessReadyTopic == aTopic) {
    removeObserver(kTorProcessReadyTopic);
    removeObserver(kTorProcessDidNotStartTopic);
    var haveWizard = (getWizard() !== null);
    showPanel();
    if (haveWizard) {
      showOrHideButton("backButton", true, false);
      showOrHideButton("nextButton", true, false);
    }
    readTorSettings();
  } else if (kTorProcessDidNotStartTopic == aTopic) {
    removeObserver(kTorProcessReadyTopic);
    removeObserver(kTorProcessDidNotStartTopic);
    showErrorMessage(false, aData);
  } else if (kTorProcessExitedTopic == aTopic) {
    removeObserver(kTorProcessExitedTopic);
    showErrorMessage(true, null);
  } else if (kTorOpenProgressTopic == aTopic) {
    openProgressDialog();
  }
}

// addObserver() will not add two observers for the same topic.
function addObserver(aTopic) {
  if (gActiveTopics.indexOf(aTopic) < 0) {
    gActiveTopics.push(aTopic);
  }
}


function removeObserver(aTopic) {
  var idx = gActiveTopics.indexOf(aTopic);
  if (idx >= 0) {
    gActiveTopics.splice(idx, 1);
  }
}


function removeAllObservers() {
  gActiveTopics = [];
}

function readTorSettings()
{
  torlauncher.util.pr_debug('network=settings: readTorSettings ' +
                            '-----------------------------------------------');
  // TorLauncherLogger.log(2, "readTorSettings " +
  //                           "----------------------------------------------");

  // var didSucceed = false;
  // try
  // {
  //   // TODO: retrieve > 1 key at one time inside initProxySettings() et al.
  //   didSucceed = initProxySettings() && initFirewallSettings() &&
  //                initBridgeSettings();
  // }
  // catch (e) { TorLauncherLogger.safelog(4, "Error in readTorSettings: ", e); }

  // if (!didSucceed)
  // {
  //   // Unable to communicate with tor.  Hide settings and display an error.
  //   showErrorMessage(false, null);

  //   setTimeout(function()
  //       {
  //         var details = TorLauncherUtil.getLocalizedString(
  //                                         "ensure_tor_is_running");
  //         var s = TorLauncherUtil.getFormattedLocalizedString(
  //                                     "failed_to_get_settings", [details], 1);
  //         TorLauncherUtil.showAlert(window, s);
  //         close();
  //       }, 0);
  // }
  // TorLauncherLogger.log(2, "readTorSettings done");
}


// If aPanelID is undefined, the first panel is displayed.
function showPanel(aPanelID)
{
  var wizard = getWizard();
  if (!aPanelID)
    aPanelID = (wizard) ? "first" : "settings";

  var deckElem = document.getElementById("deck");
  if (deckElem)
    setSelectedDeckPanel(deckElem, aPanelID);
  else if (wizard.currentPage.pageid != aPanelID)
    gDialogHelper.goTo(aPanelID);

  showOrHideButton("acceptButton", (aPanelID == "settings"), true);
}

function setSelectedDeckPanel(deckElem, aPanelID) {
  if (deckElem.children.length) {
    var children = deckElem.children;
    for (var i = 0; i < children.length; i++) {
      if (children[i].id == aPanelID)
        children[i].removeAttribute('hidden');
      else
        children[i].setAttribute('hidden', 'true');
    }
  }
}

// This function assumes that you are starting on the first page.
function advanceToWizardPanel(aPanelID) {
  var wizard = getWizard();
  if (!wizard)
    return;

  onWizardConfigure(); // Equivalent to pressing "Configure"

  const kMaxTries = 10;
  for (var count = 0;
       ((count < kMaxTries) &&
        (gDialogHelper.currentPage.pageid != aPanelID) &&
        gDialogHelper.canAdvance);
       ++count) {
    gDialogHelper.advance();
  }
}


function showStartingTorPanel() {
  var haveWizard = (getWizard() !== null);
  if (haveWizard) {
    showOrHideButton("backButton", false, false);
    showOrHideButton("nextButton", false, false);
  }

  showPanel("startingTor");
}


function showErrorMessage(aTorExited, aErrorMsg)
{
  var elem = document.getElementById("errorPanelMessage");
  var btn = document.getElementById("restartTorButton");
  if (aTorExited) {
    // Show "Tor exited" message and "Restart Tor" button.
    aErrorMsg = torlauncher.util.getLocalizedString("tor_exited") +
        "\n\n" + torlauncher.util.getLocalizedString("tor_exited2");

    if (btn)
      btn.removeAttribute("hidden");
    if (elem)
      elem.style.textAlign = "start";
  } else {
    if (btn)
      btn.setAttribute("hidden", true);
    if (elem)
      elem.style.textAlign = "center";
  }

  if (elem)
    elem.textContent = (aErrorMsg) ? aErrorMsg : "";

  showPanel("errorPanel");

  var haveWizard = (getWizard() !== null);
  if (haveWizard) {
    showOrHideButton("backButton", false, false);
    showOrHideButton("nextButton", false, false);
  }

  var haveErrorOrWarning = (gTorProcessService.TorBootstrapErrorOccurred ||
                            gProtocolSvc.TorLogHasWarnOrErr);
  showCopyLogButton(haveErrorOrWarning);
}


function showCopyLogButton(aHaveErrorOrWarning)
{
  torlauncher.util.pr_debug('network-settings: showCopyLogButton');
  var copyLogBtn = document.getElementById("extra2Button");
  if (copyLogBtn)
  {
    var haveWizard = (getWizard() !== null);
    if (haveWizard)
      copyLogBtn.setAttribute("wizardCanCopyLog", true);

    if (!gRestoreAfterHelpPanelID)
      copyLogBtn.removeAttribute("hidden"); // Show button if help is not open.

    if (aHaveErrorOrWarning) {
      var warningIcon = document.getElementById('warningIcon');
      if (warningIcon.hasAttribute('hidden'))
        warningIcon.removeAttribute('hidden');
    }
  }
}


function restoreCopyLogVisibility()
{
  var copyLogBtn = document.getElementById("extra2Button");
  if (!copyLogBtn)
    return;

  // Always show button in non-wizard case; conditionally in wizard.
  if (!getWizard() || copyLogBtn.hasAttribute("wizardCanCopyLog"))
    copyLogBtn.removeAttribute("hidden");
  else
    copyLogBtn.setAttribute("hidden", true);
}


function showOrHideButton(aID, aShow, aFocus)
{
  var btn = setButtonAttr(aID, "hidden", !aShow);
  if (btn && aFocus)
    btn.focus();
}


// Returns the button element (if found).
function enableButton(aID, aEnable)
{
  return setButtonAttr(aID, "disabled", !aEnable);
}


// Returns the button element (if found).
function setButtonAttr(aID, aAttr, aValue)
{
  if (!aID || !aAttr)
    return null;

  var btn = document.getElementById(aID);
  if (btn) {
    if (aValue)
      btn.setAttribute(aAttr, aValue);
    else
      btn.removeAttribute(aAttr);
  }

  return btn;
}


// Enables / disables aID as well as optional aID+"Label" element.
function enableElemWithLabel(aID, aEnable)
{
  if (!aID)
    return;

  var elem = document.getElementById(aID);
  if (elem)
  {
    var label = document.getElementById(aID + "Label");
    if (aEnable)
    {
      if (label)
        label.removeAttribute("disabled");

      elem.removeAttribute("disabled");
    }
    else
    {
      if (label)
        label.setAttribute("disabled", true);

      elem.setAttribute("disabled", true);
    }
  }
}


// Removes placeholder text when disabled.
function enableTextBox(aID, aEnable)
{
  enableElemWithLabel(aID, aEnable);
  var textbox = document.getElementById(aID);
  if (textbox)
  {
    if (aEnable)
    {
      var s = textbox.getAttribute("origPlaceholder");
      if (s)
        textbox.setAttribute("placeholder", s);
    }
    else
    {
      textbox.setAttribute("origPlaceholder", textbox.placeholder);
      textbox.removeAttribute("placeholder");
    }
  }
}


function overrideButtonLabel(aID, aLabelKey)
{
  var btn = document.documentElement.getButton(aID);
  if (btn)
  {
    btn.setAttribute("origLabel", btn.label);
    btn.label = TorLauncherUtil.getLocalizedString(aLabelKey);
  }
}


function restoreButtonLabel(aID)
{
  var btn = document.documentElement.getButton(aID);
  if (btn)
  {
    var oldLabel = btn.getAttribute("origLabel");
    if (oldLabel)
    {
      btn.label = oldLabel;
      btn.removeAttribute("origLabel");
    }
  }
}


// function onProxyTypeChange()
// {
//   var proxyType = getElemValue(kProxyTypeMenulist, null);
//   var mayHaveCredentials = (proxyType != "SOCKS4");
//   enableTextBox(kProxyUsername, mayHaveCredentials);
//   enableTextBox(kProxyPassword, mayHaveCredentials);
// }


// Called when user clicks "Restart Tor" button after tor unexpectedly quits.
function onRestartTor()
{
  // Re-add these observers in case they have been removed.
  addObserver(kTorProcessReadyTopic);
  addObserver(kTorProcessDidNotStartTopic);
  addObserver(kTorProcessExitedTopic);

  gTorProcessService._startTor().then(
    function () {
      gTorProcessService._controlTor();
    }
  );
}


function onCancel()
{
  if (gRestoreAfterHelpPanelID) // Is help open?
  {
    closeHelp();
    return false;
  }

  if (gIsInitialBootstrap) {
    chrome.runtime.getBackgroundPage(function (bgPage) {
      bgPage.torlauncher.torProcessService.onNetworkSettingsClose(true, false);
      window.close();
    });
    return true;
  }

  chrome.runtime.getBackgroundPage(function (bgPage) {
    bgPage.torlauncher.torProcessService.onNetworkSettingsClose(false, false);
    window.close();
  });

  return true;
}

function copyTextToClipboard(text) {
    var tmpNode = document.createElement('div');
    tmpNode.innerText = text;
    tmpNode.style.webkitUserSelect = 'text';
    tmpNode.style.webkitUserFocus = 'normal';
    document.body.appendChild(tmpNode);

    // Back up previous selection
    var selection = window.getSelection();
    var backupRange;
    if (selection.rangeCount) {
      backupRange = selection.getRangeAt(0).cloneRange();
    }

    // Copy the contents
    var copyFrom = document.createRange();
    copyFrom.selectNodeContents(tmpNode);
    selection.removeAllRanges();
    selection.addRange(copyFrom);
    document.execCommand('copy');

    // Clean-up
    tmpNode.parentNode.removeChild(tmpNode);

    // Restore selection
    selection = window.getSelection();
    selection.removeAllRanges();
    if (backupRange) {
      selection.addRange(backupRange);
    }
}

function onCopyLog() {
  // Copy tor log messages to the system clipboard.
  var countObj = { value: 0 };
  copyTextToClipboard(gProtocolSvc.TorGetLog(countObj));

  // Display a feedback popup that fades away after a few seconds.
  var forAssistance = document.getElementById("forAssistance");
  var panel = document.getElementById("copyLogFeedbackPanel");
  if (forAssistance && panel) {
    panel.firstChild.textContent = torlauncher.util.getFormattedLocalizedString(
                                     "copiedNLogMessages", [countObj.value], 1);
    $(panel).show(400).delay(2000).hide(400);
    //let rectObj = forAssistance.getBoundingClientRect();
    //panel.openPopup(null, null, rectObj.left, rectObj.top, false, false);
  }

  // // Display a feedback popup that fades away after a few seconds.
  // let forAssistance = document.getElementById("forAssistance");
  // let panel = document.getElementById("copyLogFeedbackPanel");
  // if (forAssistance && panel)
  // {
  //   panel.firstChild.textContent = TorLauncherUtil.getFormattedLocalizedString(
  //                                    "copiedNLogMessages", [countObj.value], 1);
  //   let rectObj = forAssistance.getBoundingClientRect();
  //   panel.openPopup(null, null, rectObj.left, rectObj.top, false, false);
  // }
}


function closeCopyLogFeedbackPanel()
{
  // let panel = document.getElementById("copyLogFeedbackPanel");
  // if (panel && (panel.state =="open"))
  //   panel.hidePopup();
}


function onOpenHelp()
{
  // if (gRestoreAfterHelpPanelID) // Already open?
  //   return;

  // var deckElem = document.getElementById("deck");
  // if (deckElem)
  //   gRestoreAfterHelpPanelID = deckElem.selectedPanel.id;
  // else
  //   gRestoreAfterHelpPanelID = getWizard().currentPage.pageid;

  // showPanel("bridgeHelp");

  // showOrHideButton("extra2", false, false); // Hide "Copy Tor Log To Clipboard"

  // if (getWizard())
  // {
  //   showOrHideButton("cancel", false, false);
  //   showOrHideButton("back", false, false);
  //   overrideButtonLabel("next", "done");
  //   var forAssistance = document.getElementById("forAssistance");
  //   if (forAssistance)
  //     forAssistance.setAttribute("hidden", true);
  // }
  // else
  //   overrideButtonLabel("cancel", "done");
}


function closeHelp()
{
  // if (!gRestoreAfterHelpPanelID)  // Already closed?
  //   return;

  // restoreCopyLogVisibility();

  // if (getWizard())
  // {
  //   showOrHideButton("cancel", true, false);
  //   showOrHideButton("back", true, false);
  //   restoreButtonLabel("next");
  //   var forAssistance = document.getElementById("forAssistance");
  //   if (forAssistance)
  //     forAssistance.removeAttribute("hidden");
  // }
  // else
  //   restoreButtonLabel("cancel");

  // showPanel(gRestoreAfterHelpPanelID);
  // gRestoreAfterHelpPanelID = null;
}


// Returns true if successful.
function initProxySettings()
{
  // var proxyType, proxyAddrPort, proxyUsername, proxyPassword;
  // var reply = gProtocolSvc.TorGetConfStr(kTorConfKeySocks4Proxy, null);
  // if (!gProtocolSvc.TorCommandSucceeded(reply))
  //   return false;

  // if (reply.retVal)
  // {
  //   proxyType = "SOCKS4";
  //   proxyAddrPort = reply.retVal;
  // }
  // else
  // {
  //   var reply = gProtocolSvc.TorGetConfStr(kTorConfKeySocks5Proxy, null);
  //   if (!gProtocolSvc.TorCommandSucceeded(reply))
  //     return false;

  //   if (reply.retVal)
  //   {
  //     proxyType = "SOCKS5";
  //     proxyAddrPort = reply.retVal;
  //     var reply = gProtocolSvc.TorGetConfStr(kTorConfKeySocks5ProxyUsername,
  //                                            null);
  //     if (!gProtocolSvc.TorCommandSucceeded(reply))
  //       return false;

  //     proxyUsername = reply.retVal;
  //     var reply = gProtocolSvc.TorGetConfStr(kTorConfKeySocks5ProxyPassword,
  //                                            null);
  //     if (!gProtocolSvc.TorCommandSucceeded(reply))
  //       return false;

  //     proxyPassword = reply.retVal;
  //   }
  //   else
  //   {
  //     var reply = gProtocolSvc.TorGetConfStr(kTorConfKeyHTTPSProxy, null);
  //     if (!gProtocolSvc.TorCommandSucceeded(reply))
  //       return false;

  //     if (reply.retVal)
  //     {
  //       proxyType = "HTTP";
  //       proxyAddrPort = reply.retVal;
  //       var reply = gProtocolSvc.TorGetConfStr(
  //                                  kTorConfKeyHTTPSProxyAuthenticator, null);
  //       if (!gProtocolSvc.TorCommandSucceeded(reply))
  //         return false;

  //       var values = parseColonStr(reply.retVal);
  //       proxyUsername = values[0];
  //       proxyPassword = values[1];
  //     }
  //   }
  // }

  // var haveProxy = (proxyType != undefined);
  // setYesNoRadioValue(kWizardProxyRadioGroup, haveProxy);
  // setElemValue(kUseProxyCheckbox, haveProxy);
  // setElemValue(kProxyTypeMenulist, proxyType);
  // onProxyTypeChange();

  // var proxyAddr, proxyPort;
  // if (proxyAddrPort)
  // {
  //   var values = parseColonStr(proxyAddrPort);
  //   proxyAddr = values[0];
  //   proxyPort = values[1];
  // }

  // setElemValue(kProxyAddr, proxyAddr);
  // setElemValue(kProxyPort, proxyPort);
  // setElemValue(kProxyUsername, proxyUsername);
  // setElemValue(kProxyPassword, proxyPassword);

  return true;
} // initProxySettings


// Returns true if successful.
function initFirewallSettings()
{
  // if (getWizard())
  //   return true;  // The wizard does not directly expose firewall settings.

  // var allowedPorts;
  // var reply = gProtocolSvc.TorGetConfStr(kTorConfKeyReachableAddresses, null);
  // if (!gProtocolSvc.TorCommandSucceeded(reply))
  //   return false;

  // if (reply.retVal)
  // {
  //   var portStrArray = reply.retVal.split(',');
  //   for (var i = 0; i < portStrArray.length; i++)
  //   {
  //     var values = parseColonStr(portStrArray[i]);
  //     if (values[1])
  //     {
  //       if (allowedPorts)
  //         allowedPorts += ',' + values[1];
  //       else
  //         allowedPorts = values[1];
  //     }
  //   }
  // }

  // var haveFirewall = (allowedPorts != undefined);
  // setElemValue(kUseFirewallPortsCheckbox, haveFirewall);
  // if (allowedPorts)
  //   setElemValue(kFirewallAllowedPorts, allowedPorts);

  return true;
}


// Returns true if successful.
function initBridgeSettings()
{
  // var typeList = TorLauncherUtil.defaultBridgeTypes;
  // var canUseDefaultBridges = (typeList && (typeList.length > 0));
  // var defaultType = TorLauncherUtil.getCharPref(kPrefDefaultBridgeType);
  // var useDefault = canUseDefaultBridges && !!defaultType;

  // // If not configured to use a default set of bridges, get UseBridges setting
  // // from tor.
  // var useBridges = useDefault;
  // if (!useDefault)
  // {
  //   var reply = gProtocolSvc.TorGetConfBool(kTorConfKeyUseBridges, false);
  //   if (!gProtocolSvc.TorCommandSucceeded(reply))
  //     return false;

  //   useBridges = reply.retVal;

  //   // Get bridge list from tor.
  //   var bridgeReply = gProtocolSvc.TorGetConf(kTorConfKeyBridgeList);
  //   if (!gProtocolSvc.TorCommandSucceeded(bridgeReply))
  //     return false;

  //   if (!setBridgeListElemValue(bridgeReply.lineArray))
  //   {
  //     if (canUseDefaultBridges)
  //       useDefault = true;  // We have no custom values... back to default.
  //     else
  //       useBridges = false; // No custom or default bridges are available.
  //   }
  // }

  // setElemValue(kUseBridgesCheckbox, useBridges);
  // setYesNoRadioValue(kWizardUseBridgesRadioGroup, useBridges);

  // if (!canUseDefaultBridges)
  // {
  //   var label = document.getElementById("bridgeSettingsPrompt");
  //   if (label)
  //     label.setAttribute("hidden", true);

  //   var radioGroup = document.getElementById("bridgeTypeRadioGroup");
  //   if (radioGroup)
  //     radioGroup.setAttribute("hidden", true);
  // }

  // var radioID = (useDefault) ? "bridgeRadioDefault" : "bridgeRadioCustom";
  // var radio = document.getElementById(radioID);
  // if (radio)
  //   radio.control.selectedItem = radio;
  // onBridgeTypeRadioChange();

  return true;
}


// Returns true if settings were successfully applied.
function applySettings()
{
  // TorLauncherLogger.log(2, "applySettings ---------------------" +
  //                            "----------------------------------------------");
  // var didSucceed = false;
  // try
  // {
  //   didSucceed = applyProxySettings() && applyFirewallSettings() &&
  //                applyBridgeSettings();
  // }
  // catch (e) { TorLauncherLogger.safelog(4, "Error in applySettings: ", e); }

  var didSucceed = true;
  if (didSucceed)
    useSettings();

  console.info("applySettings done");

  return false;
}


function useSettings(callbackAfter)
{
  //torlauncher.util.pr_debug('network-settings.useSettings()');
  var settings = {};
  settings[kTorConfKeyDisableNetwork] = false;
  setConfAndReportErrors(settings, null).then(
    function (unusedSuccess) {
      //torlauncher.util.pr_debug('network-settings.useSettings: after setConfAnd...');
      gProtocolSvc.TorSendCommand("SAVECONF").then(
        function (reply) {
          //torlauncher.util.pr_debug('network-settings.useSettings: after saveConf send');
          gTorProcessService.TorClearBootstrapError();

          gIsBootstrapComplete = gTorProcessService.TorIsBootstrapDone;
          if (!gIsBootstrapComplete)
            openProgressDialog();
        }
      );
    }
  );
}

function openProgressDialog()
{
  var chromeURL = "progress.html";

  chrome.app.window.create(chromeURL, {
    id: gTorProcessService.kProgressDialogWindowId,
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
      isBrowserStartup: gIsInitialBootstrap,
      openerCallbackFunc: onProgressDialogClose
    };

    createdWindow.onClosed.addListener(function () {
      console.log('netwokr-settings: progress dialog closed');
    });
  });
}


function onProgressDialogClose(aBootstrapCompleted)
{
  gIsBootstrapComplete = aBootstrapCompleted;
  if (gIsBootstrapComplete) {
    chrome.runtime.getBackgroundPage(function (bgPage) {
      bgPage.torlauncher.torProcessService.onNetworkSettingsClose(false, false);
      window.close();
    });
  }
}


// Returns true if settings were successfully applied.
function applyProxySettings()
{
  var settings = getAndValidateProxySettings();
  if (!settings)
    return false;

  return setConfAndReportErrors(settings, "proxyYES");
}


// Return a settings object if successful and null if not.
function getAndValidateProxySettings()
{
  // TODO: validate user-entered data.  See Vidalia's NetworkPage::save()

  var settings = {};
  settings[kTorConfKeySocks4Proxy] = null;
  settings[kTorConfKeySocks5Proxy] = null;
  settings[kTorConfKeySocks5ProxyUsername] = null;
  settings[kTorConfKeySocks5ProxyPassword] = null;
  settings[kTorConfKeyHTTPSProxy] = null;
  settings[kTorConfKeyHTTPSProxyAuthenticator] = null;

  var proxyType, proxyAddrPort, proxyUsername, proxyPassword;
  if (isProxyConfigured())
  {
    proxyAddrPort = createColonStr(getElemValue(kProxyAddr, null),
                                   getElemValue(kProxyPort, null));
    if (!proxyAddrPort)
    {
      reportValidationError("error_proxy_addr_missing");
      return null;
    }

    proxyType = getElemValue(kProxyTypeMenulist, null);
    if (!proxyType)
    {
      reportValidationError("error_proxy_type_missing");
      return null;
    }

    if ("SOCKS4" != proxyType)
    {
      proxyUsername = getElemValue(kProxyUsername);
      proxyPassword = getElemValue(kProxyPassword);
    }
  }

  if ("SOCKS4" == proxyType)
  {
    settings[kTorConfKeySocks4Proxy] = proxyAddrPort;
  }
  else if ("SOCKS5" == proxyType)
  {
    settings[kTorConfKeySocks5Proxy] = proxyAddrPort;
    settings[kTorConfKeySocks5ProxyUsername] = proxyUsername;
    settings[kTorConfKeySocks5ProxyPassword] = proxyPassword;
  }
  else if ("HTTP" == proxyType)
  {
    settings[kTorConfKeyHTTPSProxy] = proxyAddrPort;
    // TODO: Does any escaping need to be done?
    settings[kTorConfKeyHTTPSProxyAuthenticator] =
                                  createColonStr(proxyUsername, proxyPassword);
  }

  return settings;
} // getAndValidateProxySettings


function isProxyConfigured()
{
  return (getWizard()) ? getYesNoRadioValue(kWizardProxyRadioGroup) :
                         getElemValue(kUseProxyCheckbox, false);
}


function reportValidationError(aStrKey)
{
  showSaveSettingsAlert(TorLauncherUtil.getLocalizedString(aStrKey));
}


// Returns true if settings were successfully applied.
function applyFirewallSettings()
{
  var settings = (getWizard()) ? getAutoFirewallSettings() :
                                 getAndValidateFirewallSettings();
  if (!settings)
    return false;

  return setConfAndReportErrors(settings, null);
}


// Return a settings object if successful and null if not.
// Not used for the wizard.
function getAndValidateFirewallSettings()
{
  // TODO: validate user-entered data.  See Vidalia's NetworkPage::save()

  var settings = {};
  settings[kTorConfKeyReachableAddresses] = null;

  var allowedPorts = null;
  if (getElemValue(kUseFirewallPortsCheckbox, false))
    allowedPorts = getElemValue(kFirewallAllowedPorts, null);

  return constructFirewallSettings(allowedPorts);
}


// Return a settings object if successful and null if not.
// Only used for the wizard.
function getAutoFirewallSettings()
{
  // In the wizard, we automatically set firewall ports (ReachableAddresses) to
  // 80 and 443 if and only if the user has configured a proxy but no bridges.
  // Rationale (from ticket #11405):
  //   - Many proxies restrict which ports they will proxy for, so we want to
  //     use a small set of ports in that case.
  //
  //   - In most other situations, tor will quickly find a bridge or guard on
  //     port 443, so there is no need to limit which port may be used.
  //
  //   - People whose set of reachable ports are really esoteric will need to
  //     be very patient or they will need to edit torrc manually... but that
  //     is OK since we expect that situation to be very rare.
  var allowedPorts = null;
  if (isProxyConfigured() && !isBridgeConfigured())
    allowedPorts = "80,443";

  return constructFirewallSettings(allowedPorts);
}


function constructFirewallSettings(aAllowedPorts)
{
  var settings = {};
  settings[kTorConfKeyReachableAddresses] = null;

  if (aAllowedPorts)
  {
    var portsConfStr;
    var portsArray = aAllowedPorts.split(',');
    for (var i = 0; i < portsArray.length; ++i)
    {
      var s = portsArray[i].trim();
      if (s.length > 0)
      {
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


function initDefaultBridgeTypeMenu()
{
  var menu = document.getElementById(kDefaultBridgeTypeMenuList);
  if (!menu)
    return;

  menu.removeAllItems();

  var typeArray = TorLauncherUtil.defaultBridgeTypes;
  if (!typeArray || typeArray.length === 0)
    return;

  var recommendedType = TorLauncherUtil.getCharPref(
                                      kPrefDefaultBridgeRecommendedType, null);
  var selectedType = TorLauncherUtil.getCharPref(kPrefDefaultBridgeType, null);
  if (!selectedType)
    selectedType = recommendedType;

  for (var i=0; i < typeArray.length; i++)
  {
    var bridgeType = typeArray[i];

    var menuItemLabel = bridgeType;
    if (bridgeType == recommendedType)
    {
      const key = "recommended_bridge";
      menuItemLabel += " " + TorLauncherUtil.getLocalizedString(key);
    }

    var mi = menu.appendItem(menuItemLabel, bridgeType);
    if (bridgeType == selectedType)
      menu.selectedItem = mi;
  }
}


// Returns true if settings were successfully applied.
function applyBridgeSettings()
{
  var settings = getAndValidateBridgeSettings();
  if (!settings)
    return false;

  return setConfAndReportErrors(settings, "bridgeSettings");
}


// Return a settings object if successful and null if not.
function getAndValidateBridgeSettings()
{
  var settings = {};
  settings[kTorConfKeyUseBridges] = null;
  settings[kTorConfKeyBridgeList] = null;

  var useBridges = isBridgeConfigured();
  var defaultBridgeType;
  var bridgeList;
  if (useBridges)
  {
    var useCustom = getElemValue(kCustomBridgesRadio, false);
    if (useCustom)
    {
      var bridgeStr = getElemValue(kBridgeList, null);
      bridgeList = parseAndValidateBridges(bridgeStr);
      if (!bridgeList)
      {
        reportValidationError("error_bridges_missing");
        return null;
      }

      setBridgeListElemValue(bridgeList);
    }
    else
    {
      defaultBridgeType = getElemValue(kDefaultBridgeTypeMenuList, null);
      if (!defaultBridgeType)
      {
        reportValidationError("error_default_bridges_type_missing");
        return null;
      }
    }
  }

  // Since it returns a filterd list of bridges, TorLauncherUtil.defaultBridges
  // must be called after setting the kPrefDefaultBridgeType pref.
  TorLauncherUtil.setCharPref(kPrefDefaultBridgeType, defaultBridgeType);
  if (defaultBridgeType)
    bridgeList = TorLauncherUtil.defaultBridges;

  if (useBridges && bridgeList)
  {
    settings[kTorConfKeyUseBridges] = true;
    settings[kTorConfKeyBridgeList] = bridgeList;
  }

  return settings;
}


function isBridgeConfigured()
{
  return (getWizard()) ? getElemValue("bridgesRadioYes", false) :
                         getElemValue(kUseBridgesCheckbox, false);
}


// Returns an array or null.
function parseAndValidateBridges(aStr)
{
  if (!aStr)
    return null;

  var resultStr = aStr;
  resultStr = resultStr.replace(/bridge/gi, ""); // Remove "bridge" everywhere.
  resultStr = resultStr.replace(/\r\n/g, "\n");  // Convert \r\n pairs into \n.
  resultStr = resultStr.replace(/\r/g, "\n");    // Convert \r into \n.
  resultStr = resultStr.replace(/\n\n/g, "\n");  // Condense blank lines.

  var resultArray = new Array;
  var tmpArray = resultStr.split('\n');
  for (var i = 0; i < tmpArray.length; i++)
  {
    var s = tmpArray[i].trim(); // Remove extraneous whitespace.
    resultArray.push(s);
  }

  return (0 === resultArray.length) ? null : resultArray;
}


// Returns true if successful.
// aShowOnErrorPanelID is only used when displaying the wizard.
function setConfAndReportErrors(aSettingsObj, aShowOnErrorPanelID)
{
  return new Promise(function (resolve, reject) {
    var errObj = {};
    gProtocolSvc.TorSetConfWithReply(aSettingsObj, errObj).then(
      function (reply) {
        resolve(true);
      },
      function (errObj) {
        if (aShowOnErrorPanelID) {
          var wizardElem = getWizard();
          if (wizardElem) {
            const kMaxTries = 10;
            for (var count = 0;
                 ((count < kMaxTries) &&
                  (gDialogHelper.currentPage.pageid != aShowOnErrorPanelID) &&
                  gDialogHelper.canRewind);
                 ++count) {
              gDialogHelper.rewind();
            }
          }
        }

        showSaveSettingsAlert(errObj.details);
        resolve(false);
      }
    );
  });
}


function showSaveSettingsAlert(aDetails)
{
  torlauncher.util.showSaveSettingsAlert(window, aDetails);
  showOrHideButton("extra2", true, false);
  gWizIsCopyLogBtnShowing = true;
}


function setElemValue(aID, aValue)
{
  var elem = document.getElementById(aID);
  if (elem)
  {
    var val = aValue;
    switch (elem.tagName)
    {
      case "checkbox":
        elem.checked = val;
        toggleElemUI(elem);
        break;
      case "textbox":
        if (Array.isArray(aValue))
        {
          val = "";
          for (var i = 0; i < aValue.length; ++i)
          {
            if (val.length > 0)
              val += '\n';
            val += aValue[i];
          }
        }
        // fallthru
      case "menulist":
        elem.value = (val) ? val : "";
        break;
    }
  }
}


// Returns true if one or more values were set.
function setBridgeListElemValue(aBridgeArray)
{
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

  setElemValue(kBridgeList, bridgeList);
  return (bridgeList.length > 0);
}


// Returns a Boolean (for checkboxes/radio buttons) or a
// string (textbox and menulist).
// Leading and trailing white space is trimmed from strings.
function getElemValue(aID, aDefaultValue)
{
  var rv = aDefaultValue;
  var elem = document.getElementById(aID);
  if (elem)
  {
    switch (elem.tagName)
    {
      case "checkbox":
        rv = elem.checked;
        break;
      case "radio":
        rv = elem.selected;
        break;
      case "textbox":
      case "menulist":
        rv = elem.value;
        break;
    }
  }

  if (rv && ("string" == (typeof rv)))
    rv = rv.trim();

  return rv;
}


// This assumes that first radio button is yes.
function setYesNoRadioValue(aGroupID, aIsYes)
{
  var elem = document.getElementById(aGroupID);
  if (elem)
    elem.selectedIndex = (aIsYes) ? 0 : 1;
}


// This assumes that first radio button is yes.
function getYesNoRadioValue(aGroupID)
{
  var elem = document.getElementById(aGroupID);
  return (elem) ? (0 === elem.selectedIndex) : false;
}


function toggleElemUI(aElem)
{
  if (!aElem)
    return;

  var gbID = aElem.getAttribute("groupboxID");
  if (gbID)
  {
    var gb = document.getElementById(gbID);
    if (gb)
      gb.hidden = !aElem.checked;
  }
}


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


function createColonStr(aStr1, aStr2)
{
  var rv = aStr1;
  if (aStr2)
  {
    if (!rv)
      rv = "";
    rv += ':' + aStr2;
  }

  return rv;
}

