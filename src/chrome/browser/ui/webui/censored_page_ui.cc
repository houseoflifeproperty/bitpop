// Copyright (c) 2012 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "chrome/browser/ui/webui/censored_page_ui.h"

#include <algorithm>
#include <string>
#include <utility>
#include <vector>

#include "base/bind.h"
#include "base/bind_helpers.h"
#include "base/callback.h"
#include "base/command_line.h"
#include "base/files/file_util.h"
#include "base/i18n/number_formatting.h"
#include "base/json/json_writer.h"
#include "base/memory/singleton.h"
#include "base/metrics/statistics_recorder.h"
#include "base/strings/string_number_conversions.h"
#include "base/strings/string_piece.h"
#include "base/strings/string_util.h"
#include "base/strings/stringprintf.h"
#include "base/strings/utf_string_conversions.h"
#include "base/threading/thread.h"
#include "base/values.h"
#include "chrome/browser/about_flags.h"
#include "chrome/browser/browser_process.h"
#include "chrome/browser/defaults.h"
#include "chrome/browser/memory_details.h"
#include "chrome/browser/net/predictor.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/profiles/profile_manager.h"
#include "chrome/browser/ui/browser_dialogs.h"
#include "chrome/common/chrome_paths.h"
#include "chrome/common/render_messages.h"
#include "chrome/common/url_constants.h"
#include "chrome/grit/chromium_strings.h"
#include "chrome/grit/generated_resources.h"
#include "chrome/grit/locale_settings.h"
#include "content/public/browser/browser_thread.h"
#include "content/public/browser/render_process_host.h"
#include "content/public/browser/render_view_host.h"
#include "content/public/browser/url_data_source.h"
#include "content/public/browser/web_contents.h"
#include "content/public/common/content_client.h"
#include "content/public/common/process_type.h"
#include "google_apis/gaia/google_service_auth_error.h"
#include "grit/browser_resources.h"
#include "net/base/escape.h"
#include "net/base/filename_util.h"
#include "net/base/load_flags.h"
#include "net/http/http_response_headers.h"
#include "net/url_request/url_fetcher.h"
#include "net/url_request/url_request_status.h"
#include "ui/base/l10n/l10n_util.h"
#include "ui/base/resource/resource_bundle.h"
#include "ui/base/webui/jstemplate_builder.h"
#include "ui/base/webui/web_ui_util.h"
#include "url/gurl.h"

#if defined(ENABLE_THEMES)
#include "chrome/browser/ui/webui/theme_source.h"
#endif

//using base::Time;
//using base::TimeDelta;
//using content::BrowserThread;
//using content::WebContents;

namespace {
//const char kLocalizedStringsFile[] = "strings.js";
const char kCensoredPngPath[] = "censored.png";
}  // namespace

// CensoredPageUIHTMLSource --------------------------------------------------

CensoredPageUIHTMLSource::CensoredPageUIHTMLSource(Profile* profile)
    : profile_(profile) {}

CensoredPageUIHTMLSource::~CensoredPageUIHTMLSource() {}

std::string CensoredPageUIHTMLSource::GetSource() const {
  return chrome::kChromeUICensoredPageHost;
}

void CensoredPageUIHTMLSource::StartDataRequest(
    const std::string& path,
    int render_process_id,
    int render_frame_id,
    const content::URLDataSource::GotDataCallback& callback) {
  scoped_refptr<base::RefCountedMemory> response_bytes;
  // const std::string& app_locale = g_browser_process->GetApplicationLocale();
  // webui::SetLoadTimeDataDefaults(app_locale, localized_strings_.get());

  // if (path == kLocalizedStringsFile) {
  //   // Return dynamically-generated strings from memory.
  //   std::string strings_js;
  //   webui::AppendJsonJS(localized_strings_.get(), &strings_js);
  //   response_bytes = base::RefCountedString::TakeString(&strings_js);
  // } else
  if (path == kCensoredPngPath) {
    response_bytes = ui::ResourceBundle::GetSharedInstance().
        LoadDataResourceBytes(IDR_CENSORED_PNG);
  } else {
    // Return (and cache) the main options html page as the default.
    response_bytes = ui::ResourceBundle::GetSharedInstance().
        LoadDataResourceBytes(IDR_CENSORED_PAGE_HTML);
  }

  callback.Run(response_bytes.get());
}

std::string CensoredPageUIHTMLSource::GetMimeType(const std::string& path) const {
  if (path == kCensoredPngPath) {
    return "image/png";
  }
  return "text/html";
}

bool CensoredPageUIHTMLSource::ShouldAddContentSecurityPolicy() const {
  return content::URLDataSource::ShouldAddContentSecurityPolicy();
}

bool CensoredPageUIHTMLSource::ShouldDenyXFrameOptions() const {
  return content::URLDataSource::ShouldDenyXFrameOptions();
}

CensoredPageUI::CensoredPageUI(content::WebUI* web_ui)
    : WebUIController(web_ui) {
  Profile* profile = Profile::FromWebUI(web_ui);

#if defined(ENABLE_THEMES)
  // Set up the chrome://theme/ source.
  ThemeSource* theme = new ThemeSource(profile);
  content::URLDataSource::Add(profile, theme);
#endif

  content::URLDataSource::Add(profile, new CensoredPageUIHTMLSource(profile));
}
