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

// pop front bytes from string that is passed by reference
// and return bytes' int value
Object.prototype.readBytes = function (num) {
  if (num < 1 || num > this.toString().length)
    return 0;

  var res = this.toString.substr(0, num);

  var val = this.toString().substr(num);
  obj.valueOf = obj.toSource = obj.toString = function(){ return val; };

  return res;
}

torlauncher.TorProtocolService = function () {
  chrome.sockets.tcp.onReceive.addListener(
      this._onTorSocketDataReceived.bind(this));
  chrome.sockets.tcp.onReceiveError.addListener(
      this._onTorSocketReceiveError.bind(this));
};

torlauncher.TorProtocolService.prototype = {
  kSocketTimeoutAlarmName: "torlauncher.alarm.socketTimeout",

  mControlHost: null,
  mControlPort: null,
  mControlPassword: null,

  initWithPromise: function () {
    _this = this;
    return new Promise(function (resolve, reject) {
      chrome.alarms.onAlarm.addListener(_this.onAlarm.bind(_this));

      chrome.torlauncher.getTorServiceSettings(function (details) {
        _this.mControlHost = details.controlHost;
        _this.mControlPort = details.controlPort;
        _this.mControlPassword = details.controlPassword;
        resolve();
      });
    });
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
    return new Promise(function (resolve, reject) {
      if (!aKey || (aKey.length < 1))
        resolve(null);

      var cmd = "GETCONF";
      this.TorSendCommand(cmd, aKey).then(function (reply) {
        if (!this.TorCommandSucceeded(reply)) {
          resolve(reply);
          return;
        }

        resolve(this._parseReply(cmd, aKey, reply));
      }.bind(this), reject);
    }.bind(this));
  },

  // Returns a reply object.  If the GETCONF command succeeded, reply.retVal
  // is set (if there is no setting for aKey, it is set to aDefault).
  TorGetConfStr: function(aKey, aDefault)
  {
    return new Promise (function (resolve, reject) {
      this.TorGetConf(aKey).then(function (reply) {
        if (this.TorCommandSucceeded(reply))
        {
          if (reply.lineArray.length > 0)
            reply.retVal = reply.lineArray[0];
          else
            reply.retVal = aDefault;
        }

        resolve(reply);
      }.bind(this), reject);
    }.bind(this));
  },

  // Returns a reply object.  If the GETCONF command succeeded, reply.retVal
  // is set (if there is no setting for aKey, it is set to aDefault).
  TorGetConfBool: function(aKey, aDefault)
  {
    return new Promise (function (resolve, reject) {
      this.TorGetConf(aKey).then(function (reply) {
        if (this.TorCommandSucceeded(reply))
        {
          if (reply.lineArray.length > 0)
            reply.retVal = ("1" == reply.lineArray[0]);
          else
            reply.retVal = aDefault;
        }

        return resolve(reply);
      }.bind(this), reject);
    }.bind(this));
  },

  // Perform a SETCONF command.
  // aSettingsObj should be a JavaScript object with keys (property values)
  // that correspond to tor config. keys.  The value associated with each
  // key should be a simple string, a string array, or a Boolean value.
  // If a fatal error occurs, null is returned.  Otherwise, a reply object is
  // returned.
  TorSetConf: function(aSettingsObj)
  {
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
              cmdArgs += '=' + this._strEscape(val[i]);
            }
          }
          else if ("string" == valType)
            cmdArgs += '=' + this._strEscape(val);
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

      this.TorSendCommand("SETCONF", cmdArgs).then(resolve, reject);

    }.bind(this)); // return value of Promise type
  }, // TorSetConf()

  // Returns true if successful.
  // Upon failure, aErrorObj.details will be set to a string.
  TorSetConfWithReply: function(aSettingsObj, aErrorObj)
  {
    return new Promise(function (resolve, reject) {
      this.TorSetConf(aSettingsObj).then(function (reply) {
        var didSucceed = this.TorCommandSucceeded(reply);
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
      }.bind(this), reject);
    }.bind(this));
  },

  // If successful, sends a "TorBootstrapStatus" notification.
  TorRetrieveBootstrapStatus: function()
  {
    return new Promise(function (resolve, reject) {
      var onRejectRetrieval = function () {
        console.warn("TorRetrieveBootstrapStatus: command failed")
      };

      var cmd = "GETINFO";
      var key = "status/bootstrap-phase";
      this.TorSendCommand(cmd, key).then(function (reply) {
        if (!this.TorCommandSucceeded(reply)) {
          onRejectRetrieval();
          return;
        }

        // A typical reply looks like:
        //  250-status/bootstrap-phase=NOTICE BOOTSTRAP PROGRESS=100 TAG=done SUMMARY="Done"
        //  250 OK
        reply = this._parseReply(cmd, key, reply);
        if (reply.lineArray)
          this._parseBootstrapStatus(reply.lineArray[0]);

        resolve();
      }.bind(this), onRejectRetrieval);
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
  _parseBootstrapStatus: function(aStatusMsg)
  {
    if (!aStatusMsg || (0 == aStatusMsg.length))
      return null;

    var sawBootstrap = false;
    var sawCircuitEstablished = false;
    var statusObj = {};
    statusObj.TYPE = "NOTICE";

    // The following code assumes that this is a one-line response.
    var paramArray = this._splitReplyLine(aStatusMsg);
    for (var i = 0; i < paramArray.length; ++i)
    {
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

    if (!sawBootstrap)
    {
      var logLevel = ("NOTICE" == statusObj.TYPE) ? 3 : 4;
      TorLauncherLogger.log(logLevel, aStatusMsg);
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
        _this._getConnection().then(
          function(conn) {
            if (conn)
              return _this._sendCommand(conn, aCmd, aArgs);
          },
          function () {
            console.warn("_getConnection failed");;
            reject();
          }
        ).then(
          // success handler
          function (reply) {
            if (reply === undefined)
              reject();

            if (reply) {
              _this._returnConnection(conn); // Return for reuse.
              resolve(reply);
              return;
            }

            _this._closeConnection(conn);  // Connection is bad.
            reject();
          },

          // error handler for _sendCommand:
          function () {
            console.warn("Exception on control port");
            this._closeConnection(conn);
            reject();
          })
        );
      };

      // try to send command two times
      // FIXME: subject for garbage collection
      new Promise(attemptFunc).then(rootResolve, function () {
        new Promise(attemptFunc).then(rootResolve, rootReject);
      });
    }.bind(this));
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
    return new Promise(function (resolve, reject) {
      if (this.mEventMonitorConnection) {
        resolve();
        return;
      }

      this._openAuthenticatedConnection(true).then(
        function (conn) {
          // TODO: optionally monitor INFO and DEBUG log messages.
          var events = "STATUS_CLIENT NOTICE WARN ERR";

          var onSetEventsError = function () {
            console.warn("SETEVENTS failed");
            this._closeConnection(conn);
            reject();
          }.bind(this);

          var reply = this._sendCommand(conn, "SETEVENTS", events).then(
            function (reply) {
              if (!this.TorCommandSucceeded(reply)) {
                onSetEventsError();
                return;
              }

              this.mEventMonitorConnection = conn;
              this._waitForEventData();
              resolve();
            }.bind(this)
          ).catch(
            function (nullReply) {
              console.assert(nullReply === null);
              onSetEventsError();
            }.bind(this)
          );
        }.bind(this)
      ).catch(
        // err handler for _openAuthenticatedQuestion
        function () {
          console.warn("TorStartEventMonitor failed to create control port connection");
          reject();
        }
      );
    }.bind(this));
  },

  // // Returns true if the log messages we have captured contain WARN or ERR.
  // get TorLogHasWarnOrErr()
  // {
  //   if (!this.mTorLog)
  //     return false;

  //   for (var i = this.mTorLog.length - 1; i >= 0; i--)
  //   {
  //     var logObj = this.mTorLog[i];
  //     if ((logObj.type == "WARN") || (logObj.type == "ERR"))
  //       return true;
  //   }

  //   return false;
  // },

  // // Returns captured log message as a text string (one message per line).
  // // If aCountObj is passed, aCountObj.value is set to the message count.
  // TorGetLog: function(aCountObj)
  // {
  //   let s = "";
  //   if (this.mTorLog)
  //   {
  //     let dateFmtSvc = Cc["@mozilla.org/intl/scriptabledateformat;1"]
  //                     .getService(Ci.nsIScriptableDateFormat);
  //     let dateFormat = dateFmtSvc.dateFormatShort;
  //     let timeFormat = dateFmtSvc.timeFormatSecondsForce24Hour;
  //     let eol = (TorLauncherUtil.isWindows) ? "\r\n" : "\n";
  //     let count = this.mTorLog.length;
  //     if (aCountObj)
  //       aCountObj.value = count;
  //     for (let i = 0; i < count; ++i)
  //     {
  //       let logObj = this.mTorLog[i];
  //       let secs = logObj.date.getSeconds();
  //       let timeStr = dateFmtSvc.FormatDateTime("", dateFormat, timeFormat,
  //                        logObj.date.getFullYear(), logObj.date.getMonth() + 1,
  //                            logObj.date.getDate(), logObj.date.getHours(),
  //                            logObj.date.getMinutes(), secs);
  //       if (' ' == timeStr.substr(-1))
  //         timeStr = timeStr.substr(0, timeStr.length - 1);
  //       let fracSecsStr = "" + logObj.date.getMilliseconds();
  //       while (fracSecsStr.length < 3)
  //         fracSecsStr += "0";
  //       timeStr += '.' + fracSecsStr;

  //       s += timeStr + " [" + logObj.type + "] " + logObj.msg + eol;
  //     }
  //   }

  //   return s;
  // },


  // Return true if a control connection is established (will create a
  // connection if necessary).
  TorHaveControlConnection: function()
  {
    return new Promise(function (resolve, reject) {
      this._getConnection().then(function (conn) {
        this._returnConnection(conn);
        resolve(conn != null);
      }.bind(this), function () { resolve(false); });
    }.bind(this));
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
    return new Promise(function (resolve, reject) {
      if (this.mControlConnection) {
        if (this.mControlConnection.inUse) {
          console.warn("control connection is in use");
          reject();
        }
      }
      else
        this._openAuthenticatedConnection(false).then(function (conn) {
          this.mControlConnection = conn;
          if (this.mControlConnection)
            this.mControlConnection.inUse = true;

          resolve(this.mControlConnection);
        }.bind(this), reject);
    }.bind(this));
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
        conn = { useCount: 0, socketId = createInfo.socketId };
        chrome.sockets.tcp.connect(createInfo.socketId,
            _this.mControlHost, _this.mControlPort,
            function (result) {
              if (result < 0) {
                console.warn('Network error: ' + result +
                             ' Can\'t connect to Tor client');
                console.warn("failed to open authenticated connection");
                reject();
                return;
              }

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
                    reject();
                    return;
                  }

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
                          resolve(conn);
                          return;
                        }

                        if (!_this.TorCommandSucceeded(reply))
                          console.warn("clear owning controller process failed");

                        resolve(conn);
                      }
                    ),
                    function () {
                      console.warn("clear owning controller process failed");
                      resolve(conn);
                    }
                  );
                },
                function () {
                  console.warn("authenticate failed");
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
    if (aConn && aConn.socketId)
      aConn.socket.setTimeout(Ci.nsISocketTransport.TIMEOUT_READ_WRITE, 15);
  },

  _clearSocketTimeout: function(aConn)
  {
    if (aConn && aConn.socketId)
    {
      var secs = Math.pow(2,32) - 1; // UINT32_MAX
      aConn.socket.setTimeout(Ci.nsISocketTransport.TIMEOUT_READ_WRITE, secs);
    }
  },

  _sendCommand: function(aConn, aCmd, aArgs)
  {
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
        _this._setSocketTimeout(aConn);

        chrome.sockets.tcp.send(
          aConn.socketId,
          torlauncher.util.str2ab(cmd),
          function (sendInfo) {
            if (sendInfo.resultCode < 0) {
              console.warn("Socket send network error: " +
                           sendInfo.resultCode + ":" +
                           chrome.extension.lastError);
              reject();
              return;
            }

            _this.mNextControlConnReadReplyCallback = function (reply) {
              _this._clearSocketTimeout(aConn);
              resolve(reply);
            }
          }
        );
      }
    });
  },

  _onTorSocketDataReceived: function (info) {
    if (this.mControlConnection &&
        info.socketId = this.mControlConnection.socketId) {
      // process control socket replies
      var strData = torlauncher.util.ab2str(info.data);
      if (this.mControlConnection.prevReadReplyCallback ==
          this.mControlConnection.nextReadReplyCallback) {
        this.mControlConnection.accumBuffer += strData;
      } else {
        this.mControlConnection.accumBuffer = strData;
      }

      // pass by reference so that we can modify the string in nested function
      // calls via readBytes() call
      reply = this._torReadReply(Object(this.mControlConnection.accumBuffer));
      this.mControlConnection.nextReadReplyCallback &&
          this.mControlConnection.nextReadReplyCallback(reply);

      this.mControlConnection.prevReadReplyCallback =
          this.mControlConnection.nextReadReplyCallback);

      // clear the reply in case it was read properly, so it's not called again
      if (reply)
        this.mControlConnection.nextReadReplyCallback = null;
    }
  },

  _onTorSocketReceiveError: function (info) {
    if (this.mControlConnection &&
        info.socketId = this.mControlConnection.socketId) {
      // process control socket replies
      console.warn("Socket receive error: " + info.resultCode + ": " +
          chrome.extension.lastError);
      this.mControlConnection.nextReadReplyCallback &&
          this.mControlConnection.nextReadReplyCallback(null);

      // clear the reply, so it's not called again
      this.mControlConnection.nextReadReplyCallback = null;
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
    while(aInput.length) {
      var bytes = aInput.readBytes(1);
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

  _waitForEventData: function()
  {
    if (!this.mEventMonitorConnection)
      return;

    var _this = this;
    var eventReader = // An implementation of nsIInputStreamCallback.
    {
      onInputStreamReady: function(aInStream)
      {
        if (!_this.mEventMonitorConnection ||
            (_this.mEventMonitorConnection.inStream != aInStream))
        {
          return;
        }

        try
        {
          var binStream = _this.mEventMonitorConnection.binInStream;
          var bytes = binStream.readBytes(binStream.available());
          if (!_this.mEventMonitorBuffer)
            _this.mEventMonitorBuffer = bytes;
          else
            _this.mEventMonitorBuffer += bytes;
          _this._processEventData();

          _this._waitForEventData();
        }
        catch (e)
        {
          // Probably we got here because tor exited.  If tor is restarted by
          // Tor Launcher, the event monitor will be restarted too.
          TorLauncherLogger.safelog(4, "Event monitor read error", e);
          _this._shutDownEventMonitor();
        }
      }
    };

    var curThread = Cc["@mozilla.org/thread-manager;1"].getService()
                      .currentThread;
    var asyncInStream = this.mEventMonitorConnection.inStream
                            .QueryInterface(Ci.nsIAsyncInputStream);
    asyncInStream.asyncWait(eventReader, 0, 0, curThread);
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
        let line = replyData.substring(0, idx);
        replyData = replyData.substring(idx + 1);
        let len = line.length;
        if ((len > 0) && ('\r' == line.substr(len - 1)))
          line = line.substr(0, len - 1);

        TorLauncherLogger.safelog(2, "Event response: ", line);
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
      TorLauncherLogger.log(4, "Unexpected event status code: "
                               + aReply.statusCode);
      return;
    }

    // TODO: do we need to handle multiple lines?
    let s = aReply.lineArray[0];
    let idx = s.indexOf(' ');
    if ((idx > 0))
    {
      let eventType = s.substring(0, idx);
      let msg = s.substr(idx + 1);
      switch (eventType)
      {
        case "WARN":
        case "ERR":
          // Notify so that Copy Log can be enabled.
          var obsSvc = Cc["@mozilla.org/observer-service;1"]
                         .getService(Ci.nsIObserverService);
          obsSvc.notifyObservers(null, "TorLogHasWarnOrErr", null);
          // fallthru
        case "DEBUG":
        case "INFO":
        case "NOTICE":
          var now = new Date();
          let logObj = { date: now, type: eventType, msg: msg };
          if (!this.mTorLog)
            this.mTorLog = [];
          else
          {
            var maxEntries =
                    TorLauncherUtil.getIntPref(this.kPrefMaxTorLogEntries, 0);
            if ((maxEntries > 0) && (this.mTorLog.length >= maxEntries))
              this.mTorLog.splice(0, 1);
          }
          this.mTorLog.push(logObj);

          // We could use console.info(), console.error(), and console.warn()
          // but when those functions are used the console output includes
          // extraneous double quotes.  See Mozilla bug # 977586.
          if (this.mConsoleSvc)
          {
            let s = "Tor " + logObj.type + ": " + logObj.msg;
            this.mConsoleSvc.logStringMessage(s);
          }
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
      dump(aObjDesc + " is undefined" + "\n");
      return;
    }

    for (var prop in aObj)
    {
      let val = aObj[prop];
      if (Array.isArray(val))
      {
        for (let i = 0; i < val.length; ++i)
          dump(aObjDesc + "." + prop + "[" + i + "]: " + val + "\n");
      }
      else
        dump(aObjDesc + "." + prop + ": " + val + "\n");
    }
  }
};
