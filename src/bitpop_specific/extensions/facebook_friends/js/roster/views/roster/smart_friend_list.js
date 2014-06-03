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

Chat.Views.Roster.SmartFriendList = Ember.View.extend({
  tagName: 'ul',
  classNames: [ 'smart-list' ],
  emptyView: Ember.View.extend({
    template: Ember.Handlebars.compile('You\'ve got no friends to chat with. Go to facebook website and make some friends if you want to have a chat with any of them.')
  }),
  content: null,

  onContentUpdated: function () {
    this.rerender();
    if ($('.antiscroll-wrap').data('antiscroll'))
      $('.antiscroll-wrap').data('antiscroll').refresh();
  }.observes('content.@each'),

  render: function (buffer) {
    this.get('content') && this.get('content').forEach(function (item, index, enumerable) {
      var classNames = this.class_by_content_type(item);
      buffer.push('<li class="' + classNames + '" data-category="' + item.get('category') + '">');
      switch (item.get('type')) {
        case 'section_header':
          var category = item.get('category');
          category = category.charAt(0).toUpperCase() + category.slice(1);
          buffer.push('<div class="wrap-item">');
          buffer.push('<div class="toggle-button">&#9660</div>');
          buffer.push('<span>' + category + '</span>');
          buffer.push('</div>');
          break;
        case 'online_section_hr':
          buffer.push('<div class="wrap-item">MORE ONLINE FRIENDS</div>');
          break;
        case 'friend_entry':
          buffer.push('<div class="wrap-entry wrap-item">');
            buffer.push('<a href="#" data-facebook-uid="' + item.get('facebook_uid') + '" data-jid="' + item.get('jid') + '" data-category="' + item.get('category') + '">');
              buffer.push('<img src="' + item.get('avatar_url') + '" title="' + item.get('name') + '" />');
              buffer.push('<span>' + item.get('name') + '</span>');
            buffer.push('</a>');
            buffer.push('<div class="fav-toggle-button" data-tip="Mark as Favorite"></div>');
            buffer.push('<div class="status-indicator" data-tip="' + item.get('category') + '"></div>');
          buffer.push('</div>');
          break;
      }
      buffer.push('</li>');
    }, this);
  },

  class_by_content_type: function (item) {
    var self_jid = Chat.Controllers.application.user.get('jid');
    var res = null;
    switch (item.get('type')) {
      case 'section_header':
        var category = item.get('category');
        res = 'head '
            + 'head-' + category + ' '
            + (Chat.Controllers.localStorage.getFriendListAccordionOpenedState(self_jid, category) ?
                'head-on' : 'head-off');
        break;
      case 'online_section_hr':
        res = 'online-fav-divider';
        break;
      case 'friend_entry':
        var category = item.get('category');
        var fav = item.get('is_fav');
        res = 'friend '
            + 'friend-' + category + ' '
            + (fav ? 'friend-fav' : '');
        break;
  }
    return res;
  }
});

$(window).load(function () {
    $(document).on('click', '.friend a', function (ev) {
      chrome.bitpop.facebookChat.addChat(
                $(this).attr('data-jid'),
                $(this).find('span').text(),
                $(this).attr('data-category')
            );
      ev.preventDefault();
    });

    $(document).on('click', '.friend .fav-toggle-button', function (ev) {
      var curUser = Chat.Controllers.roster.findBy('uid', $(this).parent().find('a').attr('data-facebook-uid'));
      curUser.set('is_fav', !curUser.get('is_fav'));
      ev.preventDefault();
    });

    $(document).on('click', '.head .toggle-button', function (ev) {
      var el = $(this).parent().parent();
      var self_jid = Chat.Controllers.application.user.get('jid');
      var category = el.attr('data-category');
      Chat.Controllers.localStorage.saveFriendListAccordionOpenedState(self_jid, category, !el.hasClass('head-on'));

      if (el.hasClass('head-on')) {
        el.removeClass('head-on');
        el.addClass('head-off');
      } else {
        el.removeClass('head-off');
        el.addClass('head-on');
      }
    });
});