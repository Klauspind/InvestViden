@echo off
setlocal
chcp 65001 >nul

set "PROJECT_DIR=%~dp0"
set "DATABASE=%~1"
set "MODE=%~2"
if "%MODE%"=="" set "MODE=preview"

if "%DATABASE%"=="" goto USAGE
if not exist "%DATABASE%" (
    echo Fejl: Databasefilen findes ikke:
    echo %DATABASE%
    exit /b 2
)

cd /d "%PROJECT_DIR%"

if /I "%MODE%"=="preview" goto PREVIEW
if /I "%MODE%"=="recovery" goto RECOVERY
if /I "%MODE%"=="apply" goto APPLY
echo Fejl: Ukendt tilstand "%MODE%". Brug preview, recovery eller apply.
exit /b 2

:PREVIEW
echo Skrivebeskyttet forhaandsvisning. Ingen jobkladder oprettes.
call "%PROJECT_DIR%run.cmd" weekly-drafts --database "%DATABASE%"
exit /b %ERRORLEVEL%

:RECOVERY
echo Skrivebeskyttet recovery-afstemning. Ingen laase ryddes og intet genkoeres.
call "%PROJECT_DIR%run.cmd" weekly-recovery --database "%DATABASE%"
exit /b %ERRORLEVEL%

:APPLY
echo Foerst koeres en skrivebeskyttet forhaandsvisning.
call "%PROJECT_DIR%run.cmd" weekly-drafts --database "%DATABASE%"
if errorlevel 1 exit /b %ERRORLEVEL%
echo.
echo APPLY opretter kun ubekraeftede lokale Mistral-jobkladder og en verificeret backup.
echo Kommandoen sender intet til AI og bekraefter ingen jobs.
set /p "CONFIRM=Skriv OPRET KLADDER for at fortsaette: "
if not "%CONFIRM%"=="OPRET KLADDER" (
    echo Afbrudt uden aendringer.
    exit /b 1
)
call "%PROJECT_DIR%run.cmd" weekly-drafts --database "%DATABASE%" --apply
exit /b %ERRORLEVEL%

:USAGE
echo Brug:
echo   START_UGENTLIG_INVESTVIDEN.cmd "C:\sti\til\isoleret-schema4.sqlite" [preview^|recovery^|apply]
echo.
echo Databaseargumentet er obligatorisk. Der findes ingen standarddatabase.
exit /b 2
