# Signal Indicator Diagnostics

- Anchors: `2022-01-01, 2022-07-01, 2023-01-01, 2023-07-01, 2024-01-01, 2024-07-01, 2025-01-01`
- Window design: forward `6m` windows on top-50 PTI snapshots
- Indicator set: `vol_z, natr, bb_width, adx_1h, ema50_slope_1h, rsi, price_z`

## Mean Indicator Values

| strategy_variant   | row_type   | side   |   vol_z |      natr |   bb_width |   adx_1h |   ema50_slope_1h |     rsi |   price_z |
|:-------------------|:-----------|:-------|--------:|----------:|-----------:|---------:|-----------------:|--------:|----------:|
| baseline           | near_miss  | long   | 3.2456  | 0.0290521 |   0.171431 |  17.3234 |     -0.0013014   | 10.8453 |  -3.47424 |
| baseline           | near_miss  | short  | 2.75932 | 0.0290759 |   0.246908 |  16.2173 |      0.000535607 | 83.3764 |   2.94633 |
| baseline           | signal     | long   | 2.5772  | 0.0321299 |   0.227578 |  17.7357 |     -0.0015522   | 20.7865 |  -2.47352 |
| baseline           | signal     | short  | 2.34429 | 0.028038  |   0.157168 |  14.3935 |      0.000212158 | 74.4633 |   2.68866 |
| diagnostic         | near_miss  | long   | 2.8865  | 0.030352  |   0.180665 |  19.3012 |     -0.0024363   | 13.4487 |  -3.17476 |
| diagnostic         | near_miss  | short  | 2.07526 | 0.0292914 |   0.260304 |  19.0696 |      0.000661811 | 82.3405 |   2.8247  |
| diagnostic         | signal     | long   | 2.20366 | 0.0316286 |   0.214567 |  19.6123 |     -0.00179633  | 21.0005 |  -2.39103 |
| diagnostic         | signal     | short  | 2.05009 | 0.0267827 |   0.201492 |  17.2647 |      0.00106395  | 77.5795 |   2.48374 |

## Pair Contribution

| pair               | strategy_variant   | row_type   | side   |   size |
|:-------------------|:-------------------|:-----------|:-------|-------:|
| FARTCOIN/USDT:USDT | diagnostic         | near_miss  | short  |      8 |
| SOL/USDT:USDT      | diagnostic         | near_miss  | long   |      6 |
| 1000BONK/USDT:USDT | diagnostic         | near_miss  | long   |      4 |
| CRV/USDT:USDT      | diagnostic         | near_miss  | long   |      4 |
| CRV/USDT:USDT      | diagnostic         | signal     | long   |      4 |
| FARTCOIN/USDT:USDT | diagnostic         | near_miss  | long   |      4 |
| MAGIC/USDT:USDT    | diagnostic         | near_miss  | long   |      4 |
| ANKR/USDT:USDT     | diagnostic         | near_miss  | short  |      3 |
| FARTCOIN/USDT:USDT | baseline           | near_miss  | short  |      3 |
| FET/USDT:USDT      | diagnostic         | near_miss  | long   |      3 |
| GALA/USDT:USDT     | diagnostic         | near_miss  | long   |      3 |
| LINK/USDT:USDT     | diagnostic         | signal     | long   |      3 |
| MAGIC/USDT:USDT    | baseline           | near_miss  | long   |      3 |
| 1000LUNC/USDT:USDT | diagnostic         | near_miss  | long   |      2 |
| 1000SHIB/USDT:USDT | diagnostic         | near_miss  | long   |      2 |
| AAVE/USDT:USDT     | diagnostic         | near_miss  | long   |      2 |
| APE/USDT:USDT      | diagnostic         | near_miss  | long   |      2 |
| AXS/USDT:USDT      | diagnostic         | signal     | long   |      2 |
| CRV/USDT:USDT      | baseline           | near_miss  | long   |      2 |
| DOT/USDT:USDT      | diagnostic         | signal     | long   |      2 |
| ETH/USDT:USDT      | diagnostic         | near_miss  | short  |      2 |
| FET/USDT:USDT      | baseline           | near_miss  | long   |      2 |
| FIL/USDT:USDT      | diagnostic         | near_miss  | long   |      2 |
| FIL/USDT:USDT      | diagnostic         | signal     | long   |      2 |
| GALA/USDT:USDT     | diagnostic         | signal     | long   |      2 |
| HBAR/USDT:USDT     | baseline           | near_miss  | long   |      2 |
| HBAR/USDT:USDT     | diagnostic         | near_miss  | long   |      2 |
| INJ/USDT:USDT      | diagnostic         | near_miss  | long   |      2 |
| LINK/USDT:USDT     | diagnostic         | near_miss  | long   |      2 |
| ONT/USDT:USDT      | diagnostic         | near_miss  | long   |      2 |
