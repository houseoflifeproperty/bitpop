(function () {
  // Close Google Docs extension options window, appearing on first run
  // and focus the Sign In page.
  if (!localStorage.firstRunCompleted) {
    chrome.tabs.onUpdated.addListener(function(tabId, changeInfo, tab) {
      if (changeInfo && changeInfo.url &&
          changeInfo.url.indexOf('chrome-extension://nnbmlagghjjcbdhgmkedmbmedengocbn/options.html') == 0) {
        chrome.tabs.remove(tabId);
        chrome.tabs.query({ url: "chrome://chrome-signin/*" }, function (tabList) {
          if (tabList.length !== 1)
            return;
          chrome.tabs.update(tabList[0].id, { active: true });
        });
        localStorage.setItem("firstRunCompleted", true);
        chrome.tabs.onUpdated.removeListener(arguments.callee);
      }
    });
  }
})();