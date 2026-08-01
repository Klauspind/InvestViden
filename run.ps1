param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$InvestKbArguments
)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$entryPoint = Join-Path $projectRoot "investkb.py"
$bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
    & $pythonCommand.Source $entryPoint @InvestKbArguments
    exit $LASTEXITCODE
}

if (Test-Path -LiteralPath $bundledPython) {
    & $bundledPython $entryPoint @InvestKbArguments
    exit $LASTEXITCODE
}

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    & $pyLauncher.Source -3 $entryPoint @InvestKbArguments
    exit $LASTEXITCODE
}

Write-Error "Python 3.10+ blev ikke fundet. Installér Python, eller kør projektet fra Codex Desktop."
exit 1
