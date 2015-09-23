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

// class attribute management for dom elements
function hasClass(ele,cls) {
	return ele.className.match(new RegExp('(\\s|^)'+cls+'(\\s|$)'));
}
function addClass(ele,cls) {
	if (!this.hasClass(ele,cls)) ele.className += " "+cls;
}
function removeClass(ele,cls) {
	if (hasClass(ele,cls)) {
		var reg = new RegExp('(\\s|^)'+cls+'(\\s|$)');
		ele.className=ele.className.replace(reg,' ');
	}
}

function $(id) { return document.getElementById(id); }
function _(name) { return chrome.i18n.getMessage(name); }

var prefs = null;
var needsUpdate = true;

var insertRow = function(dst, domainPair)
{
  var table = dst;
  var compartmentTable = null;
  var prefDictionary = null;
  var compartmentDictionary = null;
  var anchorTitle = "";

  switch (dst.id) {
    case 'domain_filter_table':
      prefDictionary = 'domainFilter';
      compartmentDictionary = 'domainExceptions';
      compartmentTable = document.getElementById('domain_exceptions_table');
      anchorTitle = 'Exclude domains. Moves highlighted domain pair to Exceptions list.';
      break;
    case 'domain_exceptions_table':
      prefDictionary = 'domainExceptions';
      compartmentDictionary = 'domainFilter';
      compartmentTable = document.getElementById('domain_filter_table');
      anchorTitle = 'Enable domains. Moves highlighted domain pair to The Filter list.'
      break;
  }

  var tbody = table.getElementsByTagName('tbody').length ? table.getElementsByTagName('tbody')[0] : undefined;
  if (tbody == undefined) {
    tbody = document.createElement('tbody');
    table.appendChild(tbody);
  }

  var newRow = tbody.insertRow(-1);
  newRow.onmouseover = function() { addClass(this, 'highlight'); };
  newRow.onmouseout = function() { removeClass(this, 'highlight'); };
  if (tbody.children.length % 2 == 0) { // even row
    addClass(newRow, 'uncensor-even-row');
  }

  var oCell = newRow.insertCell(-1);
  oCell.innerHTML = "<img src='images/web.png' width='16' height='16' alt='' />";
  oCell.vAlign = "middle";
  oCell.style.width = "20px";

  oCell = newRow.insertCell(-1);
  oCell.innerHTML = domainPair.originalDomain;
  oCell.style.width = "50%";

  oCell = newRow.insertCell(-1);
  oCell.innerHTML = domainPair.newLocation;
  oCell.style.width = "50%";

  anchor = document.createElement('a');
  anchor.href = "#";
  anchor.className = "delete-icon";
  anchor.title = anchorTitle;
  anchor.domainPair = domainPair;
  icon = document.createElement('img');
  icon.src = "images/delete.png";
  icon.vAlign = "middle";
  icon.width = "16";
  icon.height = "16";
  anchor.appendChild(icon);


  anchor.onclick = function() {
    var row;
    var rowIndex = 0;
    // Search current row index
    for ( ; rowIndex < tbody.getElementsByTagName('tr').length; rowIndex++) {
      row = tbody.getElementsByTagName('tr')[rowIndex];
      rowCells = row.getElementsByTagName('td');
      if (rowCells.length != 3)
        return;
      if (rowCells[1].innerHTML == this.domainPair.originalDomain)
        break;
    }

    insertRow(compartmentTable, this.domainPair);
    tbody.deleteRow(rowIndex);

    var prefs = JSON.parse(localStorage.prefs);

    prefs[compartmentDictionary][this.domainPair.originalDomain] = this.domainPair.newLocation;
    if (prefDictionary != 'domainFilter')
        delete prefs[prefDictionary][this.domainPair.originalDomain];

    localStorage.prefs = JSON.stringify(prefs);

    return false;
  };

  oCell.appendChild(anchor);
};

var save = function() {
  var prefs = JSON.parse(localStorage.prefs);
  prefs.shouldRedirect = document.getElementById('uncensor_always_redirect').checked;
  prefs.showMessage = document.getElementById('uncensor_show_message').checked;
  prefs.notifyUpdate = document.getElementById('uncensor_notify_update').checked;
  localStorage.prefs = JSON.stringify(prefs);
};

// Make sure the checkbox checked state gets properly initialized from the
// saved preference.
var initUncensorOptions = function(prefs) {
  if (prefs.shouldRedirect) {
    document.getElementById('uncensor_always_redirect').checked = true;
    document.getElementById('uncensor_never_redirect').checked = false;
  }
  else {
    document.getElementById('uncensor_always_redirect').checked = false;
    document.getElementById('uncensor_never_redirect').checked = true;
  }

  document.getElementById('uncensor_show_message').checked = prefs.showMessage;
  document.getElementById('uncensor_notify_update').checked = prefs.notifyUpdate;
  var filterTable = document.getElementById("domain_filter_table");
  for (var originalDomain in prefs.domainFilter) {
    if (!(originalDomain in prefs.domainExceptions)) {
      this.insertRow(filterTable, { originalDomain: originalDomain,
                            newLocation: prefs.domainFilter[originalDomain] });
    }
  }
  var exceptionsTable = document.getElementById("domain_exceptions_table");
  for (var originalDomain in prefs.domainExceptions) {
    this.insertRow(exceptionsTable, { originalDomain: originalDomain,
                          newLocation: prefs.domainExceptions[originalDomain] });
  }

  document.getElementById('uncensor_always_redirect').onclick = save;
  document.getElementById('uncensor_never_redirect').onclick = save;
  document.getElementById('uncensor_show_message').onchange = save;
  document.getElementById('uncensor_notify_update').onchange = save;
};

var updateTables = function() {
  var prefs = JSON.parse(localStorage.prefs);

  fillTable = function(data) {
    var table = (data == prefs.domainFilter) ? document.getElementById('domain_filter_table') :
                                            document.getElementById('domain_exceptions_table');
    var tbody = table.getElementsByTagName('tbody').length ? table.getElementsByTagName('tbody')[0] : undefined;
    if (tbody == undefined) {
      tbody = document.createElement('tbody');
      table.appendChild(tbody);
    }

    if (tbody.hasChildNodes()) {
      while (tbody.childNodes.length >= 1) {
        tbody.removeChild( tbody.firstChild );
      }
    }

    for (var originalDomain in data) {
      if (data == prefs.domainExceptions || !(originalDomain in prefs.domainExceptions)) {
        insertRow(table, { originalDomain: originalDomain,
                              newLocation: data[originalDomain] });
      }
    }
  };

  fillTable(prefs.domainFilter);
  fillTable(prefs.domainExceptions);
};

var updatePageControlStates_ = function(e) {
  if (e.key == "prefs" && e.newValue != "") {
    var prefs = JSON.parse(e.newValue);

    initUncensorOptions(prefs);
    updateTables();
  }
};

document.title = _("optionsTitle");
document.addEventListener('storage', updatePageControlStates_, false);
window.addEventListener('load', function() {
  $('uncensorPageHeader').innerText               = _('extName');
  $('uncensorPageDescription').innerText          = _('extDesc');
  $('uncensorFilterControl').innerText            = _('filterControl');
  $('uncensorAlwaysRedirectOn').innerText         = _('alwaysRedirect');
  $('uncensorNeverRedirectOff').innerText         = _('neverRedirect');
  $('uncensorNotices').innerText                  = _('notices');
  $('uncensorShowMessage').innerText              = _('showMessage');
  $('uncensorNotifyUpdates').innerText            = _('notifyUpdates');
  $('uncensorOriginalDomain').innerText           = _('originalDomain');
  $('uncensorOriginalDomainExceptions').innerText = _('originalDomain');
  $('uncensorNewLocation').innerText              = _('newLocation');
  $('uncensorNewLocationExceptions').innerText    = _('newLocation');
  $('uncensorExceptions').innerText               = _('exceptions');

  updatePageControlStates_({key: 'prefs', newValue: localStorage.prefs ? localStorage.prefs : ''});

  $('navToSettings').addEventListener('click', function(e) {
    chrome.tabs.update(null, { url: 'chrome://settings' });
    e.preventDefault();
  });
}, false);
