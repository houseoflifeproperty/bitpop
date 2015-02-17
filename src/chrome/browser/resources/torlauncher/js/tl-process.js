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
  // the only instance
  torlauncher.protocolService = new torlauncher.TorProtocolService();
  var _this = this;
  torlauncher.protocolService.initPromise.then(function () {
    this.mProtocolSvc = torlauncher.protocolService;
  });
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
          _this.mRestartWithQuit =
              (message.param && "restart" == message.param);
        } else if (message.kind == kBootstrapStatusTopic) {
          _this._processBootstrapStatus(message.subject);
        }
      }
    );
    torlauncher.util.pr_debug('tl-process.after.runtime.onMessage.addListener');

    torlauncher.util.runGenerator(function *main() {
      var should_only_configure_tor =
          yield *torlauncher.util.shouldOnlyConfigureTor();
      var should_start_and_own_tor =
          yield *torlauncher.util.shouldStartAndOwnTor();

      torlauncher.util.pr_debug('should_only_configure_tor == ' + should_only_configure_tor);
      torlauncher.util.pr_debug('should_start_and_own_tor == ' + should_start_and_own_tor);

      // make sure protocol helper object is constructed
      yield torlauncher.protocolService.initPromise;

      torlauncher.util.pr_debug('initPromise satisfied');

      if (should_only_configure_tor)
        yield *_this.controlTor();
      else if (should_start_and_own_tor) {
        yield *_this._startTor();
        yield *_this._controlTor();
      }
    });
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
        this.mTorProcessStatus != this.kStatusExited) {
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
    if (this.mControlConnTimer) {
      clearTimeout(this.mControlConnTimer);
      this.mControlConnTimer = null;
    }

    //this.mTorProcess = null;
    this.mIsBootstrapDone = false;

    chrome.runtime.sendMessage({ 'kind': "TorProcessExited" });

    if (!this.mIsQuitting) {
      this.mProtocolSvc.TorCleanupConnection();

      var s = torlauncher.util.getLocalizedString("tor_exited") + "\n\n"
              + torlauncher.util.getLocalizedString("tor_exited2");
      console.warn(s);
      var defaultBtnLabel = torlauncher.util.getLocalizedString("restart_tor");
      var cancelBtnLabel = "OK";
      // TODO: localize "OK" button label

      var _this = this;
      torlauncher.util.runGenerator(function* () {
        if (yield torlauncher.util.showConfirm(
              null, s, defaultBtnLabel, cancelBtnLabel) &&
            !_this.mIsQuitting) {
          yield *_this._startTor();
          yield *_this._controlTor();
        }
      });
    }
  },

  onControlConnTimer: function () {
    var _this = this;
    torlauncher.util.runGenerator(function *timer_func() {
      var haveConnection =
          yield *_this.mProtocolSvc.TorHaveControlConnection();
      if (haveConnection) {
        _this.mControlConnTimer = null;
        _this.mTorProcessStatus = _this.kStatusRunning;

        // tor process service does not automatically set status to "running"
        // that's why we need to do this op
        chrome.torlauncher.setTorStatusRunning();

        _this.mProtocolSvc.TorStartEventMonitor();

        _this.mProtocolSvc.TorRetrieveBootstrapStatus();

        if ((yield *_this._defaultBridgesStatus()) ==
            _this.kDefaultBridgesStatus_InUse) {
          // We configure default bridges each time we start tor in case
          // new default bridge preference values are available (e.g., due
          // to a TBB update).
          yield *_this._configureDefaultBridges();
        }

        chrome.runtime.sendMessage({ 'kind': "TorProcessIsReady" });
      } else if ((Date.now() - _this.mTorProcessStartTime)
                 > _this.kControlConnTimeoutMS) {
        var s = torlauncher.util.getLocalizedString("tor_controlconn_failed");
        chrome.runtime.sendMessage({ 'kind': "TorProcessDidNotStart",
                                    'param': s });

        yield torlauncher.util.showAlert(null, s);
        console.warn(s);
      } else {
        _this.mControlConnDelayMS *= 2;
        if (_this.mControlConnDelayMS > _this.kMaxControlConnRetryMS)
          _this.mControlConnDelayMS = _this.kMaxControlConnRetryMS;
        this.mControlConnTimer = setTimeout(
            _this.onAlarm.bind(_this, { name: _this.kControlConnTimerName }),
            _this.mControlConnDelayMS);
      }
    });
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
  mNetworkSettingsCloseCalled: false,

  // Private Methods /////////////////////////////////////////////////////////
  _startTor: function *()
  {
    torlauncher.util.pr_debug('_startTor():');

    this.mTorProcessStatus = this.kStatusUnknown;

    // Start tor with networking disabled if first run or if the
    // "Use Default Bridges of Type" option is turned on.  Networking will
    // be enabled after initial settings are chosen or after the default
    // bridge settings have been configured.
    var defaultBridgeType =
        yield torlauncher.util.prefGet('defaultBridgeType');
    var bridgeConfigIsBad = ((yield *this._defaultBridgesStatus()) ==
                             this.kDefaultBridgesStatus_BadConfig);
    if (bridgeConfigIsBad) {
      torlauncher.util.pr_debug('bridgeConfigIsBad!');
      var key = "error_bridge_bad_default_type";
      var err = torlauncher.util.getFormattedLocalizedString(key,
                                                   [defaultBridgeType], 1);
      yield torlauncher.util.showAlert(null, err);
    }

    var disableNetwork = false;
    if ((yield *torlauncher.util.shouldShowNetworkSettings()) ||
        defaultBridgeType)
      disableNetwork = true;

    torlauncher.util.pr_debug("Starting Tor...");
    try {
      var errorDesc = yield new Promise(function (resolve,reject) {
        chrome.torlauncher.startTor(
            disableNetwork,
            function(success, error_desc) {
              success ? resolve(error_desc) : reject(error_desc);
            }
        );
      });
      this.mTorProcessStatus = this.kStatusRunning;
      this.mTorProcessStartTime = Date.now();
      var logMessage = errorDesc.log_message;
      if (logMessage)
        console.info(logMessage);

      this._processStatusInterval =
          setInterval(
              this.onAlarm.bind(this, { name: _this.kProcessStatusAlarmName}),
              500);
    } catch (e) {
      this.mTorProcessStatus = this.kStatusExited;
      if (e.alert_message_key) {
        var s = torlauncher.util.getLocalizedString(
            e.alert_message_key);
        yield torlauncher.util.showAlert(null, s);
      }
      if (e.log_message)
        console.warn(error_desc.log_message);
    }
  }, // _startTor()


  _controlTor: function *()
  {
    torlauncher.util.pr_debug('TorProcessService: _controlTor: begin');
    this._monitorTorProcessStartup();


    // if (TorLauncherUtil.shouldShowNetworkSettings || bridgeConfigIsBad)
    // {
    //   if (this.mProtocolSvc)
    //   {
    //     // Show network settings wizard.  Blocks until dialog is closed.
    //     var panelID = (bridgeConfigIsBad) ? "bridgeSettings" : undefined;
    //     this._openNetworkSettings(true, panelID);
    //   }
    // }
    var bridgeConfigIsBad = ((yield *this._defaultBridgesStatus()) ==
                             this.kDefaultBridgesStatus_BadConfig);
    if (yield *torlauncher.util.shouldShowNetworkSettings() ||
        bridgeConfigIsBad) {
      if (this.mProtocolSvc) {
        panelID = undefined;
        yield this._openNetworkSettings(true, panelID);
      }
    } else if (chrome.app.window.get(this.kNetworkSettingsWindowId) !== null) {
      // If network settings is open, open progress dialog via notification.
      chrome.runtime.sendMessage({ 'kind': "TorOpenProgressDialog" });
    }
    else {
      yield this._openProgressDialog();

      if (!this.mQuitSoon && !this.TorIsBootstrapDone)
          yield this._openNetworkSettings(true);
    }

    // If the user pressed "Quit" within settings/progress, exit.
    if (this.mQuitSoon) {
      this.mQuitSoon = false;
      chrome.torlauncher.initiateAppQuit(this.mRestartWithQuit);
    }
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
    }
    else {
      this.mIsBootstrapDone = false;

      if (aStatusObj._errorOccurred) {
        this.mBootstrapErrorOccurred = true;
        chrome.torlauncher.promptAtStartup.set({ value: true,
                                               scope: "incognito_persistent" });
        var phase = torlauncher.util.getLocalizedBootstrapStatus(aStatusObj,
                                                                 "TAG");
        var reason = torlauncher.util.getLocalizedBootstrapStatus(aStatusObj,
                                                                  "REASON");
        var details = torlauncher.util.getLocalizedString(
            'tor_bootstrap_failed_details');
        details = details.replace('%1$S', phase);
        details = details.replace('%2$S', reason);
        //var details = torlauncher.util.getFormattedLocalizedString(
        //                  "tor_bootstrap_failed_details", [phase, reason], 2);
        console.warn("Tor bootstrap error: [" + aStatusObj.TAG +
                                 "/" + aStatusObj.REASON + "] " + details);

        if ((aStatusObj.TAG != this.mLastTorWarningPhase) ||
            (aStatusObj.REASON != this.mLastTorWarningReason)) {
          this.mLastTorWarningPhase = aStatusObj.TAG;
          this.mLastTorWarningReason = aStatusObj.REASON;

          var msg = torlauncher.util.getLocalizedString("tor_bootstrap_failed");
          torlauncher.util.showAlert(null, msg + "\n\n" + details).then(
            function () {
              chrome.runtime.sendMessage({ 'kind': "TorBootstrapError" });
            }
          );
        }
      }
    }
  }, // _processBootstrapStatus()

  // Returns a kDefaultBridgesStatus value.
  _defaultBridgesStatus: function* ()
  {
    var defaultBridgeType =
                  yield torlauncher.util.prefGet(this.kPrefDefaultBridgeType);
    if (!defaultBridgeType)
      return this.kDefaultBridgesStatus_NotInUse;

    var bridgeArray = yield *torlauncher.util.defaultBridges();
    if (!bridgeArray || (0 == bridgeArray.length))
      return this.kDefaultBridgesStatus_BadConfig;

    return this.kDefaultBridgesStatus_InUse;
  },

  _configureDefaultBridges: function*() {
    var settings = {};
    var bridgeArray = yield *torlauncher.util.defaultBridges();
    var useBridges =  (bridgeArray &&  (bridgeArray.length > 0));
    settings["UseBridges"] = useBridges;
    settings["Bridge"] = bridgeArray;
    var errObj = {};
    var didSucceed =
        yield *this.mProtocolSvc.TorSetConfWithReply(settings, errObj);

    settings = {};
    settings["DisableNetwork"] = false;
    if (!(yield *this.mProtocolSvc.TorSetConfWithReply(
            settings, (didSucceed) ? errObj : null))) {
      didSucceed = false;
    }

    if (didSucceed)
      yield *this.mProtocolSvc.TorSendCommand("SAVECONF");
    else
      yield torlauncher.util.showSaveSettingsAlert(null, errObj.details);
  },

  // If this window is already open, put up "starting tor" panel, focus it and return.
  // Otherwise, open the network settings dialog and block until it is closed.
  _openNetworkSettings: function(aIsInitialBootstrap, aStartAtWizardPanel)
  {
    return new Promise(function (resolve, reject) {
      var win = this._networkSettingsWindow;
      if (win) {
        // Return to "Starting tor" panel if being asked to open & dlog already exists.
        win.contentWindow.showStartingTorPanel();
        win.focus();
        resolve();
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

        createdWindow.onClosed.addListener(resolve);
      });
    }.bind(this));
  },

  get _networkSettingsWindow() {
    return chrome.app.window.get(this.kNetworkSettingsWindowId);
  },

  _openProgressDialog: function() {
    var _this = this;
    return new Promise(function (resolve, reject) {
      var chromeURL = "progress.html";

      chrome.app.window.create(chromeURL, {
        id: _this.kProgressDialogWindowId,
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
          if (_this.TorIsBootstrapDone && _this._networkSettingsWindow)
            _this._networkSettingsWindow.close();
          resolve();
        });
      });
    });
  }
};

torlauncher.torProcessService = new torlauncher.TorProcessService();
