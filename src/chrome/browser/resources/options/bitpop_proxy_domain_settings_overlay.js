// BitPop browser with features like Facebook chat and uncensored browsing. 
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

cr.define('options', function() {
  /** @const */ var OptionsPage = options.OptionsPage;
  /** @const */ var ArrayDataModel = cr.ui.ArrayDataModel;

  function BitpopProxyDomainSettingsOverlay() {
    this.activeNavTab = null;
    OptionsPage.call(this, 'uncensorBlockedSites',
                     loadTimeData.getString('uncensorBlockedSitesTitle'),
                     'bitpop-proxy-domain-settings-overlay-page');
  }

  cr.addSingletonGetter(BitpopProxyDomainSettingsOverlay);

  BitpopProxyDomainSettingsOverlay.prototype = {
    __proto__: OptionsPage.prototype,

    domainList_: null,

    /** inheritDoc */
    initializePage: function() {
      OptionsPage.prototype.initializePage.call(this);

      this.domainList_ = $('blocked-sites-list');

      options.uncensor_proxy.ProxySettingsList.decorate(this.domainList_);
      this.domainList_.autoExpands = true;

      Preferences.getInstance().addEventListener(
      	"bitpop.ip_recognition_country_name",
      	this.onCountryChange_.bind(this));
      Preferences.getInstance().addEventListener(
        "bitpop.blocked_sites_list",
      	this.onListChange_.bind(this));

      cr.doc.addEventListener("updateProxySetting",
        this.onUpdateProxySetting_.bind(this), false);

      $('update-domains').onclick = function (e) {
        chrome.send('updateDomains');
      };
    },

    updateListFromPrefValue_: function(listPrefValue) {
      if (listPrefValue) {
    	  var data = JSON.parse(listPrefValue);
    	  this.domainList_.dataModel = new ArrayDataModel(data);
      }
    },

    onListChange_: function(event) {
    	this.updateListFromPrefValue_(event.value['value']);
    },

    onCountryChange_: function(event) {
   		var countryVal = event.value['value'];
   		$('ipRecognitionCountryName').textContent = countryVal;
    },

    onUpdateProxySetting_: function(ev) {
      var settingList = [];
      var items = this.domainList_.items;
      var modelItems = this.domainList_.dataModel;
      console.assert(items.length === modelItems.length);
      for (var i = 0; i < items.length; i++)
        settingList.push({
          description: modelItems.item(i).description,
          value: items[i].proxySetting
        });

      //Preferences.setStringPref("bitpop.blocked_sites_list",
      //    JSON.stringify(settingList), '');
      chrome.send("proxySiteListChange", [JSON.stringify(settingList)]);
    },
  };

  BitpopProxyDomainSettingsOverlay.updateListFromPrefValue =
  	function(prefValue) {
  		BitpopProxyDomainSettingsOverlay.getInstance().updateListFromPrefValue_(
  			prefValue);
  	};

  BitpopProxyDomainSettingsOverlay.updateCountryName = function(name) {
    $('ipRecognitionCountryName').textContent = name;
  };

  return {
  	BitpopProxyDomainSettingsOverlay: BitpopProxyDomainSettingsOverlay
  };
});
