// BitPop browser. Tor launcher integration part.
// Copyright (C) 2015 BitPop AS
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

// Copyright (c) 2012 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

var AlertOverlay = options.AlertOverlay;
var TorOptions = options.TorOptions;
var ConfirmDialog = options.ConfirmDialog;
var OptionsFocusManager = options.OptionsFocusManager;
var OptionsPage = options.OptionsPage;
var PageManager = cr.ui.pageManager.PageManager;
var Preferences = options.Preferences;
var SearchPage = options.SearchPage;

/**
 * DOMContentLoaded handler, sets up the page.
 */
function load() {
  // Decorate the existing elements in the document.
  cr.ui.decorate('input[pref][type=checkbox]', options.PrefCheckbox);
  cr.ui.decorate('input[pref][type=number]', options.PrefNumber);
  cr.ui.decorate('input[pref][type=radio]', options.PrefRadio);
  cr.ui.decorate('input[pref][type=range]', options.PrefRange);
  cr.ui.decorate('select[pref]', options.PrefSelect);
  cr.ui.decorate('input[pref][type=text]', options.PrefTextField);
  cr.ui.decorate('input[pref][type=url]', options.PrefTextField);
  cr.ui.decorate('button[pref]', options.PrefButton);
  cr.ui.decorate('#content-settings-page input[type=radio]:not(.handler-radio)',
      options.ContentSettingsRadio);
  cr.ui.decorate('#content-settings-page input[type=radio].handler-radio',
      options.HandlersEnabledRadio);
  cr.ui.decorate('span.controlled-setting-indicator',
      options.ControlledSettingIndicator);

  // Top level pages.
  PageManager.register(SearchPage.getInstance());
  PageManager.register(TorOptions.getInstance());

  // TODO: register overlays

  cr.ui.FocusManager.disableMouseFocusOnButtons();
  OptionsFocusManager.getInstance().initialize();
  Preferences.getInstance().initialize();
  OptionsPage.initialize();
  PageManager.initialize(TorOptions.getInstance());
  PageManager.addObserver(new uber.PageManagerObserver());
  uber.onContentFrameLoaded();

  var pageName = PageManager.getPageNameFromPath();
  // Still update history so that chrome://settings/nonexistant redirects
  // appropriately to chrome://settings/. If the URL matches, updateHistory_
  // will avoid the extra replaceState.
  var updateHistory = true;
  PageManager.showPageByName(pageName, updateHistory,
                             {replaceState: true, hash: location.hash});

  var subpagesNavTabs = document.querySelectorAll('.subpages-nav-tabs');
  for (var i = 0; i < subpagesNavTabs.length; i++) {
    subpagesNavTabs[i].onclick = function(event) {
      OptionsPage.showTab(event.srcElement);
    };
  }

  window.setTimeout(function() {
    document.documentElement.classList.remove('loading');
    chrome.send('onFinishedLoadingOptions');
  }, 0);
}

document.documentElement.classList.add('loading');
document.addEventListener('DOMContentLoaded', load);

/**
 * Listener for the |beforeunload| event.
 */
window.onbeforeunload = function() {
  PageManager.willClose();
};

/**
 * Listener for the |popstate| event.
 * @param {Event} e The |popstate| event.
 */
window.onpopstate = function(e) {
  var pageName = PageManager.getPageNameFromPath();
  PageManager.setState(pageName, location.hash, e.state);
};
