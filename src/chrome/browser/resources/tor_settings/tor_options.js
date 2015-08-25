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

cr.exportPath('options');

options.SyncStatus;

cr.define('options', function() {
  var OptionsPage = options.OptionsPage;
  var Page = cr.ui.pageManager.Page;
  var PageManager = cr.ui.pageManager.PageManager;
  var ArrayDataModel = cr.ui.ArrayDataModel;
  var RepeatingButton = cr.ui.RepeatingButton;
  var HotwordSearchSettingIndicator = options.HotwordSearchSettingIndicator;

  /**
   * Encapsulated handling of browser options page.
   * @constructor
   * @extends {cr.ui.pageManager.Page}
   */
  function TorOptions() {
    Page.call(this, 'tor-settings', loadTimeData.getString('torSettingsTitle'),
              'tor-settings');
  }

  cr.addSingletonGetter(TorOptions);

  /**
   * @param {HTMLElement} section The section to show or hide.
   * @return {boolean} Whether the section should be shown.
   * @private
   */
  TorOptions.shouldShowSection_ = function(section) {
    // If the section is hidden or hiding, it should be shown.
    return section.style.height == '' || section.style.height == '0px';
  };

  TorOptions.prototype = {
    __proto__: Page.prototype,

    /**
     * Keeps track of whether the user is signed in or not.
     * @type {boolean}
     * @private
     */
    signedIn_: false,

    /**
     * Indicates whether signing out is allowed or whether a complete profile
     * wipe is required to remove the current enterprise account.
     * @type {boolean}
     * @private
     */
    signoutAllowed_: true,

    /**
     * Keeps track of whether |onShowHomeButtonChanged_| has been called. See
     * |onShowHomeButtonChanged_|.
     * @type {boolean}
     * @private
     */
    onShowHomeButtonChangedCalled_: false,

    /**
     * Track if page initialization is complete.  All C++ UI handlers have the
     * chance to manipulate page content within their InitializePage methods.
     * This flag is set to true after all initializers have been called.
     * @type {boolean}
     * @private
     */
    initializationComplete_: false,

    torSettingsInitialized_: false,

    /** @override */
    initializePage: function() {
      console.log('intializePage: {');
      Page.prototype.initializePage.call(this);
      var self = this;

      if (window.top != window) {
        // The options page is not in its own window.
        document.body.classList.add('uber-frame');
        PageManager.horizontalOffset = 155;
      }

      // Ensure that navigation events are unblocked on uber page. A reload of
      // the settings page while an overlay is open would otherwise leave uber
      // page in a blocked state, where tab switching is not possible.
      uber.invokeMethodOnParent('stopInterceptingEvents');

      window.addEventListener('message', this.handleWindowMessage_.bind(this));

      // if (loadTimeData.getBoolean('showAbout')) {
      //   $('about-button').hidden = false;
      //   $('about-button').addEventListener('click', function() {
      //     PageManager.showPageByName('help');
      //     chrome.send('coreOptionsUserMetricsAction',
      //                 ['Options_About']);
      //   });
      // }

      $('bridgesRadioYes').addEventListener('click',
          this.onBridgeTypeRadioChange_.bind(this), false);
      $('bridgeRadioCustom').addEventListener('click',
          this.onBridgeTypeRadioChange_.bind(this), false);

      //$('cancelBtn').addEventListener('click',
      //    function () { window.close(); /*chrome.send('CancelTorSettingsChange');*/ }, false);
      $('saveSettingsBtn').addEventListener('click',
          this.saveSettings_.bind(this), false);
      Preferences.getInstance().addEventListener(
          'torlauncher.settings.show_proxy_section',
          this.onShowProxySectionChanged_.bind(this));
      Preferences.getInstance().addEventListener(
          'torlauncher.settings.show_firewall_section',
          this.onShowFirewallSectionChanged_.bind(this));
      Preferences.getInstance().addEventListener(
          'torlauncher.settings.show_isp_block_section',
          this.onShowISPBlockSectionChanged_.bind(this));

      document.body.addEventListener('click', function(e) {
        var target = assertInstanceof(e.target, Node);
        var button = findAncestor(target, function(el) {
          return el.tagName == 'BUTTON' &&
                 el.dataset.extensionId !== undefined &&
                 el.dataset.extensionId.length;
        });
        if (button)
          chrome.send('disableExtension', [button.dataset.extensionId]);
      });
      console.log('} // intializePage');
    },

    /** @override */
    didShowPage: function() {
      console.log('didShowPage {');
      $('search-field').focus();
      console.log('} // didShowPage');
    },

   /**
    * Called after all C++ UI handlers have called InitializePage to notify
    * that initialization is complete.
    * @private
    */
    notifyInitializationComplete_: function() {
      console.log('notifyInitializationComplete {');
      this.initializationComplete_ = true;
      cr.dispatchSimpleEvent(document, 'initializationComplete');
      console.log('} // notifyInitializationComplete');
    },

    /**
     * Handler for messages sent from the main uber page.
     * @param {Event} e The 'message' event from the uber page.
     * @private
     */
    handleWindowMessage_: function(e) {
      console.log('handleWindowMessage {')
      if ((/** @type {{method: string}} */(e.data)).method == 'frameSelected')
        $('search-field').focus();
      console.log('} // handleWindowMessage');
    },

    /**
     * Animatedly changes height |from| a px number |to| a px number.
     * @param {HTMLElement} section The section to animate.
     * @param {HTMLElement} container The container of |section|.
     * @param {boolean} showing Whether to go from 0 -> container height or
     *     container height -> 0.
     * @private
     */
    animatedSectionHeightChange_: function(section, container, showing) {
      // If the section is already animating, dispatch a synthetic transition
      // end event as the upcoming code will cancel the current one.
      if (section.classList.contains('sliding'))
        cr.dispatchSimpleEvent(section, 'webkitTransitionEnd');

      this.addTransitionEndListener_(section);

      section.hidden = false;
      section.style.height = (showing ? 0 : container.offsetHeight) + 'px';
      section.classList.add('sliding');

      // Force a style recalc before starting the animation.
      /** @suppress {suspiciousCode} */
      section.offsetHeight;

      section.style.height = (showing ? container.offsetHeight : 0) + 'px';
    },

    /**
     * Shows the given section.
     * @param {HTMLElement} section The section to be shown.
     * @param {HTMLElement} container The container for the section. Must be
     *     inside of |section|.
     * @param {boolean} animate Indicate if the expansion should be animated.
     * @private
     */
    showSection_: function(section, container, animate) {
      // Delay starting the transition if animating so that hidden change will
      // be processed.
      if (animate) {
        this.animatedSectionHeightChange_(section, container, true);
      } else {
        section.hidden = false;
        section.style.height = 'auto';
      }
    },

    /**
     * Shows the given section, with animation.
     * @param {HTMLElement} section The section to be shown.
     * @param {HTMLElement} container The container for the section. Must be
     *     inside of |section|.
     * @private
     */
    showSectionWithAnimation_: function(section, container) {
      this.showSection_(section, container, /* animate */ true);
    },

    /**
     * Hides the given |section| with animation.
     * @param {HTMLElement} section The section to be hidden.
     * @param {HTMLElement} container The container for the section. Must be
     *     inside of |section|.
     * @private
     */
    hideSectionWithAnimation_: function(section, container) {
      this.animatedSectionHeightChange_(section, container, false);
    },

    /**
     * Toggles the visibility of |section| in an animated way.
     * @param {HTMLElement} section The section to be toggled.
     * @param {HTMLElement} container The container for the section. Must be
     *     inside of |section|.
     * @private
     */
    toggleSectionWithAnimation_: function(section, container) {
      if (TorOptions.shouldShowSection_(section))
        this.showSectionWithAnimation_(section, container);
      else
        this.hideSectionWithAnimation_(section, container);
    },

    /**
     * Scrolls the settings page to make the section visible auto-expanding
     * advanced settings if required.  The transition is not animated.  This
     * method is used to ensure that a section associated with an overlay
     * is visible when the overlay is closed.
     * @param {!Element} section  The section to make visible.
     * @private
     */
    scrollToSection_: function(section) {
      var advancedSettings = $('advanced-settings');
      var container = $('advanced-settings-container');
      var expander = $('advanced-settings-expander');
      if (!expander.hidden &&
          advancedSettings.hidden &&
          section.parentNode == container) {
        this.showSection_($('advanced-settings'),
                          $('advanced-settings-container'),
                          /* animate */ false);
        this.updateAdvancedSettingsExpander_();
      }

      if (!this.initializationComplete_) {
        var self = this;
        var callback = function() {
           document.removeEventListener('initializationComplete', callback);
           self.scrollToSection_(section);
        };
        document.addEventListener('initializationComplete', callback);
        return;
      }

      var pageContainer = $('page-container');
      // pageContainer.offsetTop is relative to the screen.
      var pageTop = pageContainer.offsetTop;
      var sectionBottom = section.offsetTop + section.offsetHeight;
      // section.offsetTop is relative to the 'page-container'.
      var sectionTop = section.offsetTop;
      if (pageTop + sectionBottom > document.body.scrollHeight ||
          pageTop + sectionTop < 0) {
        // Currently not all layout updates are guaranteed to precede the
        // initializationComplete event (for example 'set-as-default-browser'
        // button) leaving some uncertainty in the optimal scroll position.
        // The section is placed approximately in the middle of the screen.
        var top = Math.min(0, document.body.scrollHeight / 2 - sectionBottom);
        pageContainer.style.top = top + 'px';
        pageContainer.oldScrollTop = -top;
      }
    },

    /**
     * Adds a |webkitTransitionEnd| listener to the given section so that
     * it can be animated. The listener will only be added to a given section
     * once, so this can be called as multiple times.
     * @param {HTMLElement} section The section to be animated.
     * @private
     */
    addTransitionEndListener_: function(section) {
      if (section.hasTransitionEndListener_)
        return;

      section.addEventListener('webkitTransitionEnd',
          this.onTransitionEnd_.bind(this));
      section.hasTransitionEndListener_ = true;
    },

    /**
     * Called after an animation transition has ended.
     * @param {Event} event The webkitTransitionEnd event. NOTE: May be
     *     synthetic.
     * @private
     */
    onTransitionEnd_: function(event) {
      if (event.propertyName && event.propertyName != 'height') {
        // If not a synthetic event or a real transition we care about, bail.
        return;
      }

      var section = event.target;
      section.classList.remove('sliding');

      if (!event.propertyName) {
        // Only real transitions past this point.
        return;
      }

      if (section.style.height == '0px') {
        // Hide the content so it can't get tab focus.
        section.hidden = true;
        section.style.height = '';
      } else {
        // Set the section height to 'auto' to allow for size changes
        // (due to font change or dynamic content).
        section.style.height = 'auto';
      }
    },

    /**
     * Removes the 'http://' from a URL, like the omnibox does. If the string
     * doesn't start with 'http://' it is returned unchanged.
     * @param {string} url The url to be processed
     * @return {string} The url with the 'http://' removed.
     */
    stripHttp_: function(url) {
      return url.replace(/^http:\/\//, '');
    },

    initializePageUIWithData_: function(settingsObj) {
      console.log('initializePageUIWithData {');
      console.assert(settingsObj);
      console.assert(settingsObj.hasOwnProperty('proxySettings'));
      console.assert(settingsObj.hasOwnProperty('firewallSettings'));
      console.assert(settingsObj.hasOwnProperty('bridgeSettings'));

      // Proxy block initialization
      var proxySettings = settingsObj.proxySettings;
      if (proxySettings.hasOwnProperty('haveProxy')) {
        Preferences.setBooleanPref(
            'torlauncher.settings.show_proxy_section',
            proxySettings.haveProxy,
            true);
        if (proxySettings.haveProxy) {
          console.assert(proxySettings.hasOwnProperty('proxyType'));
          $('tor-proxy-type').value = proxySettings.proxyType;
          if (proxySettings.hasOwnProperty('proxyAddr') &&
              proxySettings.hasOwnProperty('proxyPort')) {
            $('tor-proxy-addr').value = proxySettings.proxyAddr;
            $('tor-proxy-port').value = proxySettings.proxyPort;
          }
          if (proxySettings.hasOwnProperty('proxyUsername'))
            $('tor-proxy-username').value = proxySettings.proxyUsername;
          if (proxySettings.hasOwnProperty('proxyPassword'))
            $('tor-proxy-password').value = proxySettings.proxyPassword;
        }
      }

      // Firewall block initialization
      var firewallSettings = settingsObj.firewallSettings;
      if (firewallSettings.hasOwnProperty('haveFirewall')) {
        Preferences.setBooleanPref(
            'torlauncher.settings.show_firewall_section',
            firewallSettings.haveFirewall,
            true);
        if (firewallSettings.hasOwnProperty('allowedPorts'))
          $('tor-allowed-ports').value = firewallSettings.allowedPorts;
      }

      // Bridge block initialization
      var bridgeSettings = settingsObj.bridgeSettings;
      if (bridgeSettings.hasOwnProperty('useBridges')) {
        Preferences.setBooleanPref(
            'torlauncher.settings.show_isp_block_section',
            bridgeSettings.useBridges,
            true);
        this.initDefaultBridgeTypeMenu_(bridgeSettings);
        if (bridgeSettings.hasOwnProperty('canUseDefaultBridges') &&
            !bridgeSettings.canUseDefaultBridges) {
          this.enableElemWithLabel_('defaultBridgeType', false);

          var label = document.getElementById("bridgeSettingsPrompt");
          if (label)
            label.setAttribute("hidden", true);

          var radioGroup = document.getElementById("bridgeTypeRadioGroup");
          if (radioGroup)
            radioGroup.setAttribute("hidden", true);

          var radioGroup2 = document.getElementById("bridgeTypeRadioGroup2");
          if (radioGroup2)
            radioGroup2.setAttribute("hidden", true);
        }

        var radioID = ((bridgeSettings.useDefault) ?
            "bridgesRadioYes" : "bridgeRadioCustom");
        var radio = document.getElementById(radioID);
        if (radio)
          radio.checked = true;
        this.onBridgeTypeRadioChange_();
      }

      if (bridgeSettings.useBridges) {
        if (bridgeSettings.useDefault) {
          if (bridgeSettings.hasOwnProperty('defaultType'))
            $('defaultBridgeType').value = bridgeSettings.defaultType;
        } else {
          if (bridgeSettings.hasOwnProperty('bridgeList')) {
            for (var i = 0; i < bridgeSettings.bridgeList.length; ++i) {
                $('bridgeList').value +=
                   ((i != 0) ? '\n' : '') + bridgeSettings.bridgeList[i];
            }
          }
        }
      }

      console.log('} // initializePageUIWithData');
      return null;
    },

    initDefaultBridgeTypeMenu_: function (bridgeSettings) {
      var menu = document.getElementById("defaultBridgeType");
      if (!menu)
        return;

      menu.options.length = 0;

      var typeArray = bridgeSettings.typeList;
      if (!typeArray || typeArray.length === 0)
        return;

      var recommendedType = bridgeSettings.recommendedType;
      var selectedType = bridgeSettings.defaultType;
      if (!selectedType)
        selectedType = recommendedType;

      for (var i = 0; i < typeArray.length; i++) {
        var bridgeType = typeArray[i];

        var menuItemLabel = bridgeType;
        if (bridgeType == recommendedType) {
          menuItemLabel +=
              " " + bridgeSettings.recommendedBridgeMenuItemLabelSuffix;
        }

        var option = document.createElement('option');
        option.value = bridgeType;
        if (bridgeType == selectedType)
          option.selected = true;
        option.text = menuItemLabel;
        menu.add(option);
      }
    },

    onCustomBridgesTextInput_: function () {
      $('bridgeRadioCustom').checked = true;
      this.onBridgeTypeRadioChange_();
    },

    onBridgeTypeRadioChange_: function () {
      var useCustom = $('bridgeRadioCustom').hasAttribute('checked');
      this.enableElemWithLabel_('defaultBridgeType', !useCustom);
      this.enableElemWithLabel_('bridgeListLabel', useCustom);
      var focusElemID = ((useCustom) ? 'bridgeList' : 'defaultBridgeType');
      var elem = $(focusElemID);
      if (elem)
        elem.focus();
    },

    // Enables / disables aID as well as optional aID+"Label" element.
    enableElemWithLabel_: function(aID, aEnable)
    {
      if (!aID)
        return;

      var elem = document.getElementById(aID);
      if (elem) {
        var label = document.getElementById(aID + "Label");
        if (aEnable) {
          if (label)
            label.removeAttribute("disabled");

          elem.removeAttribute("disabled");
        }
        else {
          if (label)
            label.setAttribute("disabled", true);

          elem.setAttribute("disabled", true);
        }
      }
    },

    saveSettings_: function () {
      var settings = {};
      settings.proxySettings = null;
      settings.firewallSettings = null;
      settings.bridgeSettings = null;

      if (!$('tor-proxy-settings-section').hidden) {
        settings.proxySettings = {};
        var s = $('tor-proxy-type');
        settings.proxySettings.haveProxy = (s.options[s.selectedIndex].value) ? true : false;
        settings.proxySettings.proxyType = s.options[s.selectedIndex].value;
        settings.proxySettings.proxyAddr = $('tor-proxy-addr').value;
        settings.proxySettings.proxyPort = $('tor-proxy-port').value;
        settings.proxySettings.proxyUsername = $('tor-proxy-username').value;
        settings.proxySettings.proxyPassword = $('tor-proxy-password').value;
      }

      if (!$('tor-firewall-settings-section').hidden) {
        settings.firewallSettings = {};
        settings.firewallSettings.firewallAllowedPorts =
            $('tor-allowed-ports').value;
      }

      if (!$('tor-isp-block-settings-section').hidden) {
        settings.bridgeSettings = {};
        settings.bridgeSettings.useBridges = $('bridgesRadioYes').checked ||
            $('bridgeRadioCustom').checked;
        settings.bridgeSettings.useDefault = $('bridgesRadioYes').checked;
        if (settings.bridgeSettings.useDefault) {
          var ts = $('defaultBridgeType');
          settings.bridgeSettings.defaultType = ts.options[ts.selectedIndex].value;
        } else {
          settings.bridgeSettings.bridgeList = $('bridgeList').value
        }
      }

      chrome.send('SaveTorSettings', [ settings ]);
    },

    onShowProxySectionChanged_: function (event) {
      var container = $('tor-proxy-settings-section');
      container.hidden = !event.value.value;
    },

    onShowFirewallSectionChanged_: function (event) {
      var container = $('tor-firewall-settings-section');
      container.hidden = !event.value.value;
    },

    onShowISPBlockSectionChanged_: function (event) {
      var container = $('tor-isp-block-settings-section');
      container.hidden = !event.value.value;
    },

    closeSettingsWindow_: function () {
      window.close();
    },

    displayErrorMessage_: function (message) {
      $('error_message').innerText = message;
    }
  };

  //Forward public APIs to private implementations.
  cr.makePublic(TorOptions, [
    'initializePageUIWithData',
    'closeSettingsWindow',
    'displayErrorMessage',
    'notifyInitializationComplete'
  ]);

  // Export
  return {
    TorOptions: TorOptions
  };
});
