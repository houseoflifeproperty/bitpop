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

Chat.Views.SidebarMainUI = Ember.View.extend({
  template: Em.Handlebars.compile( 
        '{{view Chat.Views.SidebarHead id="sidebar-head"}}'
      + '<div class="box-wrap antiscroll-wrap">'
      +   '<div class="box">'
      +     '<div class="antiscroll-inner">'
      +       '<div class="box-inner">'
      +         '{{view Chat.Views.Roster.SmartFriendList contentBinding="Chat.Controllers.roster.universal_list"}}'
      +       '</div>'
      +     '</div>'
      +   '</div>'
      + '</div>'
  ),

  classNameBindings: ['isActive'],

  isActive: false,

  didInsertElement: function () {
    function setAntiscrollHeight() {
      $('.antiscroll-inner').height(
        $('body').height() - $('.antiscroll-wrap').offset().top
      );
      $('.antiscroll-inner').width($('body').width());
    }

    setAntiscrollHeight();
    this.$('.antiscroll-wrap').antiscroll();

    $(window).resize(function() {
      setAntiscrollHeight();
      if ($('.antiscroll-wrap').data('antiscroll')) {
        $('.antiscroll-wrap').data('antiscroll').destroy().refresh();
      }
    });

    // Set roster "UI blocked" state on startup
    Chat.Controllers.application.onChatBlockChanged();
  }
});