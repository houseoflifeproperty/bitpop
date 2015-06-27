// BitPop browser. Tor Launcher integration part.
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

#ifndef COMPONENTS_TORLAUNCHER_TORLAUNCHER_SERVICE_H_
#define COMPONENTS_TORLAUNCHER_TORLAUNCHER_SERVICE_H_

#include <stdint.h>
#include <string>

#include "base/files/file_path.h"
#include "base/gtest_prod_util.h"
#include "base/memory/scoped_ptr.h"
#include "base/time/time.h"
#include "components/keyed_service/core/keyed_service.h"
#include "content/public/browser/notification_observer.h"
#include "content/public/browser/notification_registrar.h"

class PrefService;
class Profile;

namespace base {
class Process;
}

namespace user_prefs {
class PrefRegistrySyncable;
}  // namespace user_prefs

namespace torlauncher {

class TorLauncherService : public KeyedService,
                           public content::NotificationObserver {
 public:
  enum TorFileType {
    TOR = 0,
    TORRC,
    TORRC_DEFAULTS,
    TOR_DATA_DIR
  };

  enum TorStatus {
    UNKNOWN = 0,
    STARTING,
    RUNNING,
    EXITED
  };

  TorLauncherService(Profile *profile);
  virtual ~TorLauncherService();

  // data accessors
  std::string control_host() const { return control_host_; }
  uint16_t control_port() const { return control_port_; }
  std::string control_passwd() const { return control_passwd_; }
  base::Time tor_process_start_time() const { return tor_process_start_time_; }
  bool tor_circuits_established() const { return tor_circuits_established_; }

  // Called when network connection with Tor client can be established.
  void set_tor_status_running() {
    // only allow switch of state from STARTING as a current state
    if (tor_process_status_ == STARTING)
      tor_process_status_ = RUNNING;
  }

  // Register TorLauncherService related prefs in the Profile prefs.
  static void RegisterProfilePrefs(user_prefs::PrefRegistrySyncable* registry);

  // Returns the Tor connection password and (optionally) an error message.
  // Set please_hash param to 'true' to get the hashed version of the pass.
  std::string TorGetPassword(bool please_hash, std::string* err_msg);

  // Returns (and possibly updates) status of Tor process
  TorStatus GetTorProcessStatus();

  // Error info for StartTor() method
  struct StartTorErrorDesc {
    std::string alert_message_key;
    std::string alert_message_param_key;
    std::string log_message;
  };

  // Starts the Tor process
  // Returns 'false' on failure.
  // Use error_desc out param to get additional info about launch process or
  // error description.
  bool StartTor(bool disable_network, StartTorErrorDesc* error_desc);

  void ShutdownTor();

  // NotificationObserver overrides
  virtual void Observe(int type,
                     const content::NotificationSource& source,
                     const content::NotificationDetails& details) override;
 private:
  friend class TorLauncherServiceTest;
  FRIEND_TEST_ALL_PREFIXES(TorLauncherServiceTest, GetTorFiles);
  FRIEND_TEST_ALL_PREFIXES(TorLauncherServiceTest, TorGetPassword);
  FRIEND_TEST_ALL_PREFIXES(TorLauncherServiceTest, StartTor);

  // Returns a file path.
  // If file doesn't exist, empty FilePath is returned.
  base::FilePath GetTorFile(TorFileType tor_file_type,
                            std::string* error_message);

  std::string ReadAuthenticationCookie(const base::FilePath& path);

  // Returns a random 16 character password, hex-encoded.
  std::string GenerateRandomPassword();

  // Based on Vidalia's TorSettings::hashPassword().
  std::string HashPassword(const std::string& hex_password,
                           const char salt[8],
                           std::string* err_msg);

  void SetTorOpenControlConnectionSuccess();
  void SetTorCircuitsEstablished(bool established);

  Profile* profile_;
  base::FilePath tor_file_base_dir_;
  TorStatus tor_process_status_;

  scoped_ptr<base::Process> tor_process_;
  base::Time tor_process_start_time_;

  std::string control_host_;
  uint16_t control_port_;
    std::string control_passwd_;

  PrefService* browser_prefs_;

  bool tor_circuits_established_;

  content::NotificationRegistrar registrar_;

  DISALLOW_COPY_AND_ASSIGN(TorLauncherService);
};

}

#endif // COMPONENTS_TORLAUNCHER_TORLAUNCHER_SERVICE_H_
