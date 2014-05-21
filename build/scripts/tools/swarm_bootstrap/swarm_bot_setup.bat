@echo off
:: Copyright (c) 2012 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

:: This script will setup the machine to be a swarm bot. It is assumed that
:: python is already installed on this system and the required swarm files have
:: been added.

set DIMENSIONS_FILE=dimension.in
set SLAVE_ARGUMENTS=-a %1 -p 443 -r 400 -v %DIMENSIONS_FILE%
set SLAVE_COMMAND=python slave_machine.py %SLAVE_ARGUMENTS%

:STARTUP_SCRIPT
echo Generate the machine dimensions...
cd %2
call python dimensions_generator.py %DIMENSIONS_FILE%

echo Setup up swarm script to run on startup...
cd c:\Users\chrome-bot\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
echo @cd %2 > run_swarm_bot.bat
echo @%SLAVE_COMMAND% >> run_swarm_bot.bat

:: We are done.
:END
shutdown -r -f -t 1