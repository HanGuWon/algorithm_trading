# Major 11 Concentration Diagnostics

> Research-only audit report. These diagnostics test whether the small backtest result is broad and repeatable enough to justify further strategy work.

## Decision Rules

- Minimum validation trades: `150`
- Maximum top-3 trade net-profit share: `0.50`
- Maximum top-month net-profit share: `0.35`
- Maximum top-pair net-profit share: `0.25`

## Strategy-Level Decision Summary

| strategy                                   | analysis         |   trades |   profit_usdt |   profit_pct |   win_rate |   profit_factor |   trades_per_year |   active_months |   active_years |   top1_trade_profit_share |   top3_trade_profit_share |   top5_trade_profit_share |   top_month_profit_share |   top_pair_profit_share | backtest_start      | backtest_end        | decision               | failed_checks                                            |
|:-------------------------------------------|:-----------------|---------:|--------------:|-------------:|-----------:|----------------:|------------------:|----------------:|---------------:|--------------------------:|--------------------------:|--------------------------:|-------------------------:|------------------------:|:--------------------|:--------------------|:-----------------------|:---------------------------------------------------------|
| VolatilityRotationMRFlushReboundLongOnly   | strategy_summary |       19 |       159.953 |       1.5995 |     0.6842 |          1.6958 |             2.969 |              11 |              5 |                    0.2202 |                     0.653 |                     1.073 |                   0.2202 |                  0.6383 | 2020-01-09 08:00:00 | 2026-06-02 23:55:00 | REDESIGN_RESEARCH_ONLY | sample_size, top_trade_concentration, pair_concentration |
| VolatilityRotationMRDelayedConfirmLongOnly | strategy_summary |       10 |       -20.567 |      -0.2057 |     0.7    |          0.7988 |             1.562 |               7 |              4 |                    0      |                     0     |                     0     |                   0      |                  0      | 2020-01-09 08:00:00 | 2026-06-02 23:55:00 | PARK                   | sample_size, net_profit                                  |

## VolatilityRotationMRFlushReboundLongOnly

### Summary

| strategy                                 | analysis         |   trades |   profit_usdt |   profit_pct |   win_rate |   profit_factor |   trades_per_year |   active_months |   active_years |   top1_trade_profit_share |   top3_trade_profit_share |   top5_trade_profit_share |   top_month_profit_share |   top_pair_profit_share | backtest_start      | backtest_end        | decision               | failed_checks                                            |
|:-----------------------------------------|:-----------------|---------:|--------------:|-------------:|-----------:|----------------:|------------------:|----------------:|---------------:|--------------------------:|--------------------------:|--------------------------:|-------------------------:|------------------------:|:--------------------|:--------------------|:-----------------------|:---------------------------------------------------------|
| VolatilityRotationMRFlushReboundLongOnly | strategy_summary |       19 |       159.953 |       1.5995 |     0.6842 |          1.6958 |             2.969 |              11 |              5 |                    0.2202 |                     0.653 |                     1.073 |                   0.2202 |                  0.6383 | 2020-01-09 08:00:00 | 2026-06-02 23:55:00 | REDESIGN_RESEARCH_ONLY | sample_size, top_trade_concentration, pair_concentration |

### Top Trade Removal

| strategy                                 | analysis          |   removed_top_trades |   remaining_trades |   removed_profit_usdt |   remaining_profit_usdt | removed_pairs                                                               | removed_months                              |
|:-----------------------------------------|:------------------|---------------------:|-------------------:|----------------------:|------------------------:|:----------------------------------------------------------------------------|:--------------------------------------------|
| VolatilityRotationMRFlushReboundLongOnly | top_trade_removal |                    1 |                 18 |                35.229 |                 124.725 | DOGE/USDT:USDT                                                              | 2021-10                                     |
| VolatilityRotationMRFlushReboundLongOnly | top_trade_removal |                    3 |                 16 |               104.454 |                  55.499 | DOGE/USDT:USDT, BNB/USDT:USDT, SOL/USDT:USDT                                | 2021-10, 2021-05, 2024-01                   |
| VolatilityRotationMRFlushReboundLongOnly | top_trade_removal |                    5 |                 14 |               171.624 |                 -11.671 | DOGE/USDT:USDT, BNB/USDT:USDT, SOL/USDT:USDT, AVAX/USDT:USDT, LTC/USDT:USDT | 2021-10, 2021-05, 2024-01, 2021-09, 2021-04 |

### Pair Contribution

| strategy                                 | analysis          | pair           |   trades |   wins |   profit_usdt |   avg_profit_usdt |   avg_profit_pct |   win_rate |   net_profit_share |
|:-----------------------------------------|:------------------|:---------------|---------:|-------:|--------------:|------------------:|-----------------:|-----------:|-------------------:|
| VolatilityRotationMRFlushReboundLongOnly | pair_contribution | SOL/USDT:USDT  |        7 |      5 |      102.095  |           14.585  |           1.8497 |     0.7143 |             0.6383 |
| VolatilityRotationMRFlushReboundLongOnly | pair_contribution | BNB/USDT:USDT  |        2 |      2 |       58.1338 |           29.0669 |           3.2801 |     1      |             0.3634 |
| VolatilityRotationMRFlushReboundLongOnly | pair_contribution | LTC/USDT:USDT  |        2 |      2 |       57.4832 |           28.7416 |           3.5    |     1      |             0.3594 |
| VolatilityRotationMRFlushReboundLongOnly | pair_contribution | AVAX/USDT:USDT |        1 |      1 |       33.6003 |           33.6003 |           3.5    |     1      |             0.2101 |
| VolatilityRotationMRFlushReboundLongOnly | pair_contribution | DOGE/USDT:USDT |        5 |      3 |       -0.3159 |           -0.0632 |          -0.2256 |     0.6    |             0      |
| VolatilityRotationMRFlushReboundLongOnly | pair_contribution | XRP/USDT:USDT  |        1 |      0 |      -40.65   |          -40.65   |          -3.8474 |     0      |             0      |
| VolatilityRotationMRFlushReboundLongOnly | pair_contribution | LINK/USDT:USDT |        1 |      0 |      -50.3928 |          -50.3928 |          -5.0883 |     0      |             0      |

### Year Contribution

| strategy                                 | analysis          |   year |   trades |   wins |   profit_usdt |   avg_profit_usdt |   avg_profit_pct |   win_rate |   net_profit_share |
|:-----------------------------------------|:------------------|-------:|---------:|-------:|--------------:|------------------:|-----------------:|-----------:|-------------------:|
| VolatilityRotationMRFlushReboundLongOnly | year_contribution |   2021 |       11 |      8 |      113.325  |           10.3023 |           1.1435 |     0.7273 |             0.7085 |
| VolatilityRotationMRFlushReboundLongOnly | year_contribution |   2024 |        2 |      2 |       54.9745 |           27.4873 |           2.6326 |     1      |             0.3437 |
| VolatilityRotationMRFlushReboundLongOnly | year_contribution |   2025 |        1 |      1 |       23.2084 |           23.2084 |           3.5    |     1      |             0.1451 |
| VolatilityRotationMRFlushReboundLongOnly | year_contribution |   2020 |        1 |      0 |       -0.4654 |           -0.4654 |          -0.0454 |     0      |             0      |
| VolatilityRotationMRFlushReboundLongOnly | year_contribution |   2022 |        4 |      2 |      -31.0893 |           -7.7723 |          -0.3386 |     0.5    |             0      |

### Largest Month Contributions

| strategy                                 | analysis           | month   |   trades |   wins |   profit_usdt |   avg_profit_usdt |   avg_profit_pct |   win_rate |   net_profit_share |
|:-----------------------------------------|:-------------------|:--------|---------:|-------:|--------------:|------------------:|-----------------:|-----------:|-------------------:|
| VolatilityRotationMRFlushReboundLongOnly | month_contribution | 2021-10 |        1 |      1 |       35.2285 |           35.2285 |           3.0055 |     1      |             0.2202 |
| VolatilityRotationMRFlushReboundLongOnly | month_contribution | 2021-05 |        1 |      1 |       34.9254 |           34.9254 |           3.0601 |     1      |             0.2183 |
| VolatilityRotationMRFlushReboundLongOnly | month_contribution | 2024-01 |        1 |      1 |       34.3005 |           34.3005 |           3.5    |     1      |             0.2144 |
| VolatilityRotationMRFlushReboundLongOnly | month_contribution | 2021-09 |        1 |      1 |       33.6003 |           33.6003 |           3.5    |     1      |             0.2101 |
| VolatilityRotationMRFlushReboundLongOnly | month_contribution | 2025-10 |        1 |      1 |       23.2084 |           23.2084 |           3.5    |     1      |             0.1451 |
| VolatilityRotationMRFlushReboundLongOnly | month_contribution | 2024-04 |        1 |      1 |       20.6741 |           20.6741 |           1.7652 |     1      |             0.1293 |
| VolatilityRotationMRFlushReboundLongOnly | month_contribution | 2021-04 |        6 |      4 |       15.1201 |            2.52   |           0.5445 |     0.6667 |             0.0945 |
| VolatilityRotationMRFlushReboundLongOnly | month_contribution | 2020-11 |        1 |      0 |       -0.4654 |           -0.4654 |          -0.0454 |     0      |             0      |
| VolatilityRotationMRFlushReboundLongOnly | month_contribution | 2021-01 |        2 |      1 |       -5.5491 |           -2.7745 |          -0.1271 |     0.5    |             0      |
| VolatilityRotationMRFlushReboundLongOnly | month_contribution | 2022-05 |        2 |      1 |      -14.6    |           -7.3    |          -0.1737 |     0.5    |             0      |
| VolatilityRotationMRFlushReboundLongOnly | month_contribution | 2022-11 |        2 |      1 |      -16.4893 |           -8.2446 |          -0.5034 |     0.5    |             0      |

### Buy-And-Hold Baseline Context

| strategy                                 | analysis          |   pairs |   usable_pairs |   mean_buy_hold_return_pct |   median_buy_hold_return_pct | best_pair     |   best_pair_return_pct | worst_pair    |   worst_pair_return_pct |
|:-----------------------------------------|:------------------|--------:|---------------:|---------------------------:|-----------------------------:|:--------------|-----------------------:|:--------------|------------------------:|
| VolatilityRotationMRFlushReboundLongOnly | buy_hold_baseline |      11 |             11 |                    1081.03 |                      739.173 | BNB/USDT:USDT |                2481.56 | LTC/USDT:USDT |                    3.42 |

## VolatilityRotationMRDelayedConfirmLongOnly

### Summary

| strategy                                   | analysis         |   trades |   profit_usdt |   profit_pct |   win_rate |   profit_factor |   trades_per_year |   active_months |   active_years |   top1_trade_profit_share |   top3_trade_profit_share |   top5_trade_profit_share |   top_month_profit_share |   top_pair_profit_share | backtest_start      | backtest_end        | decision   | failed_checks           |
|:-------------------------------------------|:-----------------|---------:|--------------:|-------------:|-----------:|----------------:|------------------:|----------------:|---------------:|--------------------------:|--------------------------:|--------------------------:|-------------------------:|------------------------:|:--------------------|:--------------------|:-----------|:------------------------|
| VolatilityRotationMRDelayedConfirmLongOnly | strategy_summary |       10 |       -20.567 |      -0.2057 |        0.7 |          0.7988 |             1.562 |               7 |              4 |                         0 |                         0 |                         0 |                        0 |                       0 | 2020-01-09 08:00:00 | 2026-06-02 23:55:00 | PARK       | sample_size, net_profit |

### Top Trade Removal

| strategy                                   | analysis          |   removed_top_trades |   remaining_trades |   removed_profit_usdt |   remaining_profit_usdt | removed_pairs                                                               | removed_months                              |
|:-------------------------------------------|:------------------|---------------------:|-------------------:|----------------------:|------------------------:|:----------------------------------------------------------------------------|:--------------------------------------------|
| VolatilityRotationMRDelayedConfirmLongOnly | top_trade_removal |                    1 |                  9 |                28.229 |                 -48.796 | SOL/USDT:USDT                                                               | 2024-01                                     |
| VolatilityRotationMRDelayedConfirmLongOnly | top_trade_removal |                    3 |                  7 |                57.077 |                 -77.644 | SOL/USDT:USDT, SOL/USDT:USDT, XRP/USDT:USDT                                 | 2024-01, 2021-04, 2024-01                   |
| VolatilityRotationMRDelayedConfirmLongOnly | top_trade_removal |                    5 |                  5 |                73.33  |                 -93.897 | SOL/USDT:USDT, SOL/USDT:USDT, XRP/USDT:USDT, DOGE/USDT:USDT, AVAX/USDT:USDT | 2024-01, 2021-04, 2024-01, 2021-10, 2021-09 |

### Pair Contribution

| strategy                                   | analysis          | pair           |   trades |   wins |   profit_usdt |   avg_profit_usdt |   avg_profit_pct |   win_rate |   net_profit_share |
|:-------------------------------------------|:------------------|:---------------|---------:|-------:|--------------:|------------------:|-----------------:|-----------:|-------------------:|
| VolatilityRotationMRDelayedConfirmLongOnly | pair_contribution | SOL/USDT:USDT  |        3 |      2 |       16.6571 |            5.5524 |           0.7849 |     0.6667 |                  0 |
| VolatilityRotationMRDelayedConfirmLongOnly | pair_contribution | XRP/USDT:USDT  |        2 |      2 |       15.7984 |            7.8992 |           0.7412 |     1      |                  0 |
| VolatilityRotationMRDelayedConfirmLongOnly | pair_contribution | DOGE/USDT:USDT |        1 |      1 |        8.9877 |            8.9877 |           0.8559 |     1      |                  0 |
| VolatilityRotationMRDelayedConfirmLongOnly | pair_contribution | AVAX/USDT:USDT |        2 |      1 |      -13.9344 |           -6.9672 |          -0.8284 |     0.5    |                  0 |
| VolatilityRotationMRDelayedConfirmLongOnly | pair_contribution | BNB/USDT:USDT  |        2 |      1 |      -48.0759 |          -24.0379 |          -4.0942 |     0.5    |                  0 |

### Year Contribution

| strategy                                   | analysis          |   year |   trades |   wins |   profit_usdt |   avg_profit_usdt |   avg_profit_pct |   win_rate |   net_profit_share |
|:-------------------------------------------|:------------------|-------:|---------:|-------:|--------------:|------------------:|-----------------:|-----------:|-------------------:|
| VolatilityRotationMRDelayedConfirmLongOnly | year_contribution |   2024 |        2 |      2 |       37.7349 |           18.8675 |           2.0786 |     1      |                  0 |
| VolatilityRotationMRDelayedConfirmLongOnly | year_contribution |   2021 |        6 |      5 |       22.7347 |            3.7891 |           0.4411 |     0.8333 |                  0 |
| VolatilityRotationMRDelayedConfirmLongOnly | year_contribution |   2022 |        1 |      0 |      -30.9145 |          -30.9145 |          -3.5713 |     0      |                  0 |
| VolatilityRotationMRDelayedConfirmLongOnly | year_contribution |   2025 |        1 |      0 |      -50.1222 |          -50.1222 |          -8.3846 |     0      |                  0 |

### Largest Month Contributions

| strategy                                   | analysis           | month   |   trades |   wins |   profit_usdt |   avg_profit_usdt |   avg_profit_pct |   win_rate |   net_profit_share |
|:-------------------------------------------|:-------------------|:--------|---------:|-------:|--------------:|------------------:|-----------------:|-----------:|-------------------:|
| VolatilityRotationMRDelayedConfirmLongOnly | month_contribution | 2024-01 |        2 |      2 |       37.7349 |           18.8675 |           2.0786 |        1   |                  0 |
| VolatilityRotationMRDelayedConfirmLongOnly | month_contribution | 2021-04 |        2 |      2 |       25.635  |           12.8175 |           1.6257 |        1   |                  0 |
| VolatilityRotationMRDelayedConfirmLongOnly | month_contribution | 2021-10 |        1 |      1 |        8.9877 |            8.9877 |           0.8559 |        1   |                  0 |
| VolatilityRotationMRDelayedConfirmLongOnly | month_contribution | 2021-09 |        1 |      1 |        7.265  |            7.265  |           0.78   |        1   |                  0 |
| VolatilityRotationMRDelayedConfirmLongOnly | month_contribution | 2021-05 |        2 |      1 |      -19.153  |           -9.5765 |          -1.1203 |        0.5 |                  0 |
| VolatilityRotationMRDelayedConfirmLongOnly | month_contribution | 2022-11 |        1 |      0 |      -30.9145 |          -30.9145 |          -3.5713 |        0   |                  0 |
| VolatilityRotationMRDelayedConfirmLongOnly | month_contribution | 2025-10 |        1 |      0 |      -50.1222 |          -50.1222 |          -8.3846 |        0   |                  0 |

### Buy-And-Hold Baseline Context

| strategy                                   | analysis          |   pairs |   usable_pairs |   mean_buy_hold_return_pct |   median_buy_hold_return_pct | best_pair     |   best_pair_return_pct | worst_pair    |   worst_pair_return_pct |
|:-------------------------------------------|:------------------|--------:|---------------:|---------------------------:|-----------------------------:|:--------------|-----------------------:|:--------------|------------------------:|
| VolatilityRotationMRDelayedConfirmLongOnly | buy_hold_baseline |      11 |             11 |                    1081.03 |                      739.173 | BNB/USDT:USDT |                2481.56 | LTC/USDT:USDT |                    3.42 |
