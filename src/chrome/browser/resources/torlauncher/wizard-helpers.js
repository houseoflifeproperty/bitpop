// BitPop browser. Tor launcher integration part.
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

var torlauncher = torlauncher || {};

torlauncher.UIHelper = function () {
  var wizards = document.getElementsByClassName('wizard');
  console.assert(wizards.length == 1);
  this.wizardElem_ = wizards[0];
  this.initWizardUI();

  this.pagesStack_ = [];
};


torlauncher.UIHelper.prototype = {
  initWizardUI: function() {
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
          }
        }
      }
    }
  },

  get WizardElem() {
    return this.wizardElem_;
  },

  goTo: function (pageId, details) {
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

  get canAdvance() {
    if (this.openedPage_) {
      return (this.openedPage_.getAttribute('next') != 'notUsed');
    }
    return false;
  },

  advance: function () {
    if (this.canAdvance) {
      this.pagesStack_.push(this.openedPage_.getAttribute('pageid'));
      this.goTo(this.openedPage_.getAttribute('next'),
                { from_wizard_method: true });
    }
  },

  get canRewind() {
    return this.pagesStack_.length > 0;
  },

  rewind: function() {
    if (this.canRewind) {
      var lastPage = this.pagesStack_.pop();
      this.goTo(lastPage,
                { from_wizard_method: true });
    }
  }
};
