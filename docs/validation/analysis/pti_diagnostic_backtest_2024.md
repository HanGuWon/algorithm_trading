# PTI Diagnostic Backtest 2024

- Strategy: `VolatilityRotationMRDiagnostic`
- Config: `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json`
- Snapshot: `user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json`
- Timerange: `20240101-20241231`
- Backtest artifact: `user_data/backtest_results/backtest-result-2026-04-02_12-30-31.zip`

## Command

```bash
freqtrade backtesting \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json \
  --strategy VolatilityRotationMRDiagnostic \
  --strategy-path user_data/strategies \
  --timeframe 5m \
  --timeframe-detail 1m \
  --timerange 20240101-20241231 \
  --enable-protections \
  --export signals \
  --backtest-directory user_data/backtest_results
```

## Headline Metrics

| Metric | Value |
| --- | --- |
| Trades | `11` |
| Total profit | `3.03%` |
| Profit USDT | `302.645` |
| Drawdown | `0.00%` |
| Long / Short trades | `10 / 1` |
| Win rate | `100%` |
| Average duration | `0:03:00` |

## Entry Tags

| entry_tag | Trades | Profit USDT | Total profit % |
| --- | ---: | ---: | ---: |
| `mr_long_extreme` | 10 | `276.859` | `2.77%` |
| `mr_short_extreme` | 1 | `25.786` | `0.26%` |

## Exit Tags

| exit_tag | Trades | Profit USDT | Total profit % |
| --- | ---: | ---: | ---: |
| `roi` | 8 | `264.259` | `2.64%` |
| `mean_hit` | 2 | `12.600` | `0.13%` |
| `vol_decay` | 1 | `25.786` | `0.26%` |
| `trend_expand` | 0 | `0.000` | `0.00%` |

## Caveats

- This profile is research-only and intentionally relaxed for signal-density diagnosis.
- It improves the PTI sample from `3` to `11` trades and enables a usable lookahead verdict for the tested year.
- Even so, `11` trades is still below a comfortable sample size for optimization across multiple regimes.
