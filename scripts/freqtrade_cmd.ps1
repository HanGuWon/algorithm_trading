param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Continue"

if (-not $Args -or $Args.Count -eq 0) {
    throw "Provide Freqtrade arguments, for example: .\\scripts\\freqtrade_cmd.ps1 show-config -c user_data/configs/volatility_rotation_mr_backtest_static.json"
}

if (Get-Command freqtrade -ErrorAction SilentlyContinue) {
    & freqtrade @Args
    exit $LASTEXITCODE
}

$localPython = Join-Path $PSScriptRoot "..\\.venv-freqtrade\\Scripts\\python.exe"
if (Test-Path $localPython) {
    & $localPython -m freqtrade @Args
    exit $LASTEXITCODE
}

throw "Freqtrade is not available in PATH and .venv-freqtrade\\Scripts\\python.exe was not found."
