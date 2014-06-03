// Copyright (c) 2012 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

cr.define('options', function() {
  /** @const */ var OptionsPage = options.OptionsPage;

  // Variable to track if a captcha challenge was issued. If this gets set to
  // true, it stays that way until we are told about successful login from
  // the browser.  This means subsequent errors (like invalid password) are
  // rendered in the captcha state, which is basically identical except we
  // don't show the top error blurb 'Error Signing in' or the 'Create
  // account' link.
  var captchaChallengeActive_ = false;

  // When true, the password value may be empty when submitting auth info.
  // This is true when requesting an access code or when requesting an OTP or
  // captcha with the oauth sign in flow.
  var allowEmptyPassword_ = false;

  // True if the synced account uses a custom passphrase.
  var usePassphrase_ = false;

  // True if the synced account uses 'encrypt everything'.
  var useEncryptEverything_ = false;

  // True if the support for keystore encryption is enabled. Controls whether
  // the new unified encryption UI is displayed instead of the old encryption
  // ui (where passphrase and encrypted types could be set independently of
  // each other).
  var keystoreEncryptionEnabled_ = false;

  // The last email address that this profile was connected to.  If the profile
  // was never connected this is an empty string.  Otherwise it is a normalized
  // email address.
  var lastEmailAddress_ = '';

  // Do not encrypt without setting the master password by default
  var shouldNotEncrypt_ = true;

  /**
   * SyncSetupOverlay class
   * Encapsulated handling of the 'Sync Setup' overlay page.
   * @class
   */
  function SyncSetupOverlay() {
    OptionsPage.call(this, 'syncSetup',
                     loadTimeData.getString('syncSetupOverlayTabTitle'),
                     'sync-setup-overlay');
  }

  cr.addSingletonGetter(SyncSetupOverlay);

  SyncSetupOverlay.prototype = {
    __proto__: OptionsPage.prototype,

    /**
     * Initializes the page.
     */
    initializePage: function() {
      OptionsPage.prototype.initializePage.call(this);

      var self = this;
      $('gaia-login-form').onsubmit = function() {
        self.closeOverlay_();
        return false;
      };
      $('do-not-encrypt-option').onchange =
          $('encrypt-sensitive-option').onchange =
          $('encrypt-all-option').onchange = function() {
        self.onEncryptionRadioChanged_();
      };
      $('basic-encryption-option').onchange =
          $('full-encryption-option').onchange = function() {
        self.onEncryptionRadioChanged_();
      }
      $('choose-datatypes-cancel').onclick =
          $('sync-setup-cancel').onclick =
          $('confirm-everything-cancel').onclick =
          $('stop-syncing-cancel').onclick =
          $('sync-spinner-cancel').onclick = function() {
        self.closeOverlay_();
      };
      $('confirm-everything-ok').onclick = function() {
        self.sendConfiguration_();
      };
      $('timeout-ok').onclick = function() {
        chrome.send('CloseTimeout');
        self.closeOverlay_();
      };
      $('stop-syncing-ok').onclick = function() {
        chrome.send('SyncSetupStopSyncing', [$('logout-facebook').checked]);
        self.closeOverlay_();
      };
      $('different-email').innerHTML = loadTimeData.getString('differentEmail');
    },

    showOverlay_: function() {
      if (this.waitingForSigninPageResult_) {
        window.removeEventListener('beforeunload',
            SyncSetupOverlay.openSigninInProgressDialog, false);
      }
      this.waitingForSigninPageResult_ = false;

      OptionsPage.navigateToPage('syncSetup');
    },

    closeOverlay_: function() {
      OptionsPage.closeOverlay();
    },

    /** @override */
    didShowPage: function() {
      var forceLogin = document.location.hash == '#forceLogin';
      var result = JSON.stringify({'forceLogin': forceLogin});
      chrome.send('SyncSetupAttachHandler', [result]);
    },

    /** @override */
    didClosePage: function() {
      chrome.send('SyncSetupDidClosePage');
    },

    getEncryptionRadioCheckedValue_: function() {
      var f = $('choose-data-types-form');
      for (var i = 0; i < f.encrypt.length; ++i) {
        if (f.encrypt[i].checked)
          return f.encrypt[i].value;
      }

      return undefined;
    },

    getPassphraseRadioCheckedValue_: function() {
      /*
      var f = $('choose-data-types-form');
      for (var i = 0; i < f.option.length; ++i) {
        if (f.option[i].checked) {
          return f.option[i].value;
        }
      }
      */

      return 'explicit';
    },

    disableEncryptionRadioGroup_: function() {
      var f = $('choose-data-types-form');
      for (var i = 0; i < f.encrypt.length; ++i)
        f.encrypt[i].disabled = true;
    },

    /*
    onPassphraseRadioChanged_: function() {
      var visible = this.getPassphraseRadioCheckedValue_() == 'explicit';
      $('sync-custom-passphrase').hidden = !visible;
    },
    */

    onEncryptionRadioChanged_: function() {
      var hidden = this.getEncryptionRadioCheckedValue_() == 'none';
      $('sync-passphrase-ui-toggler').hidden = hidden;
      if (!hidden)
        $('sync-custom-passphrase').hidden = false;
      this.updatePasswordsCheckbox_();
    },

    checkAllDataTypeCheckboxes_: function() {
      // Only check the visible ones (since there's no way to uncheck
      // the invisible ones).
      var checkboxes = $('choose-data-types-body').querySelectorAll(
          '.sync-type-checkbox:not([hidden]) input');
      for (var i = 0; i < checkboxes.length; i++) {
        checkboxes[i].checked = true;
      }
    },

    setDataTypeCheckboxesEnabled_: function(enabled) {
      var checkboxes = $('choose-data-types-body').querySelectorAll('input');
      for (var i = 0; i < checkboxes.length; i++) {
        checkboxes[i].disabled = !enabled;
      }
    },

    setCheckboxesToKeepEverythingSynced_: function(value) {
      this.setDataTypeCheckboxesEnabled_(!value);
      if (value)
        this.checkAllDataTypeCheckboxes_();
    },

    // Returns true if none of the visible checkboxes are checked.
    noDataTypesChecked_: function() {
      var query = '.sync-type-checkbox:not([hidden]) input:checked';
      var checkboxes = $('choose-data-types-body').querySelectorAll(query);
      return checkboxes.length === 0;
    },

    checkPassphraseMatch_: function() {
      var emptyError = $('empty-error');
      var mismatchError = $('mismatch-error');
      emptyError.hidden = true;
      mismatchError.hidden = true;

      var f = $('choose-data-types-form');
      /*
      if ((this.getPassphraseRadioCheckedValue_() != 'explicit' ||
           $('google-option').disabled) &&
          (!$('full-encryption-option').checked ||
           $('basic-encryption-option').disabled)) {
        return true;
      }
      */

      var customPassphrase = $('custom-passphrase');
      if (customPassphrase.value.length === 0) {
        emptyError.hidden = false;
        return false;
      }

      var confirmPassphrase = $('confirm-passphrase');
      if (confirmPassphrase.value != customPassphrase.value) {
        mismatchError.hidden = false;
        return false;
      }

      return true;
    },

    sendConfiguration_: function() {
      // Trying to submit, so hide previous errors.
      $('error-text').hidden = true;

      var syncAll = $('sync-select-datatypes').selectedIndex === 0;
      if (!syncAll && this.noDataTypesChecked_()) {
        $('error-text').hidden = false;
        return;
      }

      var shouldNotEncrypt = this.getEncryptionRadioCheckedValue_() == 'none';
      var encryptAllData = !shouldNotEncrypt &&
                            this.getEncryptionRadioCheckedValue_() == 'all';

      var usePassphrase;
      var customPassphrase;
      var googlePassphrase = false;
      if (!$('sync-existing-passphrase-container').hidden) {
        // If we were prompted for an existing passphrase, use it.
        customPassphrase = $('choose-data-types-form').passphrase.value;
        usePassphrase = true;
        // If we were displaying the 'enter your old google password' prompt,
        // then that means this is the user's google password.
        googlePassphrase = !$('google-passphrase-needed-body').hidden;
        // We allow an empty passphrase, in case the user has disabled
        // all their encrypted datatypes. In that case, the PSS will accept
        // the passphrase and finish configuration. If the user has enabled
        // encrypted datatypes, the PSS will prompt again specifying that the
        // passphrase failed.
      } else if (!shouldNotEncrypt) {
        // The user is setting a custom passphrase for the first time.
        if (!this.checkPassphraseMatch_())
          return;
        customPassphrase = $('custom-passphrase').value;
        usePassphrase = true;
      } else {
        // The user is not setting a custom passphrase.
        usePassphrase = false;
      }

      // Don't allow the user to tweak the settings once we send the
      // configuration to the backend.
      this.setInputElementsDisabledState_(true);
      this.animateDisableLink_($('use-default-link'), true, null);

      // These values need to be kept in sync with where they are read in
      // SyncSetupFlow::GetDataTypeChoiceData().
      var result = JSON.stringify({
        'syncAllDataTypes': syncAll,
        'bookmarksSynced': syncAll || $('bookmarks-checkbox').checked,
        'preferencesSynced': syncAll || $('preferences-checkbox').checked,
        'themesSynced': syncAll || $('themes-checkbox').checked,
        'passwordsSynced': syncAll || $('passwords-checkbox').checked,
        'autofillSynced': syncAll || $('autofill-checkbox').checked,
        'extensionsSynced': syncAll || $('extensions-checkbox').checked,
        'typedUrlsSynced': syncAll || $('typed-urls-checkbox').checked,
        'appsSynced': syncAll || $('apps-checkbox').checked,
        'sessionsSynced': syncAll || $('sessions-checkbox').checked,
        'shouldNotEncrypt': shouldNotEncrypt,
        'encryptAllData': encryptAllData,
        'usePassphrase': usePassphrase,
        'isGooglePassphrase': googlePassphrase,
        'passphrase': customPassphrase
      });
      chrome.send('SyncSetupConfigure', [result]);
    },

    /**
     * Sets the disabled property of all input elements within the 'Customize
     * Sync Preferences' screen. This is used to prohibit the user from changing
     * the inputs after confirming the customized sync preferences, or resetting
     * the state when re-showing the dialog.
     * @param {boolean} disabled True if controls should be set to disabled.
     * @private
     */
    setInputElementsDisabledState_: function(disabled) {
      var configureElements =
          $('customize-sync-preferences').querySelectorAll('input');
      for (var i = 0; i < configureElements.length; i++)
        configureElements[i].disabled = disabled;
      $('sync-select-datatypes').disabled = disabled;

      var self = this;
      this.animateDisableLink_($('customize-link'), disabled, function() {
        self.showCustomizePage_(null, true);
      });
    },

    /**
     * Animate a link being enabled/disabled. The link is hidden by animating
     * its opacity, but to ensure the user doesn't click it during that time,
     * its onclick handler is changed to null as well.
     * @param {HTMLElement} elt The anchor element to enable/disable.
     * @param {boolean} disabled True if the link should be disabled.
     * @param {function} enabledFunction The onclick handler when the link is
     *     enabled.
     * @private
     */
    animateDisableLink_: function(elt, disabled, enabledFunction) {
      if (disabled) {
        elt.classList.add('transparent');
        elt.onclick = null;
        elt.addEventListener('webkitTransitionEnd', function f(e) {
          if (e.propertyName != 'opacity')
            return;
          elt.removeEventListener('webkitTransitionEnd', f);
          elt.classList.remove('transparent');
          elt.hidden = true;
        });
      } else {
        elt.hidden = false;
        elt.onclick = enabledFunction;
      }
    },

    /**
     * Shows or hides the Sync data type checkboxes in the advanced
     * configuration screen.
     * @param {Object} args The configuration data used to show/hide UI.
     * @private
     */
    setChooseDataTypesCheckboxes_: function(args) {
      var datatypeSelect = $('sync-select-datatypes');
      datatypeSelect.selectedIndex = args.syncAllDataTypes ? 0 : 1;

      $('bookmarks-checkbox').checked = args.bookmarksSynced;
      $('preferences-checkbox').checked = args.preferencesSynced;
      $('themes-checkbox').checked = args.themesSynced;

      if (args.passwordsRegistered) {
        $('passwords-checkbox').checked = args.passwordsSynced;
        $('passwords-item').hidden = false;
      } else {
        $('passwords-item').hidden = true;
      }
      if (args.autofillRegistered) {
        $('autofill-checkbox').checked = args.autofillSynced;
        $('autofill-item').hidden = false;
      } else {
        $('autofill-item').hidden = true;
      }
      if (args.extensionsRegistered) {
        $('extensions-checkbox').checked = args.extensionsSynced;
        $('extensions-item').hidden = false;
      } else {
        $('extensions-item').hidden = true;
      }
      if (args.typedUrlsRegistered) {
        $('typed-urls-checkbox').checked = args.typedUrlsSynced;
        $('omnibox-item').hidden = false;
      } else {
        $('omnibox-item').hidden = true;
      }
      if (args.appsRegistered) {
        $('apps-checkbox').checked = args.appsSynced;
        $('apps-item').hidden = false;
      } else {
        $('apps-item').hidden = true;
      }
      if (args.sessionsRegistered) {
        $('sessions-checkbox').checked = args.sessionsSynced;
        $('sessions-item').hidden = false;
      } else {
        $('sessions-item').hidden = true;
      }

      this.setCheckboxesToKeepEverythingSynced_(args.syncAllDataTypes);
    },

    setEncryptionRadios_: function(args) {
      if (args.shouldNotEncrypt) {
        $('do-not-encrypt-option').checked = true;
      } else if (args.encryptAllData) {
        $('encrypt-all-option').checked = true;
        this.disableEncryptionRadioGroup_();
      } else {
        $('encrypt-sensitive-option').checked = true;
      }
      this.updatePasswordsCheckbox_();
    },

    updatePasswordsCheckbox_: function() {
      if ($('do-not-encrypt-option').checked === true) {
        $('passwords-checkbox').checked = false;
        $('passwords-checkbox').disabled = true;
      } else {
        var datatypeSelect = $('sync-select-datatypes');
        if (datatypeSelect.selectedIndex === 0)
          $('passwords-checkbox').checked = true;
        else if ($('passwords-checkbox').disabled === true)
          $('passwords-checkbox').disabled = false;
      }
    },

    setCheckboxesAndErrors_: function(args) {
      this.setChooseDataTypesCheckboxes_(args);
      this.setEncryptionRadios_(args);
    },

    showConfigure_: function(args) {
      var datatypeSelect = $('sync-select-datatypes');
      var self = this;
      datatypeSelect.onchange = function() {
        var syncAll = this.selectedIndex === 0;
        self.setCheckboxesToKeepEverythingSynced_(syncAll);
        self.updatePasswordsCheckbox_();
      };

      this.resetPage_('sync-setup-configure');
      $('sync-setup-configure').hidden = false;

      // onsubmit is changed when submitting a passphrase. Reset it to its
      // default.
      $('choose-data-types-form').onsubmit = function() {
        self.sendConfiguration_();
        return false;
      };

      if (args) {
        this.setCheckboxesAndErrors_(args);
        this.updatePasswordsCheckbox_();

        this.shouldNotEncrypt_ = args.shouldNotEncrypt;
        this.useEncryptEverything_ = args.encryptAllData;

        // Whether to display the 'Sync everything' confirmation page or the
        // customize data types page.
        var syncAllDataTypes = args.syncAllDataTypes;
        this.usePassphrase_ = args.usePassphrase;
        this.keystoreEncryptionEnabled_ = args.keystoreEncryptionEnabled;
        if (args.showSyncEverythingPage == false || this.usePassphrase_ ||
            syncAllDataTypes == false || args.showPassphrase) {
          this.showCustomizePage_(args, syncAllDataTypes);
        } else {
          this.showSyncEverythingPage_();
        }
      }
    },

    showSpinner_: function() {
      this.resetPage_('sync-setup-spinner');
      $('sync-setup-spinner').hidden = false;
    },

    showTimeoutPage_: function() {
      this.resetPage_('sync-setup-timeout');
      $('sync-setup-timeout').hidden = false;
    },

    showSyncEverythingPage_: function() {
      $('confirm-sync-preferences').hidden = false;
      $('customize-sync-preferences').hidden = true;

      // Reset the selection to 'Sync everything'.
      $('sync-select-datatypes').selectedIndex = 0;

      // The default state is to sync everything.
      this.setCheckboxesToKeepEverythingSynced_(true);
      this.updatePasswordsCheckbox_();

      if (this.shouldNotEncrypt_)
        $('do-not-encrypt-option').checked = true;

      // Encrypt passwords is the default, but don't set it if the previously
      // synced account is already set to encrypt everything.
      if (!this.useEncryptEverything_ && !this.shouldNotEncrypt_)
        $('encrypt-sensitive-option').checked = true;

      // If the account is not synced with a custom passphrase, reset the
      // passphrase radio when switching to the 'Sync everything' page.
      // if (!this.usePassphrase_) {
      //   $('google-option').checked = true;
      //   $('sync-custom-passphrase').hidden = this.shouldNotEncrypt_;
      // }

      /*
      if (!this.useEncryptEverything_ && !this.usePassphrase_)
        $('basic-encryption-option').checked = true;
      */

      $('confirm-everything-ok').focus();
    },

    /**
     * Reveals the UI for entering a custom passphrase during initial setup.
     * This happens if the user has previously enabled a custom passphrase on a
     * different machine.
     * @param {Array} args The args that contain the passphrase UI
     *     configuration.
     * @private
     */
    showPassphraseContainer_: function(args) {
      // Once we require a passphrase, we prevent the user from returning to
      // the Sync Everything pane.
      $('use-default-link').hidden = true;
      $('sync-custom-passphrase-container').hidden = true;
      $('sync-existing-passphrase-container').hidden = false;

      // Hide the selection options within the new encryption section when
      // prompting for a passphrase.
      $('sync-new-encryption-section-container').hidden = true;

      $('normal-body').hidden = true;
      $('google-passphrase-needed-body').hidden = true;
      // Display the correct prompt to the user depending on what type of
      // passphrase is needed.
      if (args.usePassphrase)
        $('normal-body').hidden = false;
      else
        $('google-passphrase-needed-body').hidden = false;

      $('passphrase-learn-more').hidden = false;
      // Warn the user about their incorrect passphrase if we need a passphrase
      // and the passphrase field is non-empty (meaning they tried to set it
      // previously but failed).
      $('incorrect-passphrase').hidden =
          !(args.usePassphrase && args.passphraseFailed);

      $('sync-passphrase-warning').hidden = false;
      $('passphrase').focus();
    },

    /** @private */
    showCustomizePage_: function(args, syncEverything) {
      $('confirm-sync-preferences').hidden = true;
      $('customize-sync-preferences').hidden = false;

      $('sync-custom-passphrase-container').hidden = false;

      if (this.keystoreEncryptionEnabled_) {
        $('customize-sync-encryption').hidden = true;
        $('sync-new-encryption-section-container').hidden = false;
        $('customize-sync-encryption-new').hidden = false;
      } else {
        $('customize-sync-encryption').hidden = false;
        $('customize-sync-encryption-new').hidden = true;
      }

      $('sync-existing-passphrase-container').hidden = true;

      // If the user has selected the 'Customize' page on initial set up, it's
      // likely he intends to change the data types. Select the
      // 'Choose data types' option in this case.
      var index = syncEverything ? 0 : 1;
      $('sync-select-datatypes').selectedIndex = index;
      this.setDataTypeCheckboxesEnabled_(!syncEverything);

      // The passphrase input may need to take over focus from the OK button, so
      // set focus before that logic.
      $('choose-datatypes-ok').focus();

      if (args && args.showPassphrase) {
        this.showPassphraseContainer_(args);
      } else {
        // We only show the 'Use Default' link if we're not prompting for an
        // existing passphrase.
        var self = this;
        this.animateDisableLink_($('use-default-link'), false, function() {
          self.showSyncEverythingPage_();
        });
      }
    },

    /**
     * Shows the appropriate sync setup page.
     * @param {string} page A page of the sync setup to show.
     * @param {object} args Data from the C++ to forward on to the right
     *     section.
     */
    showSyncSetupPage_: function(page, args) {
      this.setThrobbersVisible_(false);

      // Hide an existing visible overlay (ensuring the close button is not
      // hidden).
      var children = document.querySelectorAll(
          '#sync-setup-overlay > *:not(.close-button)');
      for (var i = 0; i < children.length; i++)
        children[i].hidden = true;

      this.setInputElementsDisabledState_(false);
      this.updatePasswordsCheckbox_();

      // If new passphrase bodies are present, overwrite the existing ones.
      if (args && args.enterPassphraseBody != undefined)
        $('normal-body').innerHTML = args.enterPassphraseBody;

      if (args && args.fullEncryptionBody != undefined)
        $('full-encryption-body').innerHTML = args.fullEncryptionBody;

      // NOTE: Because both showGaiaLogin_() and showConfigure_() change the
      // focus, we need to ensure that the overlay container and dialog aren't
      // [hidden] (as trying to focus() nodes inside of a [hidden] DOM section
      // doesn't work).
      if (page == 'done')
        this.closeOverlay_();
      else
        this.showOverlay_();

      if (page == 'login')
        this.showGaiaLogin_(args);
      else if (page == 'configure' || page == 'passphrase')
        this.showConfigure_(args);
      else if (page == 'spinner')
        this.showSpinner_();
      else if (page == 'timeout')
        this.showTimeoutPage_();
    },

    /**
     * Changes the visibility of throbbers on this page.
     * @param {boolean} visible Whether or not to set all throbber nodes
     *     visible.
     */
    setThrobbersVisible_: function(visible) {
      var throbbers = document.getElementsByClassName('throbber');
      for (var i = 0; i < throbbers.length; i++)
        throbbers[i].style.visibility = visible ? 'visible' : 'hidden';
    },

    /**
     * Get the sign in button DOM element.
     * @return {DOMElement} The sign in button.
     * @private
     */
    getSignInButton_: function() {
      return $('sign-in');
    },

    /**
     * Reset the state of all descendant elements of a root element to their
     * initial state.
     * The initial state is specified by adding a class to the descendant
     * element in sync_setup_overlay.html.
     * @param {HTMLElement} pageElementId The root page element id.
     * @private
     */
    resetPage_: function(pageElementId) {
      var page = $(pageElementId);
      var forEach = function(arr, fn) {
        var length = arr.length;
        for (var i = 0; i < length; i++) {
          fn(arr[i]);
        }
      };

      forEach(page.getElementsByClassName('reset-hidden'),
          function(elt) { elt.hidden = true; });
      forEach(page.getElementsByClassName('reset-shown'),
          function(elt) { elt.hidden = false; });
      forEach(page.getElementsByClassName('reset-disabled'),
          function(elt) { elt.disabled = true; });
      forEach(page.getElementsByClassName('reset-enabled'),
          function(elt) { elt.disabled = false; });
      forEach(page.getElementsByClassName('reset-value'),
          function(elt) { elt.value = ''; });
      forEach(page.getElementsByClassName('reset-opaque'),
          function(elt) { elt.classList.remove('transparent'); });
    },

    showGaiaLogin_: function(args) {
      this.resetPage_('sync-setup-login');
      $('sync-setup-login').hidden = false;
      this.allowEmptyPassword_ = false;
      this.captchaChallengeActive_ = false;

      /*
      var f = $('gaia-login-form');
      var email = $('gaia-email');
      var passwd = $('gaia-passwd');
      if (f) {
        if (args.user != undefined) {
          if (email.value != args.user)
            passwd.value = ''; // Reset the password field
          email.value = args.user;
        }

        if (!args.editableUser) {
          $('email-row').hidden = true;
          var span = $('email-readonly');
          span.textContent = email.value;
          $('email-readonly-row').hidden = false;
          $('create-account-div').hidden = true;
        }

        f.accessCode.disabled = true;
        f.otp.disabled = true;
      }
      */

      if (1 == args.error) {
        // if (oldAccessCodeValue) {
        //   $('errormsg-0-access-code').hidden = false;
        //   this.showAccessCodeRequired_();
        // } else {
        //   $('errormsg-1-password').hidden = (args.errorMessage != undefined);
        // }
        this.setBlurbError_(args.errorMessage);
      } else if (3 == args.error) {
        $('errormsg-0-connection').hidden = false;
        this.setBlurbError_(args.errorMessage);
      } else if (4 == args.error) {
        // this.showCaptcha_(args);
      } else if (7 == args.error) {
        this.setBlurbError_(loadTimeData.getString('serviceUnavailableError'));
      } else if (8 == args.error) {
        // if (args.askForOtp) {
        //   this.showOtpRequired_();
        // } else {
        //   if (oldAccessCodeValue)
        //     $('errormsg-0-access-code').hidden = false;
        //   this.showAccessCodeRequired_();
        // }
      } else if (args.errorMessage) {
        this.setBlurbError_(args.errorMessage);
      }

      $('sign-in').disabled = false;
      $('sign-in').value = loadTimeData.getString('signin');
    },

    resetErrorVisibility_: function() {
      $('errormsg-0-email').hidden = true;
      $('errormsg-0-password').hidden = true;
      $('errormsg-1-password').hidden = true;
      $('errormsg-0-connection').hidden = true;
      // $('errormsg-0-access-code').hidden = true;
      // $('errormsg-0-otp').hidden = true;
    },

    setBlurbError_: function(errorMessage) {
      // if (this.captchaChallengeActive_)
      //   return;  // No blurb in captcha challenge mode.

      if (errorMessage) {
        $('error-signing-in').hidden = true;
        $('error-custom').hidden = false;
        $('error-custom').textContent = errorMessage;
      } else {
        $('error-signing-in').hidden = false;
        $('error-custom').hidden = true;
      }

      $('top-blurb-error').hidden = false;
      // $('gaia-email').disabled = false;
      // $('gaia-passwd').disabled = false;
    },

    matchesASPRegex_: function(toMatch) {
      var noSpaces = /[a-z]{16}/;
      var withSpaces = /([a-z]{4}\s){3}[a-z]{4}/;
      if (toMatch.match(noSpaces) || toMatch.match(withSpaces))
        return true;
      return false;
    },

    setErrorVisibility_: function() {
      this.resetErrorVisibility_();
      /*
      var f = $('gaia-login-form');
      var email = $('gaia-email');
      var passwd = $('gaia-passwd');
      if (!email.value) {
        $('errormsg-0-email').hidden = false;
        this.setBlurbError_();
        return false;
      }
      // Don't enforce password being non-blank when checking access code (it
      // will have been cleared when the page was displayed).
      if (!this.allowEmptyPassword_ && !passwd.value) {
        $('errormsg-0-password').hidden = false;
        this.setBlurbError_();
        return false;
      }

      if (!f.accessCode.disabled && !f.accessCode.value) {
        $('errormsg-0-access-code').hidden = false;
        return false;
      }

      if (f.accessCode.disabled && this.matchesASPRegex_(passwd.value) &&
          $('asp-warning-div').hidden) {
        $('asp-warning-div').hidden = false;
        $('gaia-passwd').value = '';
        return false;
      }

      if (!f.otp.disabled && !f.otp.value) {
        $('errormsg-0-otp').hidden = false;
        return false;
      }
      */

      return true;
    },

    sendCredentialsAndClose_: function(result) {
      this.setThrobbersVisible_(true);

      $('sign-in').disabled = true;
      chrome.send('SyncSetupSubmitAuth', [result]);
    },

    showSuccessAndClose_: function() {
      $('sign-in').value = loadTimeData.getString('loginSuccess');
      setTimeout(this.closeOverlay_, 1600);
    },

    showSuccessAndSettingUp_: function() {
      $('sign-in').value = loadTimeData.getString('settingUp');
      this.setThrobbersVisible_(true);
      $('top-blurb-error').hidden = true;
    },

    /**
     * Displays the stop syncing dialog.
     * @private
     */
    showStopSyncingUI_: function() {
      // Hide any visible children of the overlay.
      var overlay = $('sync-setup-overlay');
      for (var i = 0; i < overlay.children.length; i++)
        overlay.children[i].hidden = true;

      // Bypass OptionsPage.navigateToPage because it will call didShowPage
      // which will set its own visible page, based on the flow state.
      this.visible = true;

      $('sync-setup-stop-syncing').hidden = false;
      $('stop-syncing-cancel').focus();
    },

    /**
     * Steps into the appropriate Sync Setup error UI.
     * @private
     */
    showErrorUI_: function() {
      chrome.send('SyncSetupShowErrorUI');
    },

    /**
     * Determines the appropriate page to show in the Sync Setup UI based on
     * the state of the Sync backend.
     * @private
     */
    showSetupUI_: function() {
      chrome.send('SyncSetupShowSetupUI');
    },

    /**
     * Shows advanced configuration UI, skipping the login dialog.
     * @private
     */
    showSetupUIWithoutLogin_: function() {
      chrome.send('SyncSetupShowSetupUIWithoutLogin');
    },

    /**
     * Forces user to sign out of Chrome for Chrome OS.
     * @private
     */
    doSignOutOnAuthError_: function() {
      chrome.send('SyncSetupDoSignOutOnAuthError');
    },

    /**
     * Hides the outer elements of the login UI. This is used by the sync promo
     * to customize the look of the login box.
     */
    hideOuterLoginUI_: function() {
      $('sync-setup-overlay-title').hidden = true;
      $('sync-setup-cancel').hidden = true;
    },

    openSigninPage_: function(source) {
      if (!this.waitingForSigninPageResult_) {
          this.waitingForSigninPageResult_ = true;
          window.addEventListener('beforeunload',
              SyncSetupOverlay.openSigninInProgressDialog, false);
    }

      chrome.send('SyncSetupOpenSigninPage', [ source ]);
    },
  };

  // These methods are for general consumption.
  SyncSetupOverlay.showErrorUI = function() {
    SyncSetupOverlay.getInstance().showErrorUI_();
  };

  SyncSetupOverlay.showSetupUI = function() {
    SyncSetupOverlay.getInstance().showSetupUI_();
  };

  SyncSetupOverlay.showSetupUIWithoutLogin = function() {
    SyncSetupOverlay.getInstance().showSetupUIWithoutLogin_();
  };

  SyncSetupOverlay.doSignOutOnAuthError = function() {
    SyncSetupOverlay.getInstance().doSignOutOnAuthError_();
  };

  SyncSetupOverlay.showSyncSetupPage = function(page, args) {
    SyncSetupOverlay.getInstance().showSyncSetupPage_(page, args);
  };

  SyncSetupOverlay.showSuccessAndClose = function() {
    SyncSetupOverlay.getInstance().showSuccessAndClose_();
  };

  SyncSetupOverlay.showSuccessAndSettingUp = function() {
    SyncSetupOverlay.getInstance().showSuccessAndSettingUp_();
  };

  SyncSetupOverlay.showStopSyncingUI = function() {
    SyncSetupOverlay.getInstance().showStopSyncingUI_();
  };

  SyncSetupOverlay.openSigninPageFromStartSyncSettings = function() {
    SyncSetupOverlay.getInstance().openSigninPage_("settingsPage");
  };

  SyncSetupOverlay.openSigninInProgressDialog = function(ev) {
    return 'Closing this page will cancel the sign-in process.\n' +
           'The sign-in tab, BitPop opened for you before,' +
           ' will also be closed.\n\n' +
           'Do you really wish to close this tab?';
  };

  // Export
  return {
    SyncSetupOverlay: SyncSetupOverlay
  };
});
