@echo off
setlocal
chcp 65001 >nul
title InvestViden - sikker OpenAI API-opsaetning

if /I "%~1"=="--check" (
    where powershell.exe >nul 2>nul
    if errorlevel 1 exit /b 1
    echo API-opsaetningstjek bestaaet.
    exit /b 0
)

echo ============================================================
echo              SIKKER OPENAI API-OPSAETNING
echo ============================================================
echo.
echo Opret foerst en personlig API-noegle paa:
echo https://platform.openai.com/api-keys
echo.
echo Indsaet aldrig noeglen i Codex, en chat, settings.json eller Git.
echo Din indtastning skjules og gemmes som OPENAI_API_KEY i din
echo personlige Windows-brugerprofil.
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$secure = Read-Host 'Indsaet OpenAI API-noeglen' -AsSecureString; $ptr = [IntPtr]::Zero; try { $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure); $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr); if ([string]::IsNullOrWhiteSpace($plain) -or $plain.Length -lt 20) { Write-Error 'Noeglen er tom eller for kort'; exit 2 }; [Environment]::SetEnvironmentVariable('OPENAI_API_KEY', $plain, 'User'); Write-Output 'API-noeglen er gemt uden for projektet.' } finally { if ($ptr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) } }"
if errorlevel 1 (
    echo.
    echo API-opsaetningen blev ikke gennemfoert.
    exit /b 1
)

echo.
echo InvestViden kan nu laese noeglen uden at vise den.
exit /b 0
