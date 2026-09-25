param(
    [Parameter(Mandatory = $true)]
    [string]$DeliveryRoot,
    [string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA 'InvestViden\runtime\morning-consumer')
)

$ErrorActionPreference = 'Stop'

$configDir = Join-Path $env:LOCALAPPDATA 'InvestViden\config'
$configPath = Join-Path $configDir 'morning-consumer.json'

$delivery = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath(
    $DeliveryRoot.Trim().Trim('"', "'")
)
$runtime = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath(
    $RuntimeRoot.Trim().Trim('"', "'")
)

if (-not (Test-Path -LiteralPath $delivery -PathType Container)) {
    throw "Leveringsmappen findes ikke: $delivery"
}

New-Item -ItemType Directory -Force -Path $configDir | Out-Null

$config = [ordered]@{
    schema_version = 'investviden-morning-consumer-config-v1'
    delivery_root = $delivery
    runtime_root = $runtime
}

$temp = Join-Path $configDir ('morning-consumer-' + [guid]::NewGuid().ToString('N') + '.tmp')
try {
    $config | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $temp -Encoding UTF8
    Move-Item -LiteralPath $temp -Destination $configPath -Force
} finally {
    Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
}

Write-Host 'Konfiguration gemt lokalt.'
Write-Host "Leveringsmappe: $delivery"
Write-Host "Runtime-rod: $runtime"
Write-Host "Konfigurationsfil: $configPath"
Write-Host 'Ingen database eller AI-tjeneste blev brugt.'
