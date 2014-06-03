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

#include "chrome/browser/ui/views/facebook_chat/chat_notification_popup.h"

#include "base/utf_string_conversions.h"
#include "base/win/win_util.h"
#include "grit/generated_resources.h"
#include "grit/theme_resources.h"
#include "grit/theme_resources.h"
#include "grit/ui_resources.h"
#include "ui/base/animation/slide_animation.h"
#include "ui/base/resource/resource_bundle.h"
#include "ui/views/controls/button/image_button.h"
#include "ui/views/layout/fill_layout.h"
#include "ui/views/widget/widget.h"

//#include "grit/theme_resources.h"
//#include "ui/base/resource/resource_bundle.h"

using views::View;

namespace {
  static const int kMaxNotifications = 20;

  static const int kNotificationLabelWidth = 180;

  static const int kNotificationLabelMaxHeight = 600;

  static const int kLabelPaddingRight = 18;

  static const SkColor kNotificationPopupBackgroundColor = SkColorSetRGB(0xc2, 0xec, 0xfc);

  static const int kNotificationBubbleAlpha = 200;
}

class NotificationPopupContent : public views::Label {
public:
  NotificationPopupContent(ChatNotificationPopup *owner)
    : views::Label(),
      owner_(owner) {
    SetMultiLine(true);
    SetAllowCharacterBreak(true);
    SetHorizontalAlignment(gfx::ALIGN_LEFT);
    //SkColor labelBgr = SkColorSetA(kNotificationPopupBackgroundColor, 0);
    SetAutoColorReadabilityEnabled(false);
    SetBackgroundColor(kNotificationPopupBackgroundColor);
    SetEnabledColor(SkColorSetRGB(0,0,0));
  }

  virtual gfx::Size GetPreferredSize() {
    int height = GetHeightForWidth(kNotificationLabelWidth);
    if (height > kNotificationLabelMaxHeight) {
      height = kNotificationLabelMaxHeight;
    }
    gfx::Size prefsize(kNotificationLabelWidth, height);
    gfx::Insets insets = GetInsets();
    prefsize.Enlarge(insets.width(), insets.height());
    return prefsize;
  }

  void UpdateOwnText() {
    const ChatNotificationPopup::MessageContainer& msgs = owner_->GetMessages();
    std::string concat = "";
    int i = 0;
    for (ChatNotificationPopup::MessageContainer::const_iterator it = msgs.begin(); it != msgs.end(); it++, i++) {
      concat += *it;
      if (i != (int)msgs.size() - 1)
        concat += "\n\n";
    }
    //SetText(L"");
    //owner_->SizeToContents();  // dirty hack to force the window redraw
    SetText(UTF8ToWide(concat));
    owner_->SetAlignment(views::BubbleBorder::ALIGN_ARROW_TO_MID_ANCHOR);  // for the call to SizeToContents() to be made
  }

private:
  ChatNotificationPopup* owner_;
};


class NotificationContainerView : public View {
public:
  NotificationContainerView(ChatNotificationPopup *owner)
    : owner_(owner),
      label_(new NotificationPopupContent(owner)),
      close_button_(new views::ImageButton(owner)),
      close_button_bg_color_(0) {

    AddChildView(label_);

    // Add the Close Button.
    ResourceBundle& rb = ResourceBundle::GetSharedInstance();

    close_button_->SetImage(views::CustomButton::STATE_NORMAL,
                            rb.GetImageSkiaNamed(IDR_CLOSE_BAR));
    close_button_->SetImage(views::CustomButton::STATE_HOVERED,
                            rb.GetImageSkiaNamed(IDR_CLOSE_BAR_H));
    close_button_->SetImage(views::CustomButton::STATE_PRESSED,
                            rb.GetImageSkiaNamed(IDR_CLOSE_BAR_P));

    // Disable animation so that the red danger sign shows up immediately
    // to help avoid mis-clicks.
    //close_button_->SetAnimationDuration(0);
    AddChildView(close_button_);

    set_background(views::Background::CreateSolidBackground(kNotificationPopupBackgroundColor));
  }

  virtual gfx::Size GetPreferredSize() {
    gfx::Size s = label_->GetPreferredSize();
    s.Enlarge(kLabelPaddingRight, 0);
    return s;
  }

  virtual void Layout() {
    gfx::Rect ourBounds = bounds();
    ourBounds.set_x(0);
    ourBounds.set_y(0);

    label_->SetBounds(ourBounds.x(), ourBounds.y(), ourBounds.width() - kLabelPaddingRight, ourBounds.height());

    gfx::Size prefsize = close_button_->GetPreferredSize();
    close_button_->SetBounds(ourBounds.width() - prefsize.width(), 0, prefsize.width(), prefsize.height());
  }

  NotificationPopupContent* GetLabelView() { return label_; }

private:
  ChatNotificationPopup* owner_;
  NotificationPopupContent* label_;
  views::ImageButton* close_button_;
  SkColor close_button_bg_color_;
};

// static
ChatNotificationPopup* ChatNotificationPopup::Show(views::View* anchor_view,
                     BubbleBorder::ArrowLocation arrow_location) {
  ChatNotificationPopup* popup = new ChatNotificationPopup(anchor_view,
                                                           arrow_location);
  popup->set_color(kNotificationPopupBackgroundColor);
  popup->set_close_on_deactivate(false);
  popup->set_use_focusless(true);
  popup->set_move_with_anchor(true);

  popup->SetLayoutManager(new views::FillLayout());
  //popup->AddChildView(popup->container_view());

  //ui::ResourceBundle& bundle = ui::ResourceBundle::GetSharedInstance();

  //views::Label* label = new views::Label(L"Hello, world!");
  //label->SetFont(bundle.GetFont(ResourceBundle::MediumFont));
  //label->SetBackgroundColor(SkColorSetRGB(0xff, 0xff, 0xff));
  //label->SetEnabledColor(SkColorSetRGB(0xe3, 0xed, 0xf6));
  //label->SetHorizontalAlignment(views::Label::ALIGN_LEFT);

  popup->AddChildView(popup->container_view());

  BubbleDelegateView::CreateBubble(popup);

  popup->GetWidget()->ShowInactive();

  return popup;
}

ChatNotificationPopup::ChatNotificationPopup(
    views::View* anchor,
    BubbleBorder::ArrowLocation arrow_location)
  : BubbleDelegateView(anchor, arrow_location) {
  container_view_ = new NotificationContainerView(this);
}

void ChatNotificationPopup::PushMessage(const std::string& message) {
  if (messages_.size() >= kMaxNotifications)
    messages_.pop_front();

  messages_.push_back(message);
  static_cast<NotificationContainerView*>(container_view_)->GetLabelView()->UpdateOwnText();
}

std::string ChatNotificationPopup::PopMessage() {
  std::string res = messages_.front();

  //if (messages_.size() == 1)
  //  return res;

  messages_.pop_front();
  if (messages_.size() == 0)
    GetWidget()->Close();
  else
    static_cast<NotificationContainerView*>(container_view_)->GetLabelView()->UpdateOwnText();
  return res;
}

const ChatNotificationPopup::MessageContainer& ChatNotificationPopup::GetMessages() {
  return this->messages_;
}

void ChatNotificationPopup::ButtonPressed(views::Button* sender, const ui::Event& event) {
  //DCHECK(sender == close_button_);
  GetWidget()->Close();
}

gfx::Size ChatNotificationPopup::GetPreferredSize() {
  if (this->child_count())
    return this->child_at(0)->GetPreferredSize();

  return gfx::Size();
}
