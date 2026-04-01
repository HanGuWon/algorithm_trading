# Public Validation Summary

## Status

This repository keeps only a small public validation summary.
Large raw backtest blobs and exchange secrets must not be committed.

Validation status as of `2026-04-01`:

- Freqtrade executable availability in this workspace: `verified via local pinned venv`
- Freqtrade version: `2026.2`
- Python version: `3.13.3`
- CCXT version: `4.5.46`
- Notes:
  - Windows DNS resolution initially failed inside `ccxt.async_support` with `aiodns/pycares`; local validation used the same pinned Freqtrade version after removing those optional resolver packages from the local venv.
  - The committed static snapshot was regenerated successfully, but it drifted materially because the runtime dynamic pairlist now selects 2025/2026 listings that did not exist during most of the 2024 research window.

## Final Merged Config

Commands used:

```bash
freqtrade show-config \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json
```

```bash
freqtrade show-config \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json \
  --config user_data/configs/volatility_rotation_mr_private.json
```

```bash
freqtrade show-config \
  --config user_data/configs/volatility_rotation_mr_binance_live.json \
  --config user_data/configs/volatility_rotation_mr_private.json
```

Effective config files:

| Purpose | Configs |
| --- | --- |
| Research | `volatility_rotation_mr_backtest_static.json` |
| Dry-run | `volatility_rotation_mr_binance_dryrun.json` + private overlay |
| Live | `volatility_rotation_mr_binance_live.json` + private overlay |

Observed result:

- Backtest merged config validated successfully.
- Dry-run merged config validated successfully.
- Live merged config validated successfully.
- `stoploss_price_type = mark` appears in the merged live config.

## Snapshot Generation

```bash
freqtrade test-pairlist \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json \
  --quote USDT \
  --print-json
```

```powershell
.\scripts\save_pair_snapshot.ps1 `
  -Config user_data/configs/volatility_rotation_mr_binance_dryrun.json `
  -AdditionalConfigs user_data/configs/volatility_rotation_mr_private.json `
  -Output user_data/pairs/binance_usdt_futures_snapshot.json
```

Observed result:

- Snapshot regeneration succeeded.
- The snapshot changed from a hand-seeded 25-pair major list to a 9-pair runtime snapshot:
  - `ETH/USDT:USDT`
  - `XAG/USDT:USDT`
  - `ZEC/USDT:USDT`
  - `KERNEL/USDT:USDT`
  - `HYPE/USDT:USDT`
  - `RIVER/USDT:USDT`
  - `CRCL/USDT:USDT`
  - `PIPPIN/USDT:USDT`
  - `SUI/USDT:USDT`
- This looks like expected market drift from the active runtime filters, not a config parsing issue.
- For the 2024 research window, only `ETH/USDT:USDT`, `ZEC/USDT:USDT`, and `SUI/USDT:USDT` had usable historical depth across the downloaded range.

## Backtest Command

```bash
freqtrade backtesting \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --timeframe-detail 1m \
  --timerange 20240101-20241231 \
  --enable-protections \
  --export signals \
  --backtest-directory user_data/backtest_results
```

Download command used before the run:

```bash
freqtrade download-data \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --trading-mode futures \
  --timeframes 1m 5m 1h \
  --timerange 20231218-20250115
```

## Bias Checks

Lookahead:

```bash
freqtrade lookahead-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --config user_data/configs/volatility_rotation_mr_analysis_market.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --timeframe-detail 1m \
  --timerange 20240101-20241231 \
  --lookahead-analysis-exportfilename docs/validation/logs/lookahead-analysis.csv \
  --backtest-directory user_data/backtest_results
```

Recursive:

```bash
freqtrade recursive-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --timerange 20240101-20241231 \
  --startup-candle 1600 2000 2400
```

Observed result:

- `recursive-analysis` completed successfully.
- Result: `No lookahead bias on indicators found.`
- Recursive deltas reported as `0.000%` or `-0.000%` across the checked indicators in the sampled comparison.
- `lookahead-analysis` completed successfully after adding the analysis-only overlay.
- Result: `too few trades caught (0/10). Test failed.`
- This is not evidence of lookahead bias. It means the validated run did not generate enough trades for the lookahead tester to reach a verdict.
- `volatility_rotation_mr_analysis_market.json` is now the minimal analysis-only overlay required for this command path on Freqtrade `2026.2`.

## Hyperopt Command

```bash
freqtrade hyperopt \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --timeframe-detail 1m \
  --spaces buy sell \
  --hyperopt-loss SharpeHyperOptLossDaily \
  --timerange 20240101-20241231 \
  --random-state 42 \
  --job-workers 1 \
  -e 10
```

Observed result:

- Hyperopt completed successfully after installing missing optional dependencies for the validated environment.
- Result: `No good result found for given optimization function in 10 epochs.`
- This is consistent with the zero-trade baseline backtest.

## Backtesting Analysis Command

```bash
freqtrade backtesting-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --backtest-directory user_data/backtest_results \
  --analysis-groups 1 2 5 \
  --analysis-to-csv \
  --analysis-csv-path docs/validation/analysis \
  --enter-reason-list mr_long_extreme mr_short_extreme \
  --exit-reason-list mean_hit time_stop vol_decay trend_expand \
  --timerange 20240101-20241231
```

Observed result:

- Command completed successfully.
- No grouped trade rows were produced because the underlying backtest generated zero trades.

## Operational Validation

Validated commands:

- `scripts/preflight_binance.ps1 -Mode dryrun`
- `scripts/preflight_binance.ps1 -Mode live`
- `scripts/start_dryrun.ps1` was started briefly and reached exchange initialization in dry-run mode before manual shutdown.
- `scripts/start_live.ps1` was started with the live profile plus a temporary local `dry_run: true` overlay and reached worker startup without rejecting `stoploss_price_type = mark`.

Observed result:

- `stoploss_price_type = mark` was accepted during startup validation of the live profile when layered with a temporary dry-run override.
- Full authenticated live trading remains intentionally unvalidated in the public repository because real Binance credentials are required and must not be committed.

## Headline Metrics

| Metric | Value |
| --- | --- |
| Trades | `0` |
| Total Profit | `0.0%` |
| Sharpe | `N/A (no closed trades)` |
| Max Drawdown | `0.00%` |
| Win Rate | `0%` |
| Avg Trade Duration | `0:00` |

## Entry Tag Breakdown

| entry_tag | Trades | Profit % | Notes |
| --- | --- | --- | --- |
| `mr_long_extreme` | `0` | `0.0` | No entries generated in the validated 2024 static research run. |
| `mr_short_extreme` | `0` | `0.0` | No entries generated in the validated 2024 static research run. |

## Exit Tag Breakdown

| exit_tag | Trades | Profit % | Notes |
| --- | --- | --- | --- |
| `mean_hit` | `0` | `0.0` | No exits because no trades were opened. |
| `time_stop` | `0` | `0.0` | No exits because no trades were opened. |
| `vol_decay` | `0` | `0.0` | No exits because no trades were opened. |
| `trend_expand` | `0` | `0.0` | No exits because no trades were opened. |

## Limitations

- The validated research environment is real, but the current-market static snapshot drifted away from the 2024 test window.
- This drift leaves only a subset of the snapshot with usable 2024 futures history and likely contributes to the zero-trade outcome.
- Published research numbers should continue to use the static research config, but the snapshot itself should be reviewed as a point-in-time research artifact rather than a perpetual benchmark.
- A full authenticated live trading session still requires real Binance credentials, correct account mode, and human operator checks on exchange-side stop orders.
