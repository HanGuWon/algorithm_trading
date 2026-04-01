param(
    [string]$Config = "user_data/configs/volatility_rotation_mr_binance_dryrun.json",
    [string[]]$AdditionalConfigs = @(),
    [string]$Strategy = "VolatilityRotationMR"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command freqtrade -ErrorAction SilentlyContinue)) {
    $freqtradeCmd = Join-Path $PSScriptRoot "freqtrade_cmd.ps1"
} else {
    $freqtradeCmd = "freqtrade"
}

$configArgs = @("--config", $Config)
foreach ($cfg in $AdditionalConfigs) {
    $configArgs += @("--config", $cfg)
}

Write-Host "Validating strategy discovery..."
& $freqtradeCmd list-strategies @configArgs | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "list-strategies failed."
}

Write-Host "Validating merged configuration..."
& $freqtradeCmd show-config @configArgs | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "show-config failed."
}
