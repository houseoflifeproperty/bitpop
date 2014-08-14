if (typeof(SHR)=="undefined") SHR = {};
if (typeof(SHR.TweetButton)=="undefined") SHR.TweetButton = {};

(function($) {
    function pageInfo(tab,callback) {
        var fallback_ms = 400;

        pageInfoCallback = callback;
        chrome.tabs.executeScript(tab.id,{file:'content_scripts/page_info.js'});
        fallback = setTimeout(function() {
            // just get info via regular chrome.tabs.* api, as it seems that content script didn't work
            // (chrome://extensions etc.)
            callback({title:tab.title,link:tab.url});
            pageInfoCallback = null;
            fallback = null;
        },fallback_ms);
    }

    chrome.extension.onMessage.addListener(function(req,sender,response) {
        if (req.type == 'pageInfo' && pageInfoCallback) {
            pageInfoCallback(req.info);
            if (fallback) clearTimeout(fallback);
            pageInfoCallback = null;
        }
    });

    chrome.tabs.onCreated.addListener(function(tab) {
        if (tab.url.indexOf('chrome://') == 0) {
          chrome.pageAction.hide(tab.id);
          return;
        }
        chrome.pageAction.show(tab.id);
    });

    chrome.tabs.onUpdated.addListener(function(tabId,changeInfo,tab) {
        if (tab.url.indexOf('chrome://') == 0) {
          chrome.pageAction.hide(tab.id)
          return;
        }
        chrome.pageAction.show(tab.id);
    });

    //// Popup

    function show(tab) {
        pageInfo(tab,function(info) {
            var message = info.selection ? info.selection : info.title;
            var widgetUrl = 'http://www.facebook.com/sharer.php?';
            widgetUrl += '&t='+encodeURIComponent(message);
            widgetUrl += '&u='+encodeURIComponent(info.link);
            window.open(widgetUrl,'tweetbutton','width=626,height=436');
        });
    }
    chrome.pageAction.onClicked.addListener(show);
})();

