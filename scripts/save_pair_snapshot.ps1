param(
    [string]$Config = "user_data/configs/volatility_rotation_mr_binance_dryrun.json",
    [string[]]$AdditionalConfigs = @(),
    [string]$Quote = "USDT",
    [string]$Output = "user_data/pairs/binance_usdt_futures_snapshot.json"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command freqtrade -ErrorAction SilentlyContinue)) {
    throw "freqtrade is not available in PATH."
}

$args = @("test-pairlist", "--config", $Config)
foreach ($cfg in $AdditionalConfigs) {
    $args += @("--config", $cfg)
}
$args += @("--quote", $Quote, "--print-json")

$rawPairs = & freqtrade @args
$pairs = $rawPairs | ConvertFrom-Json
if (-not $pairs -or $pairs.Count -eq 0) {
    throw "No pairs were returned by freqtrade test-pairlist."
}

$snapshot = [ordered]@{
    '$schema' = 'https://schema.freqtrade.io/schema.json'
    exchange  = [ordered]@{
        pair_whitelist = @($pairs)
    }
}

$directory = Split-Path -Parent $Output
if ($directory) {
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
}

$snapshot | ConvertTo-Json -Depth 8 | Set-Content -Path $Output -Encoding UTF8
Write-Host "Saved $($pairs.Count) pairs to $Output"
