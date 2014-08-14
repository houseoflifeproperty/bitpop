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

#ifndef CHROME_INSTALLER_UTIL_BITPOP_DISTRIBUTION_H_
#define CHROME_INSTALLER_UTIL_BITPOP_DISTRIBUTION_H_
#pragma once

#include <string>

#include "base/gtest_prod_util.h"
#include "chrome/installer/util/browser_distribution.h"
#include "chrome/installer/util/util_constants.h"

class DictionaryValue;
class FilePath;

class BitpopDistribution : public BrowserDistribution {
 public:
  virtual std::wstring GetAppGuid() OVERRIDE;

  virtual std::wstring GetBaseAppName() OVERRIDE;

  virtual std::wstring GetAlternateApplicationName() OVERRIDE;

  virtual std::wstring GetBaseAppId() OVERRIDE;

  virtual std::wstring GetInstallSubDir() OVERRIDE;

  virtual std::wstring GetPublisherName() OVERRIDE;

  virtual std::wstring GetAppDescription() OVERRIDE;

  virtual std::string GetSafeBrowsingName() OVERRIDE;

  virtual std::wstring GetStateKey() OVERRIDE;

  virtual std::wstring GetStateMediumKey() OVERRIDE;

  virtual std::wstring GetStatsServerURL() OVERRIDE;

  //virtual std::string GetNetworkStatsServer() const OVERRIDE;

  // This method reads data from the Google Update ClientState key for
  // potential use in the uninstall survey. It must be called before the
  // key returned by GetVersionKey() is deleted.
  virtual std::wstring GetDistributionData(HKEY root_key) OVERRIDE;

  virtual std::wstring GetUninstallLinkName() OVERRIDE;

  virtual std::wstring GetUninstallRegPath() OVERRIDE;

  virtual std::wstring GetVersionKey() OVERRIDE;

  virtual void UpdateInstallStatus(
      bool system_install,
      installer::ArchiveType archive_type,
      installer::InstallStatus install_status) OVERRIDE;

  const std::wstring& product_guid() { return product_guid_; }

 protected:
  void set_product_guid(const std::wstring& guid) { product_guid_ = guid; }

  // Disallow construction from others.
  BitpopDistribution();

 private:
  friend class BrowserDistribution;

  // The product ID for Google Update.
  std::wstring product_guid_;
};

#endif  // CHROME_INSTALLER_UTIL_BITPOP_DISTRIBUTION_H_
