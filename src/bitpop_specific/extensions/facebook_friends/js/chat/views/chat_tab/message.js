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

Chat.Views.ImageView = Ember.View.extend({
    tagName: 'img',
    attributeBindings: ['src']
});

(function() {
    var timestampTemplate =
        '<div {{bindAttr class=":timestamp view.isTimestampHidden:hidden1"}}>'
      +   '<span>{{view.timestampText}}</span>'
      + '</div>';

    function talkBubble (additionalClass) {
      return (
          '<div class="talk-bubble tri-right round border ' + additionalClass + '">'
        +   '<div class="talktext">'
        +     '{{{view.bodySmilesReplaced}}}'
        +   '</div>'
        + '</div>');
    }

    Em.TEMPLATES["self"] = Em.Handlebars.compile(
        timestampTemplate
      + '<div class="float">'
      +   talkBubble('right-in')
      + '</div>'
    );
    Em.TEMPLATES["not-self"] = Em.Handlebars.compile(
        timestampTemplate
      + '<div class="float">'
      +   '<div class="profile-image" {{bindAttr data-tip="view.titleVal"}} {{bindAttr data-tip-2="view.titleValLine2"}}>'
      +     '<a {{action "openFriendFacebookPage" target="view.parentView.parentView"}} class="profile-image-link">'
      +       '{{view Chat.Views.ImageView srcBinding="Chat.Controllers.application.friendPhotoLink"}}'
      +     '</a>'
      +   '</div>'

      +   talkBubble('left-in')
      + '</div>'
    );

    emotify.emoticons(
      '/images/smileys/',
      [
        { title: "smile", patterns: [':-)', ':)', ':]', '=)'] },
        { title: "frown", patterns: [':-(', ':(', ':[', '=('] },
        { title: "gasp", patterns: [':-O', ':O', ':-o', ':o'] },
        { title: "grin", patterns: [':-D', ':D', '=D'] },
        { title: "tongue", patterns: [':-P', ':P', ':-p', ':p', '=P'] },
        { title: "wink", patterns: [';-)', ';)'] },
        { title: "curly lips", patterns: [':3'], img_name:"curlylips" },
        { title: "kiss", patterns: [':-*', ':*'] },
        { title: "grumpy", patterns: ['&gt;:(', '&gt;:-('] },
        { title: "glasses", patterns: ['8-)', '8)', 'B-)', 'B)'] },
        { title: "sunglasses", patterns: ['8-|', '8|', 'B-|', 'B|'] },
        { title: "upset", patterns: ['&gt;:O', '&gt;:-O', '&gt;:o', '&gt;:-o'] },
        { title: "confused", patterns: ['o.O', 'O.o'] },
        { title: "shark", patterns: ['(^^^)'] },
        { title: "pacman", patterns: [':v'] },
        { title: "squint", patterns: ['-_-'] },
        { title: "angel", patterns: ['O:)', 'O:-)'] },
        { title: "devil", patterns: ['3:)', '3:-)'] },
        { title: "unsure", patterns: [':/', ':-/', ':\\', ':-\\'] },
        { title: "cry", patterns: [':\'('] },
        { title: "Chris Putnam", patterns: [':putnam:'], img_name: "putnam" },
        { title: "robot", patterns: [':|]'] },
        { title: "heart", patterns: ['&lt;3'] },
        { title: "kiki", patterns: ['^_^'] },
        { title: "42", patterns: [':42:'] },
        { title: "penguin", patterns: ['&lt;(")'] },
        { title: "poop", patterns: [':poop:'] },
        { title: "thumb", patterns: ['(y)'] }
      ]
    );
})();

Chat.Views.ChatTab.Message = Ember.View.extend({
    templateNameBinding: 'currentTemplateName',
    isTimestampHidden: true,
    timestamp: null,

    init: function () {
      this.set('timestamp', this.get('content.createdAt'));
      this.set('isTimestampHidden', true);

      return this._super();
    },

    currentTemplateName: function () {
      if (this.get('isFromSelf'))
        return 'self';
      else
        return 'not-self';
    }.property('isFromSelf'),
    
    templateNameObserver: function() {
      this.rerender();
    }.observes('templateName'),

    classNames: ['chat-message'],
    classNameBindings: ['user'],

    titleVal: function () {
      return this.get('timestampText');
    }.property('timestampText'),

    titleValLine2: function () {
       return Chat.Controllers.application.get('user_friend.name');
    }.property(),

    isFromSelf: function () {
        var from = Strophe.getBareJidFromJid(this.get('content.from')),
            you  = Strophe.getBareJidFromJid(Chat.Controllers.application.get('user_self.jid'));
        return from === you;
    }.property('content.from'),

    user: function () {
      var from = Strophe.getBareJidFromJid(this.get('content.from')),
          you  = Strophe.getBareJidFromJid(Chat.Controllers.application.get('user_self.jid'));
      return from === you ? 'self' : 'not-self';
    }.property('content.from'),

    timestampText: function () {
      var ts = this.get('timestamp');
      return ts.shortLongFormat(ts.isTodayDate());
    }.property('timestamp'),

    updateTimestampText: function () {
      this.set('timestamp', this.get('timestamp'));
    },

    willInsertElement: function () {
        var list = this.get('parentView.content');
        var today = this.get('content.createdAt');
        if (list.indexOf(this.get('content')) !== 0) {
          var lastElement = list.objectAt(list.length-2);
          var lastElementUpdateTime = lastElement.get('createdAt');
          if (lastElementUpdateTime.getDate() != today.getDate() ||
              lastElementUpdateTime.getMonth() != today.getMonth() ||
              lastElementUpdateTime.getFullYear() != today.getFullYear()) {
            this.set('isTimestampHidden', false);
            this.set('timestamp', today);
          }
        } else {
          this.set('isTimestampHidden', false);
          this.set('timestamp', today);
        }
        this.messageCollectionView().onWillInsertMessageView(this);
        this.onMessageBodyChanged();
    },

    didInsertElement: function () {
        if (Chat.Controllers.application.get('shouldScrollOnViewInsertion'))
          this.messageCollectionView().onDidInsertMessageView();
        /*this.$().addClass('created');*/
        this.$().hover(function (ev) {
          $(this).find('.timestamp.hidden1').stop(true, true).delay(2500).animate({ 'height': 'show' },
            function () {
              $('.antiscroll-wrap').data('antiscroll').refresh();
              var scrollTop = $('.antiscroll-inner').prop('scrollTop');
              $('.antiscroll-inner').stop(true, true).animate({ 'scrollTop': scrollTop + 24 }, 200);
            });
        }, function (ev) {
          $(this).find('.timestamp.hidden1').stop(true, true).animate({ 'height': 'hide' });
        });
    },

    messageCollectionView: function () {
        return this.get('parentView');
    },

    onMessageBodyChanged: function () {
      Ember.run.scheduleOnce('afterRender', this, function () {
        var self = this;
        function imageLoaded() {
          // function to invoke for loaded image
          // decrement the counter
          counter--; 
          if( counter === 0 ) {
            // counter is 0 which means the last
            //    one loaded, so do something else
            self.set('imagesLoadedScrollToBottom', true);
            self.get('parentView').onDidInsertMessageView();
            self.get('parentView').set('imagesLoadedScrollToBottom', false);
          }
        }
        var images = this.$('img.sticker-img,img.smiley');
        var counter = images.length;  // initialize the counter

        images.each(function() {
          $(this).one('error', function() {
            imageLoaded.call(this);
            $(this).hide();
          });
          if( this.complete ) {
              imageLoaded.call(this);
          } else {
              $(this).one('load', imageLoaded);
          }
        });
      });
    }.observes('content.body'),

    bodySmilesReplaced: function () {
      return emotify(this.get('content.body'));
    }.property('content.body').cacheable(),
});

// Chat.Views.ChatTab.Message.smileyRules = [
//   { title: "smile", patterns: [':-)', ':)', ':]', '=)'] },
//   { title: "frown", patterns: [':-(', ':(', ':[', '=('] },
//   { title: "gasp", patterns: [':-O', ':O', ':-o', ':o'] },
//   { title: "grin", patterns: [':-D', ':D', '=D'] },
//   { title: "tongue", patterns: [':-P', ':P', ':-p', ':p', '=P'] },
//   { title: "wink", patterns: [';-)', ';)'] },
//   { title: "curly lips", patterns: [':3'], img_name:"curlylips" },
//   { title: "kiss", patterns: [':-*', ':*'] },
//   { title: "grumpy", patterns: ['>:(', '>:-('] },
//   { title: "glasses", patterns: ['8-)', '8)', 'B-)', 'B)'] },
//   { title: "sunglasses", patterns: ['8-|', '8|', 'B-|', 'B|'] },
//   { title: "upset", patterns: ['>:O', '>:-O', '>:o', '>:-o'] },
//   { title: "confused", patterns: ['o.O', 'O.o'] },
//   { title: "shark", patterns: ['(^^^)'] },
//   { title: "pacman", patterns: [':v'] },
//   { title: "squint", patterns: ['-_-'] },
//   { title: "angel", patterns: ['O:)', 'O:-)'] },
//   { title: "devil", patterns: ['3:)', '3:-)'] },
//   { title: "unsure", patterns: [':/', ':-/', ':\\', ':-\\'] },
//   { title: "cry", patterns: [':\'('] },
//   { title: "Chris Putnam", patterns: [':putnam:'], img_name: "putnam" },
//   { title: "robot", patterns: [':|]'] },
//   { title: "heart", patterns: ['<3'] },
//   { title: "kiki", patterns: ['^_^'] },
//   { title: "42", patterns: [':42:'] },
//   { title: "penguin", patterns: ['<(")'] },
//   { title: "poop", patterns: [':poop:'] }
// ];
