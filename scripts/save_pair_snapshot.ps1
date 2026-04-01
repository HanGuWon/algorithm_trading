param(
    [string]$Config = "user_data/configs/volatility_rotation_mr_binance_dryrun.json",
    [string[]]$AdditionalConfigs = @(),
    [string]$Quote = "USDT",
    [string]$Output = "user_data/pairs/binance_usdt_futures_snapshot.json"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command freqtrade -ErrorAction SilentlyContinue)) {
    $freqtradeCmd = Join-Path $PSScriptRoot "freqtrade_cmd.ps1"
} else {
    $freqtradeCmd = "freqtrade"
}

$args = @("test-pairlist", "--config", $Config)
foreach ($cfg in $AdditionalConfigs) {
    $args += @("--config", $cfg)
}
$args += @("--quote", $Quote, "--print-json")

$rawPairs = & $freqtradeCmd @args
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

$json = $snapshot | ConvertTo-Json -Depth 8
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText([System.IO.Path]::GetFullPath($Output), $json, $utf8NoBom)
Write-Host "Saved $($pairs.Count) pairs to $Output"
