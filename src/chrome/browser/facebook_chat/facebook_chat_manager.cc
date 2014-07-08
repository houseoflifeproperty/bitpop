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

#include "chrome/browser/facebook_chat/facebook_chat_manager.h"

#include "chrome/browser/facebook_chat/facebook_chat_item.h"
#include "chrome/browser/facebook_chat/facebook_chatbar.h"
#include "chrome/browser/ui/browser.h"
#include "chrome/browser/ui/browser_window.h"
#include "chrome/browser/profiles/profile.h"
#include "base/stl_util.h"

FacebookChatManager::FacebookChatManager() :
    profile_(NULL),
    shutdown_needed_(false) {
}

FacebookChatManager::~FacebookChatManager() {
}

void FacebookChatManager::Shutdown() {
  if (!shutdown_needed_)
    return;
  shutdown_needed_ = false;

  FOR_EACH_OBSERVER(Observer, observers_, ManagerIsGoingDown());

  STLDeleteElements(&chats_);
  chats_.clear();
  jid_chats_map_.clear();
  observers_.Clear();
}

bool FacebookChatManager::Init(Profile *profile) {
  DCHECK(!shutdown_needed_)  << "FacebookChatManager already initialized.";
  shutdown_needed_ = true;

  profile_ = profile;

  return true;
}

FacebookChatItem* FacebookChatManager::GetItem(const std::string &jid) {
  ChatMap::iterator it = jid_chats_map_.find(jid);
  if (it != jid_chats_map_.end())
    return it->second;
  return NULL;
}

FacebookChatItem* FacebookChatManager::CreateFacebookChat(
    const FacebookChatCreateInfo &info) {
  ChatMap::iterator it = jid_chats_map_.find(info.jid);
  if (it != jid_chats_map_.end())
    return it->second;

  FacebookChatItem::Status status;
  if (info.status == "online")
    status = FacebookChatItem::AVAILABLE;
  else if (info.status == "idle")
    status = FacebookChatItem::IDLE;
  else if (info.status == "error")
    status = FacebookChatItem::ERROR_STATUS;
  else
    status = FacebookChatItem::OFFLINE;

  FacebookChatItem *item = new FacebookChatItem(this,
                                                info.jid,
                                                info.username,
                                                status);
  chats_.insert(item);
  jid_chats_map_[info.jid] = item;

  NotifyModelChanged();

  return item;
}

void FacebookChatManager::RemoveItem(const std::string &jid) {
  ChatMap::iterator it = jid_chats_map_.find(jid);
  if (it == jid_chats_map_.end())
    return;

  FacebookChatItem *item = it->second;

  jid_chats_map_.erase(it);
  chats_.erase(item);

  NotifyModelChanged();

  delete item;
}

void FacebookChatManager::AddNewUnreadMessage(
    const std::string &jid,
    const std::string &message) {
  ChatMap::iterator it = jid_chats_map_.find(jid);
  if (it == jid_chats_map_.end())
    return;

  FacebookChatItem *item = it->second;

  item->AddNewUnreadMessage(message);
}

void FacebookChatManager::ChangeItemStatus(const std::string &jid,
    const std::string &status) {
  ChatMap::iterator it = jid_chats_map_.find(jid);
  if (it == jid_chats_map_.end())
    return;

  FacebookChatItem *item = it->second;

  item->ChangeStatus(status);
}

void FacebookChatManager::AddObserver(Observer* observer) {
  observers_.AddObserver(observer);
  observer->ModelChanged();
}

void FacebookChatManager::RemoveObserver(Observer* observer) {
  observers_.RemoveObserver(observer);
}

void FacebookChatManager::NotifyModelChanged() {
  FOR_EACH_OBSERVER(Observer, observers_, ModelChanged());
}

int FacebookChatManager::total_unread() const {
  int total = 0;
  for (ChatSet::iterator it = chats_.begin(); it != chats_.end(); it++) {
    total += (*it)->num_notifications();
  }
  return total;
}

bool FacebookChatManager::has_message_id(const std::string& msg_id) const {
  return (message_id_set_.find(msg_id) != message_id_set_.end());
}

void FacebookChatManager::AddMessageId(const std::string& msg_id) {
  message_id_set_.insert(msg_id);
}
