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

jQuery.fn.putCursorAtEnd = function() {

  return this.each(function() {

    $(this).focus()

    var len = $(this).val().length;
    
    this.setSelectionRange(len, len);

    // Scroll to the bottom, in case we're in a tall textarea
    // (Necessary for Firefox and Google Chrome)
    this.scrollTop = 999999;

  });

};

Chat.Views.ChatTab.TextArea = Ember.TextArea.extend({
    classNames: ['autogrow'],

    init: function () {
        this.typingExpiredCallback = null;
        jQuery(window).unload(_.bind(function () {
            Chat.Controllers.localStorage.saveTextfieldValue(
                Chat.Controllers.application.get('user_friend.jid'),
                Chat.Controllers.application.get('user_self.jid'),
                this.get('value')
            );
        }, this));
        var res = this._super();

        return res;
    },

    setInitialValue: function () {
        var val = Chat.Controllers.application.get('initialText');        
        this.set('value', val);
        // a workaround to call change event handler for textarea:
        this.$().trigger('change').blur();
        setTimeout(_.bind(function () { this.$().focus() }, this), 0);
    }.observes('Chat.Controllers.application.initialText'),

    didInsertElement: function () {
        setTimeout(_.bind(function () {
            this.$().autogrow();
            this.focus();
        }, this),
        0);
        setTimeout(_.bind(this.setInitialValue, this), 500);
    },

    keyDown: function (event) {
        // Send message when Enter key is pressed
        if (event.which === 13) {
            event.preventDefault();

            var tab = Chat.Controllers.application.get('chat_tab'),
                body = this.get('value'),
                user = tab.get('user'),
                friend = tab.get('friend'),
                message = Chat.Models.Message.create({
                    from: user.get('jid'),
                    to: friend.get('jid'),
                    body: body,
                    fromName: user.get('name'),
                    direction: 'outgoing'
                });

            this.set('value', '');

            // Send message to XMPP server
            Chat.Controllers.application.sendMessage(message);

            // Display the message to the sender,
            // because it won't be sent back by XMPP server
            tab._onMessage(message);

            this.$().data('composing', false);
            _gaq.push(['_trackEvent', 'message', 'sent']);
        } else {
            var composing = this.$().data('composing');
            if (!composing) {
                if (this.typingExpiredCallback) {
                    clearTimeout(this.typingExpiredCallback);
                    delete this.typingExpiredCallback;
                }

                var that = this;
                this.typingExpiredCallback = setTimeout(function () {
                    if (that.$().data('composing') === true) {
                        Chat.Controllers.application.sendTypingState('active');
                        that.$().data('composing', false);
                    }
                    delete that.typingExpiredCallback;
                }, 5000);

                // TODO: send composing message
                Chat.Controllers.application.sendTypingState('composing');
                this.$().data('composing', true);
            }
        }
    },

    focus: function () {
        this.$().putCursorAtEnd();
    }
});
