# Long-Only Time Concentration Stress

> Explicit time-cluster stress on the frozen diagnostic long-only candidate.

## Stress Scenarios

| scenario                  |   raw_trade_count |   profit_usdt |   max_drawdown_usdt | status             |
|:--------------------------|------------------:|--------------:|--------------------:|:-------------------|
| selection_reference       |                38 |       768.682 |             111.933 | survives           |
| remove_best_month         |                15 |        46.275 |             111.933 | weakens materially |
| remove_best_two_months    |                13 |       -18.521 |             111.933 | collapses          |
| remove_best_anchor_window |                11 |        35.453 |             111.933 | weakens materially |
| promotion_holdouts_only   |                 0 |         0     |               0     | collapses          |

## Selection-Like vs Holdout Windows

| bucket                  |   windows |   raw_trade_count |   profit_usdt |   max_drawdown_pct |
|:------------------------|----------:|------------------:|--------------:|-------------------:|
| selection_like_windows  |         5 |                38 |       768.682 |               1.12 |
| forward_holdout_windows |         2 |                 0 |         0     |               0    |

## Dominant Windows

| month   |   raw_trade_count |   profit_usdt |
|:--------|------------------:|--------------:|
| 2024-01 |                23 |     722.407   |
| 2023-06 |                 2 |      64.7954  |
| 2024-03 |                 2 |      58.0495  |
| 2022-11 |                 2 |      48.8752  |
| 2022-04 |                 1 |      28.9962  |
| 2023-11 |                 1 |      -3.49388 |

| anchor     |   raw_trade_count |   profit_usdt |
|:-----------|------------------:|--------------:|
| 2024-01-01 |                27 |     733.229   |
| 2023-01-01 |                 2 |      64.7954  |
| 2022-07-01 |                 2 |      48.8752  |
| 2023-07-01 |                 2 |      -9.36546 |
| 2022-01-01 |                 5 |     -68.8522  |

## Interpretation

This stress isolates whether the published long-only edge survives removal of the dominant burst and whether anything remains in forward holdouts.

## Reproduction

```powershell
& .\.venv-freqtrade\Scripts\python.exe scripts\run_longonly_time_concentration_stress.py `
  --selection-matrix-csv docs/validation/alpha_validation_matrix_longonly.csv `
  --selection-backtest-dir user_data/backtest_results/longonly_matrix `
  --promotion-csv docs/validation/longonly_promotion_study.csv `
  --output-md docs/validation/analysis/longonly_time_concentration_stress.md
```
