@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "ENTRY_POINT=%PROJECT_DIR%investkb.py"
set "BUNDLED_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python "%ENTRY_POINT%" %*
    exit /b
)

if exist "%BUNDLED_PYTHON%" (
    "%BUNDLED_PYTHON%" "%ENTRY_POINT%" %*
    exit /b
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 "%ENTRY_POINT%" %*
    exit /b
)

echo Fejl: Python 3.10+ blev ikke fundet. Installer Python, eller kor projektet fra Codex Desktop. 1>&2
exit /b 1
