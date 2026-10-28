param(
    [Parameter(Mandatory = $true)]
    [string]$DataRoot,
    [string]$ProducerProgram = (Join-Path $env:LOCALAPPDATA 'Programs\Transskribinator-3000-1.0.1'),
    [string]$DeliveryRoot,
    [switch]$Import
)

$ErrorActionPreference = 'Stop'
$stateRoot = Join-Path $env:LOCALAPPDATA 'InvestViden\runtime\transskribinator-consumer'
$configPath = Join-Path $env:LOCALAPPDATA 'InvestViden\config\transskribinator-consumer.json'
if (-not $DeliveryRoot) {
    if (Test-Path -LiteralPath $configPath -PathType Leaf) {
        $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($config.schema_version -ne 'investviden-transskribinator-consumer-config-v1' -or -not $config.delivery_root) {
            throw 'Ugyldig consumer-konfiguration; angiv -DeliveryRoot eksplicit.'
        }
        $DeliveryRoot = [string]$config.delivery_root
    } else {
        $DeliveryRoot = Join-Path $env:LOCALAPPDATA 'InvestViden\runtime\podcast-delivery'
    }
}
$pythonExe = Join-Path $ProducerProgram 'runtime\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    throw 'Producentens Python-runtime mangler; angiv den installerede 1.0.1-mappe med -ProducerProgram.'
}
$argsList = @(
    '-I', '-B', (Join-Path $PSScriptRoot 'scripts\sync_transskribinator_podcasts.py'),
    '--producer-app', (Join-Path $ProducerProgram 'app'),
    '--data-root', $DataRoot,
    '--delivery-root', $DeliveryRoot,
    '--state-root', $stateRoot
)
if ($Import) { $argsList += '--import' }

Write-Host "Afleveringsmappe: $DeliveryRoot"
if ($Import) {
    Write-Host "Import til normal consumerdatabase: $stateRoot\knowledgebase.sqlite"
} else {
    Write-Host 'Kun aflevering. Databasen importeres kun med -Import.'
}
& $pythonExe @argsList
if ($LASTEXITCODE -ne 0) { throw 'Synkronisering stoppede; se afviste pakker eller importfejl ovenfor.' }
