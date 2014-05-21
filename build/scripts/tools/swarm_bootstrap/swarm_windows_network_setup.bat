@echo off
:: Copyright (c) 2012 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

:: This script will setup the machine to setup the network drive on startup.

echo Setting up Network Drive on Startup...
cd c:\Users\chrome-bot\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
echo @net use %1 %2 > setup_swarm_network_drive.bat
