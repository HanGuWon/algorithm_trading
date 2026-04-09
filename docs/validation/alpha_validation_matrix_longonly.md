# Long-Only Alpha Validation Matrix

> Research-only artifact. These long-only profiles are for robustness diagnosis only and are not live deployment candidates.

- Anchors: `2022-01-01, 2022-07-01, 2023-01-01, 2023-07-01, 2024-01-01, 2024-07-01, 2025-01-01`
- Window design: non-overlapping forward `6m` windows
- Snapshot top_n: `50`
- Usable-sample threshold: `20` trades per window

## Matrix

| anchor     | window_label   | strategy_variant     |   pair_count |   raw_trade_count |   unique_trade_count |   profit_pct |   profit_usdt |   drawdown_pct | usable_sample   | monthly_distribution             | pair_contribution                                                                                                                                                                     |
|:-----------|:---------------|:---------------------|-------------:|------------------:|---------------------:|-------------:|--------------:|---------------:|:----------------|:---------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 2022-01-01 | 6m             | baseline_long_only   |           44 |                 1 |                    1 |         0.29 |        28.996 |           0    | no              | 2022-04:1                        | FIL/USDT:USDT:28.996                                                                                                                                                                  |
| 2022-01-01 | 6m             | diagnostic_long_only |           44 |                 5 |                    5 |        -0.69 |       -68.852 |           1.12 | no              | 2022-04:1, 2022-05:4             | FIL/USDT:USDT:28.996, SOL/USDT:USDT:14.084, DOT/USDT:USDT:-15.374, CRV/USDT:USDT:-47.252, LINK/USDT:USDT:-49.306                                                                      |
| 2022-07-01 | 6m             | baseline_long_only   |           46 |                 0 |                    0 |         0    |         0     |           0    | no              |                                  |                                                                                                                                                                                       |
| 2022-07-01 | 6m             | diagnostic_long_only |           46 |                 2 |                    2 |         0.49 |        48.875 |           0    | no              | 2022-11:2                        | LINK/USDT:USDT:30.967, GALA/USDT:USDT:17.908                                                                                                                                          |
| 2023-01-01 | 6m             | baseline_long_only   |           50 |                 0 |                    0 |         0    |         0     |           0    | no              |                                  |                                                                                                                                                                                       |
| 2023-01-01 | 6m             | diagnostic_long_only |           50 |                 2 |                    2 |         0.65 |        64.795 |           0    | no              | 2023-06:2                        | ALGO/USDT:USDT:34.958, ONT/USDT:USDT:29.837                                                                                                                                           |
| 2023-07-01 | 6m             | baseline_long_only   |           50 |                 0 |                    0 |         0    |         0     |           0    | no              |                                  |                                                                                                                                                                                       |
| 2023-07-01 | 6m             | diagnostic_long_only |           50 |                 2 |                    2 |        -0.09 |        -9.365 |           0.09 | no              | 2023-11:1, 2023-12:1             | MAGIC/USDT:USDT:-3.494, 1000PEPE/USDT:USDT:-5.872                                                                                                                                     |
| 2024-01-01 | 6m             | baseline_long_only   |           50 |                11 |                   11 |         3.11 |       310.782 |           0    | no              | 2024-01:10, 2024-03:1            | ATOM/USDT:USDT:35.292, DOT/USDT:USDT:34.956, AXS/USDT:USDT:34.561, FET/USDT:USDT:34.133, CRV/USDT:USDT:32.785, SOL/USDT:USDT:26.322, INJ/USDT:USDT:26.303, DYDX/USDT:USDT:25.352      |
| 2024-01-01 | 6m             | diagnostic_long_only |           50 |                27 |                   27 |         7.33 |       733.229 |           0.5  | yes             | 2024-01:23, 2024-03:2, 2024-06:2 | AXS/USDT:USDT:55.793, SOL/USDT:USDT:37.881, NEO/USDT:USDT:37.009, 1000SHIB/USDT:USDT:36.640, AAVE/USDT:USDT:36.296, UNI/USDT:USDT:36.228, ATOM/USDT:USDT:36.167, LTC/USDT:USDT:35.824 |
| 2024-07-01 | 6m             | baseline_long_only   |           50 |                 0 |                    0 |         0    |         0     |           0    | no              |                                  |                                                                                                                                                                                       |
| 2024-07-01 | 6m             | diagnostic_long_only |           50 |                 0 |                    0 |         0    |         0     |           0    | no              |                                  |                                                                                                                                                                                       |
| 2025-01-01 | 6m             | baseline_long_only   |           50 |                 0 |                    0 |         0    |         0     |           0    | no              |                                  |                                                                                                                                                                                       |
| 2025-01-01 | 6m             | diagnostic_long_only |           50 |                 0 |                    0 |         0    |         0     |           0    | no              |                                  |                                                                                                                                                                                       |

## Totals

| strategy_variant     |   raw_trade_count |   unique_trade_count |   profit_pct |   profit_usdt |   max_drawdown_pct |   usable_windows |
|:---------------------|------------------:|---------------------:|-------------:|--------------:|-------------------:|-----------------:|
| baseline_long_only   |                12 |                   12 |         3.4  |       339.778 |               0    |                0 |
| diagnostic_long_only |                38 |                   38 |         7.69 |       768.682 |               1.12 |                1 |

## Decision Framing

Use this matrix to judge whether the long-only subclasses are robust enough to justify more research.
A single profitable burst is not enough if the edge collapses under concentration, regime, or cost stress.
