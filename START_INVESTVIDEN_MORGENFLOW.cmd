@echo off
setlocal
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0START_INVESTVIDEN_MORGENFLOW.ps1" %*
exit /b %ERRORLEVEL%
