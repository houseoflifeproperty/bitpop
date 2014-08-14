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

#ifndef CHROME_BROWSER_UI_VIEWS_FB_BUTTON_BUBBLE_H_
#define CHROME_BROWSER_UI_VIEWS_FB_BUTTON_BUBBLE_H_

#include "ui/views/bubble/bubble_delegate.h"
#include "ui/views/controls/link_listener.h"

class Browser;

class FbButtonBubble : public views::BubbleDelegateView {
 public:
  // |browser| is the opening browser and is NULL in unittests.
  static FbButtonBubble* ShowBubble(Browser* browser, views::View* anchor_view,
									views::BubbleDelegateView* other);
  virtual void OnWidgetActivationChanged(views::Widget* widget, bool active) OVERRIDE;

 protected:
  // views::BubbleDelegateView overrides:
  virtual void Init() OVERRIDE;

 private:
  FbButtonBubble(Browser* browser, views::View* anchor_view,
				 views::BubbleDelegateView* other);
  virtual ~FbButtonBubble();

  Browser* browser_;
  views::BubbleDelegateView* other_;

  DISALLOW_COPY_AND_ASSIGN(FbButtonBubble);
};

#endif  // CHROME_BROWSER_UI_VIEWS_FB_BUTTON_BUBBLE_H_
