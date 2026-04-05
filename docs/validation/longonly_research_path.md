# Long-Only Research Path

`VolatilityRotationMRLongOnly` and `VolatilityRotationMRDiagnosticLongOnly` are research-only profiles.

Do not use them for Binance dry-run or live deployment.
They exist only to answer whether the long side is robust enough to justify more research.

Primary configs:

- `user_data/configs/volatility_rotation_mr_backtest_top50_longonly.json`
- `user_data/configs/volatility_rotation_mr_backtest_top50_diagnostic_longonly.json`
- shared union top-50 pair overlay: `user_data/configs/volatility_rotation_mr_backtest_union_top50_pairs.json`

Primary artifacts:

- matrix: `docs/validation/alpha_validation_matrix_longonly.md`
- concentration: `docs/validation/analysis/longonly_concentration_risk.md`
- regime context: `docs/validation/analysis/longonly_regime_context.md`
- signal quality: `docs/validation/analysis/longonly_signal_quality.md`
- cost stress: `docs/validation/analysis/longonly_cost_stress.md`

## Discoverability

List strategies:

```powershell
.\scripts\freqtrade_cmd.ps1 list-strategies --strategy-path user_data/strategies
```

## Show Config

Baseline long-only:

```powershell
.\scripts\freqtrade_cmd.ps1 show-config -c user_data/configs/volatility_rotation_mr_backtest_top50_longonly.json
```

Diagnostic long-only:

```powershell
.\scripts\freqtrade_cmd.ps1 show-config -c user_data/configs/volatility_rotation_mr_backtest_top50_diagnostic_longonly.json
```

## Backtesting

Baseline long-only reference run:

```powershell
.\scripts\freqtrade_cmd.ps1 backtesting `
  --config user_data/configs/volatility_rotation_mr_backtest_top50_longonly.json `
  --strategy VolatilityRotationMRLongOnly `
  --strategy-path user_data/strategies `
  --timeframe 5m `
  --timerange 20240101-20240701 `
  --enable-protections `
  --export signals `
  --backtest-directory user_data/backtest_results/longonly_reference
```

Diagnostic long-only reference run:

```powershell
.\scripts\freqtrade_cmd.ps1 backtesting `
  --config user_data/configs/volatility_rotation_mr_backtest_top50_diagnostic_longonly.json `
  --strategy VolatilityRotationMRDiagnosticLongOnly `
  --strategy-path user_data/strategies `
  --timeframe 5m `
  --timerange 20240101-20240701 `
  --enable-protections `
  --export signals `
  --backtest-directory user_data/backtest_results/longonly_reference
```

## Recursive Analysis

Baseline long-only:

```powershell
.\scripts\freqtrade_cmd.ps1 recursive-analysis `
  --config user_data/configs/volatility_rotation_mr_backtest_top50_longonly.json `
  --strategy VolatilityRotationMRLongOnly `
  --strategy-path user_data/strategies `
  --timeframe 5m `
  --timerange 20240101-20240701 `
  --startup-candle 1600 2000 2400 `
  --pairs ETH/USDT:USDT
```

Diagnostic long-only:

```powershell
.\scripts\freqtrade_cmd.ps1 recursive-analysis `
  --config user_data/configs/volatility_rotation_mr_backtest_top50_diagnostic_longonly.json `
  --strategy VolatilityRotationMRDiagnosticLongOnly `
  --strategy-path user_data/strategies `
  --timeframe 5m `
  --timerange 20240101-20240701 `
  --startup-candle 1600 2000 2400 `
  --pairs ETH/USDT:USDT
```

## Lookahead Analysis

Baseline long-only:

```powershell
.\scripts\freqtrade_cmd.ps1 lookahead-analysis `
  --config user_data/configs/volatility_rotation_mr_backtest_top50_longonly.json `
  --config user_data/configs/volatility_rotation_mr_analysis_market.json `
  --strategy VolatilityRotationMRLongOnly `
  --strategy-path user_data/strategies `
  --timeframe 5m `
  --timeframe-detail 1m `
  --timerange 20240101-20240701 `
  --lookahead-analysis-exportfilename docs/validation/logs/lookahead-analysis-longonly.csv `
  --backtest-directory user_data/backtest_results/longonly_reference
```

Diagnostic long-only:

```powershell
.\scripts\freqtrade_cmd.ps1 lookahead-analysis `
  --config user_data/configs/volatility_rotation_mr_backtest_top50_diagnostic_longonly.json `
  --config user_data/configs/volatility_rotation_mr_analysis_market.json `
  --strategy VolatilityRotationMRDiagnosticLongOnly `
  --strategy-path user_data/strategies `
  --timeframe 5m `
  --timeframe-detail 1m `
  --timerange 20240101-20240701 `
  --lookahead-analysis-exportfilename docs/validation/logs/lookahead-analysis-diagnostic-longonly.csv `
  --backtest-directory user_data/backtest_results/longonly_reference
```

## Backtesting Analysis

Baseline long-only:

```powershell
.\scripts\freqtrade_cmd.ps1 backtesting-analysis `
  --config user_data/configs/volatility_rotation_mr_backtest_top50_longonly.json `
  --backtest-directory user_data/backtest_results/longonly_reference `
  --analysis-groups 1 2 5 `
  --analysis-to-csv `
  --analysis-csv-path docs/validation/analysis/longonly_reference `
  --enter-reason-list mr_long_extreme `
  --exit-reason-list mean_hit time_stop vol_decay trend_expand roi `
  --timerange 20240101-20240701
```

Diagnostic long-only:

```powershell
.\scripts\freqtrade_cmd.ps1 backtesting-analysis `
  --config user_data/configs/volatility_rotation_mr_backtest_top50_diagnostic_longonly.json `
  --backtest-directory user_data/backtest_results/longonly_reference `
  --analysis-groups 1 2 5 `
  --analysis-to-csv `
  --analysis-csv-path docs/validation/analysis/diagnostic_longonly_reference `
  --enter-reason-list mr_long_extreme `
  --exit-reason-list mean_hit time_stop vol_decay trend_expand roi `
  --timerange 20240101-20240701
```

## De-Overlapped Research Matrix

```powershell
& .\.venv-freqtrade\Scripts\python.exe scripts\run_longonly_validation_matrix.py `
  --anchors 2022-01-01 2022-07-01 2023-01-01 2023-07-01 2024-01-01 2024-07-01 2025-01-01 `
  --window-months 6 `
  --snapshot-top-n 50 `
  --output-md docs/validation/alpha_validation_matrix_longonly.md `
  --output-csv docs/validation/alpha_validation_matrix_longonly.csv `
  --logs-dir docs/validation/logs/longonly_matrix `
  --backtest-dir user_data/backtest_results/longonly_matrix
```

## Follow-On Diagnostics

Concentration:

```powershell
& .\.venv-freqtrade\Scripts\python.exe scripts\run_longonly_concentration_analysis.py `
  --matrix-csv docs/validation/alpha_validation_matrix_longonly.csv `
  --backtest-dir user_data/backtest_results/longonly_matrix `
  --output-md docs/validation/analysis/longonly_concentration_risk.md `
  --output-csv docs/validation/analysis/longonly_concentration_risk.csv
```

Regime context:

```powershell
& .\.venv-freqtrade\Scripts\python.exe scripts\run_longonly_regime_context.py `
  --anchors 2022-01-01 2022-07-01 2023-01-01 2023-07-01 2024-01-01 2024-07-01 2025-01-01 `
  --window-months 6 `
  --snapshot-top-n 50 `
  --matrix-csv docs/validation/alpha_validation_matrix_longonly.csv `
  --backtest-dir user_data/backtest_results/longonly_matrix `
  --output-md docs/validation/analysis/longonly_regime_context.md `
  --output-csv docs/validation/analysis/longonly_regime_context.csv
```

Signal quality:

```powershell
& .\.venv-freqtrade\Scripts\python.exe scripts\run_longonly_signal_quality.py `
  --anchors 2022-01-01 2022-07-01 2023-01-01 2023-07-01 2024-01-01 2024-07-01 2025-01-01 `
  --window-months 6 `
  --snapshot-top-n 50 `
  --matrix-csv docs/validation/alpha_validation_matrix_longonly.csv `
  --backtest-dir user_data/backtest_results/longonly_matrix `
  --output-md docs/validation/analysis/longonly_signal_quality.md `
  --output-csv docs/validation/analysis/longonly_signal_quality.csv
```

Cost stress:

```powershell
& .\.venv-freqtrade\Scripts\python.exe scripts\run_longonly_cost_stress.py `
  --matrix-csv docs/validation/alpha_validation_matrix_longonly.csv `
  --backtest-dir user_data/backtest_results/longonly_matrix `
  --output-md docs/validation/analysis/longonly_cost_stress.md `
  --output-csv docs/validation/analysis/longonly_cost_stress.csv
```
