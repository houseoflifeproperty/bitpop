(function () {

  const kOpenInitialTorSessionWindowMessage = 'open-initial-tor-session-window';
  const kInitialUrl = 'https://check.torproject.org/?lang=en_US';

  chrome.runtime.onMessageExternal.addListener(function (message, sender, sendResponse) {
    switch (message.kind) {
      case kOpenInitialTorSessionWindowMessage:
        chrome.windows.create({       url: kInitialUrl,
                                  focused: true,
                                incognito: true },
                              function (window) { /*sendResponse({ success: true });*/ });
        break;
      default:
        console.warn('Invalid message format: ' + JSON.stringify(message));
        /*sendResponse({ success: false });*/
    }
  });

})();
