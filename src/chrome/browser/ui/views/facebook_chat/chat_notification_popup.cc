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

#include "base/logging.h"
#include "base/strings/utf_string_conversions.h"
#include "base/win/win_util.h"
#include "grit/generated_resources.h"
#include "grit/theme_resources.h"
#include "grit/ui_resources.h"
#include "ui/base/l10n/l10n_util.h"
#include "ui/base/resource/resource_bundle.h"
#include "ui/views/controls/button/label_button.h"
#include "ui/views/layout/fill_layout.h"
#include "ui/views/widget/widget.h"

using views::View;

namespace {
  static const int kMaxNotifications = 20;
  static const int kNotificationLabelWidth = 180;
  static const int kNotificationLabelMaxHeight = 600;
  static const int kLabelPaddingRight = 18;
  static const int kLabelVerticalSpacing = 25;
  // static const int kMinPopupHeight = 30;

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

    SetAutoColorReadabilityEnabled(false);
    SetBackgroundColor(kNotificationPopupBackgroundColor);
    SetEnabledColor(SkColorSetRGB(0,0,0));
  }

  virtual gfx::Size GetPreferredSize() OVERRIDE {
    gfx::Size size = views::Label::GetPreferredSize();

    return gfx::Size(kNotificationLabelWidth, std::min(size.height(), kNotificationLabelMaxHeight));
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

    SetText(base::UTF8ToWide(concat));
    SizeToFit(kNotificationLabelWidth);
  }

private:
  ChatNotificationPopup* owner_;
};


class NotificationContainerView : public View {
public:
  NotificationContainerView(ChatNotificationPopup *owner)
    : owner_(owner),
      title_label_(new views::Label()),
      label_(new NotificationPopupContent(owner)),
      close_button_(new views::LabelButton(owner, base::string16())) {

    ResourceBundle& rb = ResourceBundle::GetSharedInstance();
    title_label_->SetFontList(
        rb.GetFontList(ResourceBundle::BoldFont));
    title_label_->SetAutoColorReadabilityEnabled(false);
    title_label_->SetBackgroundColor(kNotificationPopupBackgroundColor);
    title_label_->SetEnabledColor(SkColorSetRGB(0,0,0));
    title_label_->SetText(
        l10n_util::GetStringUTF16(IDS_CHAT_NOTIFICATION_BUBBLE_TITLE));
    title_label_->SetSize(title_label_->GetPreferredSize());
    AddChildView(title_label_);

    AddChildView(label_);

    // Add the Close Button.
    close_button_->SetImage(views::CustomButton::STATE_NORMAL,
                            *rb.GetImageSkiaNamed(IDR_CLOSE_DIALOG));
    close_button_->SetImage(views::CustomButton::STATE_HOVERED,
                            *rb.GetImageSkiaNamed(IDR_CLOSE_DIALOG_H));
    close_button_->SetImage(views::CustomButton::STATE_PRESSED,
                            *rb.GetImageSkiaNamed(IDR_CLOSE_DIALOG_P));
    close_button_->SetBorder(scoped_ptr<views::Border>());
    close_button_->SetSize(close_button_->GetPreferredSize());

    AddChildView(close_button_);

    set_background(views::Background::CreateSolidBackground(kNotificationPopupBackgroundColor));
  }

  virtual gfx::Size GetPreferredSize() {
    gfx::Size res = title_label_->GetPreferredSize();
    res.Enlarge(kNotificationLabelWidth - res.width() + kLabelPaddingRight, 
                kLabelVerticalSpacing);
    gfx::Size s = label_->GetPreferredSize();
    res.Enlarge(0, s.height());

    return res;
  }

  virtual void Layout() {
    title_label_->SetPosition(gfx::Point(0, 0));
    label_->SetPosition(gfx::Point(0, title_label_->bounds().height() + kLabelVerticalSpacing));
    label_->SetSize(label_->GetPreferredSize());
    close_button_->SetPosition(gfx::Point(bounds().width() - close_button_->GetPreferredSize().width(), 0));
  }

  NotificationPopupContent* GetLabelView() { return label_; }

private:
  ChatNotificationPopup* owner_;
  views::Label* title_label_;
  NotificationPopupContent* label_;
  views::LabelButton* close_button_;
};

// static
ChatNotificationPopup* ChatNotificationPopup::Show(views::View* anchor_view,
                     BubbleBorder::Arrow arrow_location) {
  ChatNotificationPopup* popup = new ChatNotificationPopup(anchor_view,
                                                           arrow_location);
  popup->set_color(kNotificationPopupBackgroundColor);
  popup->set_close_on_deactivate(false);

  popup->SetLayoutManager(new views::FillLayout());

  popup->AddChildView(popup->container_view());

  BubbleDelegateView::CreateBubble(popup);

  popup->GetWidget()->ShowInactive();

  return popup;
}

ChatNotificationPopup::ChatNotificationPopup(
    views::View* anchor,
    BubbleBorder::Arrow arrow_location)
  : BubbleDelegateView(anchor, arrow_location) {
  container_view_ = new NotificationContainerView(this);
}

void ChatNotificationPopup::PushMessage(const std::string& message) {
  if (messages_.size() >= kMaxNotifications)
    messages_.pop_front();

  messages_.push_back(message);
  container_view_->GetLabelView()->UpdateOwnText();
  SizeToContents();
}

std::string ChatNotificationPopup::PopMessage() {
  std::string res = messages_.front();

  messages_.pop_front();
  if (messages_.size() == 0)
    GetWidget()->Close();
  else {
    container_view_->GetLabelView()->UpdateOwnText();
    SizeToContents();
  }
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
    return container_view_->GetPreferredSize();

  return gfx::Size();
}

views::View* ChatNotificationPopup::container_view() {
  return static_cast<views::View*>(container_view_);
}