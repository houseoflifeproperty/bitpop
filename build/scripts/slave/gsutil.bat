set HOME=%USERPROFILE%
call python %~dp0..\command_wrapper\bin\command_wrapper.py -- python %~dp0..\..\third_party\gsutil\gsutil %*
@echo off
set saved_error=%ERRORLEVEL%
del /q /s %~dp0..\..\third_party\gsutil\boto\*.pyc > NUL
exit /b %saved_error%
