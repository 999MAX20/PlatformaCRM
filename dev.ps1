$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Missing .venv/Scripts/python.exe. Set up the project environment first.'
}
& $python (Join-Path $PSScriptRoot 'scripts/dev_local.py') @args
exit $LASTEXITCODE
