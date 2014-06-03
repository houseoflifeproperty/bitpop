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

var Chat = window.Chat = Ember.Application.create({});

Chat.Models = {};
Chat.Controllers = {};
Chat.Views = {
    Roster: {},
    ChatTab: {}
};

Chat.Jsonable = Ember.Mixin.create({
    getJson: function() {
        var v, json = {};
        for (var key in this) {
            if (this.hasOwnProperty(key)) {
                v = this[key];
                if (v === 'toString') {
                    continue;
                } 
                if (Ember.typeOf(v) === 'function') {
                    continue;
                }
                if (Chat.Jsonable.detect(v))
                    v = v.getJson();
                json[key] = v;
            }
        }
        return json;
    }
});