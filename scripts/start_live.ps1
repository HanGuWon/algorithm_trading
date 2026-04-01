param(
    [string]$PrivateConfig = "user_data/configs/volatility_rotation_mr_private.json",
    [string[]]$AdditionalConfigs = @()
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PrivateConfig) -and (-not $env:FREQTRADE__EXCHANGE__KEY -or -not $env:FREQTRADE__EXCHANGE__SECRET)) {
    throw "Live trading requires either $PrivateConfig or exchange secrets in environment variables."
}

& "$PSScriptRoot\\preflight_binance.ps1" -Mode live -PrivateConfig $PrivateConfig -AdditionalConfigs $AdditionalConfigs
if ($LASTEXITCODE -ne 0) {
    throw "Live preflight failed."
}

$args = @(
    "trade",
    "--config", "user_data/configs/volatility_rotation_mr_binance_live.json"
)
if (Test-Path $PrivateConfig) {
    $args += @("--config", $PrivateConfig)
}
foreach ($cfg in $AdditionalConfigs) {
    if ($cfg) {
        $args += @("--config", $cfg)
    }
}
$args += @("--strategy", "VolatilityRotationMR")

& "$PSScriptRoot\\freqtrade_cmd.ps1" @args
exit $LASTEXITCODE
