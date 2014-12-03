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

// constructor
torlauncher.TorProcessService = function () {
  this.mProtocolSvc = torlauncher.protocol_service; // the only instance
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

  init: function () {
    // this.mObsSvc.addObserver(this, "quit-application-granted", false);
    // this.mObsSvc.addObserver(this, kOpenNetworkSettingsTopic, false);
    // this.mObsSvc.addObserver(this, kUserQuitTopic, false);
    // this.mObsSvc.addObserver(this, kBootstrapStatusTopic, false);

    chrome.runtime.onSuspend.addListener(_.bind(this.onSuspend, this));
    chrome.alarms.onAlarm.addListener(_.bind(this.onAlarm, this));

    const kOpenNetworkSettingsTopic = "TorOpenNetworkSettings";
    const kUserQuitTopic = "TorUserRequestedQuit";
    const kBootstrapStatusTopic = "TorBootstrapStatus";

    chrome.runtime.onMessage.addListener(_.bind(function (message) {
      if (message.kind == kOpenNetworkSettingsTopic) {
        this._openNetworkSettings(false);
      } else if (message.kind == kUserQuitTopic) {
        this.mQuitSoon = true;
        this.mRestartWithQuit = ("restart" == message.param);
      } else if (message.kind == kBootstrapStatusTopic) {
        this._processBootstrapStatus(message.subject);
      }
    }, this));

    torlauncher.util.getShouldOnlyConfigureTorWithPromise().then(
      _.bind(function (should_only_configure_tor) {
        if (should_only_configure_tor)
          this._controlTor();
        else
          torlauncher.util.getShouldStartAndOwnTorWithPromise().then(
            _.bind(function (should_start_and_own_tor) {
              if (should_start_and_own_tor) {
                this._startTor().then(
                  _.bind(this._controlTor(), this)
                );
              }
            }, this);
          );
      }, this);
    );
  },

  onSuspend: function () {
    this.mIsQuitting = true;

    chrome.alarms.clearAll();

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
      console.info("Disconnecting from tor process");
      this.mProtocolSvc.TorCleanupConnection();

      this.mTorProcessStatus = kStatusExited;
    }
  },

  onAlarm: function (alarm) {
    if (alarm.name == kProcessStatusAlarmName) {
      chrome.torlauncher.getTorProcessStatus(_.bind(function (status) {
        var changed = (this.mTorProcessStatus != status);
        this.mTorProcessStatus = status;

        if (changed && this.mTorProcessStatus == this.kStatusExited)
          this.onTorProcessExited();

        if (changed) {
          // TODO: notify observers???
        }
      }, this));
    } else if (alarm.name == kControlConnTimerName) {
      this.onControlConnTimer();
    }
  },

  onTorProcessExited: function () {
      if (this.mControlConnTimer)
      {
        chrome.alarms.clear(kControlConnTimerName);
        this.mControlConnTimer = null;
      }

      //this.mTorProcess = null;
      this.mIsBootstrapDone = false;

      chrome.runtime.sendMessage({ 'kind': "TorProcessExited" });

      if (!this.mIsQuitting)
      {
        this.mProtocolSvc.TorCleanupConnection();

        var s = TorLauncherUtil.getLocalizedString("tor_exited") + "\n\n"
                + TorLauncherUtil.getLocalizedString("tor_exited2");
        console.warn(s);
        var defaultBtnLabel = torlauncher.util.getLocalizedString("restart_tor");
        var cancelBtnLabel = "OK";
        // TODO: localize "OK" button label

        torlauncher.util.showConfirm(null, s, defaultBtnLabel, cancelBtnLabel).then(
          _.bind(function () {
            if (!this.mIsQuitting)
              this._startTor().then(
                _.bind(this._controlTor(), this)
              );
          }, this);
        );
      }
  },

  onControlConnTimer: function () {
    var haveConnection = this.mProtocolSvc.TorHaveControlConnection();
    if (haveConnection)
    {
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
      this.mControlConnTimer = true;
      chrome.alarms.create(kControlConnTimerName, {
        delayInMinutes: this.mControlConnDelayMS / (1000 * 60)
      });
    }
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
    return new Promise(_.bind(function (resolve, reject) {
      this.mTorProcessStatus = this.kStatusUnknown;

      // Start tor with networking disabled if first run or if the
      // "Use Default Bridges of Type" option is turned on.  Networking will
      // be enabled after initial settings are chosen or after the default
      // bridge settings have been configured.
      var defaultBridgeType =
                    TorLauncherUtil.getCharPref(this.kPrefDefaultBridgeType);
      torlauncher.util.prefGetWithPromise('defaultBridgeType').then(
        _.bind(function (defaultBridgeType) {
          var bridgeConfigIsBad = (this._defaultBridgesStatus ==
                                   this.kDefaultBridgesStatus_BadConfig);
          if (bridgeConfigIsBad) {
            var key = "error_bridge_bad_default_type";
            var err = torlauncher.util.getFormattedLocalizedString(key,
                                                         [defaultBridgeType], 1);
            torlauncher.util.showAlert(null, err);
          }

          var disableNetwork = false;
          torlauncher.util.getShouldShowNetworkSettingsWithPromise().then(
            _.bind(function (shouldShowNetworkSettings) {
              if (shouldShowNetworkSettings || defaultBridgeType) {
                disableNetwork = true;
              }

              chrome.torlauncher.startTor(disableNetwork, _.bind(
                function (details) {
                  if (details.succeeded) {
                    this.mTorProcessStatus = this.kStatusStarting;
                    this.mTorProcessStartTime = Date.now();
                    if (details.log_message)
                      console.info(details.log_message);

                    chrome.alarms.create(kProcessStatusAlarmName, {
                      periodInMinutes: 500 / (60 * 1000)  // 500 ms
                    });

                    resolve();
                  } else {
                    this.mTorProcessStatus = this.kStatusExited;
                    if (details.alert_message_key) {
                      var s = torlauncher.util.getLocalizedString(
                          details.alert_message_key);
                      torlauncher.util.showAlert(null, s);
                    }
                    if (details.log_message)
                      console.warn(details.log_message);

                    reject();
                  }
                }, this)
              );
            }, this)
          );
        }, this)
      );
    }, this));
  }, // _startTor()


  _controlTor: function()
  {
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
      _.bind(function (shouldShowNetworkSettings) {
        if (shouldShowNetworkSettings) {
          if (this.mProtocolSvc) {
            panelID = undefined;
            this._openNetworkSettings(true, panelID);
          }
        } else if (this._networkSettingsWindow != null) {
          // If network settings is open, open progress dialog via notification.
          chrome.runtime.sendMessage({ 'kind': "TorOpenProgressDialog" });
        }
        else
        {
          this._openProgressDialog();

          // Assume that the "Open Settings" button was pressed if Quit was
          // not pressed and bootstrapping did not finish.
          if (!this.mQuitSoon && !this.TorIsBootstrapDone)
            this._openNetworkSettings(true);
        }

        // If the user pressed "Quit" within settings/progress, exit.
        if (this.mQuitSoon) {
          this.mQuitSoon = false;

          chrome.torlauncher.initiateAppQuit(this.mRestartWithQuit);
        }
      }, this)
    );
  }, // controlTor()

  _monitorTorProcessStartup: function() {
    this.mControlConnDelayMS = this.kInitialControlConnDelayMS;
    this.mControlConnTimer = true;
    chrome.alarms.create(kControlConnTimerName, {
      delayInMinutes: this.mControlConnDelayMS / (1000 * 60)
    });
  },

  _processBootstrapStatus: function(aStatusObj)
  {
    if (!aStatusObj)
      return;

    if (100 == aStatusObj.PROGRESS)
    {
      this.mIsBootstrapDone = true;
      this.mBootstrapErrorOccurred = false;
      chrome.torlauncher.promptAtStartup.set({ value: false,
                                               scope: "incognito_persistent" });
    }
    else
    {
      this.mIsBootstrapDone = false;

      if (aStatusObj._errorOccurred)
      {
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
            (aStatusObj.REASON != this.mLastTorWarningReason))
        {
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
    if (win)
    {
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
        width:     450,
        height:    450,
        minWidth:  450,
        minHeight: 450,
        maxWidth:  450,
        maxHeight: 450
      }
    }, function (createdWindow) {
      // pass window creation arguments
      createdWindow.contentWindow.windowArgs = {
        isInitialBootstrap: aIsInitialBootstrap,
        startAtWizardPanel: aStartAtWizardPanel
      };
    });
  },

  get _networkSettingsWindow()
  {
    return chrome.app.window.get(this.kNetworkSettingsWindowId);
  },

  _openProgressDialog: function()
  {
    var chromeURL = "progress.html";

    chrome.app.window.create(chromeURL, {
      id: this.kProgressDialogWindowId,
      state: "normal",
      alwaysOnTop: true,
      innerBounds: {
        left:      100,
        top:       100,
        width:     450,
        height:    450,
        minWidth:  450,
        minHeight: 450,
        maxWidth:  450,
        maxHeight: 450
      }
    }, function (createdWindow) {
      // pass window creation arguments
      createdWindow.contentWindow.windowArgs = {
        isBrowserStartup: true
      };
    });
  },
};

torlauncher.torProcessService = new TorProcessService();
