# Long-Only Parameter Stability

> Local neighborhood sweep only. This is not a new optimization pass and does not nominate a replacement candidate.

- Frozen evaluation window: `2024-01-01 -> 2024-07-01`
- Pair count: `50`
- Overall classification: `stable`

## Frozen Defaults

| parameter         |   frozen_value |
|:------------------|---------------:|
| vol_z_min         |          1     |
| price_z_threshold |          1.5   |
| bb_width_min      |          0.02  |
| adx_1h_max        |         24     |
| slope_cap         |          0.006 |

## Sweep Results

| label                  | changed_parameter   |   vol_z_min |   price_z_threshold |   bb_width_min |   adx_1h_max |   slope_cap |   raw_trade_count |   profit_pct |   profit_usdt |   max_drawdown_pct |
|:-----------------------|:--------------------|------------:|--------------------:|---------------:|-------------:|------------:|------------------:|-------------:|--------------:|-------------------:|
| baseline               | baseline            |        1    |                1.5  |          0.02  |           24 |       0.006 |                27 |         7.33 |       733.229 |               0.5  |
| vol_z_min_down         | vol_z_min           |        0.85 |                1.5  |          0.02  |           24 |       0.006 |                28 |         7.2  |       720.114 |               0.63 |
| vol_z_min_up           | vol_z_min           |        1.15 |                1.5  |          0.02  |           24 |       0.006 |                27 |         7.07 |       706.94  |               0.5  |
| price_z_threshold_down | price_z_threshold   |        1    |                1.35 |          0.02  |           24 |       0.006 |                27 |         7.33 |       733.229 |               0.5  |
| price_z_threshold_up   | price_z_threshold   |        1    |                1.65 |          0.02  |           24 |       0.006 |                27 |         7.33 |       733.229 |               0.5  |
| bb_width_min_down      | bb_width_min        |        1    |                1.5  |          0.015 |           24 |       0.006 |                27 |         7.33 |       733.229 |               0.5  |
| bb_width_min_up        | bb_width_min        |        1    |                1.5  |          0.025 |           24 |       0.006 |                27 |         7.33 |       733.229 |               0.5  |
| adx_1h_max_down        | adx_1h_max          |        1    |                1.5  |          0.02  |           22 |       0.006 |                22 |         6.39 |       639.025 |               0    |
| adx_1h_max_up          | adx_1h_max          |        1    |                1.5  |          0.02  |           26 |       0.006 |                30 |         8.21 |       821.4   |               0.5  |
| slope_cap_down         | slope_cap           |        1    |                1.5  |          0.02  |           24 |       0.005 |                27 |         7.33 |       733.229 |               0.5  |
| slope_cap_up           | slope_cap           |        1    |                1.5  |          0.02  |           24 |       0.007 |                27 |         7.33 |       733.229 |               0.5  |

## Interpretation

The frozen defaults stay in place unless the neighborhood evidence is overwhelmingly better, which this sweep is not designed to prove.

## Reproduction

```powershell
& .\.venv-freqtrade\Scripts\python.exe scripts\run_longonly_parameter_stability.py `
  --anchor 2024-01-01 `
  --window-months 6 `
  --output-md docs/validation/analysis/longonly_parameter_stability.md `
  --output-csv docs/validation/analysis/longonly_parameter_stability.csv `
  --logs-dir docs/validation/logs/longonly_parameter_stability `
  --backtest-dir user_data/backtest_results/longonly_parameter_stability
```
