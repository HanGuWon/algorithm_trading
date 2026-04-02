# PTI 2024 Signal Density Sweep

- Timerange: `20240101-20241231`
- Snapshot: `user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json`
- Target signal count for usable sample: `20`

## Profile Summary

| profile          |   rank |   vol_z_min |   price_z_threshold |   bb_width_min |   adx_1h_max |   slope_cap |   active_pair_rows |   weak_trend_rows |   long_signals |   short_signals |   total_signals |
|:-----------------|-------:|------------:|--------------------:|---------------:|-------------:|------------:|-------------------:|------------------:|---------------:|----------------:|----------------:|
| baseline         |      0 |        2    |                1.8  |          0.04  |           20 |       0.004 |                 75 |                 4 |              3 |               0 |               3 |
| regime_relaxed   |      1 |        2    |                1.8  |          0.04  |           24 |       0.006 |                 75 |                14 |              8 |               0 |               8 |
| vol_relaxed      |      1 |        1.5  |                1.8  |          0.04  |           20 |       0.004 |                100 |                 5 |              4 |               0 |               4 |
| price_relaxed    |      1 |        2    |                1.5  |          0.04  |           20 |       0.004 |                 75 |                 4 |              3 |               0 |               3 |
| bb_relaxed       |      1 |        2    |                1.8  |          0.02  |           20 |       0.004 |                 75 |                 4 |              3 |               0 |               3 |
| combined_mild    |      2 |        1.5  |                1.65 |          0.03  |           22 |       0.005 |                100 |                13 |              7 |               1 |               8 |
| diagnostic       |      3 |        1    |                1.5  |          0.02  |           24 |       0.006 |                161 |                28 |             10 |               1 |              11 |
| diagnostic_plus  |      4 |        0.75 |                1.35 |          0.015 |           26 |       0.008 |                204 |                42 |             10 |               1 |              11 |
| exploratory_plus |      5 |        0.5  |                1.2  |          0.01  |           28 |       0.01  |                268 |                60 |             11 |               1 |              12 |

## Recommendation

No tested profile reached the target sample size of `20` signals. The densest tested profile was `exploratory_plus` with `12` signals.

## Profile: `baseline`

| profile   |   rank |   vol_z_min |   price_z_threshold |   bb_width_min |   adx_1h_max |   slope_cap |   active_pair_rows |   weak_trend_rows |   long_signals |   short_signals |   total_signals |
|:----------|-------:|------------:|--------------------:|---------------:|-------------:|------------:|-------------------:|------------------:|---------------:|----------------:|----------------:|
| baseline  |      0 |           2 |                 1.8 |           0.04 |           20 |       0.004 |                 75 |                 4 |              3 |               0 |               3 |

### Pair Contribution

| pair           |   long_signals |   short_signals |   total_signals |
|:---------------|---------------:|----------------:|----------------:|
| SOL/USDT:USDT  |              1 |               0 |               1 |
| DOT/USDT:USDT  |              1 |               0 |               1 |
| ATOM/USDT:USDT |              1 |               0 |               1 |

### Monthly Distribution

| month   |   long_signals |   short_signals |   total_signals |
|:--------|---------------:|----------------:|----------------:|
| 2024-01 |              2 |               0 |               2 |
| 2024-03 |              1 |               0 |               1 |

## Profile: `diagnostic`

| profile    |   rank |   vol_z_min |   price_z_threshold |   bb_width_min |   adx_1h_max |   slope_cap |   active_pair_rows |   weak_trend_rows |   long_signals |   short_signals |   total_signals |
|:-----------|-------:|------------:|--------------------:|---------------:|-------------:|------------:|-------------------:|------------------:|---------------:|----------------:|----------------:|
| diagnostic |      3 |           1 |                 1.5 |           0.02 |           24 |       0.006 |                161 |                28 |             10 |               1 |              11 |

### Pair Contribution

| pair           |   long_signals |   short_signals |   total_signals |
|:---------------|---------------:|----------------:|----------------:|
| XRP/USDT:USDT  |              1 |               1 |               2 |
| SOL/USDT:USDT  |              1 |               0 |               1 |
| OP/USDT:USDT   |              1 |               0 |               1 |
| AVAX/USDT:USDT |              1 |               0 |               1 |
| FIL/USDT:USDT  |              1 |               0 |               1 |
| LINK/USDT:USDT |              1 |               0 |               1 |
| NEAR/USDT:USDT |              1 |               0 |               1 |
| DOT/USDT:USDT  |              1 |               0 |               1 |
| LTC/USDT:USDT  |              1 |               0 |               1 |
| ATOM/USDT:USDT |              1 |               0 |               1 |

### Monthly Distribution

| month   |   long_signals |   short_signals |   total_signals |
|:--------|---------------:|----------------:|----------------:|
| 2024-01 |              9 |               0 |               9 |
| 2024-03 |              1 |               0 |               1 |
| 2024-08 |              0 |               1 |               1 |

## Profile: `diagnostic_plus`

| profile         |   rank |   vol_z_min |   price_z_threshold |   bb_width_min |   adx_1h_max |   slope_cap |   active_pair_rows |   weak_trend_rows |   long_signals |   short_signals |   total_signals |
|:----------------|-------:|------------:|--------------------:|---------------:|-------------:|------------:|-------------------:|------------------:|---------------:|----------------:|----------------:|
| diagnostic_plus |      4 |        0.75 |                1.35 |          0.015 |           26 |       0.008 |                204 |                42 |             10 |               1 |              11 |

### Pair Contribution

| pair           |   long_signals |   short_signals |   total_signals |
|:---------------|---------------:|----------------:|----------------:|
| XRP/USDT:USDT  |              1 |               1 |               2 |
| SOL/USDT:USDT  |              1 |               0 |               1 |
| OP/USDT:USDT   |              1 |               0 |               1 |
| AVAX/USDT:USDT |              1 |               0 |               1 |
| FIL/USDT:USDT  |              1 |               0 |               1 |
| LINK/USDT:USDT |              1 |               0 |               1 |
| NEAR/USDT:USDT |              1 |               0 |               1 |
| DOT/USDT:USDT  |              1 |               0 |               1 |
| LTC/USDT:USDT  |              1 |               0 |               1 |
| ATOM/USDT:USDT |              1 |               0 |               1 |

### Monthly Distribution

| month   |   long_signals |   short_signals |   total_signals |
|:--------|---------------:|----------------:|----------------:|
| 2024-01 |              9 |               0 |               9 |
| 2024-03 |              1 |               0 |               1 |
| 2024-08 |              0 |               1 |               1 |

## Profile: `exploratory_plus`

| profile          |   rank |   vol_z_min |   price_z_threshold |   bb_width_min |   adx_1h_max |   slope_cap |   active_pair_rows |   weak_trend_rows |   long_signals |   short_signals |   total_signals |
|:-----------------|-------:|------------:|--------------------:|---------------:|-------------:|------------:|-------------------:|------------------:|---------------:|----------------:|----------------:|
| exploratory_plus |      5 |         0.5 |                 1.2 |           0.01 |           28 |        0.01 |                268 |                60 |             11 |               1 |              12 |

### Pair Contribution

| pair           |   long_signals |   short_signals |   total_signals |
|:---------------|---------------:|----------------:|----------------:|
| XRP/USDT:USDT  |              1 |               1 |               2 |
| SOL/USDT:USDT  |              1 |               0 |               1 |
| OP/USDT:USDT   |              1 |               0 |               1 |
| AVAX/USDT:USDT |              1 |               0 |               1 |
| FIL/USDT:USDT  |              1 |               0 |               1 |
| LINK/USDT:USDT |              1 |               0 |               1 |
| NEAR/USDT:USDT |              1 |               0 |               1 |
| DOT/USDT:USDT  |              1 |               0 |               1 |
| LTC/USDT:USDT  |              1 |               0 |               1 |
| SUI/USDT:USDT  |              1 |               0 |               1 |
| ATOM/USDT:USDT |              1 |               0 |               1 |

### Monthly Distribution

| month   |   long_signals |   short_signals |   total_signals |
|:--------|---------------:|----------------:|----------------:|
| 2024-01 |              9 |               0 |               9 |
| 2024-03 |              2 |               0 |               2 |
| 2024-08 |              0 |               1 |               1 |
