# Public Validation Summary

## Status

This repository keeps only a small public validation summary.
Large raw backtest blobs and exchange secrets must not be committed.

Current placeholder status:

- Freqtrade executable availability in this workspace: `not verified in-repo`
- Last template refresh date: `2026-04-01`
- Notes: fill this document after running the commands below in a Freqtrade-enabled environment

## Final Merged Config

Record the exact merged config command and the effective config files used.

Example:

```bash
freqtrade show-config \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --strategy VolatilityRotationMR
```

Effective config files:

| Purpose | Configs |
| --- | --- |
| Research | `volatility_rotation_mr_backtest_static.json` |
| Dry-run | `volatility_rotation_mr_binance_dryrun.json` + private overlay |
| Live | `volatility_rotation_mr_binance_live.json` + private overlay |

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
  --export-filename user_data/backtest_results/volatility_rotation_mr_signals.json
```

## Bias Checks

Lookahead:

```bash
freqtrade lookahead-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --timerange 20240101-20241231
```

Recursive:

```bash
freqtrade recursive-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --timerange 20240101-20241231
```

## Headline Metrics

Fill after a real run:

| Metric | Value |
| --- | --- |
| Trades | `TBD` |
| CAGR / Total Profit | `TBD` |
| Sharpe | `TBD` |
| Max Drawdown | `TBD` |
| Win Rate | `TBD` |
| Avg Trade Duration | `TBD` |

## Entry Tag Breakdown

| entry_tag | Trades | Profit % | Notes |
| --- | --- | --- | --- |
| `mr_long_extreme` | `TBD` | `TBD` |  |
| `mr_short_extreme` | `TBD` | `TBD` |  |

## Exit Tag Breakdown

| exit_tag | Trades | Profit % | Notes |
| --- | --- | --- | --- |
| `mean_hit` | `TBD` | `TBD` |  |
| `time_stop` | `TBD` | `TBD` |  |
| `vol_decay` | `TBD` | `TBD` |  |
| `trend_expand` | `TBD` | `TBD` |  |

## Limitations

- This summary template is committed even when the local environment cannot execute Freqtrade.
- Use the static research config for published research numbers.
- Do not mix dynamic runtime pairlists with reproducibility-sensitive headline metrics.
