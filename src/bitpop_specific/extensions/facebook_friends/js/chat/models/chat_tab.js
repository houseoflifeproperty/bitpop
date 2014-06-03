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

Chat.Models.ChatTab = Ember.Object.extend({
    user: null,

    init: function () {
        this.set('messages', []);
    },

    _onMessage: function (message) {
        // TODO: handle activity messages as well
        if (message.get('body')) {
            if (message.direction == 'outgoing')
                message.set('body', Chat.Controllers.localStorage.preprocessMessageText(message.get('body')));
            else
                message.set('body', $.autolink(message.get('body'),
                                                {
                                                    'target': '_blank',
                                                    'tabIndex': '-1'
                                                })
                );
            var messages = this.get('messages');
            messages.addObject(message);
            Chat.Controllers.localStorage.addChatMessageToDataObject(message);
        }
    },
});
