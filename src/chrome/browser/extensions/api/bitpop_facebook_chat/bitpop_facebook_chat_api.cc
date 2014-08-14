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

#include "chrome/browser/extensions/api/bitpop_facebook_chat/bitpop_facebook_chat_api.h"

#include <map>
#include <set>

#include "base/logging.h"
#include "base/prefs/pref_service.h"
#include "base/values.h"
#include "chrome/browser/ui/browser.h"
#include "chrome/browser/ui/browser_window.h"
#include "chrome/common/pref_names.h"
#include "chrome/browser/facebook_chat/facebook_bitpop_notification.h"
#include "chrome/browser/facebook_chat/facebook_bitpop_notification_service_factory.h"
#include "chrome/browser/facebook_chat/facebook_chat_create_info.h"
#include "chrome/browser/facebook_chat/facebook_chat_manager.h"
#include "chrome/browser/facebook_chat/facebook_chat_manager_service_factory.h"
#include "chrome/browser/facebook_chat/facebook_chat_item.h"
#include "chrome/browser/facebook_chat/received_message_info.h"
#include "chrome/browser/profiles/profile.h"
//#include "content/browser/tab_contents/tab_contents.h"
#include "content/public/browser/notification_service.h"
#include "content/public/browser/notification_types.h"

using base::ListValue;
using base::Value;

namespace {
// Errors.
const char kInvalidArguments[] =
  "Invalid arguments passed to function.";
const char kNoCurrentWindowError[] = "No current browser window was found";
} // namespace

// List is considered empty if it is actually empty or contains just one value,
// either 'null' or 'undefined'.
static bool IsArgumentListEmpty(const ListValue* arguments) {
  if (arguments->empty())
    return true;
  if (arguments->GetSize() == 1) {
    const Value* first_value = 0;
    if (!arguments->Get(0, &first_value))
      return true;
    if (first_value->GetType() == Value::TYPE_NULL)
      return true;
  }
  return false;
}

bool BitpopFacebookChatSetFriendsSidebarVisibleFunction::RunSync() {
  if (!args_.get())
    return false;

  bool is_visible = true;
  if (IsArgumentListEmpty(args_.get())) {
    error_ = kInvalidArguments;
    return false;
  } else {
    EXTENSION_FUNCTION_VALIDATE(args_->GetBoolean(0, &is_visible));
  }

  Browser* browser = GetCurrentBrowser();
  if (!browser || !browser->window()) {
    error_ = kNoCurrentWindowError;
    return false;
  }

  PrefService *prefService = browser->profile()->GetPrefs();
  prefService->SetBoolean(prefs::kFacebookShowFriendsList, is_visible);

  content::NotificationService::current()->Notify(
             content::NOTIFICATION_FACEBOOK_FRIENDS_SIDEBAR_VISIBILITY_CHANGED,
             content::Source<Profile>(browser->profile()),
             content::Details<bool>(&is_visible));
  return true;
}

bool BitpopFacebookChatGetFriendsSidebarVisibleFunction::RunSync() {
  if (!args_.get())
    return false;

  Browser* browser = GetCurrentBrowser();
  if (!browser || !browser->window()) {
    error_ = kNoCurrentWindowError;
    return false;
  }

  SetResult(Value::CreateBooleanValue(
        browser->window()->IsFriendsSidebarVisible()));
  return true;
}

bool BitpopFacebookChatAddChatFunction::RunSync() {
  if (!args_.get())
    return false;

  std::string jid(""), username(""), status("");

  if (IsArgumentListEmpty(args_.get()) || args_->GetSize() != 3) {
    error_ = kInvalidArguments;
    return false;
  } else {
    EXTENSION_FUNCTION_VALIDATE(args_->GetString(0, &jid));
    EXTENSION_FUNCTION_VALIDATE(args_->GetString(1, &username));
    EXTENSION_FUNCTION_VALIDATE(args_->GetString(2, &status));
  }

  LOG(INFO) << "AddChat() Status is: " << status;
  // FacebookChatItem::Status statusValue = FacebookChatItem::AVAILABLE;
  // if (status != "available")
  //   statusValue = FacebookChatItem::OFFLINE;

  Browser* browser = GetCurrentBrowser();
  if (!browser) {
    error_ = kNoCurrentWindowError;
    return false;
  }

  content::NotificationService::current()->Notify(
      content::NOTIFICATION_FACEBOOK_CHATBAR_ADD_CHAT,
      content::Source<Profile>(browser->profile()),
      content::Details<FacebookChatCreateInfo>(
        new FacebookChatCreateInfo(jid, username, status)));

  return true;
}

bool BitpopFacebookChatNewIncomingMessageFunction::RunSync() {
  if (!args_.get())
    return false;

  std::string msg_id(""), jid(""), username(""), status(""), message("");

  if (IsArgumentListEmpty(args_.get()) || args_->GetSize() != 5) {
    error_ = kInvalidArguments;
    return false;
  } else {
    EXTENSION_FUNCTION_VALIDATE(args_->GetString(0, &msg_id));
    EXTENSION_FUNCTION_VALIDATE(args_->GetString(1, &jid));
    EXTENSION_FUNCTION_VALIDATE(args_->GetString(2, &username));
    EXTENSION_FUNCTION_VALIDATE(args_->GetString(3, &status));
    EXTENSION_FUNCTION_VALIDATE(args_->GetString(4, &message));
  }

  LOG(INFO) << "NewIncomingMessage() Status is: " << status;
  // FacebookChatItem::Status statusValue = FacebookChatItem::AVAILABLE;
  // if (status != "available")
  //   statusValue = FacebookChatItem::OFFLINE;

  Browser* browser = GetCurrentBrowser();
  if (!browser) {
    error_ = kNoCurrentWindowError;
    return false;
  }

  FacebookChatManager *mgr = FacebookChatManagerServiceFactory::GetForProfile(browser->profile());
  if (mgr && (!mgr->has_message_id(msg_id) || msg_id == "service")) {
    mgr->AddMessageId(msg_id);

    if (!message.empty() && mgr) {
      mgr->CreateFacebookChat(FacebookChatCreateInfo(jid, username, status));

      mgr->AddNewUnreadMessage(jid, message);

      size_t at_pos = jid.find('@');
      if (at_pos != std::string::npos && at_pos > 1) {
        FacebookBitpopNotificationServiceFactory::GetForProfile(browser->profile())->
            NotifyUnreadMessagesWithLastUser(mgr->total_unread(), jid.substr(1, at_pos-1));
      }

      content::NotificationService::current()->Notify(
        content::NOTIFICATION_FACEBOOK_CHATBAR_NEW_INCOMING_MESSAGE,
        content::Source<Profile>(browser->profile()),
        content::Details<ReceivedMessageInfo>(
          new ReceivedMessageInfo(jid, username, status, message)));
    } else
      mgr->ChangeItemStatus(jid, status);
  }

  return true;
}

bool BitpopFacebookChatLoggedOutFacebookSessionFunction::RunSync() {
  Browser* browser = GetCurrentBrowser();
  if (!browser) {
    error_ = kNoCurrentWindowError;
    return false;
  }

  content::NotificationService::current()->Notify(
      content::NOTIFICATION_FACEBOOK_SESSION_LOGGED_OUT,
      content::Source<Profile>(browser->profile()),
      content::NotificationService::NoDetails());

  return true;
}

bool BitpopFacebookChatLoggedInFacebookSessionFunction::RunSync() {
  Browser* browser = GetCurrentBrowser();
  if (!browser) {
    error_ = kNoCurrentWindowError;
    return false;
  }

  content::NotificationService::current()->Notify(
      content::NOTIFICATION_FACEBOOK_SESSION_LOGGED_IN,
      content::Source<Profile>(browser->profile()),
      content::NotificationService::NoDetails());

  return true;
}

bool BitpopFacebookChatSetGlobalMyUidForProfileFunction::RunSync() {
  if (!args_.get())
    return false;

  std::string uid("");

  if (IsArgumentListEmpty(args_.get()) || args_->GetSize() != 1) {
    error_ = kInvalidArguments;
    return false;
  } else {
    EXTENSION_FUNCTION_VALIDATE(args_->GetString(0, &uid));
  }

  Browser* browser = GetCurrentBrowser();
  if (!browser) {
    error_ = kNoCurrentWindowError;
    return false;
  }

  FacebookChatManager *mgr = FacebookChatManagerServiceFactory::GetForProfile(browser->profile());
  if (mgr)
    mgr->set_global_my_uid(uid);

  return true;
}
