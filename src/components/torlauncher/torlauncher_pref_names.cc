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

#include "components/torlauncher/torlauncher_pref_names.h"

namespace torlauncher {
namespace pref_names {

const char kLogLevel[] = "extensions.torlauncher.loglevel";
const char kLogMethod[] = "extensions.torlauncher.logmethod";
const char kMaxTorLogEntries[] = "extensions.torlauncher.max_tor_log_entries";

const char kControlHost[] = "extensions.torlauncher.control_host";
const char kControlPort[] = "extensions.torlauncher.control_port";

const char kStartTor[] = "extensions.torlauncher.start_tor";
const char kPromptAtStartup[] = "extensions.torlauncher.prompt_at_startup";
const char kOnlyConfigureTor[] = "extensions.torlauncher.only_configure_tor";

const char kTorPath[] = "extensions.torlauncher.tor_path";
const char kTorrcPath[] = "extensions.torlauncher.torrc_path";
const char kTorDataDirPath[] = "extensions.torlauncher.tordatadir_path";

const char kDefaultBridgeType[] = "extensions.torlauncher.default_bridge_type";
const char kDefaultBridgeRecommendedType[] =
    "extensions.torlauncher.default_bridge_recommended_type";
const char kDefaultBridge[] = "extensions.torlauncher.default_bridge";

}
}
