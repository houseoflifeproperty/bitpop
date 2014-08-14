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

// TODO: edit CSS later (flyout/layout - no parent (layout))
Chat.Views.ChatTab.Layout = Ember.View.extend(Ember.TargetActionSupport, {
    showSmileys: false,
    template: Ember.Handlebars.compile(
        '<div class="chat-wrap">'
      //+   '<tr><td>'
      +   '<div class="chat-head" {{action "openFriendFacebookPage" target="view"}}>'
      +     '<span class="titlebar-text">{{Chat.Controllers.application.user_friend.name}}</span>'
      +   '</div>'
      //+   '</td></tr>'
      //+   '<tr><td height="*">'
      +   '<div class="box-wrap antiscroll-wrap">'
      +     '<div class="box">'
      +       '<div class="antiscroll-inner">'
      +         '<div class="box-inner">'
      +           '{{collection Chat.Views.ChatTab.MessageCollection id="msg-collection"}}'
      +         '</div>'
      +       '</div>'
      +     '</div>'
      +   '</div>'
      //+   '</td></tr>'
      +   '{{#if view.showSmileys}}'
      //+   '<tr><td>'
      +   '<div class="smileys"><table>'
      +     '<tr>'
      +       '<td><a href="#" class="smiley-link" title="smile" data-smile=":)"><img src="/images/smileys/smile.png" alt="smile"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="frown" data-smile=":("><img src="/images/smileys/frown.png" alt="frown"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="tongue" data-smile=":P"><img src="/images/smileys/tongue.png" alt="tongue"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="grin" data-smile=":D"><img src="/images/smileys/grin.png" alt="grin"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="gasp" data-smile=":-O"><img src="/images/smileys/gasp.png" alt="gasp"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="wink" data-smile=";)"><img src="/images/smileys/wink.png" alt="wink"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="pacman" data-smile=":v"><img src="/images/smileys/pacman.png" alt="pacman"></a></td>'
      +     '</tr>'

      +     '<tr>'
      +       '<td><a href="#" class="smiley-link" title="grumpy" data-smile=">:("><img src="/images/smileys/grumpy.png" alt="grumpy"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="unsure" data-smile=":/"><img src="/images/smileys/unsure.png" alt="unsure"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="cry" data-smile=":\'("><img src="/images/smileys/cry.png" alt="cry"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="kiki" data-smile="^_^"><img src="/images/smileys/kiki.png" alt="kiki"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="glasses" data-smile="8-)"><img src="/images/smileys/glasses.png" alt="glasses"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="sunglasses" data-smile="8-|"><img src="/images/smileys/sunglasses.png" alt="sunglasses"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="heart" data-smile="<3"><img src="/images/smileys/heart.png" alt="heart"></a></td>'
      +     '</tr>'

      +     '<tr>'
      +       '<td><a href="#" class="smiley-link" title="devil" data-smile="3:)"><img src="/images/smileys/devil.png" alt="devil"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="angel" data-smile="O:)"><img src="/images/smileys/angel.png" alt="angel"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="squint" data-smile="-_-"><img src="/images/smileys/squint.png" alt="squint"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="confused" data-smile="o.O"><img src="/images/smileys/confused.png" alt="confused"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="upset" data-smile=">:o"><img src="/images/smileys/upset.png" alt="upset"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="curly lips" data-smile=":3"><img src="/images/smileys/curlylips.png" alt="curly lips"></a></td>'
      +       '<td><a href="#" class="smiley-link" title="like" data-smile="(y)"><img src="/images/smileys/thumb.png" alt="like"></a></td>'
      +     '</tr>'
      +   '</table><a {{action "closeSmileys" target="view"}} class="close-smileys"></a></div>'
      //+   '</td></tr>'
      +   '{{/if}}'
      //+   '<tr><td>'
      +   '<div class="chat-input">'
      +     '<div class="chatarea-icon"></div>'
      +     '<a {{action "onPasteSmiley" target="view"}} title="Paste Smiley" class="paste-smiley"></a>'
      +     '<a {{action "onShareLink" target="view"}} title="Share visible tab page address" class="share-link"></a>'
      +     '{{view Chat.Views.ChatTab.TextArea id="msg-input"}}'
      +   '</div>'
      //+   '</td></tr>'
      + '</div>'
    ),

    classNames: ['chat-layout'],
    
    actions: {
      openFriendFacebookPage: function () {
        var profileUrl = 'http://www.facebook.com/profile.php?id=' + Chat.Controllers.application.get('user_friend.uid');
        chrome.tabs.create({ url: profileUrl });
      },

      onShareLink: function () {
        chrome.tabs.getSelected(null, _.bind(function(tab) {
            var textarea = Ember.View.views[this.$('textarea').attr('id')];
            var msgValue = textarea.get('value');
            if (msgValue == "")
              textarea.set('value', tab.url);
            else if (msgValue.charAt(msgValue.length - 1) == ' ')
              textarea.set('value', msgValue + tab.url);
            else
              textarea.set('value', msgValue + ' ' + tab.url);
            textarea.$().data('update_func')();
            textarea.focus();
        }, this));
      },

      onPasteSmiley: function () {
        this.toggleProperty('showSmileys');
        if (this.get('showSmileys') === false && $('.antiscroll-wrap').data('antiscroll')) {
          $('.antiscroll-wrap, .antiscroll-inner').height($('.chat-wrap').height() - $('.chat-head').outerHeight(true) - $('.chat-input').outerHeight(true));
        }
        setTimeout(_.bind(function () {
          if ($('.antiscroll-wrap').data('antiscroll')) {
            if (this.get('showSmileys') === true && $('.antiscroll-wrap').data('antiscroll')) {
              $('.antiscroll-wrap, .antiscroll-inner').height($('.chat-wrap').height() - $('.chat-head').outerHeight(true) - $('.smileys').outerHeight(true) - $('.chat-input').outerHeight(true));
            }
            $('.antiscroll-wrap').data('antiscroll').destroy().refresh();
            var container = $('.antiscroll-inner');
            container.prop('scrollTop', container.prop('scrollHeight'));
          }
        }, this), 100);
      },

      closeSmileys: function () {
        if (this.get('showSmileys'))
          this.triggerAction({ action: 'onPasteSmiley', target: this });
      }
    },

    didInsertElement: function () {
      this.$('.messages-wrap').click(_.bind(function (event) {
          this.$('textarea').focus();
      }, this));
      $('.antiscroll-inner').width($('.chat-wrap').width());
      $('.antiscroll-inner').height(265);
      this.$('.antiscroll-wrap').antiscroll();

      function insertAtCaret(areaId,text) {
        var txtarea = document.getElementById(areaId);
        var scrollPos = txtarea.scrollTop;
        var strPos = 0;
        var br = ((txtarea.selectionStart || txtarea.selectionStart == '0') ? 
          "ff" : (document.selection ? "ie" : false ) );
        if (br == "ie") { 
          txtarea.focus();
          var range = document.selection.createRange();
          range.moveStart ('character', -txtarea.value.length);
          strPos = range.text.length;
        }
        else if (br == "ff") strPos = txtarea.selectionStart;

        var front = (txtarea.value).substring(0,strPos);  
        var back = (txtarea.value).substring(strPos,txtarea.value.length); 
        Em.View.views[txtarea.id].set('value',
                front + ((front && front[front.length-1] == ' ') ? '' : ' ') 
                      +text + ((back && back[0] == ' ') ? '' : ' ') + back
        );
        strPos = strPos + text.length + ((front && front[front.length-1] == ' ') ? 0 : 1)
                  + ((back && back[0] == ' ') ? 0 : 1);
        if (br == "ie") { 
          txtarea.focus();
          var range = document.selection.createRange();
          range.moveStart ('character', -txtarea.value.length);
          range.moveStart ('character', strPos);
          range.moveEnd ('character', 0);
          range.select();
        }
        else if (br == "ff") {
          txtarea.selectionStart = strPos;
          txtarea.selectionEnd = strPos;
          txtarea.focus();
        }
        txtarea.scrollTop = scrollPos;
      }

      var self = this;
      $('.smiley-link').live('click', function (ev) {
        insertAtCaret('msg-input', $(this).attr('data-smile'));
        self.triggerAction({ action: 'closeSmileys', target: self });
        ev.preventDefault();
      });

      $(document).on('height_should_change', '#msg-input', _.bind(function (ev) {
        Ember.run.scheduleOnce('afterRender', this, function(){
          $('.antiscroll-wrap, .antiscroll-inner').height($('.chat-wrap').height() - $('.chat-head').outerHeight(true) - $('.chat-input').outerHeight(true) - (this.get('showSmileys') ? $('.smileys').outerHeight(true) : 0));
          if ($('.antiscroll-wrap').data('antiscroll'))
            $('.antiscroll-wrap').data('antiscroll').destroy().refresh();
        });
      }, this));
    }
});