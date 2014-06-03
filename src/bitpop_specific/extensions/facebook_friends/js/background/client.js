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

// TODO:
// - bare/full JIDs
//   - send messages using full JID if available
//   - forget full JID on presence change (from online to offline-ish)
// - properly parse activity messages (?)
// - offline (delayed) messages (?)
// - automatic reconnecting... (?)
// - fetch user data (avatar, metadata) (?)

String.prototype.hashCode = function() {
  var hash = 0, i, chr, len;
  if (this.length == 0) return hash;
  for (i = 0, len = this.length; i < len; i++) {
    chr   = this.charCodeAt(i);
    hash  = ((hash << 5) - hash) + chr;
    hash |= 0; // Convert to 32bit integer
  }
  return hash;
};

var IM = {};

// constructor
IM.Client = function (options) {
    this.host = options.host || '/http-bind';
    this.jid = options.jid;
    this.access_token = options.access_token;
    this.connection = new Strophe.Connection(this.host);
    this.connection.connectionmanager.configure({ autoReconnect: false });
    this.connection.connectionmanager.enable();
    this.jids = {};
    this.errors = 0;

    // TODO: move into a function
    // monitor all traffic in debug mode
    if (options.debug) {
        this.connection.xmlInput = function (xml) {
            console.log('Incoming:');
            console.log(xml);
        };
        this.connection.xmlOutput = function (xml) {
            console.log('Outgoing:');
            console.log(xml);
        };
    }
};

// private properties and methods
IM.Client.prototype._onConnect = function (status) {
    var Status = Strophe.Status;
    this._stropheStatus = status;

    switch (status) {
    case Status.ERROR:

        $.publish('error.client.im');
        console.log('Status.ERROR');
        break;
    case Status.CONNECTING:
        $.publish('connecting.client.im');
        console.log('Status.CONNECTING');
        if (this._connectingTimer) {
            clearTimeout(this._connectingTimer);
        }
        this._connectingTimer = setTimeout(
            _.bind(function () {
                this._connectingTimer = null;
                if (this._prevStropheStatus === Status.CONNECTING) {
                    this.connection.disconnect();
                }
            },this),
            15000);
        break;
    case Status.CONNFAIL:
        $.publish('connfail.client.im');
        console.log('Status.CONNFAIL');
        break;
        case Status.AUTHENTICATING:
        $.publish('authenticating.client.im');
        console.log('Status.AUTHENTICATING');
        // this._authenticatingTimer = setTimeout(
        //     _.bind(function () {
        //         this._authenticatingTimer = null;
        //         this.disconnect();
        //         $.publish('authfail.client.im');
        //     }, this),
        //     5000);
        break;
    case Status.AUTHFAIL:
        $.publish('authfail.client.im');
        console.log('Status.AUTHFAIL');
        break;
    case Status.CONNECTED:
        this._onConnected();
        $.publish('connected.client.im');
        console.log('Status.CONNECTED');
        break;
    case Status.DISCONNECTING:
        $.publish('disconnecting.client.im');
        console.log('Status.DISCONNECTING');
        break;
    case Status.DISCONNECTED:
        $.publish('disconnected.client.im', [ this ]);
        console.log('Status.DISCONNECTED');
        break;
    case Status.ATTACHED:
        $.publish('attached.client.im');
        console.log('Status.ATTACHED');
        break;
    }

    this._prevStropheStatus = status;
    return true;
};

// IM.Client.prototype._onUserVCardReceived = function (iq) {
//     var userName = $(iq).find('FN').text();
//     $.publish('clientJidAndNameDetermined.client.im', [this.connection.jid, userName]);

//     // get friend list
//     this.getRoster(null, _.bind(this._onRoster, this));

//     // monitor friend list changes
//     this.connection.addHandler(_.bind(this._onRosterChange, this), Strophe.NS.ROSTER, 'iq', 'set');

//     // monitor friends presence changes
//     this.connection.addHandler(_.bind(this._onPresenceChange, this), null, 'presence');

//     // monitor incoming chat messages
//     this.connection.addHandler(_.bind(this._onMessage, this), null, 'message', 'chat');

//     // notify others that we're online and request their presence status
//     this.presence();
// };

IM.Client.prototype._onConnected = function () {
    // JID set after connection may differ from the initial one
    this.jid = Strophe.getBareJidFromJid(this.connection.jid);
    $.publish('clientJidAndNameDetermined.client.im', [this.connection.jid, 'Me']);
    
    // this.connection.vcard.get(_.bind(this._onUserVCardReceived, this), this.jid,
    //     _bind(function () {
    //         console.error('Failed to get VCARD for current user. Retrying in 5 seconds...');
    //         setTimeout(_.bind(this._onConnected, this), 5000);
    //     }, this)
    // );
    // delegate further initialization to _onUserVCardReceived func

    // get friend list
    this.getRoster(null, _.bind(this._onRoster, this));

    // monitor friend list changes
    this.connection.addHandler(_.bind(this._onRosterChange, this), Strophe.NS.ROSTER, 'iq', 'set');

    // monitor friends presence changes
    this.connection.addHandler(_.bind(this._onPresenceChange, this), null, 'presence');

    // monitor incoming chat messages
    this.connection.addHandler(_.bind(this._onMessage, this), null, 'message', 'chat');

    // notify others that we're online and request their presence status
    this.presence();
};

IM.Client.prototype._onPresenceChange = function (stanza) {
    stanza = $(stanza);

    // @show: possible values: XMPP native 'away', 'chat', 'dnd', 'xa' and 2 custom 'online' and 'offline'
    // @status: human-readable string e.g. 'on vacation'

    var fullJid = stanza.attr('from'),
        bareJid = Strophe.getBareJidFromJid(fullJid),
        show = stanza.attr('type') === 'unavailable' ? 'offline' : 'online',
        message = {
            from: fullJid,
            type: stanza.attr('type') || 'available',
            show: stanza.find('show').text() || show,
            status: stanza.find('status').text()
        };

    // Reset addressing
    // if online
    this.jids[bareJid] = fullJid;
    // else
    // this.jids[bareJid] = bareJid;

    $.publish('presence.client.im', message);
    return true;
};

IM.Client.prototype._onMessage = function (stanza) {
    // Process typing notifications first
    var composing = stanza.getElementsByTagName('composing');
    var paused = stanza.getElementsByTagName('active');

    if (composing.length > 0 || paused.length > 0) {
        $.publish('typing.client.im', { 
            'is_typing': (composing.length > 0),
            'from_jid': Strophe.getBareJidFromJid($(stanza).attr('from'))
        });
    }

    // Next - process the message itself
    stanza = $(stanza);

    var fullJid = stanza.attr('from'),
        bareJid = Strophe.getBareJidFromJid(fullJid),
        body = stanza.find('body').text(),
        // TODO: fetch activity
        activity = 'active',
        message = {
            id: stanza.attr('id') || (fullJid + (new Date()).toString()).hashCode().toString(),
            from: fullJid,
            body: body,
            activity: activity,
            to: stanza.attr('to')
        };

    console.log('Msg ID: ' + message.id);
    // Reset addressing
    this.jids[bareJid] = fullJid;

    console.log(stanza.attr('to'));
    $.publish('message.client.im', message);
    return true;
};

IM.Client.prototype._onRoster = function (stanza) {
    var message = this._handleRosterStanza(stanza);

    // Wrap message array again into an array,
    // otherwise jQuery will split it into separate arguments
    // when passed to 'bind' function
    $.publish('roster.client.im', [message]);
    return true;
};

IM.Client.prototype._onRosterChange = function (stanza) {
    var message = this._handleRosterStanza(stanza);

    $.publish('rosterChange.client.im', [message]);
    return true;
};

IM.Client.prototype._handleRosterStanza = function (stanza) {
    var self = this,
        items = $(stanza).find('item');

    return items.map(function (index, item) {
        item = $(item);

        var fullJid = item.attr('jid'),
            bareJid = Strophe.getBareJidFromJid(fullJid);

        // Setup addressing
        self.jids[bareJid] = fullJid;

        return {
            jid: fullJid,
            name: item.attr('name'),
            subscription: item.attr('subscription')
        };
    }).get();
};


// public properties and methods
IM.Client.prototype.connect = function () {
    this.connection.sync = false;
    //this.connection.connect(this.jid, this.password, _.bind(this._onConnect, this));
    this.connection.facebookConnect(
        this.jid,
        _.bind(this._onConnect, this),
        60,
        1,
        FB.APPLICATION_ID,
        this.access_token
    );
    return this;
};

IM.Client.prototype.disconnect = function () {
    // sync prop doesn't work currently
    this.connection.sync = true; // Switch to using synchronous requests since this is typically called onUnload.
    this.connection.flush();
    this.connection.disconnect();
    this.connection.sync = false;
};

IM.Client.prototype.send = function (stanza) {
    this.connection.send(stanza);
};

IM.Client.prototype.iq = function (stanza, error, success) {
    this.connection.sendIQ(stanza, success, error);
};

IM.Client.prototype.presence = function (status) {
    var stanza = $pres();
    if (status) {
        stanza.attrs({type: status});
    }
    this.send(stanza);
};

IM.Client.prototype.message = function (to, message) {
    var fullJid = this.jids[to],
        stanza = $msg({
            to: fullJid,
            type: 'chat'
        }).c('body').t(message)
          .up().c('active', {xmlns: "http://jabber.org/protocol/chatstates"});
    this.send(stanza);
};

IM.Client.prototype.getRoster = function (error, success) {
    var stanza = $iq({type: 'get'}).c('query', {xmlns: Strophe.NS.ROSTER});
    this.iq(stanza, error, success);
};

IM.Client.prototype.sendTypingNotification = function (to, value) {
    var notify = $msg({ 'to': to, 'type': "chat" })
                    .c(value, {xmlns:'http://jabber.org/protocol/chatstates'});
    this.send(notify);
};
