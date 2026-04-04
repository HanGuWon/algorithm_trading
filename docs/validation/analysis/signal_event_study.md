# Signal Event Study

- Anchors: `2022-01-01, 2022-07-01, 2023-01-01, 2023-07-01, 2024-01-01, 2024-07-01, 2025-01-01`
- Window design: forward `6m` windows on top-50 PTI snapshots
- Forward horizons (candles): `1, 3, 6, 12, 24, 48`

## Mean Forward Returns by Variant and Side

| strategy_variant   | side   |     ret_1 |      ret_3 |     ret_6 |      ret_12 |      ret_24 |     ret_48 |    mfe_48 |      mae_48 |
|:-------------------|:-------|----------:|-----------:|----------:|------------:|------------:|-----------:|----------:|------------:|
| baseline           | long   | 0.0291842 | 0.0478467  | 0.0560972 |  0.0637324  |  0.0515344  |  0.0796984 | 0.0920268 | -0.00260211 |
| baseline           | short  | 0.0130746 | 0.00799847 | 0.0168041 | -0.00424751 |  0.00466286 | -0.0101    | 0.0514662 | -0.0398512  |
| diagnostic         | long   | 0.0199375 | 0.0374792  | 0.0447777 |  0.0610001  |  0.0535341  |  0.0660885 | 0.0958068 | -0.0136301  |
| diagnostic         | short  | 0.017116  | 0.00519499 | 0.0133486 | -0.00549691 | -0.0191083  | -0.0481295 | 0.0557005 | -0.0963608  |

## Anchor-Level Summary

| anchor     | strategy_variant   | side   |   signals |   mean_hit_12 |   mean_hit_24 |   mean_hit_48 |   avg_ret_12 |   avg_ret_24 |   avg_ret_48 |
|:-----------|:-------------------|:-------|----------:|--------------:|--------------:|--------------:|-------------:|-------------:|-------------:|
| 2022-01-01 | baseline           | long   |         1 |           0   |           0   |      0        |   0.0834966  |   0.0810098  |    0.10098   |
| 2022-01-01 | baseline           | short  |         2 |           0   |           0   |      0        |  -0.014318   |  -0.00800467 |   -0.0411745 |
| 2022-01-01 | diagnostic         | long   |         5 |           0.4 |           0.4 |      0.4      |   0.115077   |   0.117939   |    0.0510938 |
| 2022-01-01 | diagnostic         | short  |         3 |           0   |           0   |      0        |  -0.00895394 |  -0.00168053 |   -0.0356755 |
| 2022-07-01 | diagnostic         | long   |         2 |           0   |           0   |      0.5      |   0.083384   |   0.0975935  |    0.131328  |
| 2023-01-01 | diagnostic         | long   |         2 |           0   |           0   |      0        |   0.0423488  |   0.022667   |    0.0417574 |
| 2023-07-01 | diagnostic         | long   |         2 |           0   |           0   |      0        |  -0.00314975 |   0.00179554 |   -0.0141421 |
| 2023-07-01 | diagnostic         | short  |         1 |           0   |           0   |      0        |   0.00612989 |  -0.191518   |   -0.331842  |
| 2024-01-01 | baseline           | long   |        11 |           0   |           0   |      0        |   0.0619357  |   0.0488548  |    0.0777637 |
| 2024-01-01 | diagnostic         | long   |        27 |           0   |           0   |      0.037037 |   0.0554613  |   0.0444626  |    0.071778  |
| 2024-07-01 | diagnostic         | short  |         1 |           0   |           0   |      0        |  -0.0268293  |   0.00536585 |    0.0479675 |
| 2025-01-01 | baseline           | short  |         1 |           0   |           0   |      0        |   0.0158935  |   0.0299979  |    0.0520491 |
| 2025-01-01 | diagnostic         | short  |         2 |           0   |           0   |      0        |   0.00454141 |   0.0287176  |    0.0269975 |

## Monthly Summary

| month   | strategy_variant   | side   |   signals |   avg_ret_24 |   mean_hit_24 |
|:--------|:-------------------|:-------|----------:|-------------:|--------------:|
| 2022-04 | baseline           | long   |         1 |   0.0810098  |           0   |
| 2022-04 | diagnostic         | long   |         1 |   0.0810098  |           0   |
| 2022-05 | diagnostic         | long   |         4 |   0.127171   |           0.5 |
| 2022-06 | baseline           | short  |         2 |  -0.00800467 |           0   |
| 2022-06 | diagnostic         | short  |         3 |  -0.00168053 |           0   |
| 2022-11 | diagnostic         | long   |         2 |   0.0975935  |           0   |
| 2023-06 | diagnostic         | long   |         2 |   0.022667   |           0   |
| 2023-07 | diagnostic         | short  |         1 |  -0.191518   |           0   |
| 2023-11 | diagnostic         | long   |         1 |  -0.00697085 |           0   |
| 2023-12 | diagnostic         | long   |         1 |   0.0105619  |           0   |
| 2024-01 | baseline           | long   |        10 |   0.0522673  |           0   |
| 2024-01 | diagnostic         | long   |        23 |   0.0480132  |           0   |
| 2024-03 | baseline           | long   |         1 |   0.0147299  |           0   |
| 2024-03 | diagnostic         | long   |         2 |   0.0214365  |           0   |
| 2024-06 | diagnostic         | long   |         2 |   0.0266565  |           0   |
| 2024-08 | diagnostic         | short  |         1 |   0.00536585 |           0   |
| 2025-01 | baseline           | short  |         1 |   0.0299979  |           0   |
| 2025-01 | diagnostic         | short  |         1 |   0.0299979  |           0   |
| 2025-04 | diagnostic         | short  |         1 |   0.0274372  |           0   |

## Pair Summary

| pair               | strategy_variant   | side   |   signals |   avg_ret_24 |   mean_hit_24 |
|:-------------------|:-------------------|:-------|----------:|-------------:|--------------:|
| CRV/USDT:USDT      | diagnostic         | long   |         4 |    0.0422747 |      0        |
| LINK/USDT:USDT     | diagnostic         | long   |         3 |    0.0638617 |      0.333333 |
| AXS/USDT:USDT      | diagnostic         | long   |         2 |    0.0330639 |      0        |
| DOT/USDT:USDT      | diagnostic         | long   |         2 |    0.143584  |      0.5      |
| FIL/USDT:USDT      | diagnostic         | long   |         2 |    0.0605829 |      0        |
| GALA/USDT:USDT     | diagnostic         | long   |         2 |    0.095488  |      0        |
| SOL/USDT:USDT      | diagnostic         | long   |         2 |    0.0825244 |      0        |
| XRP/USDT:USDT      | diagnostic         | short  |         2 |   -0.0930759 |      0        |
| 1000BONK/USDT:USDT | diagnostic         | long   |         1 |    0.0596098 |      0        |
| 1000PEPE/USDT:USDT | diagnostic         | long   |         1 |    0.0105619 |      0        |
| 1000SHIB/USDT:USDT | diagnostic         | long   |         1 |    0.0367704 |      0        |
| AAVE/USDT:USDT     | diagnostic         | long   |         1 |    0.0276806 |      0        |
| ALGO/USDT:USDT     | diagnostic         | long   |         1 |    0.0497925 |      0        |
| APE/USDT:USDT      | baseline           | long   |         1 |    0.0534459 |      0        |
| APE/USDT:USDT      | diagnostic         | long   |         1 |    0.0534459 |      0        |
| ATOM/USDT:USDT     | baseline           | long   |         1 |    0.0516027 |      0        |
| ATOM/USDT:USDT     | diagnostic         | long   |         1 |    0.0516027 |      0        |
| AVAX/USDT:USDT     | diagnostic         | long   |         1 |    0.0588664 |      0        |
| AXS/USDT:USDT      | baseline           | long   |         1 |    0.0379847 |      0        |
| CRV/USDT:USDT      | baseline           | long   |         1 |    0.0496183 |      0        |
| DOT/USDT:USDT      | baseline           | long   |         1 |    0.0917151 |      0        |
| DYDX/USDT:USDT     | baseline           | long   |         1 |    0.0747173 |      0        |
| DYDX/USDT:USDT     | diagnostic         | long   |         1 |    0.0747173 |      0        |
| FARTCOIN/USDT:USDT | diagnostic         | short  |         1 |    0.0274372 |      0        |
| FET/USDT:USDT      | baseline           | long   |         1 |    0.0520203 |      0        |
| FET/USDT:USDT      | diagnostic         | long   |         1 |    0.0520203 |      0        |
| FIL/USDT:USDT      | baseline           | long   |         1 |    0.0810098 |      0        |
| GALA/USDT:USDT     | baseline           | long   |         1 |    0.0444791 |      0        |
| GALA/USDT:USDT     | diagnostic         | short  |         1 |    0.0109677 |      0        |
| INJ/USDT:USDT      | baseline           | long   |         1 |    0.030194  |      0        |
