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

if (!Chat.Globals) Chat.Globals = {};

// helpers
Chat.Globals.isObject = function (obj) {
  return obj && (typeof obj  === "object");
};

Chat.Globals.isArray = function (obj) { 
  return Chat.Globals.isObject(obj) && (obj instanceof Array);
};

Chat.Controllers.LocalStorage = Ember.Object.extend({
  facebook_uid: function (jid) {
    var jid_ = Strophe.getBareJidFromJid(jid);
    var matches = jid_.match(/\-?(\d+)@.*/);
    console.assert(matches.length === 2);
    if (matches.length === 2)
      return matches[1];
    return null;
  },

  store_index: function (friend_uid, self_uid) {
    return friend_uid + ':' + self_uid;
  },

  dataObjectForChat: function (friend_jid, self_jid) {
    var friend = this.facebook_uid(friend_jid);
    var self = this.facebook_uid(self_jid);

    var key = this.store_index(friend, self);

    if (key in localStorage) {
      var res = localStorage.getItem(key);
      return JSON.parse(res);
    } else 
    return null;
  },

  saveDataObjectForChat: function (friend_jid, self_jid, dataObject) {
    var friend = this.facebook_uid(friend_jid);
    var self = this.facebook_uid(self_jid);

    var key = this.store_index(friend, self);

    localStorage.setItem(key, JSON.stringify(dataObject));
  },

  addChatMessageToDataObject: function (message) {
    var from = message.get('from'),
    to = message.get('to'),
    direction = message.get('direction') || 'incoming',
    friend_jid, self_jid;

    if (direction === 'outgoing') {
      friend_jid = to;
      self_jid = from;
    } else {
      friend_jid = from;
      self_jid = to;
    }

    var obj = this.dataObjectForChat(friend_jid, self_jid) || {};
    if (!('history' in obj))
      obj.history = [];
    var history = obj.history;

    if (history.length === 100) {
      history.shift();
    }
    history.push(message.getProperties('body', 'createdAt', 'from', 'to', 'direction'));

    this.saveDataObjectForChat(friend_jid, self_jid, obj);
  },

  preprocessMessageText: function (msgText) {
    if (!msgText)
      return '<span style="color: #ff4444">&lt;Invalid message&gt;</span>';

    var res = msgText.replace(/&/g, "&amp;")
                     .replace(/</g, "&lt;")
                     .replace(/>/g, "&gt;");
    return $.autolink(res, {'target': '_blank', 'tabIndex': '-1'});
  },

  fillFromApiData: function (friend_jid, self_jid, api_data) {
    var obj = this.dataObjectForChat(friend_jid, self_jid) || {};
    obj.history = [];
    var history = obj.history;

    for (var i = api_data.length-1; i >= 0; --i) {
      var msg = api_data[i];
      var body = msg.body ? this.preprocessMessageText(msg.body) : '';
      if (msg.attachment &&
        ((Chat.Globals.isArray(msg.attachment) && msg.attachment.length > 0) ||
          (!Chat.Globals.isArray(msg.attachment) && Chat.Globals.isObject(msg.attachment)))) {
        if (body.length)
            body += '<br/>';
        if (msg.attachment.sticker_id) {
          body += '<img class="sticker-img" src="' + msg.attachment.href + '" alt="Sticker" />'
        } else {
          body += '-- Attachments: --<br/>';
          body += '<a href="https://www.facebook.com/messages/' + this.facebook_uid(friend_jid)
                  + '" title="Click to view the attachment" target="_blank" '
                  + 'tabIndex="-1">View Attachments</a>';
        }
      }
      history.push({ 
        "body": body,
        "createdAt": new Date(msg.created_time * 1000).getTime(),
        "direction": (msg.author_id == +this.facebook_uid(self_jid)) ? 'outgoing' : 'incoming',
        "from": (msg.author_id == +this.facebook_uid(self_jid)) ? self_jid : friend_jid, /* should care about this. sadly... */
        "to": (msg.author_id == +this.facebook_uid(self_jid)) ? friend_jid : self_jid
      });
    }

    this.saveDataObjectForChat(friend_jid, self_jid, obj);
  },

  chatMessages: function (friend_jid, self_jid) {
    var obj = this.dataObjectForChat(friend_jid, self_jid) || {};
    return obj.history || [];
  },

  saveTextfieldValue: function (friend_jid, self_jid, value) {
    var obj = this.dataObjectForChat(friend_jid, self_jid) || {};
    obj.textfieldValue = value;
    this.saveDataObjectForChat(friend_jid, self_jid, obj);
  },

  textfieldValue: function (friend_jid, self_jid) {
    var obj = this.dataObjectForChat(friend_jid, self_jid) || {};
    return obj.textfieldValue || '';
  }
});

Chat.Controllers.localStorage = Chat.Controllers.LocalStorage.create();