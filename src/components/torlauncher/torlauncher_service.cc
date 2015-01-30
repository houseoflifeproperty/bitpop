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

#include <locale>
#include <sstream>
#include <string>
#include <vector>

#include "base/command_line.h"
#include "base/environment.h"
#include "base/files/file.h"
#include "base/files/file_path.h"
#include "base/files/file_util.h"
#include "base/logging.h"
#include "base/path_service.h"
#include "base/prefs/pref_service.h"
#include "base/process/kill.h"
#include "base/process/launch.h"
#include "base/process/process.h"
#include "base/process/process_handle.h"
#include "base/sha1.h"
#include "base/strings/string_number_conversions.h"
#include "base/strings/string_util.h"
#include "base/strings/utf_string_conversions.h"
#include "base/threading/thread_restrictions.h"
#include "components/pref_registry/pref_registry_syncable.h"
#include "components/torlauncher/torlauncher_pref_names.h"
#include "crypto/random.h"
#include "grit/components_strings.h"
#include "ui/base/l10n/l10n_util.h"

namespace {

const int kLogLevelDefault = 4;
const int kLogMethodDefault = 1;
const int kMaxTorLogEntriesDefault = 1000;

const char kControlHostDefault[] = "127.0.0.1";
const int kControlPortDefault = 9151;

const bool kStartTorDefault = true;
const bool kPromptAtStartupDefault = true;
const bool kOnlyConfigureTorDefault = false;

const char kTorPathDefault[] = "";
const char kTorrcPathDefault[] = "";
const char kTorDataDirPathDefault[] = "";

const char kTorControlHostEnv[] = "TOR_CONTROL_HOST";
const char kTorControlPortEnv[] = "TOR_CONTROL_PORT";
const char kTorControlPasswdEnv[] = "TOR_CONTROL_PASSWD";
const char kTorControlCookieAuthFileEnv[] = "TOR_CONTROL_COOKIE_AUTH_FILE";

std::string ToHex(char value, int min_len) {
  std::string rv = base::HexEncode(&value, sizeof(value));
  //while (rv.size() > static_cast<size_t>(min_len))
  //  rv = rv.substr(1);
  while (rv.size() < static_cast<size_t>(min_len))
    rv = "0" + rv;

  return base::StringToLowerASCII(rv);;
}

// Generates a salted hash of <b>secret</b> using the random <b>salt</b>
// according to the iterated and salted S2K algorithm in RFC 2440. <b>c</b>
// is the one-octet coded count value that specifies how much data to hash.
// <b>salt</b> must contain at least 8 bytes, otherwise this method will
// return a default-constructed vector<unsigned char>.
std::vector<unsigned char>
CryptoSecretToKey(const std::string& secret,
                  const std::vector<unsigned char>& salt,
                  uint8_t c)
{
  if (salt.size() < 8)
    return std::vector<unsigned char>();

#define EXPBIAS 6
  int count = ((uint32_t)16 + (c & 15)) << ((c >> 4) + EXPBIAS);
#undef EXPBIAS

  std::vector<unsigned char> to_hash;
  std::vector<unsigned char> tmp(salt.begin(), salt.begin() + 8);
  for (size_t i = 0; i < secret.length(); ++i) {
    tmp.push_back(static_cast<unsigned char>(secret[i]));
  }
  while (count) {
    if (static_cast<size_t>(count) > tmp.size()) {
      to_hash.insert(to_hash.end(), tmp.begin(), tmp.end());
      count -= tmp.size();
    } else {
      to_hash.insert(to_hash.end(), tmp.begin(), tmp.begin() + count);
      count = 0;
    }
  }

  std::vector<unsigned char> hash(base::kSHA1Length);
  base::SHA1HashBytes(&(*to_hash.begin()), to_hash.size(), &(*hash.begin()));
  return hash;
}


std::string ArrayToHex(const std::vector<unsigned char>& array) {
  std::string rv = "";
  if (!array.empty()) {
    for (size_t i = 0; i < array.size(); ++i)
      rv += ToHex(array[i], 2);
  }
  return rv;
}

std::string MapTorFileTypeToString(
    torlauncher::TorLauncherService::TorFileType file_type) {
  switch (file_type) {
    case torlauncher::TorLauncherService::TOR:
      return "tor";
      break;
    case torlauncher::TorLauncherService::TORRC:
      return "torrc";
      break;
    case torlauncher::TorLauncherService::TORRC_DEFAULTS:
      return "torrc-defaults";
      break;
    case torlauncher::TorLauncherService::TOR_DATA_DIR:
      return "tordatadir";
      break;
    default:
      NOTREACHED();
  }
  return "";
}

std::string MapTorFileTypeToPrefName(
    torlauncher::TorLauncherService::TorFileType file_type) {
  std::string tor_file_type_str = MapTorFileTypeToString(file_type);
  return "extensions.torlauncher." + tor_file_type_str + "_path";
}

}

namespace torlauncher {

//static
void TorLauncherService::RegisterProfilePrefs(
    user_prefs::PrefRegistrySyncable* registry) {
  registry->RegisterIntegerPref(pref_names::kLogLevel, kLogLevelDefault,
      user_prefs::PrefRegistrySyncable::UNSYNCABLE_PREF);
  registry->RegisterIntegerPref(pref_names::kLogMethod, kLogMethodDefault,
      user_prefs::PrefRegistrySyncable::UNSYNCABLE_PREF);
  registry->RegisterIntegerPref(pref_names::kMaxTorLogEntries,
      kMaxTorLogEntriesDefault,
      user_prefs::PrefRegistrySyncable::UNSYNCABLE_PREF);

  registry->RegisterStringPref(pref_names::kControlHost,
      std::string(kControlHostDefault),
      user_prefs::PrefRegistrySyncable::UNSYNCABLE_PREF);
  registry->RegisterIntegerPref(pref_names::kControlPort, kControlPortDefault,
      user_prefs::PrefRegistrySyncable::UNSYNCABLE_PREF);

  registry->RegisterBooleanPref(pref_names::kStartTor, kStartTorDefault,
      user_prefs::PrefRegistrySyncable::UNSYNCABLE_PREF);
  registry->RegisterBooleanPref(pref_names::kPromptAtStartup,
      kPromptAtStartupDefault,
      user_prefs::PrefRegistrySyncable::UNSYNCABLE_PREF);
  registry->RegisterBooleanPref(pref_names::kOnlyConfigureTor,
      kOnlyConfigureTorDefault,
      user_prefs::PrefRegistrySyncable::UNSYNCABLE_PREF);

  registry->RegisterStringPref(pref_names::kTorPath,
      std::string(kTorPathDefault),
      user_prefs::PrefRegistrySyncable::UNSYNCABLE_PREF);
  registry->RegisterStringPref(pref_names::kTorrcPath,
      std::string(kTorrcPathDefault),
      user_prefs::PrefRegistrySyncable::UNSYNCABLE_PREF);
  registry->RegisterStringPref(pref_names::kTorDataDirPath,
      std::string(kTorDataDirPathDefault),
      user_prefs::PrefRegistrySyncable::UNSYNCABLE_PREF);

  registry->RegisterStringPref(pref_names::kDefaultBridgeType, std::string(),
      user_prefs::PrefRegistrySyncable::UNSYNCABLE_PREF);
  registry->RegisterStringPref(pref_names::kDefaultBridgeRecommendedType,
      std::string(),
      user_prefs::PrefRegistrySyncable::UNSYNCABLE_PREF);
  registry->RegisterDictionaryPref(pref_names::kDefaultBridge,
      user_prefs::PrefRegistrySyncable::UNSYNCABLE_PREF);
}

TorLauncherService::TorLauncherService(PrefService* browser_prefs)
  : tor_file_base_dir_(""),
    tor_process_status_(UNKNOWN),
    tor_process_(nullptr),
    control_host_(""),
    control_port_(0),
    control_passwd_(""),
    browser_prefs_(browser_prefs) {
  DCHECK(browser_prefs_);

  scoped_ptr<base::Environment> env(base::Environment::Create());

  if (env->HasVar(kTorControlHostEnv)) {
    env->GetVar(kTorControlHostEnv, &control_host_);
  } else {
    control_host_ =
        browser_prefs_->GetString(pref_names::kControlHost);
  }
  if (env->HasVar(kTorControlPortEnv)) {
    std::string s;
    env->GetVar(kTorControlPortEnv, &s);
    int port;
    base::StringToInt(s, &port);
    control_port_ = static_cast<uint16_t>(port);
  } else {
    control_port_ = static_cast<uint16_t>(
        browser_prefs_->GetInteger(pref_names::kControlPort));
  }
  if (env->HasVar(kTorControlPasswdEnv)) {
    env->GetVar(kTorControlPasswdEnv, &control_passwd_);
  } else if (env->HasVar(kTorControlCookieAuthFileEnv)) {
    std::string cookie_path;
    env->GetVar(kTorControlCookieAuthFileEnv, &cookie_path);
    if (!cookie_path.empty()) {
      control_passwd_ = ReadAuthenticationCookie(base::FilePath(
#if defined(OS_WIN)
          base::UTF8ToWide(cookie_path)
#elif defined(OS_MACOSX)
          cookie_path
#endif
      ));
    }
  }
  if (control_passwd_.empty())
    control_passwd_ = GenerateRandomPassword();
}

TorLauncherService::~TorLauncherService() {
  ShutdownTor();
}

std::string TorLauncherService::TorGetPassword(bool please_hash,
                                               std::string* err_msg) {
  std::string pw = this->control_passwd_;
  if (please_hash) {
    char salt[8];
    crypto::RandBytes(&salt[0], 8);
    return HashPassword(pw, salt, err_msg);
  }
  return pw;
}

TorLauncherService::TorStatus TorLauncherService::GetTorProcessStatus() {
  if (tor_process_status_ == RUNNING && tor_process_.get()) {
    base::TerminationStatus status =
        base::GetTerminationStatus(tor_process_->handle(), nullptr);
    if (status != base::TERMINATION_STATUS_STILL_RUNNING)
      tor_process_status_ = EXITED;
  }

  return tor_process_status_;
}

bool TorLauncherService::StartTor(bool disable_network,
                                  StartTorErrorDesc* error_desc) {
  tor_process_status_ = UNKNOWN;

  std::string msg;
  base::FilePath exe_file = GetTorFile(TOR, &msg);
  base::FilePath torrc_file = GetTorFile(TORRC, &msg);
  base::FilePath torrc_defaults_file = GetTorFile(TORRC_DEFAULTS, &msg);
  base::FilePath data_dir = GetTorFile(TOR_DATA_DIR, &msg);
  std::string hashed_password = TorGetPassword(true, &msg);

  std::string details_key;
  if (exe_file.empty())
    details_key = "tor_missing";
  else if (torrc_file.empty())
    details_key = "torrc_missing";
  else if (data_dir.empty())
    details_key = "datadir_missing";
  else if (hashed_password.empty())
    details_key = "password_hash_missing";

  // TODO: make an alert showing with this error message "Unable to start tor"
  if (!details_key.empty()) {
    if (error_desc) {
      error_desc->alert_message_key = "unable_to_start_tor";
      error_desc->alert_message_param_key = details_key;
      error_desc->log_message = msg;
    }
    return false;
  }

  base::FilePath geoip_file = data_dir.Append(FILE_PATH_LITERAL("geoip"));
  base::FilePath geoip6_file = data_dir.Append(FILE_PATH_LITERAL("geoip6"));

  std::vector<std::string> cmd_line;
  cmd_line.push_back(exe_file.value());

  // FIXME: add support for windows strings
  if (!torrc_defaults_file.empty()) {
    cmd_line.push_back("--defaults-torrc");
    cmd_line.push_back(torrc_defaults_file.value());
  }
  cmd_line.push_back("-f");
  cmd_line.push_back(torrc_file.value());
  cmd_line.push_back("DataDirectory");
  cmd_line.push_back(data_dir.value());
  cmd_line.push_back("GeoIPFile");
  cmd_line.push_back(geoip_file.value());
  cmd_line.push_back("GeoIPv6File");
  cmd_line.push_back(geoip6_file.value());
  cmd_line.push_back("HashedControlPassword");
  cmd_line.push_back(hashed_password);

  base::ProcessId pid = base::Process::Current().pid();
  std::ostringstream oss("");
  oss << pid;
  cmd_line.push_back("__OwningControllerProcess");
  cmd_line.push_back(oss.str());

  // TODO: part of code for starting tor with networking disabled was decided to
  // be transferred to javascript part of tor integration. Add the missing
  // code to javascript app.
  if (disable_network) {
    cmd_line.push_back("DisableNetwork");
    cmd_line.push_back("1");
  }

  std::string cl = "";
  for (auto it = cmd_line.begin(); it != cmd_line.end(); it++) {
    cl.append(*it);
    cl.append(" ");
  }
  // TODO: remove this
  DLOG(INFO) << "Tor launch command line: " << cl;

  // On Windows, prepend the Tor program directory to PATH.  This is
  // needed so that pluggable transports can find OpenSSL DLLs, etc.
  // See https://trac.torproject.org/projects/tor/ticket/10845
#if defined(OS_WIN)
  std::string path = base::WideToUTF8(exe_file.DirName().value());

  scoped_ptr<base::Environment> env(base::Environment::Create());
  if (env->HasVar("PATH")) {
    std::string sys_path;
    env->GetVar("PATH", &sys_path);
    path += ";" + sys_path;
  }
  env->SetVar("PATH", path);
#endif

  tor_process_status_ = STARTING;
  if (error_desc)
    error_desc->log_message = "Starting " + cl;

  base::ProcessHandle ph;
  if (base::LaunchProcess(cmd_line, base::LaunchOptions(), &ph)) {
    tor_process_ = make_scoped_ptr(new base::Process(ph));
    tor_process_start_time_ = base::Time::Now();
  } else {
    tor_process_status_ = EXITED;
    // TODO: show alert in javascript code
    if (error_desc) {
      error_desc->alert_message_key = "tor_failed_to_start";
      error_desc->log_message += "\nStartTor() error";
    }
    return false;
  }

  // Successful start
  return true;
} // StartTor()

void TorLauncherService::ShutdownTor() {
  if (tor_process_.get()) {
    if (base::GetTerminationStatus(tor_process_->handle(), nullptr) ==
        base::TERMINATION_STATUS_STILL_RUNNING)
      tor_process_->Terminate(0);
    tor_process_->Close();
    tor_process_.reset();
  }
}
// Returns a file path.
// If file doesn't exist, empty path is returned.
base::FilePath TorLauncherService::GetTorFile(
    TorFileType tor_file_type,
    std::string* error_message) {
  bool is_relative_path = true;

  std::string pref_name = MapTorFileTypeToPrefName(tor_file_type);
  const PrefService::Preference* preference =
      browser_prefs_->FindPreference(pref_name.c_str());
  std::string path_str = "";
  if (preference)
    path_str = browser_prefs_->GetString(pref_name.c_str());

  base::FilePath path;
  if (!path_str.empty()) {
#if defined(OS_WIN)
    std::wstring path_wstr = base::UTF8ToWide(path_str);
    path = base::FilePath(path_wstr);
#elif defined(OS_MACOSX)
    path = base::FilePath(path_str);
#endif
    is_relative_path = !path.IsAbsolute();
  } else {
    // Get default path
    switch (tor_file_type) {
      case TOR:
        path = base::FilePath(FILE_PATH_LITERAL("Tor"));
#if defined(OS_WIN)
        path = path.Append(FILE_PATH_LITERAL("tor.exe"));
#else
        path = path.Append(FILE_PATH_LITERAL("tor"));
#endif
        break;
      case TORRC_DEFAULTS:
        path = base::FilePath(FILE_PATH_LITERAL("Data"));
        path = path.Append(FILE_PATH_LITERAL("Tor"));
        path = path.Append(FILE_PATH_LITERAL("torrc-defaults"));
        break;
      case TORRC:
        path = base::FilePath(FILE_PATH_LITERAL("Data"));
        path = path.Append(FILE_PATH_LITERAL("Tor"));
        path = path.Append(FILE_PATH_LITERAL("torrc"));
        break;
      case TOR_DATA_DIR:
        path = base::FilePath(FILE_PATH_LITERAL("Data"));
        path = path.Append(FILE_PATH_LITERAL("Tor"));
        break;
      default:
        NOTREACHED();
    }
  }

  // impossible case: should have called NOTREACHED beforehand
  if (path.empty()) {
    if (error_message)
      *error_message = ""; // ?
    return base::FilePath();
  }

  if (is_relative_path) {
    // Turn into an absolute path
    if (tor_file_base_dir_.empty()) {
      if (PathService::Get(base::DIR_EXE, &tor_file_base_dir_)) {
        // FIXME: add actual path to Tor file base by modifying tor_file_base_dir_ or appending to it
#if defined(OS_WIN)
#elif defined(OS_MACOSX)
        tor_file_base_dir_ =
            tor_file_base_dir_.DirName().DirName().Append("TorBrowser");
#endif
      } else {
        if (error_message)
          *error_message =
              l10n_util::GetStringFUTF8(
                  IDS_TORLAUNCHER_ERR_FAILED_TO_FIND_REQUIRED_PATH,
                  base::UTF8ToUTF16(MapTorFileTypeToString(tor_file_type)));
        return base::FilePath();
      }
    }
    path = tor_file_base_dir_.Append(path);
  }

  base::ThreadRestrictions::ScopedAllowIO allow_io;

  if (base::PathExists(path))
    return path;

  if (error_message)
    *error_message = l10n_util::GetStringFUTF8(
                       IDS_TORLAUNCHER_ERR_TOR_BUNDLE_FILE_NOT_FOUND,
#if defined(OS_WIN)
                       base::WideToUTF16(path.value())
#elif defined(OS_MACOSX)
                       base::UTF8ToUTF16(path.value())
#endif
                       );

  return base::FilePath();
} // GetTorFile()

std::string TorLauncherService::ReadAuthenticationCookie(
    const base::FilePath& path) {

  const long long kMaxBytesToRead = 32;

  base::ThreadRestrictions::ScopedAllowIO allow_io;

  base::File file(path, base::File::FLAG_OPEN | base::File::FLAG_READ);
  // Limit the buffer size to avoid memory excessive usage as a result
  // of malicious user changing the cookie file path environment variable.
  int buf_size = std::min(file.GetLength(), kMaxBytesToRead);
  scoped_ptr<char[]> data(new char[buf_size]);
  if (!data.get())
    return "";

  int file_res = file.ReadAtCurrentPos(data.get(), buf_size);
  std::string result = "";
  if (file_res != -1) {
    for (int i = 0; i < file_res; ++i)
      result += ToHex(data[i], 2);
  }

  return result;
}

// Returns a random 16 character password, hex-encoded.
std::string TorLauncherService::GenerateRandomPassword() {
  // Similar to Vidalia's crypto_rand_string().
  const int kPasswordLen = 16;
  const char kMinCharCode = '!';
  const char kMaxCharCode = '~';
  std::string pwd = "";
  for (int i = 0; i < kPasswordLen; ++i) {
    unsigned int val = 0;
    crypto::RandBytes(&val, sizeof(val));
    val %= kMaxCharCode - kMinCharCode + 1;
    val += kMinCharCode;
    pwd += ToHex(val, 2);
  }

  return pwd;
}

// Based on Vidalia's TorSettings::hashPassword().
std::string TorLauncherService::HashPassword(const std::string& hex_password,
                                             const char salt[8],
                                             std::string* err_msg) {
  if (hex_password.empty())
    return std::string();

  // We need a vector<int> for salt value. So initialize it here.
  std::vector<unsigned char> salt_v;
  for (int i = 0; i < 8; ++i) {
    salt_v.push_back(static_cast<unsigned char>(salt[i]));
  }

  int len = hex_password.size() / 2;
  std::string password;
  int val_to_push = 0;
  for (int i = 0; i < len; ++i) {
    base::HexStringToInt(hex_password.substr(i * 2, 2), &val_to_push);
    password.push_back(static_cast<char>(val_to_push));
  }

  // Run through the S2K algorithm and convert to a string.
  const int kCodedCount = 96;
  auto hash_val = CryptoSecretToKey(password, salt_v, kCodedCount);
  if (hash_val.empty()) {
    if (err_msg)
      *err_msg = "CryptoSecretToKey() failed";
    return std::string();
  }

  std::string rv = "16:";
  rv += ArrayToHex(salt_v);
  rv += ToHex(static_cast<char>(kCodedCount), 2);
  rv += ArrayToHex(hash_val);

  return rv;
}  // HashPassword()

} // namespace torlauncher
