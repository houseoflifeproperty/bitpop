window.onload = function () {
  var menuLaunch = document.getElementById('launch_tor_browser');
  var menuAbout = document.getElementById('about_protected_mode');
  var menuNetworkSettings = document.getElementById('network_settings');

  // const kLaunchTorMenuState_Disabled = 0;
  // const kLaunchTorMenuState_LaunchTor = 1;
  // const kLaunchTorMenuState_OpenNewWindow = 2;

  // gLaunchTorMenuState = kLaunchTorMenuState_Disabled;
  const kTorLauncherAppId = "gedbhlplmladiedjcndlndakofpdibcb";

  if (menuLaunch)
    menuLaunch.addEventListener('click', function (e) {
      chrome.torlauncher.launchTorBrowser();
      return false;
    }, false);

  if (menuAbout)
    menuAbout.addEventListener('click', function (e) {
      chrome.runtime.sendMessage(kTorLauncherAppId, { kind: "TorOpenAboutProtectedModeDialog" });
      return false;
    }, false);

  if (menuNetworkSettings)
    menuNetworkSettings.addEventListener('click', function (e) {
      chrome.runtime.sendMessage(kTorLauncherAppId, { kind: "TorOpenNetworkSettingsDialog" });
      return false;
    }, false);
};
