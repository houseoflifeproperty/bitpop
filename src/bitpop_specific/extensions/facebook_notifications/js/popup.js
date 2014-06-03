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

var _gaq = _gaq || [];
_gaq.push(['_setAccount', 'UA-43394997-1']);
_gaq.push(['_trackPageview']);

(function() {
  var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
  ga.src = 'https://ssl.google-analytics.com/ga.js';
  var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
})();

var NUM_NOTIFICATIONS_SHOW = 5;

window.options.init();
var current = window.options.current;

var DesktopNotifications =
  window.chrome.extension.getBackgroundPage().DesktopNotifications;

$('.link-bitpop').live('click', function(e) {
  var href = $(this).attr('href');
  if (href) {
    chrome.tabs.create({ 'url': href });
  }
});

function showError(errorMsg) {
  var newDom =
      //"<div class='empty-feed'>" +
      "<span>" + errorMsg + "</span>";// +
      //"</div>";
  $('#feed').empty();
  $('#feed').addClass('empty-feed');
  $('#feed').removeClass('loading');
  $('#feed').append(newDom);

  $('#footer').empty();
  var footerGoToOnClick = 'href="http://www.facebook.com/notifications"';
  $('#footer').append("<div class='footer-item centered link-bitpop' " +
      footerGoToOnClick + ">Notifications</div>");
}

function showNotifications(data) {
  $('#feed').removeClass('loading');
  $('#feed').empty();
  $('#footer').empty();

  var query1 = data[0].fql_result_set;
  var query2 = data[1].fql_result_set;
  var query3 = data[2].fql_result_set;

  var newDom = '';

  var footerGoToOnClick = 'href="http://www.facebook.com/notifications"';
  if (query1.length == 0) {
    newDom =
      "<div class='empty-feed'>" +
      "  <span>No New Notifications.</span>" +
      "</div>";

    $('#footer').append("<div class='footer-item centered link-bitpop' " +
        footerGoToOnClick + ">Notifications</div>");
  } else
    $('#footer').append("<div class='footer-item centered link-bitpop' " +
        footerGoToOnClick + ">See All Notifications</div>");


  for (var i = 0; i < Math.min(query1.length, NUM_NOTIFICATIONS_SHOW); i++) {
    newDom += formatFeedItem(query1[i],
                             findNameForUid(
                               query1[i].sender_id,
                               query2,
                               query3
                               ),
                             findPicForUid(
                               query1[i].sender_id,
                               query2,
                               query3
                               )
                            );
  }

  $('#feed').append(newDom);

  var notificationIds = '';
  for (var i = 0; i < query1.length; i++) {
    if (query1[i].is_unread)
      notificationIds += query1[i].notification_id + ',';
  }

  if (notificationIds != '') {
    notificationIds = notificationIds.substring(0, notificationIds.length - 1);
    chrome.extension.sendMessage(current.controllerExtensionId,
        { type: 'restApiCall',
          method: 'notifications.markRead',
          params: { notification_ids: notificationIds }
        },
        function (response) {
          if (!response.error) {
            DesktopNotifications.fetchServerInfo(
              DesktopNotifications.handleServerInfo,
              DesktopNotifications.showInactiveIcon,
              true // no_cache after clicking popup
            );
          }
        }
    );
  }
}

function findNameForUid(uid, data, page_data) {
  for (var i = 0; i < data.length; i++) {
    if (data[i].uid && data[i].uid.toString() == uid.toString() && data[i].name)
      return data[i].name;
    if (page_data && page_data[i] &&
        page_data[i].page_id &&
        page_data[i].page_id.toString() == uid.toString() &&
        page_data[i].name)
      return page_data[i].name;
  }
  return 'Unknown sender';
}

function findPicForUid(uid, data, page_data) {
  for (var i = 0; i < data.length; i++) {
    if (data[i].uid && data[i].uid.toString() == uid.toString() && data[i].pic_square)
      return data[i].pic_square;
    if (page_data && page_data[i] &&
        page_data[i].page_id &&
        page_data[i].page_id.toString() == uid.toString() &&
        page_data[i].pic_square)
      return page_data[i].pic_square;
  }
  return 'https://graph.facebook.com/1/picture?type=square';
}

function formatFeedItem(itemData, name, pic_url) {
  var template =
    "<div class='notification link-bitpop' href='{{href}}'>" +
      "<div class='left'>" +
        "<div class='user-photo'>" +
          "<img src='{{photoUrl}}' />" +
        "</div>" +
      "</div>" +
      "<div class='right'>" +
        "<div class='top'>" +
          "<div class='user-name'>" +
            "{{displayName}}" +
          "</div>" +
          "<div class='read-{{read}} time-since'>" +
            "{{time-since}}" +
          "</div>" +
        "</div>" +
        "<div class='bottom'>" +
          "<div class='notification-content'>" +
            "<img src='{{icon}}' />" +
            "{{title}}" +
          "</div>" +
        "</div>" +
      "</div>" +
      "</div>";
  template = template.replace('{{href}}', itemData.href);
  template = template.replace('{{photoUrl}}', pic_url);
  template = template.replace('{{displayName}}', name);
  template = template.replace('{{read}}',
    itemData.is_unread ? "false" : "true");
  template = template.replace('{{time-since}}',
    humane_date(ISODateString(new Date(itemData.created_time * 1000))));
  template = template.replace('{{icon}}', itemData.icon_url);
  template = template.replace('{{title}}', itemData.title_text);

  return template;
}

window.addEventListener('load', function (e) {
  var query1 = 'SELECT notification_id, recipient_id, sender_id, created_time, title_text, href, is_unread, icon_url ' +
               'FROM notification ' +
               'WHERE recipient_id=me() AND is_hidden=0';
  var query2 = 'SELECT uid, name, pic_square ' +
               'FROM user ' +
               'WHERE uid IN ' +
               '(SELECT sender_id FROM #query1)';
  var query3 = 'SELECT page_id, name, pic_square ' +
               'FROM page ' +
               'WHERE page_id IN ' +
               '(SELECT sender_id FROM #query1)';
  var query = JSON.stringify({ query1: query1, query2: query2, query3: query3 });

  chrome.extension.sendMessage(current.controllerExtensionId,
      {
        type: 'fqlQuery',
        query: query
      },
      function (response) {
        if (response) {
          if (response.error)
            showError(response.error);
          else
            showNotifications(response);
        }
      }
  );
}, false);

