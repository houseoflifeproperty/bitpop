:: Sets up the environment for use with MSVS tools and CMake.
@echo off

setlocal
:: cmd for loops are really hard, so I hardcoded the list of MSVS paths.
:: Alternatively we could 'reg query' this key:
:: HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\VisualStudio\10.0\Setup\VS;ProductDir
set vcvars="%PROGRAMFILES%\Microsoft Visual Studio 11.0\VC\bin\vcvars32.bat"
if exist %vcvars% goto found_vcvars
set vcvars="%PROGRAMFILES%\Microsoft Visual Studio 10.0\VC\bin\vcvars32.bat"
if exist %vcvars% goto found_vcvars
:: We've installed VS 2010 in E: on some of the slaves because C: was full.
set vcvars="E:\Program Files\Microsoft Visual Studio 10.0\VC\bin\vcvars32.bat"
if exist %vcvars% goto found_vcvars
set vcvars="E:\Program Files (x86)\Microsoft Visual Studio 10.0\VC\bin\vcvars32.bat"
if exist %vcvars% goto found_vcvars
:: VS 2008 vcvars isn't standalone, it needs this env var.
set VS90COMNTOOLS=%PROGRAMFILES%\Microsoft Visual Studio 9.0\Common7\Tools\
set vcvars="%PROGRAMFILES%\Microsoft Visual Studio 9.0\VC\bin\vcvars32.bat"
if exist %vcvars% goto found_vcvars

:found_vcvars
call %vcvars%

:: We auto-unpack cmake and 7zip from svn on the bots now.  The master passes
:: an env var holding the bot_tools directory.
set PATH=%BOTTOOLS%\cmake\bin;%PATH%
set PATH=%BOTTOOLS%\7zip\Files\7-Zip;%PATH%

:: Add Cygwin to the *end* of PATH.  We don't want to override anything form
:: depot_tools in particular.
set PATH=%PATH%;C:\cygwin\bin

:: Make sure depot_tools svn.exe comes before Cygwin svn, otherwise CMake
:: prefers C:\cygwin\bin\svn.exe over E:\b\depot_tools\svn.bat.
:: TODO(rnk): Don't hardcode E:\b
set PATH=E:\b\depot_tools\svn_bin;%PATH%

echo Final PATH:
echo %PATH%
%*
