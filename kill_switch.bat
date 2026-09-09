@echo off
setlocal
title Zoovy Emergency Kill Switch
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0kill_switch.ps1" %*
echo.
echo Press any key to exit...
pause >nul
