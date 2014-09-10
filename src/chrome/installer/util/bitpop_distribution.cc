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


#include "chrome/installer/util/bitpop_distribution.h"

#include <windows.h>
#include <msi.h>

#include "base/files/file_path.h"
#include "base/path_service.h"
#include "base/strings/string_util.h"
#include "base/strings/stringprintf.h"
#include "base/strings/utf_string_conversions.h"
#include "base/win/registry.h"
#include "base/win/windows_version.h"
#include "chrome/common/chrome_icon_resources_win.h"
#include "chrome/common/net/test_server_locations.h"
#include "chrome/installer/util/channel_info.h"
#include "chrome/installer/util/google_update_constants.h"
#include "chrome/installer/util/google_update_settings.h"
#include "chrome/installer/util/helper.h"
#include "chrome/installer/util/install_util.h"
#include "chrome/installer/util/l10n_string_util.h"
#include "chrome/installer/util/uninstall_metrics.h"
#include "chrome/installer/util/util_constants.h"
#include "chrome/installer/util/wmi.h"
#include "content/public/common/result_codes.h"

#include "installer_util_strings.h"  // NOLINT

namespace {

const wchar_t kChromeGuid[] = L"{5B73C40A-84CA-406C-B1FD-5863DA4A41EE}";
const wchar_t kBrowserAppId[] = L"BitPop";
const wchar_t kBrowserProgIdPrefix[] = L"BitPopHTML";
const wchar_t kBrowserProgIdDesc[] = L"BitPop HTML Document";
const wchar_t kCommandExecuteImplUuid[] =
    L"{45F07275-4EEA-47AD-A356-755AED238AAD}";
    
}  // namespace

BitpopDistribution::BitpopDistribution()
    : BrowserDistribution(CHROME_BROWSER),
      product_guid_(kChromeGuid) {
}

void BitpopDistribution::DoPostUninstallOperations(
    const Version& version,
    const base::FilePath& local_data_path,
    const base::string16& distribution_data) {
}

base::string16 BitpopDistribution::GetActiveSetupGuid() {
  return product_guid();
}

base::string16 BitpopDistribution::GetAppGuid() {
  return product_guid();
}

base::string16 BitpopDistribution::GetBaseAppName() {
  // I'd really like to return L ## PRODUCT_FULLNAME_STRING; but that's no good
  // since it'd be "Chromium" in a non-Chrome build, which isn't at all what I
  // want.  Sigh.
  return L"BitPop";
}

base::string16 BitpopDistribution::GetShortcutName(
    ShortcutType shortcut_type) {
  int string_id = IDS_PRODUCT_NAME_BASE;
  switch (shortcut_type) {
    case SHORTCUT_CHROME_ALTERNATE:
      string_id = IDS_OEM_MAIN_SHORTCUT_NAME_BASE;
      break;
    case SHORTCUT_APP_LAUNCHER:
      string_id = IDS_APP_LIST_SHORTCUT_NAME_BASE;
      break;
    default:
      DCHECK_EQ(shortcut_type, SHORTCUT_CHROME);
      break;
  }
  return installer::GetLocalizedString(string_id);
}

int BitpopDistribution::GetIconIndex(ShortcutType shortcut_type) {
  if (shortcut_type == SHORTCUT_APP_LAUNCHER)
    return icon_resources::kAppLauncherIndex;
  DCHECK(shortcut_type == SHORTCUT_CHROME ||
         shortcut_type == SHORTCUT_CHROME_ALTERNATE) << shortcut_type;
  return icon_resources::kApplicationIndex;
}

base::string16 BitpopDistribution::GetBaseAppId() {
  return kBrowserAppId;
}

base::string16 BitpopDistribution::GetBrowserProgIdPrefix() {
  return kBrowserProgIdPrefix;
}

base::string16 BitpopDistribution::GetBrowserProgIdDesc() {
  return kBrowserProgIdDesc;
}

base::string16 BitpopDistribution::GetInstallSubDir() {
  return L"BitPop";
}

base::string16 BitpopDistribution::GetPublisherName() {
  const base::string16& publisher_name =
      installer::GetLocalizedString(IDS_ABOUT_VERSION_COMPANY_NAME_BASE);
  return publisher_name;
}

base::string16 BitpopDistribution::GetAppDescription() {
  const base::string16& app_description =
      installer::GetLocalizedString(IDS_SHORTCUT_TOOLTIP_BASE);
  return app_description;
}

std::string BitpopDistribution::GetSafeBrowsingName() {
  return "bitpop";
}

base::string16 BitpopDistribution::GetStateKey() {
  base::string16 key(google_update::kRegPathClientState);
  key.append(L"\\");
  key.append(product_guid());
  return key;
}

base::string16 BitpopDistribution::GetStateMediumKey() {
  base::string16 key(google_update::kRegPathClientStateMedium);
  key.append(L"\\");
  key.append(product_guid());
  return key;
}

std::string BitpopDistribution::GetNetworkStatsServer() const {
  return chrome_common_net::kEchoTestServerLocation;
}

std::string BitpopDistribution::GetHttpPipeliningTestServer() const {
  return chrome_common_net::kPipelineTestServerBaseUrl;
}

base::string16 BitpopDistribution::GetDistributionData(HKEY root_key) {
  base::string16 sub_key(google_update::kRegPathClientState);
  sub_key.append(L"\\");
  sub_key.append(product_guid());

  base::win::RegKey client_state_key(root_key, sub_key.c_str(), KEY_READ);
  base::string16 result;
  base::string16 brand_value;
  if (client_state_key.ReadValue(google_update::kRegRLZBrandField,
                                 &brand_value) == ERROR_SUCCESS) {
    result = google_update::kRegRLZBrandField;
    result.append(L"=");
    result.append(brand_value);
    result.append(L"&");
  }

  base::string16 client_value;
  if (client_state_key.ReadValue(google_update::kRegClientField,
                                 &client_value) == ERROR_SUCCESS) {
    result.append(google_update::kRegClientField);
    result.append(L"=");
    result.append(client_value);
    result.append(L"&");
  }

  base::string16 ap_value;
  // If we fail to read the ap key, send up "&ap=" anyway to indicate
  // that this was probably a stable channel release.
  client_state_key.ReadValue(google_update::kRegApField, &ap_value);
  result.append(google_update::kRegApField);
  result.append(L"=");
  result.append(ap_value);

  return result;
}

base::string16 BitpopDistribution::GetUninstallLinkName() {
  const base::string16& link_name =
      installer::GetLocalizedString(IDS_UNINSTALL_CHROME_BASE);
  return link_name;
}

base::string16 BitpopDistribution::GetUninstallRegPath() {
  return L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\"
         L"BitPop";
}

base::string16 BitpopDistribution::GetVersionKey() {
  base::string16 key(google_update::kRegPathClients);
  key.append(L"\\");
  key.append(product_guid());
  return key;
}

base::string16 BitpopDistribution::GetIconFilename() {
  return installer::kChromeExe;
}

bool BitpopDistribution::GetCommandExecuteImplClsid(
    base::string16* handler_class_uuid) {
  if (handler_class_uuid)
    *handler_class_uuid = kCommandExecuteImplUuid;
  return true;
}

bool BitpopDistribution::AppHostIsSupported() {
  return true;
}

// This method checks if we need to change "ap" key in Google Update to try
// full installer as fall back method in case incremental installer fails.
// - If incremental installer fails we append a magic string ("-full"), if
// it is not present already, so that Google Update server next time will send
// full installer to update Chrome on the local machine
// - If we are currently running full installer, we remove this magic
// string (if it is present) regardless of whether installer failed or not.
// There is no fall-back for full installer :)
void BitpopDistribution::UpdateInstallStatus(bool system_install,
    installer::ArchiveType archive_type,
    installer::InstallStatus install_status) {
  GoogleUpdateSettings::UpdateInstallStatus(system_install,
      archive_type, InstallUtil::GetInstallReturnCode(install_status),
      product_guid());
}

bool BitpopDistribution::ShouldSetExperimentLabels() {
  return false;
}

bool BitpopDistribution::HasUserExperiments() {
  return false;
}
