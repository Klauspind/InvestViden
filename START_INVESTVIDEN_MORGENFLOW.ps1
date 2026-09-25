param(
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $env:LOCALAPPDATA 'InvestViden\config\morning-consumer.json'
$acceptScript = Join-Path $projectDir 'scripts\verify_morning_consumer_flow.py'
$protectedDb = [System.IO.Path]::GetFullPath((Join-Path $projectDir 'data\knowledgebase.sqlite'))

function Resolve-Python {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @($python.Source) }

    $bundled = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundled -PathType Leaf) { return @($bundled) }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return @($py.Source, '-3') }

    throw 'Python 3.10+ blev ikke fundet.'
}

if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "Lokal konfiguration mangler. Kor foerst KONFIGURER_INVESTVIDEN_MORGENFLOW.ps1"
}
if (-not (Test-Path -LiteralPath $acceptScript -PathType Leaf)) {
    throw 'IV-007 consumer-scriptet mangler i denne InvestViden-version.'
}

$config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($config.schema_version -ne 'investviden-morning-consumer-config-v1') {
    throw 'Ukendt morning-consumer konfigurationsversion.'
}
if (-not $config.delivery_root -or -not $config.runtime_root) {
    throw 'Konfigurationen mangler leveringsmappe eller runtime-rod.'
}

$delivery = [System.IO.Path]::GetFullPath([string]$config.delivery_root)
$runtimeRoot = [System.IO.Path]::GetFullPath([string]$config.runtime_root)

if (-not (Test-Path -LiteralPath $delivery -PathType Container)) {
    throw "Leveringsmappen findes ikke: $delivery"
}
if ([StringComparer]::OrdinalIgnoreCase.Equals($runtimeRoot, $protectedDb)) {
    throw 'Runtime-roden maa ikke vaere den aktive database.'
}

$python = Resolve-Python

if ($Check) {
    $episodeJsons = @()
    foreach ($candidate in Get-ChildItem -LiteralPath $delivery -Filter '*.json' -File -Recurse -ErrorAction Stop) {
        try {
            $parsed = Get-Content -LiteralPath $candidate.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($null -ne $parsed.segments -and $parsed.segments -is [System.Collections.IEnumerable]) {
                $episodeJsons += $candidate
            }
        } catch {
            continue
        }
    }
    if ($episodeJsons.Count -ne 1) {
        throw "Check kraever praecis een episode-JSON med segments; fandt $($episodeJsons.Count)."
    }
    Write-Host 'VERIFICERET: Lokal morning-consumer konfiguration er klar.'
    Write-Host 'Ingen database blev oprettet, og ingen AI-tjeneste blev kaldt.'
    exit 0
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmssfff'
$workDir = Join-Path $runtimeRoot $stamp

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null

$argsList = @()
if ($python.Count -gt 1) { $argsList += $python[1..($python.Count - 1)] }
$argsList += @(
    $acceptScript,
    '--episode-root', $delivery,
    '--work-dir', $workDir
)

& $python[0] @argsList
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    throw "InvestViden morning-consumer fejlede. Runtime er bevaret under: $workDir"
}

Write-Host ''
Write-Host "VERIFICERET: Lokal consumer-korsel gennemfort."
Write-Host "Runtime: $workDir"
Write-Host 'Flowet stoppede ved lokal draft; ingen ekstern AI blev kaldt.'
