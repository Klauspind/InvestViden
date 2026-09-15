@echo off
setlocal
chcp 65001 >nul

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"
title InvestViden

if /I "%~1"=="--check" goto CHECK

:MENU
cls
echo ============================================================
echo                         INVESTVIDEN
echo ============================================================
echo.
echo   1. Hent nye podcasttransskriptioner fra OneDrive
echo   2. Importer andre dokumenter fra indbakken
echo   3. Send naeste nye kilde til AI (API-pilot)
echo   4. Kontroller og indlaes AI-resultater
echo   5. Aabn kontroloversigten
echo   6. Vis status
echo   7. Tag en verificeret backup
echo   8. Opsaet eller kontroller Mistral API
echo   9. Lav en manuel AI-pakke
echo   0. Luk
echo.
choice /C 1234567890 /N /M "Vaelg et punkt: "

if errorlevel 10 goto END
if errorlevel 9 goto MANUAL_AI
if errorlevel 8 goto SETUP_MISTRAL
if errorlevel 7 goto BACKUP
if errorlevel 6 goto STATUS
if errorlevel 5 goto DASHBOARD
if errorlevel 4 goto PROCESS_AI
if errorlevel 3 goto RUN_AI
if errorlevel 2 goto IMPORT_DOCUMENTS
if errorlevel 1 goto SYNC_PODCASTS
goto MENU

:SYNC_PODCASTS
cls
echo Henter nye podcasttransskriptioner
echo ----------------------------------
if not exist "config\settings.json" (
    echo.
    echo Konfigurationen config\settings.json mangler.
    echo Bed Codex om at oprette podcastforbindelsen, foer du fortsaetter.
    goto PAUSE_MENU
)

echo Foerst vises en skrivebeskyttet forhaandsvisning.
echo OneDrive-filer bliver ikke aendret, flyttet eller slettet.
echo.
call "%PROJECT_DIR%run.cmd" sync-podcasts
if errorlevel 1 goto COMMAND_ERROR

echo.
choice /C JN /N /M "Vil du klargoere de nye episoder lokalt? [J/N]: "
if errorlevel 2 goto MENU
call "%PROJECT_DIR%run.cmd" sync-podcasts --apply
if errorlevel 1 goto COMMAND_ERROR

echo.
echo Nu kontrolleres den lokale podcastindbakke.
call "%PROJECT_DIR%run.cmd" scan-inbox --path "inbox\transskriptioner" --dry-run
if errorlevel 1 goto COMMAND_ERROR

echo.
choice /C JN /N /M "Vil du importere de viste nye kilder i InvestViden? [J/N]: "
if errorlevel 2 goto MENU
call "%PROJECT_DIR%run.cmd" scan-inbox --path "inbox\transskriptioner"
if errorlevel 1 goto COMMAND_ERROR

echo.
echo Podcastimporten er faerdig. Nye kilder kan nu klargoeres til AI med punkt 3.
goto PAUSE_MENU

:IMPORT_DOCUMENTS
cls
echo Importer andre dokumenter
echo -------------------------
if not exist "inbox" mkdir "inbox"
echo Indbakken aabnes nu i Stifinder.
echo Laeg tekst- eller Markdown-filer i den relevante undermappe.
echo PDF og Word skal foreloebig ogsaa have en tekstkopi.
echo.
start "" "%PROJECT_DIR%inbox"
pause

echo.
echo Foerst vises en skrivebeskyttet forhaandsvisning.
call "%PROJECT_DIR%run.cmd" scan-inbox --dry-run
if errorlevel 1 goto COMMAND_ERROR

echo.
choice /C JN /N /M "Vil du importere de viste nye kilder? [J/N]: "
if errorlevel 2 goto MENU
call "%PROJECT_DIR%run.cmd" scan-inbox
if errorlevel 1 goto COMMAND_ERROR

echo.
echo Dokumentimporten er faerdig. Nye kilder kan nu klargoeres til AI med punkt 3.
goto PAUSE_MENU

:RUN_AI
cls
echo Send naeste nye kilde til AI
echo ---------------------------
call "%PROJECT_DIR%run.cmd" mistral-status --verify
if errorlevel 1 goto COMMAND_ERROR
echo.
echo Foerst vises en lokal forhaandsvisning uden API-forbrug.
call "%PROJECT_DIR%run.cmd" run-mistral --limit 1
if errorlevel 1 goto COMMAND_ERROR
echo.
echo Ved fortsaettelse sendes kildeteksten til Mistral API.
echo Det kan koste et mindre API-beloeb. Der sendes hoejst een kilde.
choice /C JN /N /M "Vil du starte API-piloten? [J/N]: "
if errorlevel 2 goto MENU
call "%PROJECT_DIR%run.cmd" run-mistral --apply --limit 1
if errorlevel 1 goto COMMAND_ERROR
echo.
echo AI-svaret ligger nu i den lokale indlaesningskoe.
echo Brug punkt 4 til validering og indlaesning. Intet er menneskeligt godkendt endnu.
goto PAUSE_MENU

:MANUAL_AI
cls
echo Lav en manuel AI-pakke
echo ----------------------
call "%PROJECT_DIR%run.cmd" prepare-ai
if errorlevel 1 goto COMMAND_ERROR
echo.
echo AI-pakken er klar. Mappen aabnes nu.
echo Foelg START-HER.md i mappen, eller bed Codex om at behandle pakken.
if exist "output\ai-pakke" start "" "%PROJECT_DIR%output\ai-pakke"
goto PAUSE_MENU

:PROCESS_AI
cls
echo Kontroller og indlaes AI-resultater
echo ----------------------------------
if not exist "extractions\incoming" mkdir "extractions\incoming"
echo API-resultater ligger automatisk i denne mappe.
echo Manuelle AI-resultater kan ogsaa gemmes her som JSON.
echo Mappen aabnes nu. Tryk derefter paa en tast for at kontrollere filerne.
echo.
start "" "%PROJECT_DIR%extractions\incoming"
pause

call "%PROJECT_DIR%run.cmd" process-ai --dry-run
if errorlevel 1 goto COMMAND_ERROR

echo.
choice /C JN /N /M "Vil du indlaese de validerede AI-resultater? [J/N]: "
if errorlevel 2 goto MENU
call "%PROJECT_DIR%run.cmd" process-ai
if errorlevel 1 goto COMMAND_ERROR

echo.
echo AI-resultaterne er indlaest. Rapport, kontroloversigt, eksport og backup er opdateret.
goto PAUSE_MENU

:DASHBOARD
cls
echo Aabner kontroloversigten
echo -----------------------
if not exist "output\kontroloversigt.html" (
    call "%PROJECT_DIR%run.cmd" dashboard
    if errorlevel 1 goto COMMAND_ERROR
)
start "" "%PROJECT_DIR%output\kontroloversigt.html"
echo Kontroloversigten er aabnet i din browser.
goto PAUSE_MENU

:STATUS
cls
call "%PROJECT_DIR%run.cmd" status
if errorlevel 1 goto COMMAND_ERROR
goto PAUSE_MENU

:BACKUP
cls
echo Opretter og verificerer backup
echo -----------------------------
call "%PROJECT_DIR%run.cmd" backup
if errorlevel 1 goto COMMAND_ERROR
goto PAUSE_MENU

:SETUP_MISTRAL
cls
call "%PROJECT_DIR%SETUP_MISTRAL_API.cmd"
if errorlevel 1 goto COMMAND_ERROR
echo.
call "%PROJECT_DIR%run.cmd" mistral-status --verify
if errorlevel 1 goto COMMAND_ERROR
goto PAUSE_MENU

:COMMAND_ERROR
echo.
echo Handlingen blev stoppet, fordi InvestViden meldte en fejl.
echo Ingen efterfoelgende trin er koert. Laes beskeden ovenfor, eller bed Codex om hjaelp.
goto PAUSE_MENU

:PAUSE_MENU
echo.
echo Tryk paa en tast for at vende tilbage til menuen.
pause >nul
goto MENU

:CHECK
if not exist "%PROJECT_DIR%run.cmd" (
    echo Menutjek fejlede: run.cmd mangler.
    exit /b 1
)
call "%PROJECT_DIR%run.cmd" status >nul
if errorlevel 1 (
    echo Menutjek fejlede: InvestViden kunne ikke vise status.
    exit /b 1
)
call "%PROJECT_DIR%run.cmd" run-mistral --limit 1 >nul
if errorlevel 1 (
    echo Menutjek fejlede: AI-forhaandsvisningen virkede ikke.
    exit /b 1
)
call "%PROJECT_DIR%SETUP_MISTRAL_API.cmd" --check >nul
if errorlevel 1 (
    echo Menutjek fejlede: API-opsaetningen virkede ikke.
    exit /b 1
)
echo Menutjek bestaaet.
exit /b 0

:END
endlocal
exit /b 0
