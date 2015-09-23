// Copyright (c) 2011 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef CHROME_BROWSER_UI_WEBUI_CENSORED_PAGE_UI_H_
#define CHROME_BROWSER_UI_WEBUI_CENSORED_PAGE_UI_H_

#include <string>

#include "base/basictypes.h"
#include "base/compiler_specific.h"
#include "content/public/browser/url_data_source.h"
#include "content/public/browser/web_ui_controller.h"

class Profile;

// We expose this class because the OOBE flow may need to explicitly add the
// chrome://terms source outside of the normal flow.
class CensoredPageUIHTMLSource : public content::URLDataSource {
 public:
  // Construct a data source for the specified |source_name|.
  CensoredPageUIHTMLSource(Profile* profile);

  // content::URLDataSource implementation.
  std::string GetSource() const override;
  void StartDataRequest(
      const std::string& path,
      int render_process_id,
      int render_frame_id,
      const content::URLDataSource::GotDataCallback& callback) override;
  std::string GetMimeType(const std::string& path) const override;
  bool ShouldAddContentSecurityPolicy() const override;
  bool ShouldDenyXFrameOptions() const override;

  Profile* profile() { return profile_; }

 private:
  ~CensoredPageUIHTMLSource() override;

  std::string source_name_;
  Profile* profile_;

  DISALLOW_COPY_AND_ASSIGN(CensoredPageUIHTMLSource);
};

class CensoredPageUI : public content::WebUIController {
 public:
  explicit CensoredPageUI(content::WebUI* web_ui);
  ~CensoredPageUI() override {}

 private:
  DISALLOW_COPY_AND_ASSIGN(CensoredPageUI);
};

#endif  // CHROME_BROWSER_UI_WEBUI_CENSORED_PAGE_UI_H_
