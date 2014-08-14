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

  var lconst = { PREPROCESS_FILTER: 1, PREPROCESS_EXCEPTIONS: 2 }; // bit flags

  function BitpopUncensorFilterOverlay() {
    this.activeNavTab = null;
    OptionsPage.call(this, 'uncensorFilter',
                     loadTimeData.getString('uncensorFilterOverlayTitle'),
                     'bitpop-uncensor-filter-overlay-page');
  }

  cr.addSingletonGetter(BitpopUncensorFilterOverlay);

  BitpopUncensorFilterOverlay.prototype = {
    __proto__: OptionsPage.prototype,

    filterList_: null,

    exceptionList_: null,

    /** inheritDoc */
    initializePage: function() {
      OptionsPage.prototype.initializePage.call(this);

      this.filterList_ = $('domain-filter-table');
      this.exceptionList_ = $('domain-exceptions-table');

      this.filterList_.companion = this.exceptionList_;
      this.exceptionList_.companion = this.filterList_;

      this.setUpList_(this.filterList_);
      this.setUpList_(this.exceptionList_);

      Preferences.getInstance().addEventListener(
        "bitpop.uncensor_domain_filter",
      	this.onFilterChange_.bind(this));
      Preferences.getInstance().addEventListener(
        "bitpop.uncensor_domain_exceptions",
      	this.onExceptionsChange_.bind(this));
    },

    setUpList_: function(list) {
      options.uncensor_filter.DomainRedirectionList.decorate(list);
      list.autoExpands = true;
    },

    updateFiltersList_: function(filter, exceptions, flags) {
      var newFilter = [];
      var newExceptions = [];

      if (flags & lconst.PREPROCESS_FILTER)
        this.filter = filter;
      else
        filter = this.filter;

      if (flags & lconst.PREPROCESS_EXCEPTIONS)
        this.exceptions = exceptions;
      else
        exceptions = this.exceptions;

      for (var i in filter) {
        if (filter.hasOwnProperty(i) && !(exceptions.hasOwnProperty(i)))
          newFilter.push({ srcDomain: i, dstDomain: filter[i] });
      }

      if (flags & lconst.PREPROCESS_EXCEPTIONS) {
        for (var i in exceptions) {
          if (exceptions.hasOwnProperty(i))
            newExceptions.push({ srcDomain: i, dstDomain: exceptions[i] });
        }
      }

      this.initListDiv_('filter-list-div', 'filterList_', newFilter);
      this.initListDiv_('exception-list-div', 'exceptionList_', newExceptions);
    },

		initListDiv_: function(divId, dataMemberName, listData) {
    	if (listData.length > 0) {
    		$(divId).hidden = false;

        listData.sort(function(a, b) {
          return a.srcDomain.localeCompare(b.srcDomain);
        });

    		for (var i = 0; i < listData.length; i++) {
    			listData[i].modelIndex = i;
          listData[i].isHeader = false;
    		}

    		var modelData = listData.slice();
        modelData.unshift(
	    		{
	    			srcDomain: loadTimeData.getString('uncensorOriginalDomainHeader'),
	    			dstDomain: loadTimeData.getString('uncensorNewLocationHeader'),
	    			isHeader: true
	    		}
    		);

        this[dataMemberName].arraySrc = listData.slice();
        this[dataMemberName].isFilterList = (dataMemberName == "filterList_");
    		this[dataMemberName].dataModel = new ArrayDataModel(modelData);

    	} else {
    		$(divId).hidden = true;
        this[dataMemberName].arraySrc = [];
    	}
    },

    onFilterChange_: function(event) {
    	var filter = JSON.parse(event.value['value']);

    	this.updateFiltersList_(filter, null, //TODO: refactor: remove 3rd param
          lconst.PREPROCESS_FILTER);
    },

    onExceptionsChange_: function(event) {
    	var exceptions = JSON.parse(event.value['value']);

    	this.updateFiltersList_(null, exceptions,
          lconst.PREPROCESS_EXCEPTIONS);
    },

    initLists_: function(filterPref, exceptionsPref) {
    	var filter = JSON.parse(filterPref);
    	var exceptions = JSON.parse(exceptionsPref);

    	this.updateFiltersList_(filter, exceptions,
          lconst.PREPROCESS_FILTER | lconst.PREPROCESS_EXCEPTIONS);
    },

  };

  //BitpopUncensorFilterOverlay.updateFiltersList = function(filter,
  //                                                      	 exceptions) {
  //  BitpopUncensorFilterOverlay.getInstance().updateFiltersList_(filter,
  //                                                       				 exceptions);
  //};

	BitpopUncensorFilterOverlay.initLists = function(filterPref,
                                                   exceptionsPref) {
    BitpopUncensorFilterOverlay.getInstance().initLists_(filterPref,
                                                         exceptionsPref);
  };

  // Export
  return {
    BitpopUncensorFilterOverlay: BitpopUncensorFilterOverlay,
  };

});

