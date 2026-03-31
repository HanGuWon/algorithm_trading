param(
    [string]$Config = "user_data/configs/volatility_rotation_mr_backtest_static.json",
    [string[]]$AdditionalConfigs = @(),
    [string]$Strategy = "VolatilityRotationMR",
    [string]$Timerange = "20240101-20241231"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command freqtrade -ErrorAction SilentlyContinue)) {
    throw "freqtrade is not available in PATH."
}

$outputDir = "user_data/backtest_results"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$configArgs = @("--config", $Config)
foreach ($cfg in $AdditionalConfigs) {
    $configArgs += @("--config", $cfg)
}

$lookaheadLog = Join-Path $outputDir "lookahead-analysis.log"
$recursiveLog = Join-Path $outputDir "recursive-analysis.log"

& freqtrade lookahead-analysis @configArgs --strategy $Strategy --timeframe 5m --timerange $Timerange 2>&1 | Tee-Object -FilePath $lookaheadLog
& freqtrade recursive-analysis @configArgs --strategy $Strategy --timeframe 5m --timerange $Timerange 2>&1 | Tee-Object -FilePath $recursiveLog
