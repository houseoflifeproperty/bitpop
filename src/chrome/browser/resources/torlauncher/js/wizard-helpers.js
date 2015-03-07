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

var torlauncher = torlauncher || {};

torlauncher.UIHelper = function (firstPageShowCallback) {
  var wizards = document.getElementsByClassName('wizard');
  console.assert(wizards.length == 1);
  this.wizardElem_ = wizards[0];
  this.lastPage_ = null;
  this.callbacks = {};
  if (firstPageShowCallback)
    this.setPageShowCallback($('.wizardpage')[0].getAttribute('pageid'),
                             firstPageShowCallback);
  this._initWizardUI();

  this.pagesStack_ = [];

  var _this = this;
  document.getElementById('nextButton').addEventListener(
      'click', function (ev) {
        torlauncher.util.runGenerator(_this.advance.bind(_this));
      }, false);
  document.getElementById('backButton').addEventListener(
      'click', function (ev) {
        torlauncher.util.runGenerator(_this.rewind.bind(_this));
      }, false);
};


torlauncher.UIHelper.prototype = {
  // @private:
  _initWizardUI: function() {
    if (this.wizardElem_.children.length) {
      var children = this.wizardElem_.children;
      var isFirstPage = true;
      for (var i = 0; i < children.length; i++) {
        if (children[i].classList.contains('wizardpage')) {
          if (!isFirstPage) {
            children[i].setAttribute('aria-hidden', 'true');
            children[i].setAttribute('style', 'display:none');
          } else {
            isFirstPage = false;
            this.openedPage_ = children[i];
            var onShowCallback =
                this.callbacks[this.currentPage.pageid].onShow || null;
            if (onShowCallback &&
                torlauncher.util.isGeneratorFunction(onShowCallback))
              // call the onshow callback for the first opened page
              torlauncher.util.runGenerator(onShowCallback);
            this._setNextPointer();
          }
        }
      }
    }
  },

  // @private:
  _setNextPointer: function () {
    var next = this.openedPage_.getAttribute('next');
    if (!this.openedPage_.next)
      this.openedPage_.next = (next != 'notUsed') ? next : null;
  },

  get WizardElem() {
    return this.wizardElem_;
  },

  goTo: function *(pageId, details) {
    var gotoPage = this.WizardElem.querySelector('.wizardpage[pageid="' +
        pageId + '"]');
    if (!gotoPage)
      return false;

    if (gotoPage != this.openedPage_) {
      gotoPage.removeAttribute('aria-hidden');
      gotoPage.removeAttribute('style');
      if (this.openedPage_) {

        if ((!details || details.from_wizard_method !== true)) {
          this.pagesStack_.push(this.openedPage_.getAttribute('pageid'));
        }

        this.openedPage_.setAttribute('aria-hidden', 'true');
        this.openedPage_.setAttribute('style', 'display:none');
      }
      this.openedPage_ = gotoPage;

      var onShowCallback =
          this.callbacks[this.currentPage.pageid].onShow || null;
      if (onShowCallback &&
          torlauncher.util.isGeneratorFunction(onShowCallback))
        yield *onShowCallback();
      // TODO: check the needed order of execution for _setNextPointer
      this._setNextPointer();
    }

    return true;
  },

  get currentPage() {
    if (this.openedPage_) {
      return { pageid: this.openedPage_.getAttribute('pageid'),
                 elem: this.openedPage_ };
    }
    return null;
  },

  canAdvance: function *() {
    if (this.openedPage_) {
      var lastOpenedPage = this.currentPage;
      var onPageAdvanced =
          this.callbacks[lastOpenedPage.pageid].onAdvanced || null;
      return ((this.openedPage_.next !== null) &&
          // if callback is not present we cannot advance
          // we cannot advance also if callback returns false
          (!onPageAdvanced ||
           !torlauncher.util.isGeneratorFunction(onPageAdvanced) ||
            (yield *onPageAdvanced(this.openedPage_))
          ));
    }
    return false;
  },

  canRewind: function *() {
    return this.pagesStack_.length > 0;
  },

  get lastPage() {
    return this.lastPage_;
  },

  set lastPage(pageid) {
    this.lastPage_ = pageid;
    this._updateAcceptState();
  },

  // @@private:
  _updateAcceptState: function () {
    if (this.lastPage_ == this.currentPage.pageid) {
      $('#nextButton').hide(0);
      $('#acceptButton').show(0);
    } else if ($('#acceptButton').is(':visible')) {
      $('#nextButton').show(0);
      $('#acceptButton').hide(0);
    }
  },

  advance: function *(aPage) {
    var protector = 0;
    do {
      var nextPage = null;
      if (yield *this.canAdvance()) {
        if (this.openedPage_.next) {
          nextPage = this.openedPage_.next;
          if (!aPage)
            aPage = nextPage;
        }
        this.pagesStack_.push(this.openedPage_.getAttribute('pageid'));
        yield *this.goTo( aPage,
                         { from_wizard_method: true });
        this._updateAcceptState();
      }
    } while (aPage && aPage != this.currentPage.pageid && ++protector < 100);
    if (protector == 100)
      console.error('WizardHelper.advance: Runtime error: infinite loop.');
  },

  rewind: function *(page) {
    var protector = 0;
    do {
      if (this.canRewind()) {
        var lastPage = this.pagesStack_.pop();
        yield *this.goTo(lastPage,
                        { from_wizard_method: true });
        this._updateAcceptState();
      }
    } while (page && page != this.currentPage.pageid && ++protector < 100);
    if (protector == 100)
      console.error('WizardHelper.rewind: Runtime error: infinite loop.');
  },

  setPageShowCallback: function (pageid, callback) {
    if (!this.callbacks[pageid])
      this.callbacks[pageid] = {};
    this.callbacks[pageid].onShow = callback;
  },

  setPageAdvancedCallback: function (pageid, callback) {
    if (!this.callbacks[pageid])
      this.callbacks[pageid] = {};
    this.callbacks[pageid].onAdvanced = callback;
  }
};
