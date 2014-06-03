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

//#include "base/command_line.h"
//#include "base/file_path.h"
//#include "base/memory/scoped_ptr.h"
//#include "base/path_service.h"
//#include "base/rand_util.h"
#include "base/string_split.h"
#include "base/string_number_conversions.h"
#include "base/string_util.h"
#include "base/utf_string_conversions.h"
//#include "base/win/registry.h"
//#include "base/win/windows_version.h"
//#include "chrome/common/attrition_experiments.h"
//#include "chrome/common/chrome_switches.h"
//#include "chrome/common/pref_names.h"
//#include "chrome/installer/util/channel_info.h"
//#include "chrome/installer/util/product.h"
#include "chrome/installer/util/install_util.h"
#include "chrome/installer/util/l10n_string_util.h"
#include "chrome/installer/util/google_update_constants.h"
#include "chrome/installer/util/google_update_settings.h"
#include "chrome/installer/util/helper.h"
#include "chrome/installer/util/util_constants.h"
//#include "chrome/installer/util/wmi.h"
//#include "content/common/json_value_serializer.h"
#include "content/public/common/result_codes.h"

namespace {

const wchar_t kChromeGuid[] = L"{5B73C40A-84CA-406C-B1FD-5863DA4A41EE}";
const wchar_t kBrowserAppId[] = L"BitPop";

}  // namespace

BitpopDistribution::BitpopDistribution()
    : BrowserDistribution(CHROME_BROWSER),
      product_guid_(kChromeGuid) {
}

std::wstring BitpopDistribution::GetAppGuid() {
  return product_guid();
}

std::wstring BitpopDistribution::GetBaseAppName() {
  return L"BitPop";
}

std::wstring BitpopDistribution::GetAlternateApplicationName() {
  return L"The Internet";
}

std::wstring BitpopDistribution::GetBaseAppId() {
  return kBrowserAppId;
}

std::wstring BitpopDistribution::GetInstallSubDir() {
  return L"BitPop";
}

std::wstring BitpopDistribution::GetPublisherName() {
  return L"House of Life";
}

std::wstring BitpopDistribution::GetAppDescription() {
  return L"Browse the web";
}

std::string BitpopDistribution::GetSafeBrowsingName() {
  return "bitpop";
}

std::wstring BitpopDistribution::GetStateKey() {
  std::wstring key(google_update::kRegPathClientState);
  key.append(L"\\");
  key.append(product_guid());
  return key;
}

std::wstring BitpopDistribution::GetStateMediumKey() {
  std::wstring key(google_update::kRegPathClientStateMedium);
  key.append(L"\\");
  key.append(product_guid());
  return key;
}

std::wstring BitpopDistribution::GetStatsServerURL() {
  return L"";
}

//std::string BitpopDistribution::GetNetworkStatsServer() const {
//  return "";
//}

std::wstring BitpopDistribution::GetDistributionData(HKEY root_key) {
  return L"";
}

std::wstring BitpopDistribution::GetUninstallLinkName() {
  return L"Uninstall BitPop";
}

std::wstring BitpopDistribution::GetUninstallRegPath() {
  return L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\"
         L"BitPop";
}

std::wstring BitpopDistribution::GetVersionKey() {
  std::wstring key(google_update::kRegPathClients);
  key.append(L"\\");
  key.append(product_guid());
  return key;
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
