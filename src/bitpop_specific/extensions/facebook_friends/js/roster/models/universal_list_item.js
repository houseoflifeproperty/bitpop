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

Chat.Models.UniversalListItem = Ember.Object.extend({
	type: null,
	category: null,
	
	facebook_uid: function () {
		var jid_ = Strophe.getBareJidFromJid(this.get('jid'));
		var matches = jid_.match(/\-?(\d+)@.*/);
		console.assert(matches.length === 2);
		if (matches.length === 2)
			return matches[1];
		return null;
	}.property('jid').cacheable(),

	categoriesForFriendEntry: function () {
		var res = null;
		if (this.get('type') == 'friend_entry') {
			res = [ this.get('category') ];
			if (this.get('category') == 'online' &&
				(this.get('is_fav') || this.get('daysSinceLastActive') <= 10)) {
				res.push('online-top');
			} else {
				res.push('online-bottom');
			}
		}
		return res;
	}.property('category', 'type', 'is_fav', 'daysSinceLastActive'),

	data_id: function () {
		if (this.get('type') != 'friend_entry')
			return this.get('type') + ':' + this.get('category');
		else
			return this.get('facebook_uid');
	}.property('category', 'type', 'facebook_uid'),

	avatar_url: function () {
        return 'https://graph.facebook.com/' + this.get('facebook_uid') + '/picture';
    }.property('facebook_uid'),
});