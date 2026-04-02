# PTI Alpha Validation Matrix

- Anchors: `2023-07-01, 2024-01-01, 2024-04-01, 2024-07-01, 2024-10-01, 2025-01-01`
- Windows: `3m, 6m`
- Trade-count threshold for usable sample: `20` trades

## Matrix

| anchor     | window_label   | strategy_variant   |   trades |   profit_pct |   profit_usdt |   drawdown_pct |   long_trades |   short_trades | usable_sample   | monthly_distribution   |
|:-----------|:---------------|:-------------------|---------:|-------------:|--------------:|---------------:|--------------:|---------------:|:----------------|:-----------------------|
| 2023-07-01 | 3m             | baseline           |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |
| 2023-07-01 | 3m             | diagnostic         |        1 |         0.35 |        34.922 |              0 |             0 |              1 | no              | 2023-07:1              |
| 2023-07-01 | 6m             | baseline           |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |
| 2023-07-01 | 6m             | diagnostic         |        1 |         0.35 |        34.922 |              0 |             0 |              1 | no              | 2023-07:1              |
| 2024-01-01 | 3m             | baseline           |        3 |         0.96 |        95.813 |              0 |             3 |              0 | no              | 2024-01:2, 2024-03:1   |
| 2024-01-01 | 3m             | diagnostic         |       10 |         3.39 |       338.643 |              0 |            10 |              0 | no              | 2024-01:9, 2024-03:1   |
| 2024-01-01 | 6m             | baseline           |        3 |         0.96 |        95.813 |              0 |             3 |              0 | no              | 2024-01:2, 2024-03:1   |
| 2024-01-01 | 6m             | diagnostic         |       10 |         3.39 |       338.643 |              0 |            10 |              0 | no              | 2024-01:9, 2024-03:1   |
| 2024-04-01 | 3m             | baseline           |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |
| 2024-04-01 | 3m             | diagnostic         |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |
| 2024-04-01 | 6m             | baseline           |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |
| 2024-04-01 | 6m             | diagnostic         |        1 |         0.25 |        25.091 |              0 |             0 |              1 | no              | 2024-08:1              |
| 2024-07-01 | 3m             | baseline           |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |
| 2024-07-01 | 3m             | diagnostic         |        1 |         0.25 |        25.091 |              0 |             0 |              1 | no              | 2024-08:1              |
| 2024-07-01 | 6m             | baseline           |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |
| 2024-07-01 | 6m             | diagnostic         |        1 |         0.25 |        25.091 |              0 |             0 |              1 | no              | 2024-08:1              |
| 2024-10-01 | 3m             | baseline           |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |
| 2024-10-01 | 3m             | diagnostic         |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |
| 2024-10-01 | 6m             | baseline           |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |
| 2024-10-01 | 6m             | diagnostic         |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |
| 2025-01-01 | 3m             | baseline           |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |
| 2025-01-01 | 3m             | diagnostic         |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |
| 2025-01-01 | 6m             | baseline           |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |
| 2025-01-01 | 6m             | diagnostic         |        0 |         0    |         0     |              0 |             0 |              0 | no              |                        |

## Variant Totals

| strategy_variant   |   trades |   profit_usdt |
|:-------------------|---------:|--------------:|
| baseline           |        6 |       191.626 |
| diagnostic         |       25 |       822.403 |

## Decision Notes

No tested anchor/window/variant combination reached the usable-sample threshold.