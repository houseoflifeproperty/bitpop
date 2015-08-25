// BitPop browser. Facebook chat integration part.
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

#include "chrome/browser/extensions/api/torlauncher/torlauncher_api.h"

#include <string>
#include <vector>

#include "base/command_line.h"
#include "base/environment.h"
#include "base/files/file.h"
#include "base/files/file_path.h"
#include "base/json/json_reader.h"
#include "base/logging.h"
#include "base/memory/scoped_ptr.h"
#include "base/path_service.h"
#include "base/prefs/pref_service.h"
#include "base/process/launch.h"
#include "base/strings/string_number_conversions.h"
#include "base/values.h"
#include "chrome/browser/chrome_notification_types.h"
#include "chrome/browser/lifetime/application_lifetime.h"
#include "chrome/browser/prefs/proxy_config_dictionary.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/torlauncher/torlauncher_service_factory.h"
#include "chrome/browser/ui/browser_commands.h"
#include "chrome/browser/ui/browser_finder.h"
#include "chrome/browser/ui/browser_navigator.h"
#include "chrome/common/chrome_paths.h"
#include "chrome/common/chrome_switches.h"
#include "chrome/common/extensions/api/torlauncher.h"
#include "chrome/common/pref_names.h"
#include "chrome/common/url_constants.h"
#include "components/torlauncher/torlauncher_service.h"
#include "content/public/browser/notification_details.h"
#include "content/public/browser/notification_service.h"
#include "content/public/browser/notification_source.h"
#include "extensions/common/switches.h"

#if defined(OS_MACOSX)
#include "chrome/browser/chrome_browser_application_mac.h"
#endif

namespace extensions {

ExtensionFunction::ResponseAction TorlauncherLaunchTorBrowserFunction::Run() {
  scoped_ptr<api::torlauncher::LaunchTorBrowser::Params> params(
      api::torlauncher::LaunchTorBrowser::Params::Create(*args_));
  EXTENSION_FUNCTION_VALIDATE(params.get());

  bool open_tor_settings = false;
  if (params->options.get() && params->options->open_tor_settings.get())
    open_tor_settings = *params->options->open_tor_settings;

  //Profile* profile = Profile::FromBrowserContext(browser_context());

  Browser* browser = chrome::FindLastActiveWithHostDesktopType(
      chrome::HOST_DESKTOP_TYPE_NATIVE);
  Profile* profile = browser->profile();

  if (base::CommandLine::ForCurrentProcess()->HasSwitch(
          ::switches::kLaunchTorBrowser)) {
    if (open_tor_settings) {
      chrome::NavigateParams params(
          profile,
          GURL("chrome://chrome/tor-settings/"),
          ui::PAGE_TRANSITION_LINK);
      chrome::Navigate(&params);
    } else {
      // We are already launched in Protected Tor Mode. Just open a new window.
      // Protected also means incognito, so no need to GetOffTheRecordProfile().
      static_cast<void>(
          chrome::NewEmptyWindow(profile, chrome::HOST_DESKTOP_TYPE_NATIVE));
    }
  } else {
    // Launch Protected Mode browser instance
    base::CommandLine command_line = *base::CommandLine::ForCurrentProcess();
    base::FilePath program_path = command_line.GetProgram();
    base::CommandLine new_command_line(program_path);

    new_command_line.AppendSwitch(::switches::kLaunchTorBrowser);

    base::FilePath original_profile_dir = profile->GetPath();
    new_command_line.AppendSwitchPath(::switches::kOriginalBrowserProfileDir,
                                      original_profile_dir);

    if (open_tor_settings)
      new_command_line.AppendSwitch(::switches::kOpenTorSettingsPage);

    new_command_line.AppendSwitch(
        extensions::switches::kShowComponentExtensionOptions);

    if (base::LaunchProcess(new_command_line, base::LaunchOptions()).IsValid()) {
      DLOG(INFO) << "Tor browser instance launched successfully.";
    }
  }

  results_ = make_scoped_ptr(new base::ListValue());

  return RespondNow(ArgumentList(results_.Pass()));
}

ExtensionFunction::ResponseAction TorlauncherStartTorFunction::Run() {
  scoped_ptr<api::torlauncher::StartTor::Params> params(
      api::torlauncher::StartTor::Params::Create(*args_));
  EXTENSION_FUNCTION_VALIDATE(params.get());

  Profile* profile = Profile::FromBrowserContext(browser_context());

  torlauncher::TorLauncherService* tl_service =
      torlauncher::TorLauncherServiceFactory::GetForProfile(profile);

  torlauncher::TorLauncherService::StartTorErrorDesc err_desc;
  bool success = tl_service->StartTor(params->disable_network, &err_desc);

  api::torlauncher::StartTorErrorDesc rv_error_desc;
  rv_error_desc.alert_message_key = err_desc.alert_message_key;
  rv_error_desc.alert_message_param_key = err_desc.alert_message_param_key;
  rv_error_desc.log_message = err_desc.log_message;
  results_ =
      api::torlauncher::StartTor::Results::Create(success, rv_error_desc);

  return RespondNow(ArgumentList(results_.Pass()));
}

ExtensionFunction::ResponseAction TorlauncherInitiateAppQuitFunction::Run() {
  scoped_ptr<api::torlauncher::InitiateAppQuit::Params> params(
      api::torlauncher::InitiateAppQuit::Params::Create(*args_));
  EXTENSION_FUNCTION_VALIDATE(params.get());

  Profile* profile = Profile::FromBrowserContext(browser_context());

  torlauncher::TorLauncherService* tl_service =
      torlauncher::TorLauncherServiceFactory::GetForProfile(profile);
  tl_service->ShutdownTor();

  chrome::CloseAllBrowsersAndQuit();

  results_ = make_scoped_ptr(new base::ListValue());

  return RespondNow(ArgumentList(results_.Pass()));
}

ExtensionFunction::ResponseAction TorlauncherGetTorProcessStatusFunction::Run() {
  Profile* profile = Profile::FromBrowserContext(browser_context());

  torlauncher::TorLauncherService* tl_service =
      torlauncher::TorLauncherServiceFactory::GetForProfile(profile);

  torlauncher::TorLauncherService::TorStatus status =
      tl_service->GetTorProcessStatus();

  results_ = api::torlauncher::GetTorProcessStatus::Results::Create(
      static_cast<int>(status));

  return RespondNow(ArgumentList(results_.Pass()));
}

ExtensionFunction::ResponseAction TorlauncherSetTorStatusRunningFunction::Run() {
  Profile* profile = Profile::FromBrowserContext(browser_context());

  torlauncher::TorLauncherService* tl_service =
      torlauncher::TorLauncherServiceFactory::GetForProfile(profile);

  tl_service->set_tor_status_running();

  results_ = make_scoped_ptr(new base::ListValue());

  return RespondNow(ArgumentList(results_.Pass()));
}

ExtensionFunction::ResponseAction TorlauncherGetTorServiceSettingsFunction::Run() {
  Profile* profile = Profile::FromBrowserContext(browser_context());

  torlauncher::TorLauncherService* tl_service =
      torlauncher::TorLauncherServiceFactory::GetForProfile(profile);

  api::torlauncher::TorServiceSettings rv;
  rv.control_host = tl_service->control_host();
  rv.control_port = static_cast<int>(tl_service->control_port());
  rv.control_password = tl_service->control_passwd();

  results_ = api::torlauncher::GetTorServiceSettings::Results::Create(rv);

  return RespondNow(ArgumentList(results_.Pass()));
}

ExtensionFunction::ResponseAction TorlauncherEnvExistsFunction::Run() {
  scoped_ptr<api::torlauncher::EnvExists::Params> params(
      api::torlauncher::EnvExists::Params::Create(*args_));
  EXTENSION_FUNCTION_VALIDATE(params.get());

  scoped_ptr<base::Environment> env(base::Environment::Create());
  results_ = api::torlauncher::EnvExists::Results::Create(
      env->HasVar(params->env_var_name.c_str()));

  return RespondNow(ArgumentList(results_.Pass()));
}

ExtensionFunction::ResponseAction TorlauncherEnvGetFunction::Run() {
  scoped_ptr<api::torlauncher::EnvGet::Params> params(
      api::torlauncher::EnvGet::Params::Create(*args_));
  EXTENSION_FUNCTION_VALIDATE(params.get());

  scoped_ptr<base::Environment> env(base::Environment::Create());
  std::string value;
  env->GetVar(params->env_var_name.c_str(), &value);
  results_ = api::torlauncher::EnvGet::Results::Create(value);

  return RespondNow(ArgumentList(results_.Pass()));
}

ExtensionFunction::ResponseAction
TorlauncherReadAuthenticationCookieFunction::Run() {
  const long long kMaxBytesToRead = 32;

  base::ThreadRestrictions::ScopedAllowIO allow_io;

  base::FilePath path;
  if (PathService::Get(base::DIR_EXE, &path)) {
// FIXME: add actual path to Tor file base by modifying tor_file_base_dir_ or appending to it
#if defined(OS_WIN)
#elif defined(OS_MACOSX)
    path = path.DirName().DirName().Append("TorBrowser");
    path = path.Append("Data/Tor/control_auth_cookie");
#endif
  }

  if (path.empty())
  // TODO: set lastError here
  {}

  base::File file(path, base::File::FLAG_OPEN | base::File::FLAG_READ);
  // Limit the buffer size to avoid memory excessive usage as a result
  // of malicious user changing the cookie file path environment variable.
  int buf_size = std::min(file.GetLength(), kMaxBytesToRead);
  scoped_ptr<char[]> data(new char[buf_size]);
  std::string res = "";
  if (data.get()) {
    int file_res = file.ReadAtCurrentPos(data.get(), buf_size);

    if (file_res != -1) {
      res = std::string(data.get(), static_cast<size_t>(file_res));
    }
  }

  results_ = api::torlauncher::ReadAuthenticationCookie::Results::Create(res);

  return RespondNow(ArgumentList(results_.Pass()));
}

ExtensionFunction::ResponseAction
TorlauncherSendTorNetworkSettingsResultFunction::Run() {
  scoped_ptr<api::torlauncher::SendTorNetworkSettingsResult::Params> params(
      api::torlauncher::SendTorNetworkSettingsResult::Params::Create(*args_));
  EXTENSION_FUNCTION_VALIDATE(params.get());

  Profile* profile = Profile::FromBrowserContext(browser_context());
  if (!params->settings.empty()) {
      base::JSONReader reader(base::JSON_ALLOW_TRAILING_COMMAS);
      base::Value *result = reader.ReadToValue(params->settings);
    if (!result)
      DLOG(ERROR) << reader.GetErrorMessage();
    else {
      content::NotificationService::current()->Notify(
          chrome::NOTIFICATION_TOR_NETWORK_SETTINGS_READY,
          content::Source<Profile>(profile),
          content::Details<base::Value>(result)
        );
    }
  }

  results_ = make_scoped_ptr(new base::ListValue());

  return RespondNow(ArgumentList(results_.Pass()));
}

ExtensionFunction::ResponseAction
TorlauncherNotifyTorOpenControlConnectionSuccessFunction::Run() {
  Profile* profile = Profile::FromBrowserContext(browser_context());
  content::NotificationService::current()->Notify(
      chrome::TORLAUNCHER_APP_OPEN_CONTROL_CONNECTION_SUCCESS,
      content::Source<Profile>(profile),
      content::NotificationService::NoDetails());

  results_ = make_scoped_ptr(new base::ListValue());

  return RespondNow(ArgumentList(results_.Pass()));
}

ExtensionFunction::ResponseAction
TorlauncherNotifyTorCircuitsEstablishedFunction::Run() {
  Profile* profile = Profile::FromBrowserContext(browser_context());
  content::NotificationService::current()->Notify(
      chrome::TORLAUNCHER_APP_FINISHED_INITIALIZING_CIRCUITS,
      content::Source<Profile>(profile),
      content::NotificationService::NoDetails());

  results_ = make_scoped_ptr(new base::ListValue());

  return RespondNow(ArgumentList(results_.Pass()));
}

ExtensionFunction::ResponseAction
TorlauncherNotifyTorSaveSettingsSuccessFunction::Run() {
  Profile* profile = Profile::FromBrowserContext(browser_context());
  content::NotificationService::current()->Notify(
      chrome::TORLAUNCHER_APP_TOR_SAVE_SETTINGS_SUCCESS,
      content::Source<Profile>(profile),
      content::NotificationService::NoDetails());

  results_ = make_scoped_ptr(new base::ListValue());

  return RespondNow(ArgumentList(results_.Pass()));
}

ExtensionFunction::ResponseAction
TorlauncherNotifyTorSaveSettingsErrorFunction::Run() {
  scoped_ptr<api::torlauncher::NotifyTorSaveSettingsError::Params> params(
      api::torlauncher::NotifyTorSaveSettingsError::Params::Create(*args_));
  EXTENSION_FUNCTION_VALIDATE(params.get());

  Profile* profile = Profile::FromBrowserContext(browser_context());
  content::NotificationService::current()->Notify(
      chrome::TORLAUNCHER_APP_TOR_SAVE_SETTINGS_ERROR,
      content::Source<Profile>(profile),
      content::Details<std::string>(new std::string(params->message)));

  results_ = make_scoped_ptr(new base::ListValue());

  return RespondNow(ArgumentList(results_.Pass()));
}

ExtensionFunction::ResponseAction
TorlauncherSetTorProxyFunction::Run() {
  scoped_ptr<api::torlauncher::SetTorProxy::Params> params(
      api::torlauncher::SetTorProxy::Params::Create(*args_));
  EXTENSION_FUNCTION_VALIDATE(params.get());

  Profile* profile = Profile::FromBrowserContext(browser_context());
  if (base::CommandLine::ForCurrentProcess()->HasSwitch(
          ::switches::kLaunchTorBrowser)) {
    DLOG(INFO) << "Setting proxy server...";
    if (!params->tor_proxy_username.empty() && !params->tor_proxy_password.empty()) {
      base::DictionaryValue* proxy_dict =
          ProxyConfigDictionary::CreateFixedServers(
              "socks5://" + params->tor_proxy_username + ":" +
                params->tor_proxy_password + "@localhost:9150",
              "");
      profile->GetOffTheRecordProfile()->
          GetPrefs()->Set(prefs::kProxy, *proxy_dict);
    }
  }

  results_ = make_scoped_ptr(new base::ListValue());

  return RespondNow(ArgumentList(results_.Pass()));
}

} // namespace extensions
