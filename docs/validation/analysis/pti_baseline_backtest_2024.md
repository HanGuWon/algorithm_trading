# PTI Baseline Backtest 2024

- Strategy: `VolatilityRotationMR`
- Config: `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json`
- Snapshot: `user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json`
- Timerange: `20240101-20241231`
- Backtest artifact: `user_data/backtest_results/backtest-result-2026-04-02_12-44-18.zip`

## Command

```bash
freqtrade backtesting \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json \
  --strategy VolatilityRotationMR \
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
| Trades | `3` |
| Total profit | `0.96%` |
| Profit USDT | `95.690` |
| Drawdown | `0.00%` |
| Long / Short trades | `3 / 0` |
| Win rate | `100%` |
| Average duration | `0:03:00` |

## Entry Tags

| entry_tag | Trades | Profit USDT | Total profit % |
| --- | ---: | ---: | ---: |
| `mr_long_extreme` | 3 | `95.690` | `0.96%` |
| `mr_short_extreme` | 0 | `0.000` | `0.00%` |

## Exit Tags

| exit_tag | Trades | Profit USDT | Total profit % |
| --- | ---: | ---: | ---: |
| `roi` | 2 | `69.913` | `0.70%` |
| `mean_hit` | 1 | `25.777` | `0.26%` |
| `vol_decay` | 0 | `0.000` | `0.00%` |
| `trend_expand` | 0 | `0.000` | `0.00%` |

## Caveats

- This run fixes the old current-market snapshot drift by using the PTI 2024 snapshot.
- The result is no longer degenerate, but `3` trades is still too sparse for optimization-grade statistics.
- Lookahead analysis on the same PTI baseline config remains inconclusive because the trade count stays below Freqtrade's minimum trade threshold.
