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

#include "chrome/browser/ui/views/fb_button_bubble.h"

#include "chrome/browser/first_run/first_run.h"
#include "chrome/browser/search_engines/util.h"
#include "chrome/browser/ui/browser.h"
#include "chrome/browser/ui/chrome_pages.h"
#include "grit/generated_resources.h"
#include "ui/base/l10n/l10n_util.h"
#include "ui/base/resource/resource_bundle.h"
#include "ui/views/controls/label.h"
#include "ui/views/controls/link.h"
#include "ui/views/layout/grid_layout.h"
#include "ui/views/layout/layout_constants.h"
#include "ui/views/widget/widget.h"

namespace {
const int kAnchorVerticalInset = 5;
const int kTopInset = 1;
const int kLeftInset = 2;
const int kBottomInset = 7;
const int kRightInset = 2;
}  // namespace

// static
FbButtonBubble* FbButtonBubble::ShowBubble(Browser* browser,
                                           views::View* anchor_view,
										   views::BubbleDelegateView* other) {
  FbButtonBubble* delegate = new FbButtonBubble(browser, anchor_view, other);
  delegate->set_arrow(views::BubbleBorder::TOP_RIGHT);
  views::BubbleDelegateView::CreateBubble(delegate);
  return delegate;
}

void FbButtonBubble::Init() {
  ui::ResourceBundle& rb = ui::ResourceBundle::GetSharedInstance();
  const gfx::Font& original_font = rb.GetFont(ui::ResourceBundle::MediumFont);

  views::Label* title = new views::Label(
      l10n_util::GetStringUTF16(IDS_FBB_BUBBLE_TITLE));
  title->SetFontList(gfx::FontList(original_font.Derive(2, gfx::Font::BOLD)));

  views::Label* subtext =
      new views::Label(l10n_util::GetStringUTF16(IDS_FBB_BUBBLE_SUBTEXT));
  subtext->SetFontList(gfx::FontList(original_font));
  subtext->SetHorizontalAlignment(gfx::ALIGN_LEFT);
  subtext->SetMultiLine(true);

  views::GridLayout* layout = views::GridLayout::CreatePanel(this);
  SetLayoutManager(layout);
  layout->SetInsets(kTopInset, kLeftInset, kBottomInset, kRightInset);

  views::ColumnSet* columns = layout->AddColumnSet(0);
  columns->AddColumn(views::GridLayout::LEADING, views::GridLayout::LEADING, 0,
                     views::GridLayout::FIXED, 350, 0);

  layout->StartRow(0, 0);
  layout->AddView(title);
  layout->StartRowWithPadding(0, 0, 0,
      views::kRelatedControlSmallVerticalSpacing);
  layout->AddView(subtext);
}

FbButtonBubble::FbButtonBubble(Browser* browser, views::View* anchor_view,
							   views::BubbleDelegateView* other)
    : views::BubbleDelegateView(anchor_view, views::BubbleBorder::TOP_LEFT),
      browser_(browser),
	  other_(other) {
  // Compensate for built-in vertical padding in the anchor view's image.
  set_anchor_view_insets(
      gfx::Insets(kAnchorVerticalInset, 0, kAnchorVerticalInset, 0));
}

FbButtonBubble::~FbButtonBubble() {
}

void FbButtonBubble::OnWidgetActivationChanged(views::Widget* widget, bool active) {
  if (close_on_deactivate() && widget == GetWidget() && !active) {
    GetWidget()->Close();
	if (other_)
	  other_->GetWidget()->Close();
  }
}