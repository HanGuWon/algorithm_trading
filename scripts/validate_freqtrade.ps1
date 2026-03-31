param(
    [string]$Config = "user_data/configs/volatility_rotation_mr_binance_dryrun.json",
    [string[]]$AdditionalConfigs = @(),
    [string]$Strategy = "VolatilityRotationMR"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command freqtrade -ErrorAction SilentlyContinue)) {
    throw "freqtrade is not available in PATH."
}

$configArgs = @("--config", $Config)
foreach ($cfg in $AdditionalConfigs) {
    $configArgs += @("--config", $cfg)
}

Write-Host "Validating strategy discovery..."
& freqtrade list-strategies @configArgs --strategy-path user_data/strategies | Out-Host

Write-Host "Validating merged configuration..."
& freqtrade show-config @configArgs --strategy $Strategy | Out-Host
