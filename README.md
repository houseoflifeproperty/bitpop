# BitPop

BitPop is an easy, fast, powerful, pretty and brave web browser based on open-source Chromium project.

## Our goal

**Avoid unfair censorship on the Internets**

## Download

You can download BitPop from http://www.bitpop.com

## Feedback

Contact either the [project support](mailto:support@bitpop.com) for general questions, or the [main contributor](mailto:vgachkaylo@bitpop.com) for discussing development and source code-related topics.

## Features

- Facebook chat integrated into main browser interface
- support for both Windows and Mac OS X
- own mechanism of autoupdates
- redirects from censored domains to their new locations
- proxying banned sites in different countries
- Firefox-like black-arrow address bar dropdown for most visited sites in browser history
- easy Facebook image sharing via right-clicking image and choosing an item in a popup menu
- some support to see recent Facebook messages and notifications in the browser actions bar

## Build Instructions

1. install depot_tools. Refer to http://dev.chromium.org/developers/how-tos/install-depot-tools for the steps needed
2. add the depot_tools directory to your system PATH variable
3. pull the repository to a local folder
4. cd into the directory from Step 3

4.1. Mac OS X: setup environment variable GYP_GENERATORS='ninja,xcode' to have an option for either building slightly faster with ninja build system or using old good xcodebuild

5. Run


```
gclient runhooks
```

5.1 Windows: http://www.chromium.org/developers/how-tos/build-instructions-windows
5.2 Mac OS X
5.2.1 Use XCode 4.4 command-line tools setup. 
5.2.2 Add 10.6 SDK from XCode 3.2.6 distro to the main XCode bundle by using the following Terminal command

```
ln -s <XCode 3.2.6 directory>/SDKs/MacOSX10.6.sdk <XCode 4.4 directory>/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.6.sdk
```

6. Build either
6.1 Using ninja: ninja -C out/Release chrome
6.2 Using xcodebuild: xcodebuild -project chrome/chrome.xcodeproj -configuration Release -target chrome
6.3. Using MSVS: Open build/all.sln, set `chrome` as current active project, set configuration to Debug or Release, build it

## Legal

The source for BitPop is released under both the MIT licence for the Chromium part, and the GNU General Public License, for the features we added, as published by the Free Software Foundation, either version 2 of the license, or (at your option) any later version.

BitPop is a trademark of BitPop AS.