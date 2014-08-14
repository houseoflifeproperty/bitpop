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

#include "chrome/browser/ui/webui/options/bitpop_options_ui.h"

#include <algorithm>
#include <vector>

#include "base/basictypes.h"
#include "base/callback.h"
#include "base/command_line.h"
#include "base/memory/ref_counted_memory.h"
#include "base/memory/singleton.h"
#include "base/message_loop/message_loop.h"
#include "base/strings/string_piece.h"
#include "base/strings/string_util.h"
#include "base/threading/thread.h"
#include "base/time/time.h"
#include "base/values.h"
#include "chrome/browser/autocomplete/autocomplete_match.h"
#include "chrome/browser/autocomplete/autocomplete_result.h"
#include "chrome/browser/browser_about_handler.h"
#include "chrome/browser/browser_process.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/ui/webui/metrics_handler.h"
#include "chrome/browser/ui/webui/options/bitpop_core_options_handler.h"
#include "chrome/browser/ui/webui/options/bitpop_options_handler.h"
#include "chrome/browser/ui/webui/options/bitpop_proxy_domain_settings_handler.h"
#include "chrome/browser/ui/webui/options/bitpop_uncensor_filter_handler.h"
#include "chrome/browser/ui/webui/sync_setup_handler.h"
#include "chrome/browser/ui/webui/theme_source.h"
#include "chrome/common/url_constants.h"
#include "content/public/browser/notification_types.h"
#include "content/public/browser/render_view_host.h"
#include "content/public/browser/url_data_source.h"
#include "content/public/browser/web_contents.h"
#include "content/public/browser/web_contents_delegate.h"
#include "content/public/browser/web_ui.h"
#include "grit/chromium_strings.h"
#include "grit/generated_resources.h"
#include "grit/locale_settings.h"
#include "grit/options_resources.h"
#include "grit/theme_resources.h"
#include "net/base/escape.h"
#include "ui/base/l10n/l10n_util.h"
#include "ui/base/resource/resource_bundle.h"
#include "ui/base/webui/jstemplate_builder.h"
#include "ui/base/webui/web_ui_util.h"
#include "url/gurl.h"

#if defined(USE_NSS)
#include "chrome/browser/ui/webui/options/certificate_manager_handler.h"
#endif

#if defined(ENABLE_GOOGLE_NOW)
#include "chrome/browser/ui/webui/options/geolocation_options_handler.h"
#endif

using content::RenderViewHost;

namespace {

const char kLocalizedStringsFile[] = "strings.js";
const char kOptionsBundleJsFile[]  = "options_bundle.js";

}  // namespace

namespace options {

////////////////////////////////////////////////////////////////////////////////
//
// BitpopOptionsUIHTMLSource
//
////////////////////////////////////////////////////////////////////////////////

class BitpopOptionsUIHTMLSource : public content::URLDataSource {
 public:
  // The constructor takes over ownership of |localized_strings|.
  explicit BitpopOptionsUIHTMLSource(base::DictionaryValue* localized_strings);

  // content::URLDataSource implementation.
  virtual std::string GetSource() const OVERRIDE;
  virtual void StartDataRequest(
      const std::string& path,
      int render_process_id,
      int render_frame_id,
      const content::URLDataSource::GotDataCallback& callback) OVERRIDE;
  virtual std::string GetMimeType(const std::string&) const OVERRIDE;
  virtual bool ShouldDenyXFrameOptions() const OVERRIDE;

 private:
  virtual ~BitpopOptionsUIHTMLSource();

  // Localized strings collection.
  scoped_ptr<base::DictionaryValue> localized_strings_;

  DISALLOW_COPY_AND_ASSIGN(BitpopOptionsUIHTMLSource);
};

BitpopOptionsUIHTMLSource::BitpopOptionsUIHTMLSource(
    base::DictionaryValue* localized_strings) {
  DCHECK(localized_strings);
  localized_strings_.reset(localized_strings);
}

std::string BitpopOptionsUIHTMLSource::GetSource() const {
  return chrome::kChromeUIBitpopSettingsFrameHost;
}

void BitpopOptionsUIHTMLSource::StartDataRequest(
    const std::string& path,
    int render_process_id,
    int render_frame_id,
    const content::URLDataSource::GotDataCallback& callback) {
  scoped_refptr<base::RefCountedMemory> response_bytes;
  webui::SetFontAndTextDirection(localized_strings_.get());

  if (path == kLocalizedStringsFile) {
    // Return dynamically-generated strings from memory.
    webui::UseVersion2 version;
    std::string strings_js;
    webui::AppendJsonJS(localized_strings_.get(), &strings_js);
    response_bytes = base::RefCountedString::TakeString(&strings_js);
  } else if (path == kOptionsBundleJsFile) {
    // Return (and cache) the options javascript code.
    response_bytes = ui::ResourceBundle::GetSharedInstance().
        LoadDataResourceBytes(IDR_OPTIONS_BITPOP_BUNDLE_JS);
  } else {
    // Return (and cache) the main options html page as the default.
    response_bytes = ui::ResourceBundle::GetSharedInstance().
        LoadDataResourceBytes(IDR_OPTIONS_BITPOP_HTML);
  }

  callback.Run(response_bytes.get());
}

std::string BitpopOptionsUIHTMLSource::GetMimeType(const std::string& path) const {
  if (path == kLocalizedStringsFile || path == kOptionsBundleJsFile)
    return "application/javascript";

  return "text/html";
}

bool BitpopOptionsUIHTMLSource::ShouldDenyXFrameOptions() const {
  return false;
}

BitpopOptionsUIHTMLSource::~BitpopOptionsUIHTMLSource() {}

////////////////////////////////////////////////////////////////////////////////
//
// BitpopOptionsPageUIHandler
//
////////////////////////////////////////////////////////////////////////////////

const char BitpopOptionsPageUIHandler::kSettingsAppKey[] = "settingsApp";

BitpopOptionsPageUIHandler::BitpopOptionsPageUIHandler() {
}

BitpopOptionsPageUIHandler::~BitpopOptionsPageUIHandler() {
}

bool BitpopOptionsPageUIHandler::IsEnabled() {
  return true;
}

// static
void BitpopOptionsPageUIHandler::RegisterStrings(
    base::DictionaryValue* localized_strings,
    const OptionsStringResource* resources,
    size_t length) {
  for (size_t i = 0; i < length; ++i) {
    base::string16 value;
    if (resources[i].substitution_id == 0) {
      value = l10n_util::GetStringUTF16(resources[i].id);
    } else {
      value = l10n_util::GetStringFUTF16(
          resources[i].id,
          l10n_util::GetStringUTF16(resources[i].substitution_id));
    }
    localized_strings->SetString(resources[i].name, value);
  }
}

void BitpopOptionsPageUIHandler::RegisterTitle(
    base::DictionaryValue* localized_strings,
    const std::string& variable_name,
    int title_id) {
  localized_strings->SetString(variable_name,
      l10n_util::GetStringUTF16(title_id));
  localized_strings->SetString(variable_name + "TabTitle",
      l10n_util::GetStringFUTF16(IDS_OPTIONS_TAB_TITLE,
          l10n_util::GetStringUTF16(IDS_SETTINGS_TITLE),
          l10n_util::GetStringUTF16(title_id)));
}

////////////////////////////////////////////////////////////////////////////////
//
// BitpopOptionsUI
//
////////////////////////////////////////////////////////////////////////////////

BitpopOptionsUI::BitpopOptionsUI(content::WebUI* web_ui)
    : WebUIController(web_ui),
      WebContentsObserver(web_ui->GetWebContents()),
      initialized_handlers_(false) {
  base::DictionaryValue* localized_strings = new base::DictionaryValue();
  localized_strings->Set(BitpopOptionsPageUIHandler::kSettingsAppKey,
                         new base::DictionaryValue());

  BitpopCoreOptionsHandler* core_handler;
#if defined(OS_CHROMEOS)
  core_handler = new chromeos::options::CoreChromeOSOptionsHandler();
#else
  core_handler = new BitpopCoreOptionsHandler();
#endif
  core_handler->set_handlers_host(this);
  AddOptionsPageUIHandler(localized_strings, core_handler);

  BitpopOptionsHandler* bitpop_options_handler = new BitpopOptionsHandler();
  AddOptionsPageUIHandler(localized_strings, bitpop_options_handler);

  AddOptionsPageUIHandler(localized_strings,
      new BitpopProxyDomainSettingsHandler());
  AddOptionsPageUIHandler(localized_strings,
      new BitpopUncensorFilterHandler());

  // |localized_strings| ownership is taken over by this constructor.
  BitpopOptionsUIHTMLSource* html_source =
      new BitpopOptionsUIHTMLSource(localized_strings);

  // Set up the chrome://settings-frame/ source.
  Profile* profile = Profile::FromWebUI(web_ui);
  content::URLDataSource::Add(profile, html_source);

  // Set up the chrome://theme/ source.
  ThemeSource* theme = new ThemeSource(profile);
  content::URLDataSource::Add(profile, theme);
}

BitpopOptionsUI::~BitpopOptionsUI() {
  // Uninitialize all registered handlers. Deleted by WebUIImpl.
  for (size_t i = 0; i < handlers_.size(); ++i)
    handlers_[i]->Uninitialize();
}

scoped_ptr<BitpopOptionsUI::OnFinishedLoadingCallbackList::Subscription>
BitpopOptionsUI::RegisterOnFinishedLoadingCallback(const base::Closure& callback) {
  return on_finished_loading_callbacks_.Add(callback);
}

// static
void BitpopOptionsUI::ProcessAutocompleteSuggestions(
    const AutocompleteResult& result,
    base::ListValue* const suggestions) {
  for (size_t i = 0; i < result.size(); ++i) {
    const AutocompleteMatch& match = result.match_at(i);
    AutocompleteMatchType::Type type = match.type;
    if (type != AutocompleteMatchType::HISTORY_URL &&
        type != AutocompleteMatchType::HISTORY_TITLE &&
        type != AutocompleteMatchType::HISTORY_BODY &&
        type != AutocompleteMatchType::HISTORY_KEYWORD &&
        type != AutocompleteMatchType::NAVSUGGEST &&
        type != AutocompleteMatchType::NAVSUGGEST_PERSONALIZED) {
      continue;
    }
    base::DictionaryValue* entry = new base::DictionaryValue();
    entry->SetString("title", match.description);
    entry->SetString("displayURL", match.contents);
    entry->SetString("url", match.destination_url.spec());
    suggestions->Append(entry);
  }
}

// static
base::RefCountedMemory* BitpopOptionsUI::GetFaviconResourceBytes(
      ui::ScaleFactor scale_factor) {
  return ui::ResourceBundle::GetSharedInstance().
      LoadDataResourceBytesForScale(IDR_SETTINGS_FAVICON, scale_factor);
}

void BitpopOptionsUI::DidStartProvisionalLoadForFrame(
    int64 frame_id,
    int64 parent_frame_id,
    bool is_main_frame,
    const GURL& validated_url,
    bool is_error_page,
    bool is_iframe_srcdoc,
    content::RenderViewHost* render_view_host) {
  if (render_view_host == web_ui()->GetWebContents()->GetRenderViewHost() &&
      validated_url.host() == chrome::kChromeUIBitpopSettingsFrameHost) {
    for (size_t i = 0; i < handlers_.size(); ++i)
      handlers_[i]->PageLoadStarted();
  }
}

void BitpopOptionsUI::InitializeHandlers() {
  Profile* profile = Profile::FromWebUI(web_ui());
  DCHECK(!profile->IsOffTheRecord() || profile->IsGuestSession());

  // A new web page DOM has been brought up in an existing renderer, causing
  // this method to be called twice. If that happens, ignore the second call.
  if (!initialized_handlers_) {
    for (size_t i = 0; i < handlers_.size(); ++i)
      handlers_[i]->InitializeHandler();
    initialized_handlers_ = true;

#if defined(OS_CHROMEOS)
    pointer_device_observer_->Init();
#endif
  }

#if defined(OS_CHROMEOS)
  pointer_device_observer_->CheckDevices();
#endif

  // Always initialize the page as when handlers are left over we still need to
  // do various things like show/hide sections and send data to the Javascript.
  for (size_t i = 0; i < handlers_.size(); ++i)
    handlers_[i]->InitializePage();

  web_ui()->CallJavascriptFunction(
      "BrowserOptions.notifyInitializationComplete");
}

void BitpopOptionsUI::OnFinishedLoading() {
  on_finished_loading_callbacks_.Notify();
}

void BitpopOptionsUI::AddOptionsPageUIHandler(
    base::DictionaryValue* localized_strings,
    BitpopOptionsPageUIHandler* handler_raw) {
  scoped_ptr<BitpopOptionsPageUIHandler> handler(handler_raw);
  DCHECK(handler.get());
  // Add only if handler's service is enabled.
  if (handler->IsEnabled()) {
    // Add handler to the list and also pass the ownership.
    web_ui()->AddMessageHandler(handler.release());
    handler_raw->GetLocalizedValues(localized_strings);
    handlers_.push_back(handler_raw);
  }
}

}  // namespace options
