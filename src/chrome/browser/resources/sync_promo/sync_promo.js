// Copyright (c) 2012 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// TODO(sail): Refactor options_page and remove this include.
<include src="../options/options_page.js"/>
<include src="../shared/js/util.js"/>
<include src="../sync_setup_overlay.js"/>

cr.define('sync_promo', function() {
  /**
   * SyncPromo class
   * Subclass of options.SyncSetupOverlay that customizes the sync setup
   * overlay for use in the new tab page.
   * @class
   */
  function SyncPromo() {
    options.SyncSetupOverlay.call(this, 'syncSetup',
        loadTimeData.getString('syncSetupOverlayTabTitle'),
        'sync-setup-overlay');
  }

  // Replicating enum from chrome/common/extensions/extension_constants.h.
  /** @const */ var actions = (function() {
    var i = 0;
    return {
      VIEWED: i++,
      LEARN_MORE_CLICKED: i++,
      ACCOUNT_HELP_CLICKED: i++,
      CREATE_ACCOUNT_CLICKED: i++,
      SKIP_CLICKED: i++,
      SIGN_IN_ATTEMPTED: i++,
      SIGNED_IN_SUCCESSFULLY: i++,
      ADVANCED_CLICKED: i++,
      ENCRYPTION_HELP_CLICKED: i++,
      CANCELLED_AFTER_SIGN_IN: i++,
      CONFIRMED_AFTER_SIGN_IN: i++,
      CLOSED_TAB: i++,
      CLOSED_WINDOW: i++,
      LEFT_DURING_THROBBER: i++,
    };
  }());

  cr.addSingletonGetter(SyncPromo);

  SyncPromo.prototype = {
    __proto__: options.SyncSetupOverlay.prototype,

    showOverlay_: function() {
      $('sync-setup-overlay').hidden = false;
    },

    closeOverlay_: function() {
      chrome.send('SyncPromo:Close');
    },

    // Initializes the page.
    initializePage: function() {
      options.SyncSetupOverlay.prototype.initializePage.call(this);

      // Cancel: // Hide parts of the login UI and show the promo UI.
      this.hideOuterLoginUI_();
      // $('promo-skip').hidden = false;

      chrome.send('SyncPromo:Initialize');

      var self = this;

      $('promo-skip-button').addEventListener('click', function() {
        chrome.send('SyncPromo:UserSkipped');
        self.closeOverlay_();
      });

      var learnMoreClickedAlready = false;
      $('promo-learn-more').addEventListener('click', function() {
        if (!learnMoreClickedAlready)
          chrome.send('SyncPromo:UserFlowAction', [actions.LEARN_MORE_CLICKED]);
        learnMoreClickedAlready = true;
      });

      $('promo-advanced').addEventListener('click', function() {
        chrome.send('SyncPromo:ShowAdvancedSettings');
      });

      // We listen to the <form>'s submit vs. the <input type="submit"> click so
      // we also track users that use the keyboard and press enter.
      var signInAttemptedAlready = false;

      // The
      var argsDict = SyncPromo.getPageArgumentsDictionary();

      document.getElementsByClassName('sync_setup_wrap')[0].style.display =
          'table';
      var strArgs = JSON.stringify(argsDict);
      if (argsDict.token && argsDict.type && argsDict.email)
        this.sendCredentialsAndClose_(strArgs);
      else if (argsDict.message) {
        chrome.send('SyncPromo:InitializeError', [ strArgs ]);
      } else {
        chrome.send('SyncPromo:InitializeError',
                    [ JSON.stringify({"message": "Invalid page arguments"}) ]);
      }

      ++self.signInAttempts_;
      if (!signInAttemptedAlready)
         chrome.send('SyncPromo:UserFlowAction', [actions.SIGN_IN_ATTEMPTED]);
      signInAttemptedAlready = true;

      var encryptionHelpClickedAlready = false;
      $('encryption-help-link').addEventListener('click', function() {
        if (!encryptionHelpClickedAlready)
          chrome.send('SyncPromo:UserFlowAction',
                      [actions.ENCRYPTION_HELP_CLICKED]);
        encryptionHelpClickedAlready = true;
      });

      var advancedOptionsClickedAlready = false;
      $('customize-link').addEventListener('click', function() {
        if (!advancedOptionsClickedAlready)
          chrome.send('SyncPromo:UserFlowAction', [actions.ADVANCED_CLICKED]);
        advancedOptionsClickedAlready = true;
      });

      // Re-used across both cancel buttons after a successful sign in.
      var cancelFunc = function() {
        chrome.send('SyncPromo:UserFlowAction',
                    [actions.CANCELLED_AFTER_SIGN_IN]);
      };
      $('confirm-everything-cancel').addEventListener('click', cancelFunc);
      $('choose-datatypes-cancel').addEventListener('click', cancelFunc);

      // Add the source parameter to the document so that it can be used to
      // selectively show and hide elements using CSS.
      var params = parseQueryParams(document.location);
      if (params.source == '0')
        document.documentElement.setAttribute('isstartup', '');
    },

    /**
     * Called when the page is unloading.
     * @private
     */
    onUnload: function() {
      // Record number of times a user tried to sign in and if they left
      // while a throbber was running.
      chrome.send('SyncPromo:RecordSignInAttempts', [this.signInAttempts_]);
      if (this.throbberStart_)
        chrome.send('SyncPromo:UserFlowAction', [actions.LEFT_DURING_THROBBER]);
      chrome.send('SyncSetupDidClosePage');
    },

    /** @override */
    sendConfiguration_: function() {
      chrome.send('SyncPromo:UserFlowAction',
                  [actions.CONFIRMED_AFTER_SIGN_IN]);
      options.SyncSetupOverlay.prototype.sendConfiguration_.apply(this,
          arguments);
    },

    /** @override */
    setThrobbersVisible_: function(visible) {
      if (visible) {
        this.throbberStart_ = Date.now();
      } else {
        if (this.throbberStart_) {
          chrome.send('SyncPromo:RecordThrobberTime',
                      [Date.now() - this.throbberStart_]);
        }
        this.throbberStart_ = 0;
      }
      // Pass through to SyncSetupOverlay to handle display logic.
      options.SyncSetupOverlay.prototype.setThrobbersVisible_.apply(
          this, arguments);
    },

    /**
     * Number of times a user attempted to sign in to GAIA during this page
     * view.
     * @private
     */
    signInAttempts_: 0,

    /**
     * The start time of a throbber on the page.
     * @private
     */
    throbberStart_: 0,
  };

  SyncPromo.showErrorUI = function() {
    SyncPromo.getInstance().showErrorUI_();
  };

  SyncPromo.showSyncSetupPage = function(page, args) {
    SyncPromo.getInstance().showSyncSetupPage_(page, args);
  };

  SyncPromo.showSuccessAndClose = function() {
    SyncPromo.getInstance().showSuccessAndClose_();
  };

  SyncPromo.showSuccessAndSettingUp = function() {
    chrome.send('SyncPromo:UserFlowAction', [actions.SIGNED_IN_SUCCESSFULLY]);
    SyncPromo.getInstance().showSuccessAndSettingUp_();
  };

  SyncPromo.showStopSyncingUI = function() {
    SyncPromo.getInstance().showStopSyncingUI_();
  };

  SyncPromo.initialize = function() {
    SyncPromo.getInstance().initializePage();
  };

  SyncPromo.onUnload = function() {
    SyncPromo.getInstance().onUnload();
  };

  SyncPromo.populatePromoMessage = function(resName) {
    SyncPromo.getInstance().populatePromoMessage_(resName);
  };

  SyncPromo.getPageArgumentsDictionary = function() {
    var allowedArgs = [ 'state', 'token', 'type', 'email', 'backend', 'message', 'fb_login' ];
    var args = parseQueryParams(document.location);
    for (var arg in args) {
      if (args.hasOwnProperty(arg) && allowedArgs.indexOf(arg) == -1) {
        delete args[arg];
      }
    }
    return args;
  };

  // Export
  return {
    SyncPromo: SyncPromo
  };
});

var OptionsPage = options.OptionsPage;
var SyncSetupOverlay = sync_promo.SyncPromo;
(function() {
  var argsDict = SyncSetupOverlay.getPageArgumentsDictionary();

  if (argsDict.token || argsDict.message) {
    window.addEventListener('DOMContentLoaded',
                            sync_promo.SyncPromo.initialize);
    window.addEventListener('unload',
       sync_promo.SyncPromo.onUnload.bind(sync_promo.SyncPromo));
  } else if (argsDict.state) {
    window.addEventListener('DOMContentLoaded',
      function() {
        $('facebooklogin').href += argsDict.state;
        $('bitpoplogin').href += argsDict.state;
      });
  } else {
    var state = "2";
    var chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    var numChars = 32;
    for (var i = 0; i < numChars-1; i++) {
      state += chars[Math.round(Math.random() * (chars.length - 1))];
    }
    localStorage.setItem('state', state);

    chrome.send('SyncPromo:StateSet', [ state ]);

    if (argsDict.fb_login) {
      document.location.href = 'https://sync.bitpop.com/login/facebook/' + state;
    }

    window.addEventListener('DOMContentLoaded',
      function() {
        $('facebooklogin').href += state;
        $('bitpoplogin').href += state;
      });
  }
})();
