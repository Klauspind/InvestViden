@echo off
setlocal
chcp 65001 >nul
title InvestViden - sikker Mistral API-opsaetning

if /I "%~1"=="--check" (
    where powershell.exe >nul 2>nul
    if errorlevel 1 exit /b 1
    echo Mistral-opsaetningstjek bestaaet.
    exit /b 0
)

echo ============================================================
echo              SIKKER MISTRAL API-OPSAETNING
echo ============================================================
echo.
echo API-noegler kan administreres paa:
echo https://console.mistral.ai/api-keys
echo.
echo Indsaet aldrig noeglen i Codex, en chat, settings.json eller Git.
echo Din indtastning skjules og gemmes som MISTRAL_API_KEY i din
echo personlige Windows-brugerprofil.
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$value = [Environment]::GetEnvironmentVariable('MISTRAL_API_KEY','User'); if (-not [string]::IsNullOrWhiteSpace($value)) { exit 10 }"
if errorlevel 10 (
    echo Der findes allerede en Mistral API-noegle. Selve noeglen vises aldrig.
    choice /C BE /N /M "Vil du beholde eller erstatte den? [B/E]: "
    if errorlevel 2 goto WRITE_KEY
    echo Den eksisterende noegle blev beholdt.
    exit /b 0
)

:WRITE_KEY
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$secure = Read-Host 'Indsaet Mistral API-noeglen' -AsSecureString; $ptr = [IntPtr]::Zero; try { $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure); $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr); if ([string]::IsNullOrWhiteSpace($plain) -or $plain.Length -lt 20) { Write-Error 'Noeglen er tom eller for kort'; exit 2 }; [Environment]::SetEnvironmentVariable('MISTRAL_API_KEY', $plain, 'User'); Write-Output 'Mistral API-noeglen er gemt uden for projektet.' } finally { if ($ptr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) } }"
if errorlevel 1 (
    echo.
    echo API-opsaetningen blev ikke gennemfoert.
    exit /b 1
)

echo.
echo InvestViden kan nu laese noeglen uden at vise den.
exit /b 0
