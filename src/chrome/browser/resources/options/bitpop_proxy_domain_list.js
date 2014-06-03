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

cr.define('options.uncensor_proxy', function() {
 /** @const */ var List = cr.ui.List;
 /** @const */ var ListItem = cr.ui.ListItem;

  var ProxySettingsListItemParent = cr.ui.define('li');
  ProxySettingsListItemParent.prototype = {
    __proto__: ListItem.prototype,
  };


  function ProxySettingsListItem(data) {
    var el = cr.doc.createElement('div');
    el.data_ = data;
    ProxySettingsListItem.decorate(el);
    return el;
  }

  ProxySettingsListItem.decorate = function(el) {
    el.__proto__ = ProxySettingsListItem.prototype;
    el.decorate();
  };

  ProxySettingsListItem.prototype = {
    __proto__: ProxySettingsListItemParent.prototype,

    descEl_: null,
    comboField_: null,

    /** @inheritDoc */
    decorate: function() {
      ProxySettingsListItemParent.prototype.decorate.call(this);

      var data = this.data_;

      // Construct the src column.
      var descColEl = this.ownerDocument.createElement('div');
      descColEl.className = 'domain-description-column';
      descColEl.classList.add('weakrtl');
      this.appendChild(descColEl);

      descColEl.textContent = data.description;
      this.descEl_ = descColEl;

      // Then the keyword column.
      var actColEl = this.ownerDocument.createElement('div');
      actColEl.className = 'dst-domain-column';
      actColEl.classList.add('weakrtl');
      this.appendChild(actColEl);

      var comboField = this.ownerDocument.createElement('select');
      comboField.className = "proxy-usage-select";
      comboField.classList.add('weakrtl');
      var itemValues = [
      	[ loadTimeData.getString("useGlobalSettingDefaultOption"),
      			'use_global' ],
      	[ loadTimeData.getString("useAutoProxy"), 'use_auto'],
      	[ loadTimeData.getString("neverUseProxy"), 'never_use' ],
      	[ loadTimeData.getString("askBeforeUsing"), 'ask_me' ]
      ];

      for (var i = 0; i < itemValues.length; i++)
      	comboField.appendChild(new Option(itemValues[i][0], itemValues[i][1]),
                               false, false);

      var self = this;
      comboField.addEventListener('change', function(e) {
        var ev = new CustomEvent("updateProxySetting",
          {
            cancelable: true,
            bubbles: true,
            detail: null,
          });
        cr.doc.dispatchEvent(ev);
      });

   		actColEl.appendChild(comboField);
      this.comboField_ = comboField;

      var toSelect = comboField.querySelector('[value="' +
                                              String(data.value) + '"]');
      toSelect.selected = true;
    },

    get proxySetting() {
      return this.comboField_.value;
    },
  };

  var ProxySettingsList = cr.ui.define('list');

  ProxySettingsList.prototype = {
    __proto__: List.prototype,

    /** @inheritDoc */
    createItem: function(dataItem) {
      return new ProxySettingsListItem(dataItem);
    },

  };

  // Export
  return {
    ProxySettingsList: ProxySettingsList
  };

});
