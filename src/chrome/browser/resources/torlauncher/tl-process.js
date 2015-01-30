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

// constructor
torlauncher.TorProcessService = function () {
  if (torlauncher.protocolService)
    this.mProtocolSvc = torlauncher.protocolService; // the only instance
};

torlauncher.TorProcessService.prototype = {
  kInitialControlConnDelayMS: 25,
  kMaxControlConnRetryMS: 500,
  kControlConnTimeoutMS: 30000, // Wait at most 30 seconds for tor to start.

  kStatusUnknown: 0, // Tor process status.
  kStatusStarting: 1,
  kStatusRunning: 2,
  kStatusExited: 3,  // Exited or failed to start.

  kDefaultBridgesStatus_NotInUse: 0,
  kDefaultBridgesStatus_InUse: 1,
  kDefaultBridgesStatus_BadConfig: 2,

  kProcessStatusAlarmName: "torlauncher.alarm.processStatusAlarm",
  kControlConnTimerName: "torlauncher.alarm.controlConnTimer",

  kNetworkSettingsWindowId: "torlauncher.window.network_settings",
  kProgressDialogWindowId: "torlauncher.window.progress_dialog",

  kTorOpenNewSessionWindowMessage: "open-initial-tor-session-window",

  kTorHelperExtensionId: "nnldggpjfmmhhmjoekppejaejalbchbh",

  init: function () {

    var _this = this;

    chrome.runtime.onSuspend.addListener(function () { _this.onSuspend(); });
    torlauncher.util.pr_debug('tl-process.after.runtime.onSuspend');
    //chrome.alarms.onAlarm.addListener(function (alarm) { _this.onAlarm(alarm); });
    torlauncher.util.pr_debug('tl-process.after.alarms.onAlarm.addListener');

    const kOpenNetworkSettingsTopic = "TorOpenNetworkSettings";
    const kUserQuitTopic = "TorUserRequestedQuit";
    const kBootstrapStatusTopic = "TorBootstrapStatus";

    chrome.runtime.onMessage.addListener(
      function (message) {
        if (message.kind == kOpenNetworkSettingsTopic) {
          _this._openNetworkSettings(false);
        } else if (message.kind == kUserQuitTopic) {
          _this.mQuitSoon = true;
          _this.mRestartWithQuit = ("restart" == message.param);
        } else if (message.kind == kBootstrapStatusTopic) {
          _this._processBootstrapStatus(message.subject);
        }
      }
    );
    //torlauncher.util.pr_debug('tl-process.after.runtime.onMessage.addListener');

    torlauncher.util.getShouldOnlyConfigureTorWithPromise().then(
      function (should_only_configure_tor) {
        //torlauncher.util.pr_debug('TorProcessService.init: should_only_configure_tor: ' + should_only_configure_tor);
        if (should_only_configure_tor)
          _this._controlTor();
        else
          return torlauncher.util.getShouldStartAndOwnTorWithPromise();
      }
    ).then(
      function (should_start_and_own_tor) {
        //torlauncher.util.pr_debug('TorProcessService.init: should_start_and_own_tor: ' + should_start_and_own_tor);
        if (should_start_and_own_tor === undefined)
          return;

        if (should_start_and_own_tor) {
          _this._startTor().then(
            _this._controlTor().bind(_this)
          );
        }
      }
    );
  },

  onSuspend: function () {
    this.mIsQuitting = true;

    if (this._processStatusInterval) {
      clearInterval(this._processStatusInterval);
      this._processStatusInterval = null;
    }
    if (this.mControlConnTimer) {
      clearTimeout(this.mControlConnTimer);
      this.mControlConnTimer = null;
    }

    if (this.mTorProcessStatus != this.kStatusUnknown &&
        this.mTorProcessStatus != this.kStatusExited)
    {
      // Tor Firefox Browser Bundle comment here
      //
      // We now rely on the TAKEOWNERSHIP feature to shut down tor when we
      // close the control port connection.
      //
      // Previously, we sent a SIGNAL HALT command to the tor control port,
      // but that caused hangs upon exit in the Firefox 24.x based browser.
      // Apparently, Firefox does not like to process socket I/O while
      // quitting if the browser did not finish starting up (e.g., when
      // someone presses the Quit button on our Network Settings or progress
      // window during startup).
      torlauncher.util.pr_debug("Disconnecting from tor process");
      this.mProtocolSvc.TorCleanupConnection();

      this.mTorProcessStatus = kStatusExited;
    }
  },

  onAlarm: function (alarm) {
    if (alarm.name == this.kProcessStatusAlarmName) {
      //torlauncher.util.pr_debug('tl-process.onAlarm: ' + alarm.name);
      chrome.torlauncher.getTorProcessStatus(
        function (status) {
          var changed = (this.mTorProcessStatus != status);
          this.mTorProcessStatus = status;

          if (changed && this.mTorProcessStatus == this.kStatusExited)
            this.onTorProcessExited();

          // if (changed) {
          //   // TODO: notify observers???
          // }
        }.bind(this));
    } else if (alarm.name == this.kControlConnTimerName) {
      //torlauncher.util.pr_debug('tl-process.onAlarm: ' + alarm.name);
      this.onControlConnTimer();
    }
  },

  onTorProcessExited: function () {
    if (this.mControlConnTimer)
    {
      clearTimeout(this.mControlConnTimer);
      this.mControlConnTimer = null;
    }

    //this.mTorProcess = null;
    this.mIsBootstrapDone = false;

    chrome.runtime.sendMessage({ 'kind': "TorProcessExited" });

    if (!this.mIsQuitting)
    {
      this.mProtocolSvc.TorCleanupConnection();

      var s = torlauncher.util.getLocalizedString("tor_exited") + "\n\n"
              + torlauncher.util.getLocalizedString("tor_exited2");
      console.warn(s);
      var defaultBtnLabel = torlauncher.util.getLocalizedString("restart_tor");
      var cancelBtnLabel = "OK";
      // TODO: localize "OK" button label

      torlauncher.util.showConfirm(null, s, defaultBtnLabel, cancelBtnLabel).then(
        function () {
          if (!this.mIsQuitting)
            this._startTor().then(
              this._controlTor().bind(this)
            );
        }.bind(this)
      );
    }
  },

  onControlConnTimer: function () {
    this.mProtocolSvc.TorHaveControlConnection().then(
      function (haveConnection) {
        if (haveConnection) {
          this.mControlConnTimer = null;
          this.mTorProcessStatus = this.kStatusRunning;

          // tor process service does not automatically set status to "running"
          // that's why we need to do this op
          chrome.torlauncher.setTorStatusRunning();

          this.mProtocolSvc.TorStartEventMonitor();

          this.mProtocolSvc.TorRetrieveBootstrapStatus();

          // if (this._defaultBridgesStatus == this.kDefaultBridgesStatus_InUse)
          // {
          //   // We configure default bridges each time we start tor in case
          //   // new default bridge preference values are available (e.g., due
          //   // to a TBB update).
          //   this._configureDefaultBridges();
          // }

          chrome.runtime.sendMessage({ 'kind': "TorProcessIsReady" });
        } else if ((Date.now() - this.mTorProcessStartTime)
                   > this.kControlConnTimeoutMS) {
          var s = torlauncher.util.getLocalizedString("tor_controlconn_failed");
          chrome.runtime.sendMessage({ 'kind': "TorProcessDidNotStart", 'param': s });

          torlauncher.util.showAlert(null, s);
          console.warn(s);
        } else {
          this.mControlConnDelayMS *= 2;
          if (this.mControlConnDelayMS > this.kMaxControlConnRetryMS)
            this.mControlConnDelayMS = this.kMaxControlConnRetryMS;
          this.mControlConnTimer = setTimeout(
              this.onAlarm.bind(this, { name: this.kControlConnTimerName }),
              this.mControlConnDelayMS);
        }
      }.bind(this)
    );
  },

  // Public Properties and Methods ///////////////////////////////////////////
  get TorProcessStatus()
  {
    return this.mTorProcessStatus;
  },

  get TorIsBootstrapDone()
  {
    return this.mIsBootstrapDone;
  },

  get TorBootstrapErrorOccurred()
  {
    return this.mBootstrapErrorOccurred;
  },


  TorClearBootstrapError: function()
  {
    this.mLastTorWarningPhase = null;
    this.mLastTorWarningReason = null;
  },

  // Private Member Variables ////////////////////////////////////////////////
  mTorProcessStatus: 0,  // kStatusUnknown
  mIsBootstrapDone: false,
  mBootstrapErrorOccurred: false,
  mIsQuitting: false,
  mObsSvc: null,
  mProtocolSvc: null,
  mTorProcess: null,    // nsIProcess
  mTorProcessStartTime: null, // JS Date.now()
  mTorFileBaseDir: null,      // nsIFile (cached)
  mControlConnTimer: null,
  mControlConnDelayMS: 0,
  mQuitSoon: false,     // Quit was requested by the user; do so soon.
  mRestartWithQuit: false,
  mLastTorWarningPhase: null,
  mLastTorWarningReason: null,
  mTorProcessStatusObserverTimer: null,

  // Private Methods /////////////////////////////////////////////////////////
  _startTor: function()
  {
    //console.log('TorProcessService._startTor: begin');
    var _this = this;
    return new Promise(function (resolve, reject) {
      _this.mTorProcessStatus = _this.kStatusUnknown;

      // Start tor with networking disabled if first run or if the
      // "Use Default Bridges of Type" option is turned on.  Networking will
      // be enabled after initial settings are chosen or after the default
      // bridge settings have been configured.
      torlauncher.util.prefGetWithPromise('defaultBridgeType').then(
        function (defaultBridgeType) {
          //console.log('TorProcessService._startTor: defaultBridgeType:' + defaultBridgeType);
          var bridgeConfigIsBad = (_this._defaultBridgesStatus ==
                                   _this.kDefaultBridgesStatus_BadConfig);
          if (bridgeConfigIsBad) {
            var key = "error_bridge_bad_default_type";
            var err = torlauncher.util.getFormattedLocalizedString(key,
                                                         [defaultBridgeType], 1);
            torlauncher.util.showAlert(null, err);
          }

          var disableNetwork = false;
          torlauncher.util.getShouldShowNetworkSettingsWithPromise().then(
            function (shouldShowNetworkSettings) {
              if (shouldShowNetworkSettings || defaultBridgeType) {
                disableNetwork = true;
              }

              torlauncher.util.pr_debug("Starting Tor...");
              chrome.torlauncher.startTor(disableNetwork,
                function (success, error_desc) {
                  //torlauncher.util.pr_debug("Starting Tor... Details: " + JSON.stringify({success:success, error_desc: error_desc}));
                  if (success) {
                    _this.mTorProcessStatus = _this.kStatusStarting;
                    _this.mTorProcessStartTime = Date.now();
                    if (error_desc.log_message)
                      console.info(error_desc.log_message);

                    _this._processStatusInterval =
                        setInterval(
                            _this.onAlarm.bind(_this,
                                               { name: _this.kProcessStatusAlarmName}),
                            500);

                    //torlauncher.util.pr_debug("Starting Tor... Resolving...");
                    resolve();
                  } else {
                    _this.mTorProcessStatus = _this.kStatusExited;
                    if (error_desc.alert_message_key) {
                      var s = torlauncher.util.getLocalizedString(
                          error_desc.alert_message_key);
                      torlauncher.util.showAlert(null, s);
                    }
                    if (error_desc.log_message)
                      console.warn(error_desc.log_message);

                    reject();
                  }
                }
              );
            }
          );
        }
      );
    });
  }, // _startTor()


  _controlTor: function()
  {
    torlauncher.util.pr_debug('TorProcessService: _controlTor: begin');
    this._monitorTorProcessStartup();

    // var bridgeConfigIsBad = (this._defaultBridgesStatus ==
    //                          this.kDefaultBridgesStatus_BadConfig);
    // if (TorLauncherUtil.shouldShowNetworkSettings || bridgeConfigIsBad)
    // {
    //   if (this.mProtocolSvc)
    //   {
    //     // Show network settings wizard.  Blocks until dialog is closed.
    //     var panelID = (bridgeConfigIsBad) ? "bridgeSettings" : undefined;
    //     this._openNetworkSettings(true, panelID);
    //   }
    // }
    torlauncher.util.getShouldShowNetworkSettingsWithPromise().then(
      function (shouldShowNetworkSettings) {
        if (shouldShowNetworkSettings) {
          if (this.mProtocolSvc) {
            panelID = undefined;
            this._openNetworkSettings(true, panelID);
          }
        } else if (this._networkSettingsWindow !== null) {
          // If network settings is open, open progress dialog via notification.
          chrome.runtime.sendMessage({ 'kind': "TorOpenProgressDialog" });
        }
        else {
          this._openProgressDialog();
        }
      }.bind(this));
  }, // controlTor()

  _monitorTorProcessStartup: function() {
    this.mControlConnDelayMS = this.kInitialControlConnDelayMS;
    this.mControlConnTimer = setTimeout(
        this.onAlarm.bind(this, { name: this.kControlConnTimerName }),
        this.mControlConnDelayMS);
  },

  _processBootstrapStatus: function(aStatusObj)
  {
    if (!aStatusObj)
      return;

    if (100 == aStatusObj.PROGRESS) {
      this.mIsBootstrapDone = true;
      this.mBootstrapErrorOccurred = false;
      chrome.torlauncher.promptAtStartup.set({ value: false,
                                               scope: "incognito_persistent" });
      chrome.runtime.sendMessage(
          this.kTorHelperExtensionId,
          {
            'kind': this.kTorOpenNewSessionWindowMessage
          },
          function () {}  // sendResponse callback
      );
    }
    else
    {
      this.mIsBootstrapDone = false;

      if (aStatusObj._errorOccurred) {
        this.mBootstrapErrorOccurred = true;
        chrome.torlauncher.promptAtStartup.set({ value: true,
                                               scope: "incognito_persistent" });
        var phase = torlauncher.util.getLocalizedBootstrapStatus(aStatusObj,
                                                                 "TAG");
        var reason = torlauncher.util.getLocalizedBootstrapStatus(aStatusObj,
                                                                  "REASON");
        var details = torlauncher.util.getFormattedLocalizedString(
                          "tor_bootstrap_failed_details", [phase, reason], 2);
        console.warn("Tor bootstrap error: [" + aStatusObj.TAG +
                                 "/" + aStatusObj.REASON + "] " + details);

        if ((aStatusObj.TAG != this.mLastTorWarningPhase) ||
            (aStatusObj.REASON != this.mLastTorWarningReason)) {
          this.mLastTorWarningPhase = aStatusObj.TAG;
          this.mLastTorWarningReason = aStatusObj.REASON;

          var msg = torlauncher.util.getLocalizedString("tor_bootstrap_failed");
          torlauncher.util.showAlert(null, msg + "\n\n" + details);

          chrome.runtime.sendMessage({ 'kind': "TorBootstrapError" });
        }
      }
    }
  }, // _processBootstrapStatus()

  // Returns a kDefaultBridgesStatus value.
  get _defaultBridgesStatus()
  {
    // var defaultBridgeType =
    //               TorLauncherUtil.getCharPref(this.kPrefDefaultBridgeType);
    // if (!defaultBridgeType)
      return this.kDefaultBridgesStatus_NotInUse;

    // var bridgeArray = TorLauncherUtil.defaultBridges;
    // if (!bridgeArray || (0 == bridgeArray.length))
    //   return this.kDefaultBridgesStatus_BadConfig;

    // return this.kDefaultBridgesStatus_InUse;
  },

  // If this window is already open, put up "starting tor" panel, focus it and return.
  // Otherwise, open the network settings dialog and block until it is closed.
  _openNetworkSettings: function(aIsInitialBootstrap, aStartAtWizardPanel)
  {
    var win = this._networkSettingsWindow;
    if (win) {
      // Return to "Starting tor" panel if being asked to open & dlog already exists.
      win.contentWindow.showStartingTorPanel();
      win.focus();
      return;
    }

    const kSettingsURL = "network-settings.html";
    const kWizardURL = "network-settings-wizard.html";

    var url = (aIsInitialBootstrap) ? kWizardURL : kSettingsURL;

    chrome.app.window.create(url, {
      id: this.kNetworkSettingsWindowId,
      state: "normal",
      alwaysOnTop: true,
      innerBounds: {
        left:      100,
        top:       100,
        width:     600,
        height:    500,
        minWidth:  600,
        minHeight: 500,
        maxWidth:  600,
        maxHeight: 500
      }
    }, function (createdWindow) {
      // pass window creation arguments
      createdWindow.contentWindow.windowArgs = {
        isInitialBootstrap: aIsInitialBootstrap,
        startAtWizardPanel: aStartAtWizardPanel
      };

      createdWindow.onClosed.addListener(function () {
        console.log("tl-process: network settings window closed");
      });
    });
  },

  get _networkSettingsWindow() {
    return chrome.app.window.get(this.kNetworkSettingsWindowId);
  },

  _openProgressDialog: function() {
    var chromeURL = "progress.html";

    chrome.app.window.create(chromeURL, {
      id: this.kProgressDialogWindowId,
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
        isBrowserStartup: true
      };

      createdWindow.onClosed.addListener(function () {
        console.log("tl-process: progress window closed");
      });
    });
  },

  onNetworkSettingsClose: function (quitSoon, restartWithQuit) {
    this.mQuitSoon = quitSoon;
    this.mRestartWithQuit = restartWithQuit;

    // If the user pressed "Quit" within settings/progress, exit.
    if (this.mQuitSoon) {
      this.mQuitSoon = false;

      chrome.torlauncher.initiateAppQuit(this.mRestartWithQuit);
    }
  },

  onProgressDialogClose: function (quitSoon) {
    this.mQuitSoon = quitSoon;
    this.mRestartWithQuit = false;

    // Assume that the "Open Settings" button was pressed if Quit was
    // not pressed and bootstrapping did not finish.
    if (!this.mQuitSoon && !this.TorIsBootstrapDone)
      this._openNetworkSettings(true);

    // If the user pressed "Quit" within settings/progress, exit.
    if (this.mQuitSoon) {
      this.mQuitSoon = false;

      chrome.torlauncher.initiateAppQuit(this.mRestartWithQuit);
    }
  },
};

torlauncher.torProcessService = new torlauncher.TorProcessService();
