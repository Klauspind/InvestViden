@echo off
setlocal
chcp 65001 >nul

set "PROJECT_DIR=%~dp0"
set "ENTRY_POINT=%PROJECT_DIR%start_consumer_ui.py"
set "CONSUMER_DB=%LOCALAPPDATA%\InvestViden\runtime\transskribinator-consumer\knowledgebase.sqlite"
set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

cd /d "%PROJECT_DIR%"
title InvestViden

echo ============================================================
echo                         INVESTVIDEN
echo ============================================================
echo.
echo Starter den normale consumer-vidensbase:
echo %CONSUMER_DB%
echo.

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python "%ENTRY_POINT%" --db "%CONSUMER_DB%" %*
    exit /b %ERRORLEVEL%
)

if exist "%BUNDLED_PYTHON%" (
    "%BUNDLED_PYTHON%" "%ENTRY_POINT%" --db "%CONSUMER_DB%" %*
    exit /b %ERRORLEVEL%
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 "%ENTRY_POINT%" --db "%CONSUMER_DB%" %*
    exit /b %ERRORLEVEL%
)

echo Fejl: Python 3.10+ blev ikke fundet. Installer Python 3, eller koer projektet fra et miljo med Python. 1>&2
exit /b 1
