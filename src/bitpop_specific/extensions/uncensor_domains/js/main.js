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

String.prototype.endsWith = function(suffix) {
  return this.indexOf(suffix, this.length - suffix.length) !== -1;
};

String.prototype.format = function() {
  var formatted = this;
  for (var i = 0; i < arguments.length; i++) {
      var regexp = new RegExp('\\{'+i+'\\}', 'gi');
      formatted = formatted.replace(regexp, arguments[i]);
  }
  return formatted;
};

var prefsString = ("prefs" in localStorage) ? localStorage.prefs : "";
var localPrefs = (prefsString != "") ? JSON.parse(prefsString) : null;
var prefs = null;

//var inSetFilter = false;
//var inSetExceptions = false;

function downloadFilterData() {
  var xhr = new XMLHttpRequest();
  xhr.onreadystatechange = function() {
    if (xhr.readyState == 4) {
      var d = JSON.parse(xhr.responseText);
      var changed = false;
      var od = {};
      for (var x in d) {
        od[d[x]['srcDomain']] = d[x]['dstDomain'];
        if (!(d[x]['srcDomain'] in prefs.domainFilter) || !prefs.domainFilter)
          changed = true;
      }

      for (var x in prefs.domainFilter)
        if (!(x in od))
          changed = true;

      if (changed && prefs.notifyUpdate) {
        var notification = webkitNotifications.createNotification(
          '48uncensor.png',  // icon url - can be relative
          chrome.i18n.getMessage("extName"),  // notification title
          chrome.i18n.getMessage("updateSuccessMsg")  // notification body text
        );
        notification.show();
        setTimeout(function() {
          notification.cancel();
        }, 5000);
      }

      prefs.domainFilter = od;
      //inSetFilter = true;
      chrome.bitpop.prefs.uncensorDomainFilter.set({
          scope: "regular",
          value: JSON.stringify(prefs.domainFilter)
        });

      var exceptionsChanged = false;
      for (var excDomain in prefs.domainExceptions) {
        if (!(excDomain in prefs.domainFilter)) {
          delete prefs.domainExceptions[excDomain];
          exceptionsChanged = true;
        }
      }
      if (exceptionsChanged) {
        //inSetExceptions = true;
        chrome.bitpop.prefs.uncensorDomainExceptions.set({
            scope: "regular",
            value: JSON.stringify(prefs.domainExceptions)
          });
      }

      localPrefs.lastUpdate = Date.now();
      localStorage.prefs = JSON.stringify(localPrefs);
    }
  };
  xhr.open("GET", 'http://tools.bitpop.com/service/uncensor_domains', true);
  xhr.send();
}

function initPrefs() {
  if (prefsString === "") {
    localPrefs = {};
    localPrefs.lastUpdate = 0;

    localStorage.prefs = JSON.stringify(localPrefs);
  }

  prefs = {};
  chrome.bitpop.prefs.uncensorShouldRedirect.get({}, function(details) {
    prefs.shouldRedirect = (+details.value === 0);
  });
  chrome.bitpop.prefs.uncensorShowMessage.get({}, function(details) {
    prefs.showMessage = details.value;
  });
  chrome.bitpop.prefs.uncensorNotifyUpdates.get({}, function(details) {
    prefs.notifyUpdate = details.value;
  });
  chrome.bitpop.prefs.uncensorDomainFilter.get({}, function(details) {
    prefs.domainFilter = JSON.parse(details.value);
  });
  chrome.bitpop.prefs.uncensorDomainExceptions.get({}, function(details) {
    prefs.domainExceptions = JSON.parse(details.value);
  });
}

function checkAndUpdate() {
  if (Date.now() - localPrefs.lastUpdate > 1000 * 60 * 60 * 24)
    downloadFilterData();
  setTimeout(checkAndUpdate, 1000 * 60 * 60);
}

// Called when the url of a tab changes.
function redirectListener(tabId, changeInfo, tab) {
  if (!prefs || !prefs.shouldRedirect)
    return;

  var uri = parseUri(tab.url);
  for (var domain in prefs.domainFilter) {
    if (!(domain in prefs.domainExceptions) && uri["host"].endsWith(domain) &&
        prefs.showMessage && changeInfo.status == "loading") {

      uri['host'] = uri['host'].replace(new RegExp(domain+'$', ''), prefs.domainFilter[domain]);
      var newUri = reconstructUri(uri);
      chrome.tabs.update(tabId, {"url": newUri});

      var notification = webkitNotifications.createNotification(
        '48uncensor.png',  // icon url - can be relative
        chrome.i18n.getMessage("extName"),  // notification title
        chrome.i18n.getMessage("redirectedMsg").format(newUri)  // notification body text
      );
      notification.show();

      setTimeout(function() {
        notification.cancel();
      }, 5000);
    }
  }
};

(function() {
  //if (prefsString == "")
  initPrefs();
  checkAndUpdate();

  //window.addEventListener("storage", function(e) {
  //  if (e.key == "prefs" && e.newValue != "") {
  //    prefsString = e.newValue;
  //    prefs = JSON.parse(e.newValue);
  //  }
  //}, false);

  chrome.bitpop.prefs.uncensorShouldRedirect.onChange.addListener(function(details) {
    prefs.shouldRedirect = (+details.value === 0);
  });
  chrome.bitpop.prefs.uncensorShowMessage.onChange.addListener(function(details) {
    prefs.showMessage = details.value;
  });
  chrome.bitpop.prefs.uncensorNotifyUpdates.onChange.addListener(function(details) {
    prefs.notifyUpdate = details.value;
  });
  chrome.bitpop.prefs.uncensorDomainFilter.onChange.addListener(function(details) {
    //if (!inSetFilter)
      prefs.domainFilter = JSON.parse(details.value);
    //else
    //  inSetFilter = false;
  });
  chrome.bitpop.prefs.uncensorDomainExceptions.onChange.addListener(function(details) {
    //if (!inSetExceptions)
      prefs.domainExceptions = JSON.parse(details.value);
    //else
    //  inSetExceptions = false;
  });

  // Listen for any changes to the URL of any tab.
  chrome.tabs.onUpdated.addListener(redirectListener);
})();
