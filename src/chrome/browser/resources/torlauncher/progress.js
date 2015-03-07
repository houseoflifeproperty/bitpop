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

const kTorProcessExitedTopic = "TorProcessExited";
const kBootstrapStatusTopic = "TorBootstrapStatus";
const kTorLogHasWarnOrErrTopic = "TorLogHasWarnOrErr";

const kTorOpenNewSessionWindowMessage = "open-initial-tor-session-window";
const kTorHelperExtensionId = "nnldggpjfmmhhmjoekppejaejalbchbh";

var gObsSvc;
var gOpenerCallbackFunc; // Set when opened from network settings.

window.addEventListener('load', initDialog, true);

function initDialog() {
  torlauncher.util.localizePage();

  document.getElementById('cancelButton').addEventListener(
    'click', onCancel, false);
  document.getElementById('extra2Button').addEventListener(
    'click', onOpenSettings, false);

  // If tor bootstrap has already finished, just close the progress dialog.
  // This situation can occur if bootstrapping is very fast and/or if this
  // window opens slowly (observed with Adblock Plus installed).
  chrome.runtime.getBackgroundPage(function (backgroundPage) {
    gProtocolSvc = backgroundPage.torlauncher.protocolService;
    gTorProcessService = backgroundPage.torlauncher.torProcessService;

    if (gTorProcessService.TorIsBootstrapDone ||
        gTorProcessService.TorBootstrapErrorOccurred) {
      closeThisWindow(gTorProcessService.TorIsBootstrapDone);
      return;
    }

    chrome.runtime.onMessage.addListener(onMessage);

    var isBrowserStartup = false;
    if (window.windowArgs) {
      isBrowserStartup = window.windowArgs.isBrowserStartup;

      if (window.windowArgs.openerCallbackFunc)
        gOpenerCallbackFunc = window.windowArgs.openerCallbackFunc;
    }

    var extraBtn = document.getElementById("extra2Button");
    if (gOpenerCallbackFunc) {
      // Dialog was opened from network settings: hide Open Settings button.
      extraBtn.setAttribute("hidden", true);
    }
    else {
      // Dialog was not opened from network settings: change Cancel to Quit.
      var cancelBtn = document.getElementById("cancelButton");
      chrome.runtime.getPlatformInfo(function (info) {
        var quitKey = (info.os == 'win') ? "quit_win" : "quit";
        cancelBtn.innerText = torlauncher.util.getLocalizedString(quitKey);
      });
    }

    // If opened during browser startup, display the "please wait" message.
    if (isBrowserStartup) {
      var pleaseWait = document.getElementById("progressPleaseWait");
      if (pleaseWait)
        pleaseWait.removeAttribute("hidden");
    }
  });
}

function cleanup() {
  chrome.runtime.onMessage.removeListener(onMessage);
}


function closeThisWindow(aBootstrapDidComplete) {
  cleanup();

  if (gOpenerCallbackFunc) {
    gOpenerCallbackFunc(aBootstrapDidComplete);
  }

  if (aBootstrapDidComplete) {
    chrome.runtime.sendMessage( { kind: "TorBootstrapCompleteInProgressDialog" });
    chrome.runtime.sendMessage(
        kTorHelperExtensionId,  { 'kind': kTorOpenNewSessionWindowMessage });
  }

  window.close();
}


function onCancel() {
  cleanup();

  if (gOpenerCallbackFunc) {
    // TODO: stop the bootstrapping process?
    gOpenerCallbackFunc(false);
  }
  else {
    chrome.runtime.sendMessage({ kind: 'TorUserRequestedQuit' });
  }

  window.close();
}


function onOpenSettings() {
  cleanup();
  window.close();
}


function onMessage(message) {
  var aTopic = message.kind;
  var aSubject = message.subject;
  if (kTorProcessExitedTopic == aTopic) {
    // TODO: provide a way to access tor log e.g., leave this dialog open
    //       and display the open settings button.
    cleanup();
    window.close();
  }
  else if (kBootstrapStatusTopic == aTopic) {
    var statusObj = aSubject;
    var labelText =
              torlauncher.util.getLocalizedBootstrapStatus(statusObj, "TAG");
    var percentComplete = (statusObj.PROGRESS) ? statusObj.PROGRESS : 0;

    var meter = document.getElementById("progressMeter");
    if (meter) {
      meter.value = percentComplete;
      meter.innerText = percentComplete.toString() + "%";
    }

    var bootstrapDidComplete = (percentComplete >= 100);
    if (percentComplete >= 100) {
      // To ensure that 100% progress is displayed, wait a short while
      // before closing this window.
      window.setTimeout(function() { closeThisWindow(true); }, 250);
    }
    else if (statusObj._errorOccurred) {
      var s = torlauncher.util.getLocalizedBootstrapStatus(statusObj, "REASON");
      if (s)
        labelText = s;

      if (meter)
        meter.setAttribute("hidden", true);

      var pleaseWait = document.getElementById("progressPleaseWait");
      if (pleaseWait)
        pleaseWait.setAttribute("hidden", true);
    }

    var desc = document.getElementById("progressDesc");
    if (labelText && desc)
      desc.innerText = labelText;
  }
  else if (kTorLogHasWarnOrErrTopic == aTopic) {
    var warningIcon = document.getElementById("warningIcon");
    if (warningIcon.hasAttribute('hidden'))
      warningIcon.removeAttribute("hidden");

    // TODO: show error / warning message in this dialog?
  }
}
