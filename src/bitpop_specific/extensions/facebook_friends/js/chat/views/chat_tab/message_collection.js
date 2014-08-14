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

Chat.Views.ChatTab.MessageCollection = Ember.CollectionView.extend({
  itemViewClass: Chat.Views.ChatTab.Message,
  contentBinding: 'Chat.Controllers.application.chat_tab.messages',
  classNames: ['messages-wrap'],
  imagesLoadedScrollToBottom: false,

  emptyView: Ember.View.extend({
    template: Ember.Handlebars.compile("The message history is empty.")
  }),

  onWillInsertMessageView: function (view) {
    this.doScrollFlyoutView = this.isNearBottom() || view.get('isFromSelf');
  },

  onDidInsertMessageView: function () {
    if ($('.antiscroll-wrap').data('antiscroll'))
      $('.antiscroll-wrap').data('antiscroll').refresh();
    if (this.doScrollFlyoutView || this.get('imagesLoadedScrollToBottom')) {
      this.scrollFlyoutView();
    }
  },

  isNearBottom: function (threshold) {
    var container = this.$().parent().parent();
    threshold = threshold || 10;
    return (container.prop("scrollTop") + container.prop("offsetHeight") + threshold) >= container.prop("scrollHeight");
  },

  scrollFlyoutView: function (amtScrolled) {
    var container = this.$().parent().parent();
    if (!amtScrolled)
      container.prop('scrollTop', container.prop('scrollHeight'));
    else
      container.prop('scrollTop', container.prop('scrollHeight') * amtScrolled - container.prop('offsetHeight'));
  },

  amtScrolled: function() {
    var container = this.$().parent().parent();
    return (container.prop("scrollTop") + container.prop("offsetHeight")) / container.prop('scrollHeight');
  }
});
