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

#ifndef COMPONENTS_TORLAUNCHER_TORLAUNCHER_PREF_NAMES_H_
#define COMPONENTS_TORLAUNCHER_TORLAUNCHER_PREF_NAMES_H_

namespace torlauncher {
namespace pref_names {

extern const char kLogLevel[];
extern const char kLogMethod[];
extern const char kMaxTorLogEntries[];

extern const char kControlHost[];
extern const char kControlPort[];

extern const char kStartTor[];
extern const char kPromptAtStartup[];
extern const char kOnlyConfigureTor[];

extern const char kTorPath[];
extern const char kTorrcPath[];
extern const char kTorDataDirPath[];

extern const char kDefaultBridgeType[];
extern const char kDefaultBridgeRecommendedType[];
extern const char kDefaultBridge[];

}
}

#endif // COMPONENTS_TORLAUNCHER_TORLAUNCHER_PREF_NAMES_H_
