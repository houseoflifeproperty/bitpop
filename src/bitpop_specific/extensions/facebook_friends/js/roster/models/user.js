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

Chat.Models.User = Ember.Object.extend(Chat.Jsonable, {
    // Default attribute values
    jid: null,
    name: "{Unknown}",
    subscription: 'none',
    resources: null, // Set of opened connections
    last_active_time: null,
    is_fav: false,
    show: 'offline',

    init: function () {
        // We have to initialize 'resources' inside init function,
        // because otherwise all User objects would use the same Set object
        this.set('resources', []);
    },

    uid: function() {
        return Strophe.getNodeFromJid(this.get('jid')).substring(1);
    }.property('jid').cacheable(),

    presence: function () {
        return this.get('show') == 'offline' ? 'unavailable' : 'available';
    }.property('show').cacheable(),

    status: function () {
        return this.get('show');
    }.property('show').cacheable(),

    daysSinceLastActive: function () {
        var d = this.get('last_active_time') || (new Date(0)),
            now = new Date();
        if (!(d instanceof Date))   // needed when property is initialized from JSON localStorage and presented as a plain string
            d = new Date(d);
        return Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
    }.property('last_active_time'),

    onlineCategory: function () {
        if (this.get('status') == 'online') {
            if (this.get('is_fav') || this.get('daysSinceLastActive') <= 14)
                return 'top';
            else
                return 'bottom';
        }
        return null;
    }.property('is_fav', 'daysSinceLastActive', 'status'),

    setPresence: function (presence) {
        // var resources = this.get('resources'),
        //     id = Strophe.getResourceFromJid(presence.from),
        //     resource = resources.findProperty('id', id);

        // if (presence.type === 'unavailable' && resource) {
        //     resources.removeObject(resource);
        // } else {
        //     if (resource) {
        //         // TODO: set both properties at once?
        //         resource.set('show', presence.show);
        //         resource.set('status', presence.status);
        //     } else {
        //         resource = Chat.Models.Resource.create({
        //             id: id,
        //             show: presence.show,
        //             status: presence.status
        //         });
        //         resources.addObject(resource);
        //     }
        // }

        // return resource;
        var newValue = 'offline';
        switch (presence) {
            case 'active':
                newValue = 'online';
                break;
            case 'idle':
                newValue = 'idle';
                break;
            default:
                break;
        }
        if (this.get('show') != newValue) {
            this.set('show', newValue);
            // Update browser status of user
            chrome.bitpop.facebookChat.newIncomingMessage(
                "service",
                Strophe.getBareJidFromJid(this.get('jid')),
                "",
                newValue,
                ""
            );
        }
    },

    onFavChanged: function () {
        Chat.Controllers.localStorage.setUserFavState(
            Chat.Controllers.application.get('self_uid'),
            this.get('jid'),
            this.get('is_fav')
        );
    }.observes('is_fav')
});
