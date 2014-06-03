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

Chat.Controllers.LocalStorage = Ember.Object.extend({
	facebook_uid: function (jid) {
		var jid_ = Strophe.getBareJidFromJid(jid);
		var matches = jid_.match(/\-?(\d+)@.*/);
		if (!matches)
			return 'user';
		console.assert(matches.length === 2);
		if (matches.length === 2)
			return matches[1];
		return null;
	},

	saveFriendListAccordionOpenedState: function (self_jid, accordion_category, open_flag) {
		var key = this.facebook_uid(self_jid);
			storageData = localStorage.getItem(key),
		    keyData = storageData ? JSON.parse(storageData) : { accordionData: {} };
		if (!('accordionData' in keyData)) {
			keyData.accordionData = {};
		}
		var accordionData = keyData.accordionData;
		accordionData[accordion_category] = open_flag;
		localStorage.setItem(key, JSON.stringify(keyData));
	},

	getFriendListAccordionOpenedState: function (self_jid, accordion_category) {
		var key = this.facebook_uid(self_jid),
			storageData = localStorage.getItem(key);
		if (!storageData)
			return true;
		var keyData = JSON.parse(storageData);
		if (!('accordionData' in keyData))
			return true;
		var value = keyData.accordionData[accordion_category];
		if (value === undefined)
			return true;
		else
			return value;
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

	setUserFavState: function (self_jid, friend_jid, isFavorite) {
		var obj = this.dataObjectForChat(friend_jid, self_jid);
		obj.is_fav = isFavorite;
		this.saveDataObjectForChat(friend_jid, self_jid, obj);
	},

	getUserFavState: function (self_jid, friend_jid) {
		var obj = this.dataObjectForChat(friend_jid, self_jid);
		if ('is_fav' in obj) {
			return obj.is_fav;
		} else
			return false;
	},

	saveRoster: function (self_jid, dataObject) {
		var key = this.facebook_uid(self_jid) + ':roster';
		localStorage.setItem(key, JSON.stringify(dataObject));
	},

	getSavedRoster: function (self_jid) {
		var key = this.facebook_uid(self_jid) + ':roster';
		var res = null;
		
		if (key in localStorage) {
			res = JSON.parse(localStorage.getItem(key));
		}

		return res;
	}
});

Chat.Controllers.localStorage = Chat.Controllers.LocalStorage.create();