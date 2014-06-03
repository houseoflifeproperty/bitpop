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

#include "chrome/browser/ui/cocoa/facebook_chat/facebook_chat_item_mac.h"

#import "chrome/browser/ui/cocoa/facebook_chat/facebook_chat_item_controller.h"

FacebookChatItemMac::FacebookChatItemMac(FacebookChatItem *model,
                                         FacebookChatItemController *controller)
                                         : model_(model),
                                           controller_(controller) {
  model_->AddObserver(this);
}

FacebookChatItemMac::~FacebookChatItemMac() {
  model_->RemoveObserver(this);
}

void FacebookChatItemMac::OnChatUpdated(FacebookChatItem *source) {
  DCHECK(source == model_);
  switch (source->state()) {
  // case FacebookChatItem::ACTIVE_STATUS_CHANGED:
  //   if (source->active())
  //     [controller_ openChatWindow];
  //   break;
  case FacebookChatItem::REMOVING:
    [controller_ remove];
    break;
  case FacebookChatItem::NUM_NOTIFICATIONS_CHANGED:
    [controller_ setUnreadMessagesNumber:source->num_notifications()];
    break;
  case FacebookChatItem::STATUS_CHANGED:
    [controller_ statusChanged];
    break;
  default:
    break;
  }
}

FacebookChatItem* FacebookChatItemMac::chat() const {
  return model_;
}
