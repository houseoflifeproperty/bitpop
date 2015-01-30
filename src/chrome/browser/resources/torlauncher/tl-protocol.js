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

torlauncher.TorProtocolService = function () {
  var _this = this;
  chrome.sockets.tcp.onReceive.addListener(this._onTorSocketDataReceived.bind(this));
  chrome.sockets.tcp.onReceiveError.addListener(this._onTorSocketReceiveError.bind(this));
  chrome.runtime.getPlatformInfo(function (info) {
    this.mPlatformOs = info.os;
  }.bind(this));
  torlauncher.util.prefGetWithPromise('maxTorLogEntries').then(
    function (maxEntries) {
      this.kMaxTorLogEntries = maxEntries;
    }.bind(this)
  );
};

torlauncher.TorProtocolService.prototype = {
  kSocketTimeoutAlarmName: "torlauncher.alarm.socketTimeout",

  mControlHost: null,
  mControlPort: null,
  mControlPassword: null,

  initWithPromise: function () {
    var _this = this;
    _this._initPromise = new Promise(function (resolve, reject) {
      //chrome.alarms.onAlarm.addListener(function (alarm) { _this._onAlarm(alarm); });

      chrome.torlauncher.getTorServiceSettings(function (details) {
        _this.mControlHost = details.controlHost;
        _this.mControlPort = details.controlPort;
        _this.mControlPassword = details.controlPassword;
        //console.log('getTorServiceSettings completed');
        resolve();
      });
    });
    return _this._initPromise;
  },

  get initPromise() {
    return this._initPromise || null;
  },

  // Public Constants and Methods ////////////////////////////////////////////
  kCmdStatusOK: 250,
  kCmdStatusEventNotification: 650,

  // FIXME
  // Returns Tor password string or null if an error occurs.
  // TorGetPassword: function(aPleaseHash)
  // {
  //   var pw = this.mControlPassword;
  //   return (aPleaseHash) ? this._hashPassword(pw) : pw;
  // },

  // NOTE: Many Tor protocol functions return a reply object, which is a
  // a JavaScript object that has the following fields:
  //   reply.statusCode  -- integer, e.g., 250
  //   reply.lineArray   -- an array of strings returned by tor
  // For GetConf calls, the aKey prefix is removed from the lineArray strings.

  // Perform a GETCONF command.
  // If a fatal error occurs, null is returned.  Otherwise, a reply object is
  // returned.
  TorGetConf: function(aKey)
  {
    var _this = this;
    return new Promise(function (resolve, reject) {
      if (!aKey || (aKey.length < 1))
        reject(null);

      var cmd = "GETCONF";
      _this.TorSendCommand(cmd, aKey).then(function (reply) {
        if (!_this.TorCommandSucceeded(reply)) {
          reject();
          return;
        }

        resolve(_this._parseReply(cmd, aKey, reply));
      }, reject);
    });
  },

  // Returns a reply object.  If the GETCONF command succeeded, reply.retVal
  // is set (if there is no setting for aKey, it is set to aDefault).
  TorGetConfStr: function(aKey, aDefault)
  {
    var _this = this;
    return new Promise (function (resolve, reject) {
      _this.TorGetConf(aKey).then(function (reply) {
        if (_this.TorCommandSucceeded(reply))
        {
          if (reply.lineArray.length > 0)
            reply.retVal = reply.lineArray[0];
          else
            reply.retVal = aDefault;
        } else
          reject();

        resolve(reply);
      }, reject);
    });
  },

  // Returns a reply object.  If the GETCONF command succeeded, reply.retVal
  // is set (if there is no setting for aKey, it is set to aDefault).
  TorGetConfBool: function(aKey, aDefault)
  {
    var _this = this;
    return new Promise (function (resolve, reject) {
      _this.TorGetConf(aKey).then(function (reply) {
        if (_this.TorCommandSucceeded(reply))
        {
          if (reply.lineArray.length > 0)
            reply.retVal = ("1" == reply.lineArray[0]);
          else
            reply.retVal = aDefault;
        } else
          reject();

        resolve(reply);
      }, reject);
    });
  },

  // Perform a SETCONF command.
  // aSettingsObj should be a JavaScript object with keys (property values)
  // that correspond to tor config. keys.  The value associated with each
  // key should be a simple string, a string array, or a Boolean value.
  // If a fatal error occurs, null is returned.  Otherwise, a reply object is
  // returned.
  TorSetConf: function(aSettingsObj)
  {
    var _this = this;
    return new Promise(function (resolve, reject) {
      if (!aSettingsObj)
        reject();

      var cmdArgs;
      for (var key in aSettingsObj)
      {
        if (!cmdArgs)
          cmdArgs = key;
        else
          cmdArgs += ' ' + key;
        var val = aSettingsObj[key];
        if (val)
        {
          var valType = (typeof val);
          if ("boolean" == valType)
            cmdArgs += '=' + ((val) ? '1' : '0');
          else if (Array.isArray(val))
          {
            for (var i = 0; i < val.length; ++i)
            {
              if (i > 0)
                cmdArgs += ' ' + key;
              cmdArgs += '=' + _this._strEscape(val[i]);
            }
          }
          else if ("string" == valType)
            cmdArgs += '=' + _this._strEscape(val);
          else
          {
            console.warn("TorSetConf: unsupported type '" +
                         valType + "' for " + key);
            reject();
          }
        }
      }

      if (!cmdArgs)
      {
        console.warn("TorSetConf: no settings to set");
        reject();
      }

      _this.TorSendCommand("SETCONF", cmdArgs).then(resolve, reject);

    }); // return value of Promise type
  }, // TorSetConf()

  // Resolves if successful.
  // Upon failure, aErrorObj.details will be set to a string and set as
  // a rejected promise result.
  TorSetConfWithReply: function(aSettingsObj, aErrorObj)
  {
    var _this = this;
    return new Promise(function (resolve, reject) {
      _this.TorSetConf(aSettingsObj).then(function (reply) {
        var didSucceed = _this.TorCommandSucceeded(reply);
        if (!didSucceed)
        {
          var details = "";
          if (reply && reply.lineArray)
          {
            for (var i = 0; i < reply.lineArray.length; ++i)
            {
              if (i > 0)
                details += '\n';
              details += reply.lineArray[i];
            }
          }

          if (aErrorObj)
            aErrorObj.details = details;
        }

        if (didSucceed)
          resolve();
        else
          reject(aErrorObj);
      }, reject);
    });
  },

  // If successful, sends a "TorBootstrapStatus" notification.
  TorRetrieveBootstrapStatus: function()
  {
    var _this = this;
    return new Promise(function (resolve, reject) {
      var onRejectRetrieval = function () {
        console.warn("TorRetrieveBootstrapStatus: command failed")
        reject();
      };

      var cmd = "GETINFO";
      var key = "status/bootstrap-phase";
      _this.TorSendCommand(cmd, key).then(function (reply) {
        if (!_this.TorCommandSucceeded(reply)) {
          onRejectRetrieval();
          return;
        }

        // A typical reply looks like:
        //  250-status/bootstrap-phase=NOTICE BOOTSTRAP PROGRESS=100 TAG=done SUMMARY="Done"
        //  250 OK
        reply = _this._parseReply(cmd, key, reply);
        if (reply.lineArray)
          _this._parseBootstrapStatus(reply.lineArray[0]);

        resolve();
      }, onRejectRetrieval);
    });
  },

  // If successful, returns a JS object with these fields:
  //   status.TYPE            -- "NOTICE" or "WARN"
  //   status.PROGRESS        -- integer
  //   status.TAG             -- string
  //   status.SUMMARY         -- string
  //   status.WARNING         -- string (optional)
  //   status.REASON          -- string (optional)
  //   status.COUNT           -- integer (optional)
  //   status.RECOMMENDATION  -- string (optional)
  // A "TorBootstrapStatus" notification is also sent.
  // Returns null upon failure.
  _parseBootstrapStatus: function(aStatusMsg) {
    if (!aStatusMsg || (0 == aStatusMsg.length))
      return null;

    var sawBootstrap = false;
    var sawCircuitEstablished = false;
    var statusObj = {};
    statusObj.TYPE = "NOTICE";

    // The following code assumes that this is a one-line response.
    var paramArray = this._splitReplyLine(aStatusMsg);
    for (var i = 0; i < paramArray.length; ++i) {
      var tokenAndVal = paramArray[i];
      var token, val;
      var idx = tokenAndVal.indexOf('=');
      if (idx < 0)
        token = tokenAndVal;
      else
      {
        token = tokenAndVal.substring(0, idx);
        var valObj = {};
        if (!this._strUnescape(tokenAndVal.substring(idx + 1), valObj))
          continue; // skip this token/value pair.

        val = valObj.result;
      }

      if ("BOOTSTRAP" == token)
        sawBootstrap = true;
      else if ("CIRCUIT_ESTABLISHED" == token)
        sawCircuitEstablished = true;
      else if (("WARN" == token) || ("NOTICE" == token) || ("ERR" == token))
        statusObj.TYPE = token;
      else if (("COUNT" == token) || ("PROGRESS" == token))
        statusObj[token] = parseInt(val, 10);
      else
        statusObj[token] = val;
    }

    if (!sawBootstrap) {
      var logLevel = ("NOTICE" == statusObj.TYPE) ? 3 : 4;
      console.log(aStatusMsg);
      return null;
    }

    // this._dumpObj("BootstrapStatus", statusObj);
    statusObj._errorOccurred = (("NOTICE" != statusObj.TYPE) &&
                                ("warn" == statusObj.RECOMMENDATION));

    // Notify observers.
    chrome.runtime.sendMessage({ 'kind': "TorBootstrapStatus",
                                 'subject': statusObj });
    return statusObj;
  }, // _parseBootstrapStatus()

  // Executes a command on the control port.
  // Return a reply object or null if a fatal error occurs.
  TorSendCommand: function(aCmd, aArgs)
  {
    var _this = this;
    return new Promise(function (rootResolve, rootReject) {
      var attemptFunc = function (resolve, reject) {
        //torlauncher.util.pr_debug('tl-protocol.TorSendCommand.attemptFunc called');
        _this._getConnection().then(
          function(conn) {
            if (!conn) {
              reject();
              return;
            }

            //torlauncher.util.pr_debug('tl-protocol.TorSendCommand _getConnection succeeded. sending command...');
            _this._sendCommand(conn, aCmd, aArgs).then(
              function (reply) {
                //torlauncher.util.pr_debug('tl-protocol.TorSendCommand, _sendCommand succeeded');
                if (reply) {
                  //torlauncher.util.pr_debug('tl-protocol.TorSendCommand, _sendCommand succeeded, reply non-empty. resolving...');
                  _this._returnConnection(conn); // Return for reuse.
                  resolve(reply);
                  return;
                }

                //torlauncher.util.pr_debug('tl-protocol.TorSendCommand, _sendCommand succeeded, reply is null. closing connection and rejecting...');
                _this._closeConnection(conn);  // Connection is bad.
                reject();
              },
              // error handler for _sendCommand:
              function () {
                console.warn("Exception on control port");
                _this._closeConnection(conn);
                reject();
              }
            );
          },
          function () {
            console.warn("_getConnection failed");;
            reject();
          }
        );
      };

      // try to send command two times
      // FIXME: subject for garbage collection
      _this._torSendCommandPromise1 = new Promise(attemptFunc);
      _this._torSendCommandPromise1.then(
        rootResolve,
        function () {
          //torlauncher.util.pr_debug('tl-protocol.TorSendCommand, 2nd attempt');
          _this._torSendCommandPromise2 = new Promise(attemptFunc);
          _this._torSendCommandPromise2.then(rootResolve, rootReject);
        }
      );
    });
  }, // TorSendCommand()

  TorCommandSucceeded: function(aReply)
  {
    return !!(aReply && (this.kCmdStatusOK == aReply.statusCode));
  },

  // TorCleanupConnection() is called during browser shutdown.
  TorCleanupConnection: function()
  {
    this._closeConnection();
    this._shutDownEventMonitor();
  },

  TorStartEventMonitor: function()
  {
    var _this = this;
    return new Promise(function (resolve, reject) {
      if (_this.mEventMonitorConnection) {
        resolve();
        return;
      }

      _this._openAuthenticatedConnection(true).then(
        function (conn) {
          // TODO: optionally monitor INFO and DEBUG log messages.
          var events = "STATUS_CLIENT NOTICE WARN ERR";

          var onSetEventsError = function () {
            console.warn("SETEVENTS failed");
            _this.mTempControlConnection = null;
            _this._closeConnection(conn);
            reject();
          };

          var reply = _this._sendCommand(conn, "SETEVENTS", events).then(
            function (reply) {
              if (!_this.TorCommandSucceeded(reply)) {
                onSetEventsError();
                return;
              }

              _this.mTempControlConnection = null;
              _this.mEventMonitorConnection = conn;
              torlauncher.util.pr_debug("TorStartEventMonitor successfully created event monitor connection");
              resolve();
            },

            function () {
              onSetEventsError();
            }
          );
        }
      ).catch(
        // err handler for _openAuthenticatedConnection
        function () {
          console.warn("TorStartEventMonitor failed to create control port connection");
          reject();
        }
      );
    });
  },

  // Returns true if the log messages we have captured contain WARN or ERR.
  get TorLogHasWarnOrErr()
  {
    if (!this.mTorLog)
      return false;

    for (var i = this.mTorLog.length - 1; i >= 0; i--)
    {
      var logObj = this.mTorLog[i];
      if ((logObj.type == "WARN") || (logObj.type == "ERR"))
        return true;
    }

    return false;
  },

  // Returns captured log message as a text string (one message per line).
  // If aCountObj is passed, aCountObj.value is set to the message count.
  TorGetLog: function(aCountObj)
  {
    var s = "";
    if (this.mTorLog)
    {
      var eol = (this.mPlatformOs == 'win') ? "\r\n" : "\n";
      var count = this.mTorLog.length;
      if (aCountObj)
        aCountObj.value = count;
      for (var i = 0; i < count; ++i)
      {
        var logObj = this.mTorLog[i];
        var secs = logObj.date.getSeconds();
        var timeStr = logObj.date.getFullYear().toString() + '-' +
                      ('0' + (logObj.date.getMonth() + 1).toString()).slice(-2) + '-' +
                      ('0' + logObj.date.getDate().toString()).slice(-2) + ' ' +
                      ('0' + logObj.date.getHours().toString()).slice(-2) + ':' +
                      ('0' + logObj.date.getMinutes().toString()).slice(-2) + ':' +
                      ('0' + secs.toString()).slice(-2);

        var fracSecsStr = "" + logObj.date.getMilliseconds();
        while (fracSecsStr.length < 3)
          fracSecsStr += "0";
        timeStr += '.' + fracSecsStr;

        s += timeStr + " [" + logObj.type + "] " + logObj.msg + eol;
      }
    }

    return s;
  },


  // Return true if a control connection is established (will create a
  // connection if necessary).
  TorHaveControlConnection: function()
  {
    var _this = this;
    return new Promise(function (resolve, reject) {
      _this._getConnection().then(
        function (conn) {
          _this._returnConnection(conn);
          resolve(conn != null);
        },
        function () { resolve(false); }
      );
    });
  },


  // Private Member Variables ////////////////////////////////////////////////
  mControlPort: null,
  mControlHost: null,
  mControlPassword: null,     // JS string that contains hex-encoded password.
  mControlConnection: null,   // This is cached and reused.
  mEventMonitorConnection: null,
  mEventMonitorBuffer: null,
  mEventMonitorInProgressReply: null,
  // mTorLog: null,      // Array of objects with date, type, and msg properties.


  // Private Methods /////////////////////////////////////////////////////////

  // Returns a JS object that contains these fields:
  //   inUse        // Boolean
  //   useCount     // Integer
  //   socketId     // Integer

  // Not used:
  //   inStream     // nsIInputStream
  //   binInStream  // nsIBinaryInputStream
  //   binOutStream // nsIBinaryOutputStream
  _getConnection: function()
  {
    var _this = this;
    return new Promise(function (resolve, reject) {
      if (_this.mControlConnection) {
        if (_this.mControlConnection.inUse) {
          console.warn("control connection is in use");
          reject();
        }

        _this.mControlConnection.inUse = true;
        resolve(_this.mControlConnection);
      }
      else
        _this._openAuthenticatedConnection(false).then(
          function (conn) {
            _this.mControlConnection = conn;
            if (_this.mControlConnection)
              _this.mControlConnection.inUse = true;

            resolve(_this.mControlConnection);
          },
          reject
        );
    });
  },

  _returnConnection: function(aConn)
  {
    if (aConn && (aConn == this.mControlConnection))
      this.mControlConnection.inUse = false;
  },

  _openAuthenticatedConnection: function(aIsEventConnection)
  {
    var _this = this;
    return new Promise(function (resolve, reject) {
      var conn;
      console.info("Opening control connection to " +
                   _this.mControlHost + ":" + _this.mControlPort);
      chrome.sockets.tcp.create(null, function (createInfo) {
        conn = { useCount: 0, socketId: createInfo.socketId, inUse: false };
        chrome.sockets.tcp.connect(createInfo.socketId,
            _this.mControlHost, _this.mControlPort,
            function (result) {
              if (chrome.runtime.lastError)
                console.warn(chrome.runtime.lastError.message);

              if (result < 0) {
                console.warn('Network error: ' + result +
                             ' Can\'t connect to Tor client');
                console.warn("failed to open authenticated connection");
                reject();
                return;
              }

              _this.mTempControlConnection = conn;

              chrome.sockets.tcp.setPaused(conn.socketId, false);

              // AUTHENTICATE
              var pwdArg = _this._strEscape(_this.mControlPassword);
              if (pwdArg && (pwdArg.length > 0) && (pwdArg.charAt(0) != '"')) {
                // Surround non-hex strings with double quotes.
                const kIsHexRE = /^[A-Fa-f0-9]*$/;
                if (!kIsHexRE.test(pwdArg))
                  pwdArg = '"' + pwdArg + '"';
              }
              _this._sendCommand(conn, "AUTHENTICATE", pwdArg).then(
                function (reply) {
                  if (!_this.TorCommandSucceeded(reply)) {
                    console.warn("authenticate failed");
                    _this.mTempControlConnection = null;
                    reject();
                    return;
                  }

                  //torlauncher.util.pr_debug('authenticate succeeded');

                  if (!aIsEventConnection)
                    torlauncher.util.getShouldStartAndOwnTorWithPromise().then(
                      function (shouldStartAndOwnTor) {
                        if (shouldStartAndOwnTor === undefined)
                          return;

                        if (shouldStartAndOwnTor)
                           return torlauncher.util.getShouldOnlyConfigureTorWithPromise();
                      }
                    ).then(
                      function (shouldOnlyConfigureTor) {
                        if (shouldOnlyConfigureTor === undefined)
                          return;

                        if (!shouldOnlyConfigureTor)
                          // Try to become the primary controller (TAKEOWNERSHIP).
                          return _this._sendCommand(conn, "TAKEOWNERSHIP", null);
                      }
                    ).then(
                      function (reply) {
                        if (reply === undefined)
                          return;

                        if (!_this.TorCommandSucceeded(reply)) {
                          console.warn("take ownership failed");
                        } else
                          return _this._sendCommand(conn, "RESETCONF",
                                                    "__OwningControllerProcess");
                      },
                      function () {
                        console.warn("take ownership failed");
                      }
                    ).then(
                      function (reply) {
                        if (reply === undefined) {
                          _this.mTempControlConnection = null;
                          //torlauncher.util.pr_debug('resolving _openAuthenticatedConnection...');
                          resolve(conn);
                          return;
                        }

                        if (!_this.TorCommandSucceeded(reply))
                          console.warn("clear owning controller process failed");

                        _this.mTempControlConnection = null;
                        //torlauncher.util.pr_debug('resolving _openAuthenticatedConnection...');
                        resolve(conn);
                      },
                      function () {
                        console.warn("clear owning controller process failed");
                        _this.mTempControlConnection = null;
                        //torlauncher.util.pr_debug('resolving _openAuthenticatedConnection...');
                        resolve(conn);
                      }
                    );
                  // IsEventMonitorConnection == true
                  else
                    resolve(conn);
                },
                function () {
                  console.warn("authenticate failed");
                  _this.mTempControlConnection = null;
                  reject();
                }
              );
            }
        );   // connectSocket
      });  // createSocket
    }); // return Promise
  }, // _openAuthenticatedConnection()

  // If aConn is omitted, the cached connection is closed.
  _closeConnection: function(aConn)
  {
    if (!aConn)
      aConn = this.mControlConnection;

    if (aConn && aConn.socketId) {
      chrome.sockets.tcp.disconnect(aConn.socketId, function () {
        chrome.sockets.tcp.close(aConn.socketId);
      });
    }

    if (aConn == this.mControlConnection)
      this.mControlConnection = null;
  },

  _setSocketTimeout: function(aConn)
  {
    if (aConn && aConn.socketId) {
      aConn._socketTimeout =
          setTimeout(this._onAlarm.bind(this,
                                        { name: this.kSocketTimeoutAlarmName, conn: aConn }),
                     15000);
    }
  },

  _clearSocketTimeout: function(aConn)
  {
    if (aConn && aConn.socketId && aConn._socketTimeout) {
      clearTimeout(aConn._socketTimeout);
      aConn._socketTimeout = null;
    }
  },

  _onAlarm: function (alarm) {
    if (alarm.name == this.kSocketTimeoutAlarmName && alarm.conn) {
      //torlauncher.util.pr_debug('tl-protocol: _onAlarm timeout fired')
      if (alarm.conn.mNextControlConnSendCommandTimeoutCallback) {
        alarm.conn.mNextControlConnSendCommandTimeoutCallback();
        alarm.conn.mNextControlConnSendCommandTimeoutCallback = null;
      }
    }
  },

  _sendCommand: function(aConn, aCmd, aArgs)
  {
    //torlauncher.util.pr_debug('tl-protocol._sendCommand: conn = ' + JSON.stringify(aConn))
    var _this = this;
    return new Promise(function (resolve, reject) {
      if (aConn)
      {
        var cmd = aCmd;
        if (aArgs)
          cmd += ' ' + aArgs;
        console.info("Sending Tor command: " + cmd);
        cmd += "\r\n";

        ++aConn.useCount;
        //torlauncher.util.pr_debug('tl-protocol._sendCommand aConn.useCount == ' + aConn.useCount);
        _this._setSocketTimeout(aConn);
        //torlauncher.util.pr_debug('tl-protocol._sendCommand after _setSocketTimeout');

        aConn.mNextControlConnSendCommandTimeoutCallback = reject;

        aConn.mNextControlConnReadReplyCallback = function (reply) {
          //torlauncher.util.pr_debug('controlConnReadReplyCallback called. resolving...');
          _this._clearSocketTimeout(aConn);
          aConn.mNextControlConnSendCommandTimeoutCallback = null;
          torlauncher.util.pr_debug(JSON.stringify(reply));
          resolve(reply);
        };

        chrome.sockets.tcp.send(
          aConn.socketId,
          torlauncher.util.str2ab(cmd),
          function (sendInfo) {
            //torlauncher.util.pr_debug('chrome.sockets.tcp.send callback called');
            if (sendInfo.resultCode < 0) {
              console.warn("Socket send network error: " +
                           sendInfo.resultCode + ":" +
                           chrome.runtime.lastError.message);

              _this._clearSocketTimeout(aConn);
              aConn.mNextControlConnReadReplyCallback = null;
              aConn.mNextControlConnSendCommandTimeoutCallback = null;
              reject();
              return;
            }
          }
        );
        if (chrome.runtime.lastError)
            console.warn('tl-protocol._sendCommand: ' + chrome.runtime.lastError.message);
      }
    });
  },

  _onTorSocketDataReceived: function (info) {
    var controlConnection = null;
    if (this.mControlConnection &&
        info.socketId == this.mControlConnection.socketId)
      controlConnection = this.mControlConnection;
    else if (this.mTempControlConnection &&
             info.socketId == this.mTempControlConnection.socketId)
      controlConnection = this.mTempControlConnection;

    if (controlConnection) {
      //torlauncher.util.pr_debug('tl-protocol._onTorSocketDataReceived: control connection rcvd: ' +
      //    JSON.stringify(info));
      // process control socket replies
      var strData = torlauncher.util.ab2str(info.data);
      var arrData = strData.split('');

      controlConnection.nextReadReplyCallback =
          controlConnection.mNextControlConnReadReplyCallback;

      if (controlConnection.prevReadReplyCallback ==
          controlConnection.nextReadReplyCallback) {
        //torlauncher.util.pr_debug('tl-protocol._onTorSocketDataReceived: prevReadReplyCallback == nextReadReplyCallback');
        //torlauncher.util.pr_debug('tl-protocol._onTorSocketDataReceived strData: ' + strData);
        if (!controlConnection.accumBuffer)
          controlConnection.accumBuffer = [];
        controlConnection.accumBuffer =
            controlConnection.accumBuffer.concat(arrData);
      } else {
        //torlauncher.util.pr_debug('tl-protocol._onTorSocketDataReceived: prevReadReplyCallback != nextReadReplyCallback');
        controlConnection.accumBuffer = arrData;
      }

      reply = this._torReadReply(controlConnection.accumBuffer);
      controlConnection.nextReadReplyCallback &&
          controlConnection.nextReadReplyCallback(reply);

      controlConnection.prevReadReplyCallback =
          controlConnection.nextReadReplyCallback;

      // clear the reply in case it was read properly, so it's not called again
      if (reply)
        controlConnection.nextReadReplyCallback = null;
    } else if (this.mEventMonitorConnection &&
               info.socketId == this.mEventMonitorConnection.socketId) {
      torlauncher.util.pr_debug('tl-protocol._onTorSocketDataReceived: event monitor connection rcvd: ' +
          JSON.stringify(info));

      var bytes = torlauncher.util.ab2str(info.data);

      if (!this.mEventMonitorBuffer) {
        torlauncher.util.pr_debug('tl-protocol._onTorSocketDataReceived: mEventMonitorBuffer non-empty');
        this.mEventMonitorBuffer = bytes;
      } else {
        torlauncher.util.pr_debug('tl-protocol._onTorSocketDataReceived: mEventMonitorBuffer empty');
        this.mEventMonitorBuffer += bytes;
      }
      this._processEventData();
    }
  },

  _onTorSocketReceiveError: function (info) {
    var controlConnection = null;
    if (this.mControlConnection &&
        info.socketId == this.mControlConnection.socketId)
      controlConnection = this.mControlConnection;
    else if (this.mTempControlConnection &&
             info.socketId == this.mTempControlConnection.socketId)
      controlConnection = this.mTempControlConnection;

    if (controlConnection) {
      // process control socket replies
      console.warn("Socket receive error: " + info.resultCode + ": " +
          chrome.runtime.lastError.message);
      controlConnection.nextReadReplyCallback &&
          controlConnection.nextReadReplyCallback(null);

      // clear the reply, so it's not called again
      controlConnection.nextReadReplyCallback = null;
    } else if (this.mEventMonitorConnection &&
               info.socketId == this.mEventMonitorConnection.socketId) {
      console.warn("Event monitor connection error: " + info.resultCode + ": " +
                   chrome.runtime.lastError.message);
      this._shutDownEventMonitor();
    }
  },

  // Returns a reply object.  Blocks until entire reply has been received.
  _torReadReply: function(aInput)
  {
    var replyObj = {};
    do
    {
      var line = this._torReadLine(aInput);
      console.info("Command response: " + line);
    } while (!this._parseOneReplyLine(line, replyObj));

    return (replyObj._parseError) ? null : replyObj;
  },

  // Returns a string.  Blocks until a line has been received.
  _torReadLine: function(aInput)
  {
    var str = "";
    while (aInput.length) {
      var bytes = aInput.shift();
      if ('\n' == bytes)
        break;

      str += bytes;
    }

    var len = str.length;
    if ((len > 0) && ('\r' == str.substr(len - 1)))
      str = str.substr(0, len - 1);
    return str;
  },

  // Returns false if more lines are needed.  The first time, callers
  // should pass an empty aReplyObj.
  // Parsing errors are indicated by aReplyObj._parseError = true.
  _parseOneReplyLine: function(aLine, aReplyObj)
  {
    if (!aLine || !aReplyObj)
      return false;

    if (!("_parseError" in aReplyObj)) {
      aReplyObj.statusCode = 0;
      aReplyObj.lineArray = [];
      aReplyObj._parseError = false;
    }

    if (aLine.length < 4) {
      console.info("Unexpected response: " + aLine);
      aReplyObj._parseError = true;
      return true;
    }

    // TODO: handle + separators (data)
    aReplyObj.statusCode = parseInt(aLine.substr(0, 3), 10);
    var s = (aLine.length < 5) ? "" : aLine.substr(4);
     // Include all lines except simple "250 OK" ones.
    if ((aReplyObj.statusCode != this.kCmdStatusOK) || (s != "OK"))
      aReplyObj.lineArray.push(s);

    return (aLine.charAt(3) == ' ');
  },

  // _parseReply() understands simple GETCONF and GETINFO replies.
  _parseReply: function(aCmd, aKey, aReply)
  {
    if (!aCmd || !aKey || !aReply)
      return;

    var lcKey = aKey.toLowerCase();
    var prefix = lcKey + '=';
    var prefixLen = prefix.length;
    var tmpArray = [];
    for (var i = 0; i < aReply.lineArray.length; ++i)
    {
      var line = aReply.lineArray[i];
      var lcLine = line.toLowerCase();
      if (lcLine == lcKey)
        tmpArray.push("");
      else if (0 != lcLine.indexOf(prefix)) {
        console.warn("Unexpected " + aCmd + " response: " + line);
      }
      else
      {
        var valObj = {};
        if (!this._strUnescape(line.substring(prefixLen), valObj))
        {
          console.warn("Invalid string within " + aCmd +
                       " response: " + line);
        }
        else
          tmpArray.push(valObj.result);
      }
    }

    aReply.lineArray = tmpArray;
    return aReply;
  }, // _parseReply

  // Split aStr at spaces, accounting for quoted values.
  // Returns an array of strings.
  _splitReplyLine: function(aStr)
  {
    var rv = [];
    if (!aStr)
      return rv;

    var inQuotedStr = false;
    var val = "";
    for (var i = 0; i < aStr.length; ++i)
    {
      var c = aStr.charAt(i);
      if ((' ' == c) && !inQuotedStr)
      {
        rv.push(val);
        val = "";
      }
      else
      {
        if ('"' == c)
          inQuotedStr = !inQuotedStr;

        val += c;
      }
    }

    if (val.length > 0)
      rv.push(val);

    return rv;
  },

  // Escape non-ASCII characters for use within the Tor Control protocol.
  // Based on Vidalia's src/common/stringutil.cpp:string_escape().
  // Returns the new string.
  _strEscape: function(aStr)
  {
    // Just return if all characters are printable ASCII excluding SP and "
    const kSafeCharRE = /^[\x21\x23-\x7E]*$/;
    if (!aStr || kSafeCharRE.test(aStr))
      return aStr;

    var rv = '"';
    for (var i = 0; i < aStr.length; ++i)
    {
      var c = aStr.charAt(i);
      switch (c)
      {
        case '\"':
          rv += "\\\"";
          break;
        case '\\':
          rv += "\\\\";
          break;
        case '\n':
          rv += "\\n";
          break;
        case '\r':
          rv += "\\r";
          break;
        case '\t':
          rv += "\\t";
          break;
        default:
          var charCode = aStr.charCodeAt(i);
          if ((charCode >= 0x0020) && (charCode <= 0x007E))
            rv += c;
          else
          {
            // Generate \xHH encoded UTF-8.
            var utf8bytes = unescape(encodeURIComponent(c));
            for (var j = 0; j < utf8bytes.length; ++j)
              rv += "\\x" + this._toHex(utf8bytes.charCodeAt(j), 2);
          }
      }
    }

    rv += '"';
    return rv;
  }, // _strEscape()

  // Unescape Tor Control string aStr (removing surrounding "" and \ escapes).
  // Based on Vidalia's src/common/stringutil.cpp:string_unescape().
  // Returns true if successful and sets aResultObj.result.
  _strUnescape: function(aStr, aResultObj)
  {
    if (!aResultObj)
      return false;

    if (!aStr)
    {
      aResultObj.result = aStr;
      return true;
    }

    var len = aStr.length;
    if ((len < 2) || ('"' != aStr.charAt(0)) || ('"' != aStr.charAt(len - 1)))
    {
      aResultObj.result = aStr;
      return true;
    }

    var rv = "";
    var i = 1;
    var lastCharIndex = len - 2;
    while (i <= lastCharIndex)
    {
      var c = aStr.charAt(i);
      if ('\\' == c)
      {
        if (++i > lastCharIndex)
          return false; // error: \ without next character.

        c = aStr.charAt(i);
        if ('n' == c)
          rv += '\n';
        else if ('r' == c)
          rv += '\r';
        else if ('t' == c)
          rv += '\t';
        else if ('x' == c)
        {
          if ((i + 2) > lastCharIndex)
            return false; // error: not enough hex characters.

          var val = parseInt(aStr.substr(i, 2), 16);
          if (isNaN(val))
            return false; // error: invalid hex characters.

          rv += String.fromCharCode(val);
          i += 2;
        }
        else if (this._isDigit(c))
        {
          if ((i + 3) > lastCharIndex)
            return false; // error: not enough octal characters.

          var val = parseInt(aStr.substr(i, 3), 8);
          if (isNaN(val))
            return false; // error: invalid octal characters.

          rv += String.fromCharCode(val);
          i += 3;
        }
        else // "\\" and others
        {
          rv += c;
          ++i;
        }
      }
      else if ('"' == c)
        return false; // error: unescaped double quote in middle of string.
      else
      {
        rv += c;
        ++i;
      }
    }

    // Convert from UTF-8 to Unicode. TODO: is UTF-8 always used in protocol?
    rv = decodeURIComponent(escape(rv));

    aResultObj.result = rv;
    return true;
  }, // _strUnescape()

  _isDigit: function(aChar)
  {
    const kRE = /^\d$/;
    return aChar && kRE.test(aChar);
  },

  _toHex: function(aValue, aMinLen)
  {
    var rv = aValue.toString(16);
    while (rv.length < aMinLen)
      rv = '0' + rv;

    return rv;
  },

  _ArrayToHex: function(aArray)
  {
    var rv = "";
    if (aArray)
    {
      for (var i = 0; i < aArray.length; ++i)
        rv += this._toHex(aArray[i], 2);
    }

    return rv;
  },

  _shutDownEventMonitor: function()
  {
    if (this.mEventMonitorConnection)
    {
      this._closeConnection(this.mEventMonitorConnection);
      this.mEventMonitorConnection = null;
      this.mEventMonitorBuffer = null;
      this.mEventMonitorInProgressReply = null;
    }
  },

  _processEventData: function()
  {
    var replyData = this.mEventMonitorBuffer;
    if (!replyData)
      return;

    var idx = -1;
    do
    {
      idx = replyData.indexOf('\n');
      if (idx >= 0)
      {
        var line = replyData.substring(0, idx);
        replyData = replyData.substring(idx + 1);
        var len = line.length;
        if ((len > 0) && ('\r' == line.substr(len - 1)))
          line = line.substr(0, len - 1);

        console.info("Event response: " + line);
        if (!this.mEventMonitorInProgressReply)
          this.mEventMonitorInProgressReply = {};
        var replyObj = this.mEventMonitorInProgressReply;
        var isComplete = this._parseOneReplyLine(line, replyObj);
        if (isComplete)
        {
          this._processEventReply(replyObj);
          this.mEventMonitorInProgressReply = null;
        }
      }
    } while ((idx >= 0) && replyData)

    this.mEventMonitorBuffer = replyData;
  },

  _processEventReply: function(aReply)
  {
    if (aReply._parseError || (0 == aReply.lineArray.length))
      return;

    if (aReply.statusCode != this.kCmdStatusEventNotification)
    {
      console.warn("Unexpected event status code: "
                               + aReply.statusCode);
      return;
    }

    // TODO: do we need to handle multiple lines?
    var s = aReply.lineArray[0];
    var idx = s.indexOf(' ');
    if ((idx > 0))
    {
      var eventType = s.substring(0, idx);
      var msg = s.substr(idx + 1);
      switch (eventType)
      {
        case "WARN":
        case "ERR":
          // Notify so that Copy Log can be enabled.
          chrome.runtime.sendMessage({ 'kind': 'TorLogHasWarnOrErr' });
          // fallthru
        case "DEBUG":
        case "INFO":
        case "NOTICE":
          var now = new Date();
          var logObj = { date: now, type: eventType, msg: msg };

          if (!this.mTorLog)
            this.mTorLog = [];
          else
          {
            var maxEntries = this.kMaxTorLogEntries;
            if ((maxEntries > 0) && (this.mTorLog.length >= maxEntries))
              this.mTorLog.splice(0, 1);
          }

          this.mTorLog.push(logObj);

          var s = "Tor " + logObj.type + ": " + logObj.msg;

          if (eventType == "WARN" || eventType == "ERR")
            console.warn(s);
          else
            console.info(s);

          break;
        case "STATUS_CLIENT":
          this._parseBootstrapStatus(msg);
          break;
        default:
          this._dumpObj(eventType + "_event", aReply);
      }
    }
  },

  // Debugging Methods ///////////////////////////////////////////////////////
  _dumpObj: function(aObjDesc, aObj)
  {
    if (!aObjDesc)
      aObjDesc = "JS object";

    if (!aObj)
    {
      console.log(aObjDesc + " is undefined" + "\n");
      return;
    }

    for (var prop in aObj)
    {
      var val = aObj[prop];
      if (Array.isArray(val))
      {
        for (var i = 0; i < val.length; ++i)
          console.log(aObjDesc + "." + prop + "[" + i + "]: " + val + "\n");
      }
      else
        console.log(aObjDesc + "." + prop + ": " + val + "\n");
    }
  }
};

torlauncher.protocolService = new torlauncher.TorProtocolService();
