window.addEvent("domready", function () {
  new FancySettings.initWithManifest(function (settings) {
    settingsStore = new Store('settings');

    settings.manifest.domains_description.element.set('html',
            'A list of sites blocked in <strong>' +
            settingsStore.get('country_name') +
            '</strong> collected through IP recognition:');

    settings.manifest.update_domains.addEvent('action', function() {
      chrome.extension.getBackgroundPage().updateProxifiedDomains();
    });

    chrome.extension.onRequest.addListener(function(request, sender,
        sendResponse) {
      if (request && request.reason === 'settingsChanged') {
        settings.manifest.domains.set(settingsStore.get('domains'), true);
      }
    });

    var emptySpace = document.createElement('div');
    emptySpace.className = 'tab';

    var container = document.getElementById('tab-container');
    container.appendChild(emptySpace);

    var backLink = document.createElement('div');
    backLink.className = 'tab';
    backLink.innerText = 'Back to main settings';
    backLink.addEventListener('click', function (e) {
      chrome.tabs.update(null, { url: 'chrome://settings' });
      e.preventDefault();
    });

    container.appendChild(backLink);

  });
});
