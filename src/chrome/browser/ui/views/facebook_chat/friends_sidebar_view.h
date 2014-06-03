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

#ifndef CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_FRIENDS_SIDEBAR_VIEW_H_
#define CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_FRIENDS_SIDEBAR_VIEW_H_

#include "chrome/browser/ui/views/extensions/extension_view_views.h"
//#include "content/public/browser/notification_details.h"
#include "content/public/browser/notification_observer.h"
#include "content/public/browser/notification_registrar.h"
//#include "content/public/browser/notification_source.h"
#include "ui/views/view.h"

class Browser;
class BrowserView;

namespace extensions {
  class ExtensionHost;
}

class FriendsSidebarView : public views::View,
                           public content::NotificationObserver,
                           public ExtensionViewViews::Container {
public:
  FriendsSidebarView(Browser* browser, BrowserView* parent);
  virtual ~FriendsSidebarView();

  // Implementation of View.
  virtual gfx::Size GetPreferredSize() OVERRIDE;

protected:
  // content::NotificationObserver override
  virtual void Observe(int type,
      const content::NotificationSource& source,
      const content::NotificationDetails& details) OVERRIDE;

  // ExtensionView::Container override
  virtual void OnExtensionSizeChanged(ExtensionViewViews* view) OVERRIDE;

private:
  void Init();

  void InitializeExtensionHost();

  /* data */
  Browser* browser_;
  BrowserView* parent_;
  scoped_ptr<extensions::ExtensionHost> extension_host_;

  content::NotificationRegistrar registrar_;

  //static scoped_ptr<TabContents> extension_page_contents_;
};
#endif // CHROME_BROWSER_UI_VIEWS_FACEBOOK_CHAT_FRIENDS_SIDEBAR_VIEW_H_

