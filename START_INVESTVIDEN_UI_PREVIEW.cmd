@echo off
setlocal
chcp 65001 >nul

set "PROJECT_DIR=%~dp0"
set "PREVIEW_DB=%PROJECT_DIR%output\investviden-ui-preview-schema4.sqlite"
cd /d "%PROJECT_DIR%"
title InvestViden - sikker UI-forhaandsvisning

if not exist "%PREVIEW_DB%" (
    echo InvestViden-forhaandskopien mangler:
    echo %PREVIEW_DB%
    echo.
    echo Den aktive database er ikke blevet aendret. Bed Codex om at oprette
    echo en ny kontrolleret schema-4-kopi, foer UI'en startes.
    echo.
    pause
    exit /b 2
)

if /I "%~1"=="--check" (
    call "%PROJECT_DIR%run.cmd" --db "%PREVIEW_DB%" status >nul
    if errorlevel 1 exit /b 2
    echo UI-forhaandsvisningen er klar, og den aktive database blev ikke brugt.
    exit /b 0
)

echo Starter InvestViden med den kontrollerede databasekopi.
echo Den aktive database data\knowledgebase.sqlite bruges ikke.
echo.
call "%PROJECT_DIR%run.cmd" --db "%PREVIEW_DB%" ui
if errorlevel 1 (
    echo.
    echo UI'en blev stoppet med en fejl. Den aktive database er stadig urort.
    pause
)

endlocal
