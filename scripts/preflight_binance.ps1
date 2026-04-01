param(
    [ValidateSet("dryrun", "live")]
    [string]$Mode = "dryrun",
    [string]$PrivateConfig = "user_data/configs/volatility_rotation_mr_private.json",
    [string[]]$AdditionalConfigs = @()
)

$ErrorActionPreference = "Stop"

$config = if ($Mode -eq "live") {
    "user_data/configs/volatility_rotation_mr_binance_live.json"
} else {
    "user_data/configs/volatility_rotation_mr_binance_dryrun.json"
}

$configArgs = @("--config", $config)
if (Test-Path $PrivateConfig) {
    $configArgs += @("--config", $PrivateConfig)
}
elseif (-not $env:FREQTRADE__EXCHANGE__KEY -or -not $env:FREQTRADE__EXCHANGE__SECRET) {
    throw "Secrets are missing. Provide $PrivateConfig or set FREQTRADE__EXCHANGE__KEY and FREQTRADE__EXCHANGE__SECRET."
}
foreach ($cfg in $AdditionalConfigs) {
    if ($cfg) {
        $configArgs += @("--config", $cfg)
    }
}

Write-Host "Checking strategy discovery..."
$strategyOutput = (& "$PSScriptRoot\\freqtrade_cmd.ps1" list-strategies @configArgs | Out-String -Width 240)
if ($LASTEXITCODE -ne 0) {
    throw "Strategy discovery failed."
}
if ($strategyOutput -notmatch "VolatilityRotationMR") {
    throw "VolatilityRotationMR is not discoverable."
}

Write-Host "Checking merged config..."
$showConfig = (& "$PSScriptRoot\\freqtrade_cmd.ps1" show-config @configArgs | Out-String -Width 400)
if ($LASTEXITCODE -ne 0) {
    throw "show-config failed."
}

if ($showConfig -notmatch '"trading_mode"\s*:\s*"futures"') {
    throw "Merged config is not using futures mode."
}
if ($showConfig -notmatch '"margin_mode"\s*:\s*"isolated"') {
    throw "Merged config is not using isolated margin."
}
if ($showConfig -notmatch '"use_order_book"\s*:\s*true') {
    throw "Orderbook pricing is not enabled."
}
if ($Mode -eq "live" -and $showConfig -notmatch '"stoploss_price_type"\s*:\s*"mark"') {
    throw "Live profile is not validating stoploss_price_type = mark."
}

Write-Host "Checking pairlist..."
& "$PSScriptRoot\\freqtrade_cmd.ps1" test-pairlist @configArgs --quote USDT --print-json
if ($LASTEXITCODE -ne 0) {
    throw "Pairlist validation failed."
}

if ($Mode -eq "live") {
    Write-Host "Validated live stoploss pricing mode in merged config." -ForegroundColor Green
}
else {
    Write-Host "Validated merged config and dynamic pairlist for dry-run mode." -ForegroundColor Green
}

Write-Host ""
Write-Host "Operator checklist:"
Write-Host "- Verify Binance account Position Mode is One-way Mode."
Write-Host "- Verify Binance account Asset Mode is Single-Asset Mode."
Write-Host "- Verify the API key can read balances and place/cancel USDT-M futures orders."
Write-Host "- Verify withdrawals remain disabled and IP whitelist is set."
Write-Host "- After startup, verify exchange-side stop orders match open positions."
Write-Host "- After reconnect or restart, verify no orphaned conditional stop orders remain."
