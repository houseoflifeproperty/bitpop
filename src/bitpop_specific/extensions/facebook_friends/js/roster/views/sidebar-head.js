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

var localConst = {};
localConst.TEXTAREA_HEIGHT = 80;

Chat.Views.StatusForm = Ember.View.extend({
  tagName: 'form',
  classNames: [ 'hidden' ],

  template: Em.Handlebars.compile(
      '<div class="status-input-wrap">'
    +   '<textarea id="status-input-area" wrap="soft" autofocus></textarea>'
    + '</div>'
    + '<div id="t1000">'
    +   '<button id="cancel-but" class="small-button" {{action "onCancel" target="view"}}>Cancel</button>'
    +   '<input class="small-button" type="submit" value="Post" {{action "onSubmit" target="view"}}/>'
    + '</div>'
  ),

  actions: {
    onCancel: function () {
      console.log('onCancel');
      console.assert(this.get('parentSidebarHead.statusToSetOnCancel'));
      console.assert(this.get('parentSidebarHead.isEditingStatus'));

      this.returnToShowingStatus();
      setTimeout(
          _.bind(function () {
            this.set('parentSidebarHead.statusTitle', this.get('parentSidebarHead.statusToSetOnCancel'));
            this.set('parentSidebarHead.isEditingStatus', false);
            this.set('parentSidebarHead.respondToClicks', true);
          }, this),
          600);

      return false;
    },

    onSubmit: function () {
      console.log('onSubmit');
      this.statusSubmitted();
    },
  },

  didInsertElement: function () {
    $('#status-input-area').keypress(_.bind(function (ev) {
      if (ev.which == 13 && $('#status-input-area').val()) {
        console.log('onTextareaKeyPress: ENTER');
        this.statusSubmitted();
      }
    }, this));
  },

  returnToShowingStatus: function() {
    var duration = 600;
    var textareaHeight = localConst.TEXTAREA_HEIGHT; // px
    var imgColumnWidth = $('#sidebar-head #head-col1 img').width() +
                         parseInt($('#sidebar-head #head-col1').css('padding-right'), 10);

    $('#head-col1').css('padding-top', (textareaHeight - $('#t1000').height() - 2).toString() + 'px')
      .stop().animate({ 'padding-top' : '0' }, duration);

    $('#status-form').fadeOut(duration);

    $('#head-col2-row1').css({
      'border': 'none',
      'padding': '0',
      'height': textareaHeight.toString() + 'px',
      'margin-left': '-' + imgColumnWidth.toString() + 'px',
      'max-height': textareaHeight.toString() + 'px' }).stop()
      .animate({ 'height': '16px', 'margin-left': '0', 'max-height': '26px' }, duration, 'linear',
          function() {
            $('#status-form').addClass('hidden');
            $(this).css({
              'border': 'solid 1px #ccc',
              'padding': '0 2px',
              'height': ''
            });
          });
  },

  statusSubmitted: function() {
    var val = $('#status-input-area').val();
    if (!val)
      return false;

    chrome.extension.sendMessage({
        kind: 'setFacebookStatus',
        msg: val
      },
      _.bind(function(response) {
        console.assert(this.get('parentSidebarHead.isEditingStatus'));

        if (response.error == 'yes')
          this.set('parentSidebarHead.statusTitle', 'Set Status Error');
        else {
          this.set('parentSidebarHead.statusTitle', val);
          _gaq.push(['_trackEvent', 'status', 'set']);
        }
        this.set('parentSidebarHead.isEditingStatus', false);
        this.set('parentSidebarHead.respondToClicks', true);
      }, this)
    );

    this.returnToShowingStatus();
  }
});

Chat.Views.ImageView = Ember.View.extend({
    tagName: 'img',
    attributeBindings: ['src']
});

// Ember.SelectOption.reopen({
//   attributeBindings: ['title'],
//   title: function() {
//     var titlePath = this.get('parentView.optionTitlePath');
//     return this.get(titlePath);
//   }.property('parentView.optionTitlePath')
// });

Chat.Views.SidebarHead = Ember.View.extend({
  respondToClicks: true,

  controller: Chat.Controllers.sidebarMainUI,

  // statusSelectContent: [
  //   { id: 'available', value: 'Available', title: "images/chat/active.png" },
  //   { id: 'unavailable', value: 'Offline', title: "images/chat/unavail.png"}
  // ],
  template: Em.Handlebars.compile(
      '<div id="head-row1">'
    +   '<div id="head-col1">'
    +     '{{view Chat.Views.ImageView id="head-profile-img" srcBinding="view.selfPicUrl" alt="profile image"}}'
    +   '</div>'
    +   '<div id="head-col2">'
    +     '<div {{action "statusClicked" on="click" target="view"}} id="head-col2-row1" title="Set your Facebook status message by clicking this area.">'
    +       '<span id="status-title">{{statusTitle}}</span>'
    +       '{{view Chat.Views.StatusForm isVisible="false" id="status-form" viewName="form"}}'
    +     '</div>'
    +     '<div id="head-col2-row2"><!-- chat status + logout -->'
    +       '<div id="status-select">'
    // +         '{{view Ember.Select id="status-control" value=onlineStatus'
    // +           ' content=view.statusSelectContent optionLabelPath="content.id"'
    // +           ' optionValuePath="content.value" optionTitlePath="content.title"}}'
    +         '<select name="status-control" id="status-control">'
    +           '<option value="available" title="images/chat/active.png">Available</option>'
    +           '<option value="unavailable" title="images/chat/unavail.png">Offline</option>'
    +         '</select>'
    +       '</div>'
    +       '<p id="logout"><a {{action "logoutClicked"}} tabIndex="-1">Logout</a></p>'
    +     '</div><!-- #head-col2-row2 -->'
    +   '</div><!-- #head-col2 -->'
    + '</div><!-- #head-row1 -->'
    + '<div id="head-row2">'
    +   '{{input id="search" type="search" placeholder="Search..." name="s" tabIndex="-1" incremental="incremental" value=Chat.Controllers.roster.searchVal}}'
    + '</div>'
  ),

  selfPicUrl: function () {
    return 'http://graph.facebook.com/' + (Chat.Controllers.application ? Chat.Controllers.application.get('self_uid') : '1') + '/picture?type=square';
  }.property('Chat.Controllers.application.self_uid'),

  didInsertElement: function () {
    try {
      this.$('select').msDropDown();
    } catch(e) {
      console.error(e.message);
    }

    $('#status-control').change(_.bind(function () {
      var status = $('#status-control').val();
      if (status == 'available') {
        Chat.Controllers.application.reconnect();
      } else if (status == 'unavailable') {
        Chat.Controllers.application.disconnect();
      }
    }, this));
  },

  actions: {
    statusClicked: function () {
      if (this.get('respondToClicks') === false)
        return;

      this.set('respondToClicks', false);

      var duration = 600; // ms
      var textareaHeight = localConst.TEXTAREA_HEIGHT; // px
      var imgColumnWidth = $('#sidebar-head #head-col1 img').width() +
                           parseInt($('#sidebar-head #head-col1').css('padding-right'), 10);

      var prevStatus = this.get('statusTitle').trim();
      this.set('statusToSetOnCancel', prevStatus);
      this.set('isEditingStatus', true);
      if (prevStatus == 'Set your status here.')
        prevStatus = '';

      $('#head-col2-row1').css({
        'border': 'none',
        'padding': '0',
        'max-height': '26px'
      }).stop();
      this.set('statusTitle', '');
      $('#head-col2-row1').animate({ 'margin-left': '-' + imgColumnWidth.toString() + 'px',
                 'height'     : textareaHeight.toString() + 'px',
                 'max-height' : textareaHeight.toString() + 'px',
               }, duration);
      
      this.get('form').set('parentSidebarHead', this);

      $('#status-form').removeClass('hidden').fadeIn(duration);

      $('#head-col1').css('padding-top', '0').stop()
        .animate({ 'padding-top': (textareaHeight - $('#t1000').height() - 2).toString() + 'px' }, duration);

      $('#status-input-area').val(prevStatus).select();
    }
  }
});