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

#include "base/environment.h"
#include "base/memory/scoped_ptr.h"
#include "base/values.h"
//#include "chrome/browser/browser_shutdown.h"
#include "chrome/browser/lifetime/application_lifetime.h"
#include "chrome/browser/profiles/profile.h"
#include "chrome/browser/torlauncher/torlauncher_service_factory.h"
#include "chrome/common/extensions/api/torlauncher.h"
#include "components/torlauncher/torlauncher_service.h"

#if defined(OS_MACOSX)
#include "chrome/browser/chrome_browser_application_mac.h"
#endif

namespace extensions {

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

// #if defined(OS_MACOSX)
//   chrome_browser_application_mac::Terminate();
// #else
//   chrome::AttemptUserExit();
// #endif
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

} // namespace extensions
