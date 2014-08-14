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

cr.define('options.uncensor_filter', function() {
  /** @const */ var DeletableItemList = options.DeletableItemList;
  /** @const */ var DeletableItem = options.DeletableItem;
  var ListSingleSelectionModel = cr.ui.ListSingleSelectionModel;

  ///** @const */ var ListSelectionController = cr.ui.ListSelectionController;

  function DomainRedirectionListItem(redirect) {
    var el = cr.doc.createElement('div');
    el.redirect_ = redirect;
    DomainRedirectionListItem.decorate(el);
    return el;
  }

  DomainRedirectionListItem.decorate = function(el) {
    el.__proto__ = DomainRedirectionListItem.prototype;
    el.decorate();
  };

  DomainRedirectionListItem.prototype = {
    __proto__: DeletableItem.prototype,

    srcField_: null,
    dstField_: null,

    /** @inheritDoc */
    decorate: function() {
      DeletableItem.prototype.decorate.call(this);

      var redirect = this.redirect_;

      if (('isHeader' in redirect) && redirect.isHeader)
        this.deletable = false;
      else
        this.deletable = true;

      // Construct the src column.
      var srcColEl = this.ownerDocument.createElement('div');
      srcColEl.className = 'src-domain-column';
      if (('isHeader' in redirect) && redirect.isHeader)
        srcColEl.classList.add('header-column');
      srcColEl.classList.add('weakrtl');
      this.contentElement.appendChild(srcColEl);

      // Then the keyword column.
      var dstColEl = this.ownerDocument.createElement('div');
      dstColEl.className = 'dst-domain-column';
      if (('isHeader' in redirect) && redirect.isHeader)
        dstColEl.classList.add('header-column');
      dstColEl.classList.add('weakrtl');
      this.contentElement.appendChild(dstColEl);

      srcColEl.textContent = redirect.srcDomain;
      dstColEl.textContent = redirect.dstDomain;
    },
  };

  var DomainRedirectionList = cr.ui.define('list');

  DomainRedirectionList.prototype = {
    __proto__: DeletableItemList.prototype,

    decorate: function() {
      DeletableItemList.prototype.decorate.call(this);
      this.selectionModel = new ListSingleSelectionModel();
    },

    /** @inheritDoc */
    createItem: function(redirect) {
      return new DomainRedirectionListItem(redirect);
    },

    /** @inheritDoc */
    deleteItemAtIndex: function(index) {
      var item = this.items[index];
      var delData = this.dataModel.item(index);

      // A vaabshe-to:
      // console.assert(this.arraySrc && this.arraySrc.length &&
      //                  this.arraySrc.length !== 0)
      var selfDataArray = (this.arraySrc && this.arraySrc.slice()) || [];
      var companionDataArray = (this.companion.arraySrc &&
          this.companion.arraySrc.slice()) || [];

      for (var i = 0; i < companionDataArray.length; i++)
        console.assert(companionDataArray[i].srcDomain !== delData.srcDomain);

      if (selfDataArray[delData.modelIndex].srcDomain === delData.srcDomain) {
        companionDataArray.push(selfDataArray[delData.modelIndex]);
        selfDataArray.splice(delData.modelIndex, 1);
      }

      function modelToPref(modelArray) {
        var res = {};
        for (var i = 0; i < modelArray.length; i++)
          res[modelArray[i].srcDomain] = modelArray[i].dstDomain;
        return JSON.stringify(res);
      }

      if (this.isFilterList)
        //Preferences.setStringPref("bitpop.uncensor_domain_exceptions",
        //    modelToPref(companionDataArray), '');
        chrome.send("changeUncensorExceptions", [modelToPref(companionDataArray)]);
      else
        //Preferences.setStringPref("bitpop.uncensor_domain_exceptions",
        //    modelToPref(companionDataArray), '');
        chrome.send("changeUncensorExceptions", [modelToPref(selfDataArray)]);
    },

  };

  // Export
  return {
    DomainRedirectionList: DomainRedirectionList
  };

});

