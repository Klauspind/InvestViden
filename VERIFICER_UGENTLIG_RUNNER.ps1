param(
    [Parameter(Mandatory = $true)]
    [string]$Database
)

$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$databasePath = [System.IO.Path]::GetFullPath($Database)
$activePath = [System.IO.Path]::GetFullPath((Join-Path $projectDir 'data\knowledgebase.sqlite'))

if (-not (Test-Path -LiteralPath $databasePath -PathType Leaf)) {
    throw "Databasefilen findes ikke: $databasePath"
}
if ([StringComparer]::OrdinalIgnoreCase.Equals($databasePath, $activePath)) {
    throw 'Den aktive data\knowledgebase.sqlite må ikke bruges i denne test.'
}

Write-Host '1/2 Skrivebeskyttet recovery-afstemning'
& (Join-Path $projectDir 'run.cmd') weekly-recovery --database $databasePath
if ($LASTEXITCODE -ne 0) { throw 'Recovery-afstemningen fejlede.' }

Write-Host '2/2 Skrivebeskyttet uge-preview'
& (Join-Path $projectDir 'run.cmd') weekly-drafts --database $databasePath
if ($LASTEXITCODE -ne 0) { throw 'Uge-preview fejlede.' }

Write-Host 'VERIFICERET: Begge read-only kontroller bestod. Ingen kladder blev oprettet.'
