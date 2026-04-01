param(
    [string]$Config = "user_data/configs/volatility_rotation_mr_backtest_static.json",
    [string[]]$AdditionalConfigs = @(),
    [string]$Strategy = "VolatilityRotationMR",
    [string]$Timerange = "20240101-20241231",
    [string]$LookaheadOverlay = "user_data/configs/volatility_rotation_mr_analysis_market.json"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command freqtrade -ErrorAction SilentlyContinue)) {
    $freqtradeCmd = Join-Path $PSScriptRoot "freqtrade_cmd.ps1"
} else {
    $freqtradeCmd = "freqtrade"
}

$outputDir = "user_data/backtest_results"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$configArgs = @("--config", $Config)
foreach ($cfg in $AdditionalConfigs) {
    $configArgs += @("--config", $cfg)
}
$lookaheadConfigArgs = @($configArgs)
if (Test-Path $LookaheadOverlay) {
    $lookaheadConfigArgs += @("--config", $LookaheadOverlay)
}

$lookaheadLog = Join-Path $outputDir "lookahead-analysis.log"
$recursiveLog = Join-Path $outputDir "recursive-analysis.log"

& $freqtradeCmd lookahead-analysis @lookaheadConfigArgs --strategy $Strategy --timeframe 5m --timeframe-detail 1m --timerange $Timerange > $lookaheadLog 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "lookahead-analysis failed. See $lookaheadLog"
}

& $freqtradeCmd recursive-analysis @configArgs --strategy $Strategy --timeframe 5m --timerange $Timerange --startup-candle 1600 2000 2400 > $recursiveLog 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "recursive-analysis failed. See $recursiveLog"
}

Write-Host "Saved lookahead-analysis log to $lookaheadLog"
Write-Host "Saved recursive-analysis log to $recursiveLog"
