@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0scripts\Start-Windows.ps1" -Action Stop
set "result=%ERRORLEVEL%"
echo.
pause
exit /b %result%
