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

#include "components/torlauncher/torlauncher_service.h"

#include <stdint.h>

#include "base/environment.h"
#include "base/files/file_path.h"
#include "base/memory/scoped_ptr.h"
#include "base/process/kill.h"
#include "base/process/process.h"
#include "base/strings/string_util.h"
#include "base/test/test_timeouts.h"
#include "components/pref_registry/testing_pref_service_syncable.h"
#include "components/torlauncher/torlauncher_pref_names.h"
#include "testing/gtest/include/gtest/gtest.h"

namespace {

const char kTorControlHostEnv[] = "TOR_CONTROL_HOST";
const char kTorControlPortEnv[] = "TOR_CONTROL_PORT";
const char kTorControlPasswdEnv[] = "TOR_CONTROL_PASSWD";
const char kTorControlCookieAuthFileEnv[] = "TOR_CONTROL_COOKIE_AUTH_FILE";

}

namespace torlauncher {

class TorLauncherServiceTest : public testing::Test {
 public:
 protected:
  TorLauncherServiceTest()
    : pref_service_(new user_prefs::TestingPrefServiceSyncable) {}

  virtual ~TorLauncherServiceTest() {}

  virtual void SetUp() OVERRIDE {
    TorLauncherService::RegisterProfilePrefs(pref_service_->registry());
  }

  user_prefs::TestingPrefServiceSyncable* pref_service() {
    return pref_service_.get();
  }

  TorLauncherService* CreateTorLauncherService() {
    return new TorLauncherService(pref_service_.get());
  }

 protected:
  scoped_ptr<user_prefs::TestingPrefServiceSyncable> pref_service_;
};

TEST_F(TorLauncherServiceTest, InitSuccess) {
  scoped_ptr<base::Environment> env(base::Environment::Create());

  env->UnSetVar(kTorControlHostEnv);
  env->UnSetVar(kTorControlPortEnv);
  env->UnSetVar(kTorControlPasswdEnv);
  env->UnSetVar(kTorControlCookieAuthFileEnv);

  scoped_ptr<TorLauncherService> service(CreateTorLauncherService());
  EXPECT_TRUE(service != NULL);

  EXPECT_EQ(service->GetTorProcessStatus(), TorLauncherService::UNKNOWN);

  EXPECT_FALSE(service->control_host().empty());
  EXPECT_TRUE(service->control_port() > 0);
  EXPECT_FALSE(service->control_passwd().empty());
}

TEST_F(TorLauncherServiceTest, EnvVars) {
  scoped_ptr<base::Environment> env(base::Environment::Create());

  const char kHost1[] = "10.0.0.1";
  const char kPort1[] = "1234";

  // must be the exact value of kPort1
  const uint16_t kPort1UInt16Value = 1234;

  // kPasswd1 and kPasswd2 MUST differ
  const char kPasswd1[] = "passwd";
  // Should contain 32 bytes
  const char kPasswd2[] =
      "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f";

#if defined(OS_WIN)
  const char kCookieFile1[] = "torlauncher\\cookie1.bin";
  const char kCookieFile2[] = "torlauncher\\cookie2.bin";
#else
  const char kCookieFile1[] = "torlauncher/cookie1.bin";
  const char kCookieFile2[] = "torlauncher/cookie2.bin";
#endif

  env->SetVar(kTorControlHostEnv, std::string(kHost1));
  env->SetVar(kTorControlPortEnv, std::string(kPort1));

  env->SetVar(kTorControlPasswdEnv, std::string(kPasswd1));
  env->SetVar(kTorControlCookieAuthFileEnv, std::string(kCookieFile1));

  {
    scoped_ptr<TorLauncherService> service(CreateTorLauncherService());
    EXPECT_TRUE(service != NULL);

    EXPECT_EQ(service->control_host(), std::string(kHost1));
    EXPECT_EQ(service->control_port(), kPort1UInt16Value);
    EXPECT_EQ(service->control_passwd(), kPasswd1);
  }

  // To check the password loading from auth cookie file
  // we need to clear the passwd env var first, so that service doesn't load
  // passwd data from passwd env var.
  env->UnSetVar(kTorControlPasswdEnv);
  {
    scoped_ptr<TorLauncherService> service(CreateTorLauncherService());
    EXPECT_TRUE(service != NULL);

    EXPECT_EQ(service->control_passwd(), std::string(kPasswd2));
  }

  // Check the limitation for the password length which can be read from
  // auth cookie file
  // kCookieFile2 is larger than 32 bytes and kPasswd2 is exactly 32 bytes
  env->SetVar(kTorControlCookieAuthFileEnv, std::string(kCookieFile2));
  {
    scoped_ptr<TorLauncherService> service(CreateTorLauncherService());
    EXPECT_TRUE(service != NULL);

    EXPECT_EQ(service->control_passwd(), std::string(kPasswd2));
  }

  env->UnSetVar(kTorControlHostEnv);
  env->UnSetVar(kTorControlPortEnv);
  env->UnSetVar(kTorControlPasswdEnv);
  env->UnSetVar(kTorControlCookieAuthFileEnv);
}

TEST_F(TorLauncherServiceTest, Prefs) {
  scoped_ptr<base::Environment> env(base::Environment::Create());

  env->UnSetVar(kTorControlHostEnv);
  env->UnSetVar(kTorControlPortEnv);
  env->UnSetVar(kTorControlPasswdEnv);
  env->UnSetVar(kTorControlCookieAuthFileEnv);

  const char kControlHostDefault[] = "127.0.0.1";
  const uint16_t kControlPortDefault = 9151;

  const char kControlHost2[] = "10.0.0.1";
  const uint16_t kControlPort2 = 123;

  {
    scoped_ptr<TorLauncherService> service(CreateTorLauncherService());
    EXPECT_TRUE(service != NULL);

    EXPECT_EQ(service->control_host(), std::string(kControlHostDefault));
    EXPECT_EQ(service->control_port(), kControlPortDefault);
  }

  pref_service()->SetString(pref_names::kControlHost, kControlHost2);
  pref_service()->SetInteger(pref_names::kControlPort,
                             static_cast<int>(kControlPort2));
  {
    scoped_ptr<TorLauncherService> service(CreateTorLauncherService());
    EXPECT_TRUE(service != NULL);

    EXPECT_EQ(service->control_host(), std::string(kControlHost2));
    EXPECT_EQ(service->control_port(), kControlPort2);
  }
}

TEST_F(TorLauncherServiceTest, TorGetPassword) {
  scoped_ptr<TorLauncherService> service(CreateTorLauncherService());
  EXPECT_TRUE(service != NULL);

  std::string rnd_pw = service->GenerateRandomPassword();
  EXPECT_EQ(rnd_pw.length(), static_cast<size_t>(32));
  for (size_t i = 0; i < rnd_pw.length(); ++i) {
    EXPECT_TRUE(IsHexDigit(rnd_pw[i]));
  }

  char salt[8] = { 0x33, 0x9E, 0x10, 0x73, 0xCA, 0x36, 0x26, 0x9D };
  std::string err_msg;
  std::string hashed_pw =
      service->HashPassword("3322693f6e4f6b2a2536736b4429343f",
                            salt,
                            &err_msg);
  EXPECT_EQ(hashed_pw,
      std::string(
          "16:339e1073ca36269d6014964b08e1e13b08564e3957806999cd3435acdd"
      ));
  EXPECT_TRUE(err_msg.empty());
}

TEST_F(TorLauncherServiceTest, GetTorFiles) {
  scoped_ptr<TorLauncherService> service(CreateTorLauncherService());
  EXPECT_TRUE(service != NULL);

  service->tor_file_base_dir_ =
      base::FilePath(FILE_PATH_LITERAL("torlauncher/"));
  std::string err_msg;
  base::FilePath path1 = service->GetTorFile(TorLauncherService::TOR,
                                             &err_msg);
  EXPECT_TRUE(!path1.empty());
  EXPECT_TRUE(err_msg.empty());
  base::FilePath path2 = service->GetTorFile(TorLauncherService::TORRC,
                                             &err_msg);
  EXPECT_TRUE(!path2.empty());
  EXPECT_TRUE(err_msg.empty());
  base::FilePath path3 = service->GetTorFile(TorLauncherService::TORRC_DEFAULTS,
                                             &err_msg);
  EXPECT_TRUE(!path3.empty());
  EXPECT_TRUE(err_msg.empty());
  base::FilePath path4 = service->GetTorFile(TorLauncherService::TOR_DATA_DIR,
                                             &err_msg);
  EXPECT_TRUE(!path4.empty());
  EXPECT_TRUE(err_msg.empty());

  // invert the condition by using the wrong base dir for tor files
  service->tor_file_base_dir_ = base::FilePath(FILE_PATH_LITERAL("./"));
  path1 = service->GetTorFile(TorLauncherService::TOR,
                              &err_msg);
  EXPECT_FALSE(!path1.empty());
  EXPECT_FALSE(err_msg.empty());
  path2 = service->GetTorFile(TorLauncherService::TORRC,
                              &err_msg);
  EXPECT_FALSE(!path2.empty());
  EXPECT_FALSE(err_msg.empty());
  path3 = service->GetTorFile(TorLauncherService::TORRC_DEFAULTS,
                              &err_msg);
  EXPECT_FALSE(!path3.empty());
  EXPECT_FALSE(err_msg.empty());
  path4 = service->GetTorFile(TorLauncherService::TOR_DATA_DIR,
                              &err_msg);
  EXPECT_FALSE(!path4.empty());
  EXPECT_FALSE(err_msg.empty());
}

TEST_F(TorLauncherServiceTest, StartTor) {
  scoped_ptr<base::Environment> env(base::Environment::Create());

  env->UnSetVar(kTorControlHostEnv);
  env->UnSetVar(kTorControlPortEnv);
  env->UnSetVar(kTorControlPasswdEnv);
  env->UnSetVar(kTorControlCookieAuthFileEnv);

  // begin new scope tor release the service pointer in the end of this
  {
    scoped_ptr<TorLauncherService> service(CreateTorLauncherService());
    EXPECT_TRUE(service != NULL);

    EXPECT_EQ(service->GetTorProcessStatus(), TorLauncherService::UNKNOWN);

    // set the path to test data directory
    service->tor_file_base_dir_ =
        base::FilePath(FILE_PATH_LITERAL("torlauncher/"));
    TorLauncherService::StartTorErrorDesc error_desc;
    // Start Tor with network disabled
    bool success = service->StartTor(true, &error_desc);
    EXPECT_TRUE(success);
    EXPECT_TRUE(error_desc.alert_message_key.empty() &&
                error_desc.alert_message_param_key.empty());
    EXPECT_EQ(service->GetTorProcessStatus(), TorLauncherService::STARTING);
    EXPECT_TRUE(service->tor_process_.get() != NULL);
    EXPECT_FALSE(service->tor_process_start_time().is_null());

    service->set_tor_status_running();
    EXPECT_EQ(service->GetTorProcessStatus(), TorLauncherService::RUNNING);

    service->tor_process_->Terminate(0);

    // Wait for 500 milliseconds
    base::Time time_start = base::Time::Now();
    while ((base::Time::Now() - time_start).InMilliseconds() < 500)
      ;

    EXPECT_EQ(service->GetTorProcessStatus(), TorLauncherService::EXITED);
  }

  {
    scoped_ptr<TorLauncherService> service(CreateTorLauncherService());
    EXPECT_TRUE(service != NULL);

    EXPECT_EQ(service->GetTorProcessStatus(), TorLauncherService::UNKNOWN);

    // set the path to non-existing directory as a base for tor files
    service->tor_file_base_dir_ =
        base::FilePath(FILE_PATH_LITERAL("non-existing/"));
    TorLauncherService::StartTorErrorDesc error_desc;
    // Start Tor with network disabled
    bool success = service->StartTor(true, &error_desc);
    EXPECT_FALSE(success);
    EXPECT_FALSE(error_desc.alert_message_key.empty() &&
                 error_desc.alert_message_param_key.empty());
    EXPECT_EQ(service->GetTorProcessStatus(), TorLauncherService::UNKNOWN);
    EXPECT_FALSE(service->tor_process_.get() != NULL);
    EXPECT_TRUE(service->tor_process_start_time().is_null());

    service->set_tor_status_running();
    EXPECT_EQ(service->GetTorProcessStatus(), TorLauncherService::UNKNOWN);
  }
}

}  // namespace torlauncher
