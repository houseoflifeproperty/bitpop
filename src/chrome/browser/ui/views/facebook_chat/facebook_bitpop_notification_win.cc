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

#include "chrome/browser/ui/views/facebook_chat/facebook_bitpop_notification_win.h"

#include "base/strings/string_number_conversions.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/ui/browser.h"
#include "chrome/browser/ui/browser_finder.h"
#include "chrome/browser/ui/browser_window.h"
#include "chrome/browser/ui/lion_badge_image_source.h"
#include "chrome/common/badge_util.h"
#include "grit/ui_resources.h"
#include "third_party/skia/include/core/SkBitmap.h"
#include "third_party/skia/include/core/SkPaint.h"
#include "third_party/skia/include/core/SkTypeface.h"
#include "third_party/skia/include/effects/SkGradientShader.h"
#include "ui/base/resource/resource_bundle.h"
#include "ui/gfx/canvas.h"
#include "ui/gfx/skia_util.h"

#if defined(OS_WIN)
#include <shobjidl.h>
#include "base/win/scoped_comptr.h"
#include "base/win/windows_version.h"
#include "skia/ext/image_operations.h"
#include "ui/gfx/icon_util.h"
#include "ui/views/win/hwnd_util.h"
#endif

namespace {

const int kNotifyIconDimX = 16;
const int kNotifyIconDimY = 16;

}

FacebookBitpopNotificationWin::FacebookBitpopNotificationWin(Profile* profile)
  : profile_(profile), notified_hwnd_(NULL) {
}

FacebookBitpopNotificationWin::~FacebookBitpopNotificationWin() {
}

void FacebookBitpopNotificationWin::Shutdown() {
}

void FacebookBitpopNotificationWin::ClearNotification() {
  if (base::win::GetVersion() < base::win::VERSION_WIN7)
    return;

  if (!notified_hwnd_)
    return;

  base::win::ScopedComPtr<ITaskbarList3> taskbar;
  HRESULT result = taskbar.CreateInstance(CLSID_TaskbarList, NULL,
                                          CLSCTX_INPROC_SERVER);
  if (FAILED(result) || FAILED(taskbar->HrInit()))
    return;

  taskbar->SetOverlayIcon(notified_hwnd_, NULL, L"");
  notified_hwnd_ = NULL;
}

void FacebookBitpopNotificationWin::NotifyUnreadMessagesWithLastUser(int num_unread,
                                                const std::string& user_id) {

  Browser* browser = chrome::FindTabbedBrowser(profile_, false, chrome::HOST_DESKTOP_TYPE_FIRST);
  if (browser == NULL)
    return;

  HWND hwnd = views::HWNDForNativeWindow(browser->window()->GetNativeWindow());

  FLASHWINFO fwInfo;
  ::ZeroMemory(&fwInfo, sizeof(FLASHWINFO));
  fwInfo.cbSize = sizeof(FLASHWINFO);
  fwInfo.hwnd = hwnd;
  fwInfo.dwFlags = FLASHW_TIMERNOFG | FLASHW_TRAY;
  ::FlashWindowEx(&fwInfo);

  if (base::win::GetVersion() < base::win::VERSION_WIN7)
    return;

  base::win::ScopedComPtr<ITaskbarList3> taskbar;
  HRESULT result = taskbar.CreateInstance(CLSID_TaskbarList, NULL,
                                          CLSCTX_INPROC_SERVER);
  if (FAILED(result) || FAILED(taskbar->HrInit()))
    return;
  HICON icon = NULL;

  int number = num_unread;
  if (number <= 0) {
    return;
  }

  if (number > 99)
    number = 99;
  std::string num = base::IntToString(number);

  LionBadgeImageSource* source = new LionBadgeImageSource(
          gfx::Size(kNotifyIconDimX, kNotifyIconDimY),
          num);

  gfx::ImageSkia image(source, gfx::Size(kNotifyIconDimX, kNotifyIconDimY));

  icon = IconUtil::CreateHICONFromSkBitmap(*image.bitmap());
  if (!icon)
    return;
  taskbar->SetOverlayIcon(hwnd, icon, L"");
  notified_hwnd_ = hwnd;
  if (icon)
    ::DestroyIcon(icon);
}
