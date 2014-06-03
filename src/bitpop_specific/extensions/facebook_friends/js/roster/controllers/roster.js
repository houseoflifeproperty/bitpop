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

Chat.Models.FriendItem = Chat.Models.UniversalListItem.extend({
    type: 'friend_entry',
    user: null,

    category: function () {
        return this.get('user.status');
    }.property('user.status').cacheable(),

    jid: function () {
        return this.get('user.jid');
    }.property('user.jid').cacheable(),

    is_fav: function () {
        return this.get('user.is_fav');
    }.property('user.is_fav').cacheable(),

    status: function () {
        return this.get('user.status');
    }.property('user.status').cacheable(),

    name: function () {
        return this.get('user.name');
    }.property('user.name').cacheable(),

    daysSinceLastActive: function () {
        return this.get('user.daysSinceLastActive');
    }.property('user.daysSinceLastActive').cacheable()
});

Chat.Controllers.Roster = Ember.ArrayController.extend({
    type: '',
    content: null,
    timer: null,

    online_head:    Chat.Models.UniversalListItem.create({ type: 'section_header', category: 'online', jid: "0" }),
    idle_head:      Chat.Models.UniversalListItem.create({ type: 'section_header', category: 'idle', jid: "1" }),
    offline_head:   Chat.Models.UniversalListItem.create({ type: 'section_header', category: 'offline', jid: "2" }),
    online_hr:      Chat.Models.UniversalListItem.create({ type: 'online_section_hr', category: 'online', jid: "3" }),
    friend_items: null,

    init: function () {
        this._super();
        this.set('content', []);
        this.set('friend_items', {});
    },

    fillUsers: function (data) {
        // var names = [ 'Alex', 'Mike', 'John', 'Nick', 'Dick', 'Joshua', 'Ray', 'Alice', 'David', 'Brian', 'Richard', 'Tommy', 'Jane', 'Andrew' ];
        // var lastnames = [ 'Smith', 'Johnson', 'Mikhailov', 'McDonald', 'Creepfold', 'Clayton', 'Charles', 'Douglas', 'Duhovny', 'McDougall' ];
        // var statuses = [ 'online', 'idle', 'offline' ];
        // for (var i = 0; i < 300; ++i) {
        //     data.pushObject(Chat.Models.User.create({
        //         name: names[Math.floor(Math.random() * names.length)] + ' ' + lastnames[Math.floor(Math.random() * lastnames.length)],
        //         jid: '-' + Math.floor(Math.random() * 999999999) + '@chat.facebook.com',
        //         show: statuses[Math.floor(Math.random() * statuses.length)],
        //         last_active_time: 0
        //     }));
        // }

        // if (this.get('timer') != null)
        //     clearInterval(this.get('timer'));
        // this.set('timer', setInterval(_.bind(function () { this.get('content')[299].set('show', statuses[2-statuses.indexOf(this.get('content')[299].get('show')) ]) }, this), 15000));
        
        var friend_items = this.get('friend_items');
        data.forEach(function (item, index, enumerable) { friend_items[item.get('jid')] = Chat.Models.FriendItem.create({ user: item }); })
        this.set('content', data);
    },

    addUser: function (user) {
        this.get('friend_items')[user.get('jid')] = Chat.Models.FriendItem.create({ user: user });
        this.get('content').addObject(user);
    },

    removeUser: function (user) {
        delete this.get('friend_items')[user.get('jid')];
        this.get('content').removeObject(user);
    },

    findUserByProperty: function (prop, value) {
        return this.get('content').findProperty(prop, value);
    },

    // filterUserByProperty: function (prop, value) {
    //     return this.get('content').filterProperty(prop, value).sortBy('name');
    // },

    // online: function () {
    //     return this.filterProperty('status', 'online');
    // }.property('content.@each.status'),

    // online_top: function () {
    //     return this.filterProperty('onlineCategory', 'top');
    // }.property('content.@each.onlineCategory'),

    // online_bottom: function () {
    //     return this.filterProperty('onlineCategory', 'bottom');
    // }.property('content.@each.onlineCategory'),

    // idle: function () {
    //     return this.filterProperty('status', 'idle');
    // }.property('content.@each.status'),

    // offline: function () {
    //     return this.filterProperty('status', 'offline');
    // }.property('content.@each.status'),

    isNonEmptySearch: function () {
        return (this.get('searchVal') && this.get('searchVal').trim().length > 0);
    },

    // applySearchQuery: function (items) {
    //     if (this.isNonEmptySearch()) {
    //         var s = this.get('searchVal').trim().toLowerCase();
    //         return items.filter(
    //                 _.bind(function (item, index, enumerable) {
    //                     return (item.get('name').toLowerCase().indexOf(s) !== -1);
    //                 }, this)
    //             );
    //     }
    //     return items;
    // },

    universal_list: function () {
        var new_items = [],
            online_top      = [],
            online_bottom   = [],
            idle            = [],
            offline         = [];
            friend_items    = this.get('friend_items');
        
        var content = this.get('content').sortBy('name');

        var s = this.get('searchVal') && this.get('searchVal').trim().toLowerCase();
        for (var i = 0; i < content.length; ++i) {
            var item = content[i];
            if (!s || (s && item.get('name').toLowerCase().indexOf(s) !== -1)) {
                switch (item.get('status')) {
                    case 'online':
                        if (item.get('onlineCategory') == 'top')
                            online_top.push(item);
                        else
                            online_bottom.push(item);
                        break;
                    case 'idle':
                        idle.push(item);
                        break;
                    case 'offline':
                        offline.push(item);
                        break;
                }
            }
        }    

        function pushToRes(item, index, enumerable) {
            new_items.push(friend_items[item.get('jid')]);
        }

        if (online_top.length + online_bottom.length) {
            new_items.push(this.get('online_head'));
            if (online_top.length) {
                online_top.forEach(pushToRes);
                if (online_bottom.length && !this.isNonEmptySearch())
                    new_items.push(this.get('online_hr'));
            }
            if (online_bottom.length)
                online_bottom.forEach(pushToRes);
        }
        if (idle.length) {
            if (!this.isNonEmptySearch())
                new_items.push(this.get('idle_head'));
            idle.forEach(pushToRes);
        }
        if (offline.length) {
            if (!this.isNonEmptySearch())
                new_items.push(this.get('offline_head'));
            offline.forEach(pushToRes);
        }

        return new_items;
    }.property('content.@each.status', 'content.@each.onlineCategory', 'content.@each.is_fav', 'searchVal'),

    getAsJsonable: function () {
        var res = [];
        this.get('content').forEach(function (item, index, enumerable) {
            res.push(item.getJson());
        });

        return res;
    }
});

Chat.Controllers.roster = Chat.Controllers.Roster.create();
