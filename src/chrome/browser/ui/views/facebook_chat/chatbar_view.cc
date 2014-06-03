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

#include "chrome/browser/ui/views/facebook_chat/chatbar_view.h"

#include <algorithm>

#include "chrome/browser/facebook_chat/facebook_chat_item.h"
#include "chrome/browser/themes/theme_service.h"
#include "chrome/browser/ui/browser.h"
#include "chrome/browser/ui/fullscreen/fullscreen_controller.h"
#include "chrome/browser/ui/view_ids.h"
#include "chrome/browser/ui/views/facebook_chat/chat_item_view.h"
#include "chrome/browser/ui/views/frame/browser_view.h"
#include "grit/generated_resources.h"
#include "grit/theme_resources.h"
#include "grit/ui_resources.h"
#include "ui/base/animation/slide_animation.h"
#include "ui/base/l10n/l10n_util.h"
#include "ui/base/resource/resource_bundle.h"
#include "ui/gfx/canvas.h"
#include "ui/views/controls/button/image_button.h"

namespace {

// Max number of chat buttons we'll contain. Any time a view is added and
// we already have this many chat item views, one is removed.
static const size_t kMaxChatItemViews = 15;

// Padding from left edge and first chat item view.
static const int kLeftPadding = 2;

// Padding from right edge and close button link.
static const int kRightPadding = 10;

// Padding between the chat item views.
static const int kChatItemPadding = 10;

// Padding between the top/bottom and the content.
static const int kTopBottomPadding = 4;

static const SkColor kBorderColor = SkColorSetRGB(214, 214, 214);

// Bar show/hide speed.
static const int kBarAnimationDurationMs = 120;

static const int kAddAnimationDuration = 600;
static const int kRemoveAnimationDuration = 600;
static const int kPlaceFirstAnimationDuration = 600;

// Sets size->width() to view's preferred width + size->width().s
// Sets size->height() to the max of the view's preferred height and
// size->height();
void AdjustSize(views::View* view, gfx::Size* size) {
  gfx::Size view_preferred = view->GetPreferredSize();
  size->Enlarge(view_preferred.width(), 0);
  size->set_height(std::max(view_preferred.height(), size->height()));
}

int CenterPosition(int size, int target_size) {
  return std::max((target_size - size) / 2, kTopBottomPadding);
}

}  // namespace

ChatbarView::ChatbarView(Browser* browser, BrowserView* parent)
  : browser_(browser),
    parent_(parent),
    item_to_add_(NULL),
    item_to_remove_(NULL),
    item_to_place_first_(NULL) {
  set_id(VIEW_ID_FACEBOOK_CHATBAR);
  SetVisible(false);
  
  parent->AddChildView(this);

  ResourceBundle &rb = ui::ResourceBundle::GetSharedInstance();

  close_button_ = new views::ImageButton(this);
  close_button_->SetImage(views::CustomButton::STATE_NORMAL,
                          rb.GetImageSkiaNamed(IDR_CLOSE_BAR));
  close_button_->SetImage(views::CustomButton::STATE_HOVERED,
                          rb.GetImageSkiaNamed(IDR_CLOSE_BAR_H));
  close_button_->SetImage(views::CustomButton::STATE_PRESSED,
                          rb.GetImageSkiaNamed(IDR_CLOSE_BAR_P));
  close_button_->SetAccessibleName(
      l10n_util::GetStringUTF16(IDS_ACCNAME_CLOSE));
  UpdateButtonColors();
  AddChildView(close_button_);

  bar_animation_.reset(new ui::SlideAnimation(this));
  bar_animation_->SetSlideDuration(kBarAnimationDurationMs);

  new_item_animation_.reset(new ui::SlideAnimation(this));
  new_item_animation_->SetSlideDuration(kAddAnimationDuration);

  remove_item_animation_.reset(new ui::SlideAnimation(this));
  remove_item_animation_->SetSlideDuration(kRemoveAnimationDuration);

  place_first_animation_.reset(new ui::SlideAnimation(this));
  place_first_animation_->SetSlideDuration(kPlaceFirstAnimationDuration);
}

ChatbarView::~ChatbarView() {
  parent_->RemoveChildView(this);
}

gfx::Size ChatbarView::GetPreferredSize() {
  gfx::Size prefsize(kRightPadding + kLeftPadding, 0);
  AdjustSize(close_button_, &prefsize);

  // Add one chat item to the preferred size.
  if (!chat_items_.empty()) {
    AdjustSize(*chat_items_.begin(), &prefsize);
    prefsize.Enlarge(kChatItemPadding, 0);
  }
  prefsize.Enlarge(0, kTopBottomPadding + kTopBottomPadding);
  if (bar_animation_->is_animating()) {
    prefsize.set_height(static_cast<int>(
        static_cast<double>(prefsize.height()) *
                            bar_animation_->GetCurrentValue()));
  }
  return prefsize;
}

void ChatbarView::Layout() {
  // Now that we know we have a parent, we can safely set our theme colors.
  set_background(views::Background::CreateSolidBackground(
      GetThemeProvider()->GetColor(ThemeService::COLOR_TOOLBAR)));

  // Let our base class layout our child views
  views::View::Layout();

  gfx::Size close_button_size = close_button_->GetPreferredSize();
  // If the window is maximized, we want to expand the hitbox of the close
  // button to the right and bottom to make it easier to click.
  bool is_maximized = browser_->window()->IsMaximized();
  const int rightSideX = width() - kRightPadding - close_button_size.width();
  int next_x = rightSideX;
  int y = CenterPosition(close_button_size.height(), height());
  close_button_->SetBounds(next_x, y,
      is_maximized ? width() - next_x : close_button_size.width(),
      is_maximized ? height() - y : close_button_size.height());

  if (!chat_items_.empty()) {
    bool isBeforeCertainItem = true;
    for (std::list<ChatItemView*>::iterator it = chat_items_.begin(); it != chat_items_.end(); it++) {
      gfx::Size itemSize = (*it)->GetPreferredSize();
      next_x -= kChatItemPadding + itemSize.width();

      // handle adding a chat item
      if (new_item_animation_.get() && new_item_animation_->is_animating()) {
        if (*it == item_to_add_) {
          next_x += (1.0 - new_item_animation_->GetCurrentValue()) * (kChatItemPadding + itemSize.width());
          itemSize.set_width(new_item_animation_->GetCurrentValue() * itemSize.width());
        }
      }

      // handle removing a chat item
      if (remove_item_animation_.get() && remove_item_animation_->is_animating()) {
        double newWidth = (1.0 - remove_item_animation_->GetCurrentValue()) * itemSize.width();
        double oldWidth = itemSize.width();
        if (*it == item_to_remove_) {
          //isBeforeCertainItem = false;
          next_x += oldWidth - newWidth;
          itemSize.set_width(newWidth);
        }
        //if (!isBeforeCertainItem)
      }

      int x = -10000;

      // handle placing chat item first in order
      if (place_first_animation_.get() && place_first_animation_->is_animating()) {
        if (*it == item_to_place_first_) {
          isBeforeCertainItem = false;
          next_x += place_first_animation_->GetCurrentValue() * (kChatItemPadding + itemSize.width());
          x = next_x + place_first_animation_->GetCurrentValue() * (rightSideX - (kChatItemPadding + itemSize.width()) - next_x);
        }
        if (isBeforeCertainItem) {
          isBeforeCertainItem = false;
          next_x -= place_first_animation_->GetCurrentValue() * (kChatItemPadding + itemSize.width());
        }
      }

      y = CenterPosition(itemSize.height(), height());
      (*it)->SetBounds((x != -10000) ? x : next_x, y, itemSize.width(), itemSize.height());

      if (next_x < 10)
        (*it)->SetVisible(false);
      else
        (*it)->SetVisible(true);

      (*it)->Layout();
    }
  }
}

void ChatbarView::OnPaintBorder(gfx::Canvas* canvas) {
  canvas->DrawLine(gfx::Point(0, 0), gfx::Point(width(), 0), kBorderColor);
}

void ChatbarView::AddChatItem(FacebookChatItem *chat_item) {
  if (browser_->fullscreen_controller()->IsFullscreenForTabOrPending()) {
    browser_->fullscreen_controller()->SetOpenChatbarOnNextFullscreenEvent();
  } else if (!this->visible())
    Show();

  // do not allow duplicate chat items
  for (std::list<ChatItemView*>::iterator it = chat_items_.begin(); it != chat_items_.end(); it++) {
    if ((*it)->GetModel()->jid() == chat_item->jid()) {
      if (chat_item->needs_activation()) {
        if (!(*it)->visible())
          PlaceFirstInOrder(*it);
        (*it)->ActivateChat();
      }
      return;
    }
  }

  ChatItemView *item = new ChatItemView(chat_item, this);
  chat_items_.push_front(item);
  AddChildView(item);

  StopPendingAnimations();
  item_to_add_ = item;
  new_item_animation_->Show();

  Layout();

  if (chat_item->needs_activation())
    item->ActivateChat();
  else if (chat_item->num_notifications() > 0)
    item->NotifyUnread();
}

void ChatbarView::RemoveAll() {
  while (chat_items_.size() > 0)
    chat_items_.back()->Close(false);
  Hide();
}

void ChatbarView::Show() {
  this->SetVisible(true);
  bar_animation_->Show();
}

void ChatbarView::Hide() {
  bar_animation_->Hide();
}

Browser *ChatbarView::browser() const {
  return browser_;
}

bool ChatbarView::IsShowing() const {
  return bar_animation_->IsShowing();
}

bool ChatbarView::IsClosing() const {
  return bar_animation_->IsClosing();
}

void ChatbarView::Remove(ChatItemView *item, bool should_animate) {
  if (should_animate) {
    std::list<ChatItemView*>::iterator it = std::find(chat_items_.begin(), chat_items_.end(), item);
    if (it != chat_items_.end()) {
      StopPendingAnimations();
      item_to_remove_ = item;
      remove_item_animation_->Show();
    }
  } else
    RemoveItem(item);
}

void ChatbarView::AnimationProgressed(const ui::Animation *animation) {
  if (animation == bar_animation_.get()) {
    // Force a re-layout of the parent, which will call back into
    // GetPreferredSize, where we will do our animation. In the case where the
    // animation is hiding, we do a full resize - the fast resizing would
    // otherwise leave blank white areas where the shelf was and where the
    // user's eye is. Thankfully bottom-resizing is a lot faster than
    // top-resizing.
    Layout();
    parent_->ToolbarSizeChanged(bar_animation_->IsShowing());
  } else if (animation == new_item_animation_.get() || animation == remove_item_animation_.get() ||
             animation == place_first_animation_.get()) {
    Layout();
    SchedulePaint();
  }
}

void ChatbarView::AnimationEnded(const ui::Animation *animation) {
  if (animation == bar_animation_.get()) {
    parent_->SetChatbarVisible(bar_animation_->IsShowing());
    if (!bar_animation_->IsShowing())
      Closed();
  } else if (animation == new_item_animation_.get()) {
    item_to_add_ = NULL;
    new_item_animation_->Reset();
  } else if (animation == remove_item_animation_.get()) {
    DCHECK(item_to_remove_);
    RemoveItem(item_to_remove_);
    item_to_remove_ = NULL;
    remove_item_animation_->Reset();
  } else if (animation == place_first_animation_.get()) {
    DCHECK(item_to_place_first_);
    std::list<ChatItemView*>::iterator it = std::find(chat_items_.begin(), chat_items_.end(), item_to_place_first_);
    if (it != chat_items_.end()) {
      chat_items_.erase(it);
      chat_items_.push_front(item_to_place_first_);
      item_to_place_first_ = NULL;
      Layout();
      SchedulePaint();
    }
    place_first_animation_->Reset();
  }
}

void ChatbarView::ButtonPressed(views::Button* button, const ui::Event& event) {
  Hide();
}

void ChatbarView::Closed() {
  //parent_->RemoveChildView(this);
  //this->SetVisible(false);
}

void ChatbarView::UpdateButtonColors() {
  ResourceBundle& rb = ResourceBundle::GetSharedInstance();
  if (GetThemeProvider()) {
    close_button_->SetBackground(
        GetThemeProvider()->GetColor(ThemeService::COLOR_TAB_TEXT),
        rb.GetImageSkiaNamed(IDR_CLOSE_BAR),
        rb.GetImageSkiaNamed(IDR_CLOSE_BAR_MASK));
  }
}

void ChatbarView::StopPendingAnimations() {
  if (remove_item_animation_.get() && remove_item_animation_->IsShowing())
    remove_item_animation_->Reset();

  if (place_first_animation_.get() && place_first_animation_->IsShowing())
    place_first_animation_->Reset();

  if (new_item_animation_.get() && new_item_animation_->IsShowing())
    new_item_animation_->Reset();
}

void ChatbarView::RemoveItem(ChatItemView* item) {
  std::list<ChatItemView*>::iterator it = std::find(chat_items_.begin(), chat_items_.end(), item);
  if (it != chat_items_.end()) {
    RemoveChildView(item);
    chat_items_.erase(it);
    delete item;
    Layout();
    SchedulePaint();
  }
  if (chat_items_.empty())
    Hide();
}

void ChatbarView::PlaceFirstInOrder(ChatItemView* item) {
  gfx::Rect itemBounds = item->bounds();
  if (!item->visible()) {  // chat item is invisible - move it to first position
    StopPendingAnimations();
    item_to_place_first_ = item;
    place_first_animation_->Show();
  }
}
