# Deduped PTI Alpha Validation Matrix

- Anchors: `2022-01-01, 2022-07-01, 2023-01-01, 2023-07-01, 2024-01-01, 2024-07-01, 2025-01-01`
- Window design: non-overlapping forward `6m` windows
- Snapshot top_n: `50`
- Usable-sample threshold: `20` trades per window

## Matrix

| anchor     | window_label   | strategy_variant   |   pair_count |   trades |   profit_pct |   profit_usdt |   drawdown_pct |   long_trades |   short_trades | usable_sample   | monthly_distribution             | pair_contribution                                                                                                                                   |
|:-----------|:---------------|:-------------------|-------------:|---------:|-------------:|--------------:|---------------:|--------------:|---------------:|:----------------|:---------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------|
| 2022-01-01 | 6m             | baseline           |           44 |        3 |         0.49 |        49.1   |           0    |             1 |              2 | no              | 2022-04:1, 2022-06:2             | FIL/USDT:USDT:1, LINK/USDT:USDT:1, SAND/USDT:USDT:1                                                                                                 |
| 2022-01-01 | 6m             | diagnostic         |           44 |        8 |        -0.14 |       -14.231 |           1.12 |             5 |              3 | no              | 2022-04:1, 2022-05:4, 2022-06:3  | LINK/USDT:USDT:2, DOT/USDT:USDT:1, CRV/USDT:USDT:1, FIL/USDT:USDT:1, GALA/USDT:USDT:1, SAND/USDT:USDT:1, SOL/USDT:USDT:1                            |
| 2022-07-01 | 6m             | baseline           |           46 |        0 |         0    |         0     |           0    |             0 |              0 | no              |                                  |                                                                                                                                                     |
| 2022-07-01 | 6m             | diagnostic         |           46 |        2 |         0.49 |        48.875 |           0    |             2 |              0 | no              | 2022-11:2                        | GALA/USDT:USDT:1, LINK/USDT:USDT:1                                                                                                                  |
| 2023-01-01 | 6m             | baseline           |           50 |        0 |         0    |         0     |           0    |             0 |              0 | no              |                                  |                                                                                                                                                     |
| 2023-01-01 | 6m             | diagnostic         |           50 |        2 |         0.65 |        64.795 |           0    |             2 |              0 | no              | 2023-06:2                        | ALGO/USDT:USDT:1, ONT/USDT:USDT:1                                                                                                                   |
| 2023-07-01 | 6m             | baseline           |           50 |        0 |         0    |         0     |           0    |             0 |              0 | no              |                                  |                                                                                                                                                     |
| 2023-07-01 | 6m             | diagnostic         |           50 |        3 |         0.26 |        25.524 |           0.09 |             2 |              1 | no              | 2023-07:1, 2023-11:1, 2023-12:1  | 1000PEPE/USDT:USDT:1, MAGIC/USDT:USDT:1, XRP/USDT:USDT:1                                                                                            |
| 2024-01-01 | 6m             | baseline           |           50 |       11 |         3.11 |       310.782 |           0    |            11 |              0 | no              | 2024-01:10, 2024-03:1            | APE/USDT:USDT:1, ATOM/USDT:USDT:1, AXS/USDT:USDT:1, CRV/USDT:USDT:1, DOT/USDT:USDT:1, DYDX/USDT:USDT:1, FET/USDT:USDT:1, GALA/USDT:USDT:1           |
| 2024-01-01 | 6m             | diagnostic         |           50 |       27 |         7.33 |       733.229 |           0.5  |            27 |              0 | yes             | 2024-01:23, 2024-03:2, 2024-06:2 | CRV/USDT:USDT:3, AXS/USDT:USDT:2, 1000BONK/USDT:USDT:1, 1000SHIB/USDT:USDT:1, APE/USDT:USDT:1, AAVE/USDT:USDT:1, AVAX/USDT:USDT:1, ATOM/USDT:USDT:1 |
| 2024-07-01 | 6m             | baseline           |           50 |        0 |         0    |         0     |           0    |             0 |              0 | no              |                                  |                                                                                                                                                     |
| 2024-07-01 | 6m             | diagnostic         |           50 |        1 |         0.25 |        25.091 |           0    |             0 |              1 | no              | 2024-08:1                        | XRP/USDT:USDT:1                                                                                                                                     |
| 2025-01-01 | 6m             | baseline           |           50 |        1 |         0.16 |        16.499 |           0    |             0 |              1 | no              | 2025-01:1                        | VIRTUAL/USDT:USDT:1                                                                                                                                 |
| 2025-01-01 | 6m             | diagnostic         |           50 |        2 |         0.26 |        25.587 |           0.04 |             0 |              2 | no              | 2025-01:1, 2025-04:1             | FARTCOIN/USDT:USDT:1, VIRTUAL/USDT:USDT:1                                                                                                           |

## Raw vs Unique Totals

| strategy_variant   |   raw_trades |   unique_trades |   profit_usdt |   long_trades |   short_trades |
|:-------------------|-------------:|----------------:|--------------:|--------------:|---------------:|
| baseline           |           15 |              15 |       376.381 |            12 |              3 |
| diagnostic         |           45 |              45 |       908.87  |            38 |              7 |

## Notes

This matrix uses non-overlapping windows, so raw and unique trade totals should match unless a trade signature is duplicated unexpectedly.
Use this artifact as the primary de-overlapped alpha-validation path instead of the older overlapping 3m/6m matrix.
