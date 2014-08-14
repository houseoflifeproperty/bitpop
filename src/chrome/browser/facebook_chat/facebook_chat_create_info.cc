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

#include "chrome/browser/facebook_chat/facebook_chat_create_info.h"

FacebookChatCreateInfo::FacebookChatCreateInfo(const std::string &jid,
    const std::string &username,
    const std::string &status)
      : jid(jid),
        username(username),
        status(status) {
}

FacebookChatCreateInfo::FacebookChatCreateInfo()
      : jid("#NONE#"),
        username("#NONE#"),
        status("offline") {
}

FacebookChatCreateInfo::~FacebookChatCreateInfo()
{
}

