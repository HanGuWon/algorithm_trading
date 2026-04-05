# Long-Only Promotion Study

> Frozen-candidate study only. No new hyperopt, no threshold retuning in the conclusion path, and no strategy redesign.

## Frozen Candidate

- Strategy: `VolatilityRotationMRDiagnosticLongOnly`
- Snapshot design: point-in-time top-50 universes on the broadened PTI research set
- Selection evidence ends at `2024-01-01 -> 2024-07-01`.
- Promotion evidence starts at `2024-07-01 -> 2025-01-01`.

| parameter         |   frozen_value |
|:------------------|---------------:|
| vol_z_min         |          1     |
| price_z_threshold |          1.5   |
| bb_width_min      |          0.02  |
| adx_1h_max        |         24     |
| slope_cap         |          0.006 |

## Candidate-Selection Reference

| study_label         | anchor                 | timerange                                  |   raw_trade_count |   unique_trade_count |   profit_pct |   profit_usdt |   max_drawdown_pct | monthly_distribution                                                                               | pair_contribution                                                                                                                                                                     |
|:--------------------|:-----------------------|:-------------------------------------------|------------------:|---------------------:|-------------:|--------------:|-------------------:|:---------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| selection_reference | 2022-01-01..2024-01-01 | 20220101-20240701 (selection windows only) |                38 |                   38 |         7.69 |       768.682 |               1.12 | 2022-04:1, 2022-05:4, 2022-11:2, 2023-06:2, 2023-11:1, 2023-12:1, 2024-01:23, 2024-03:2, 2024-06:2 | FIL/USDT:USDT:59.479, AXS/USDT:USDT:55.793, SOL/USDT:USDT:51.965, GALA/USDT:USDT:39.901, NEO/USDT:USDT:37.009, 1000SHIB/USDT:USDT:36.640, AAVE/USDT:USDT:36.296, UNI/USDT:USDT:36.228 |

## Promotion Holdouts

| study_label         | anchor     |   window_months | timerange         |   raw_trade_count |   unique_trade_count |   profit_pct |   profit_usdt |   max_drawdown_pct | sample_large_enough   | monthly_distribution   | pair_contribution   |
|:--------------------|:-----------|----------------:|:------------------|------------------:|---------------------:|-------------:|--------------:|-------------------:|:----------------------|:-----------------------|:--------------------|
| holdout_2024h2      | 2024-07-01 |               6 | 20240701-20250101 |                 0 |                    0 |            0 |             0 |                  0 | no                    |                        |                     |
| holdout_2025h1      | 2025-01-01 |               6 | 20250101-20250701 |                 0 |                    0 |            0 |             0 |                  0 | no                    |                        |                     |
| holdout_forward_12m | 2024-07-01 |              12 | 20240701-20250701 |                 0 |                    0 |            0 |             0 |                  0 | no                    |                        |                     |

## Decision

- Combined holdout raw trades: `0`
- Combined holdout profit: `0.000 USDT`
- Holdout evidence large enough to justify continued research? `No. Forward holdouts do not supply enough sample to justify continued research.`

## Reproduction

```powershell
& .\.venv-freqtrade\Scripts\python.exe scripts\run_longonly_promotion_study.py `
  --selection-matrix-csv docs/validation/alpha_validation_matrix_longonly.csv `
  --selection-backtest-dir user_data/backtest_results/longonly_matrix `
  --output-md docs/validation/longonly_promotion_study.md `
  --output-csv docs/validation/longonly_promotion_study.csv `
  --logs-dir docs/validation/logs/longonly_promotion `
  --backtest-dir user_data/backtest_results/longonly_promotion
```
