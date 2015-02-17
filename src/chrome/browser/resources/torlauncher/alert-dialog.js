$document.ready(function () {
  console.assert(torlauncher && torlauncher.alertWindowType &&
                 torlauncher.alertContent);

  $('#content').append(torlauncher.alertContent);
  if (torlauncher.alertWindowType == 'alert' &&
      torlauncher.confirmButtonId) {
    $('#' + torlauncher.confirmButtonId).click(function (e) {
      chrome.app.window.current().close();
    });
  } else if (torlauncher.alertWindowType == 'confirm' &&
             torlauncher.confirmButtonId && torlauncher.cancelButtonId &&
             torlauncher.resolveCallback && torlauncher.rejectCallback) {
    $('#' + torlauncher.confirmButtonId).click(function (e) {
      torlauncher.resolveCallback();
      chrome.app.window.current().close();
    });
    $('#' + torlauncher.cancelButtonId).click(function (e) {
      torlauncher.rejectCallback();
      chrome.app.window.current().close();
    });
  }
});
