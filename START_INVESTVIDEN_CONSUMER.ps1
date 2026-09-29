param(
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $env:LOCALAPPDATA 'InvestViden\config\transskribinator-consumer.json'
$consumerScript = Join-Path $projectDir 'scripts\run_transskribinator_consumer.py'

function Resolve-Python {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return [pscustomobject]@{
            executable = [string]$python.Source
            prefix_args = @()
        }
    }

    $bundled = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundled -PathType Leaf) {
        return [pscustomobject]@{
            executable = [string]$bundled
            prefix_args = @()
        }
    }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return [pscustomobject]@{
            executable = [string]$py.Source
            prefix_args = @('-3')
        }
    }

    throw 'Python 3.10+ blev ikke fundet.'
}

if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw 'Lokal consumer-konfiguration mangler. Koer foerst KONFIGURER_INVESTVIDEN_CONSUMER.ps1'
}
if (-not (Test-Path -LiteralPath $consumerScript -PathType Leaf)) {
    throw 'IV-009 consumer-scriptet mangler i denne InvestViden-version.'
}

$config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($config.schema_version -ne 'investviden-transskribinator-consumer-config-v1') {
    throw 'Ukendt consumer-konfigurationsversion.'
}
if (-not $config.delivery_root -or -not $config.state_root) {
    throw 'Konfigurationen mangler leveringsmappe eller consumer-state.'
}

$python = Resolve-Python
$pythonExe = [string]$python.executable
$argsList = @($python.prefix_args)
$argsList += @(
    $consumerScript,
    '--delivery-root', [string]$config.delivery_root,
    '--state-root', [string]$config.state_root
)
if ($Check) {
    $argsList += '--check'
}

& $pythonExe @argsList
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    throw 'InvestViden Transskribinator-consumer blev ikke verificeret.'
}

if ($Check) {
    Write-Host ''
    Write-Host 'VERIFICERET: Consumer-konfiguration og leveringsmappe bestod read-only check.'
    Write-Host 'Ingen consumer-database blev oprettet af checket, og ingen AI-tjeneste blev kaldt.'
} else {
    Write-Host ''
    Write-Host 'VERIFICERET: Persistent multi-episode consumer-koersel gennemfoert.'
    Write-Host 'Kun lokale, ubekraeftede AI-jobkladder kan vaere oprettet; ingen ekstern AI blev kaldt.'
}
