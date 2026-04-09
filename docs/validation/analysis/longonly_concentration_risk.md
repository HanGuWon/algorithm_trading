# Long-Only Concentration Risk

> Research-only attribution study. Pair and window removals are contribution counterfactuals, not a redesigned strategy.

## baseline_long_only

| strategy_variant   |   raw_trade_count |   window_raw_trade_count |   profit_usdt |   drawdown_abs_usdt |   top1_pair_share |   top3_pair_share |   top5_pair_share |   pair_profit_hhi |   pair_trade_hhi |
|:-------------------|------------------:|-------------------------:|--------------:|--------------------:|------------------:|------------------:|------------------:|------------------:|-----------------:|
| baseline_long_only |                12 |                       12 |       339.778 |                   0 |             0.104 |             0.309 |             0.505 |             0.087 |            0.083 |

### Pair Contribution

| pair           |   trades |   profit_usdt |   profit_share |
|:---------------|---------:|--------------:|---------------:|
| ATOM/USDT:USDT |        1 |       35.2919 |          0.104 |
| DOT/USDT:USDT  |        1 |       34.956  |          0.103 |
| AXS/USDT:USDT  |        1 |       34.5609 |          0.102 |
| FET/USDT:USDT  |        1 |       34.1326 |          0.1   |
| CRV/USDT:USDT  |        1 |       32.7845 |          0.096 |
| FIL/USDT:USDT  |        1 |       28.9962 |          0.085 |
| SOL/USDT:USDT  |        1 |       26.3222 |          0.077 |
| INJ/USDT:USDT  |        1 |       26.3033 |          0.077 |
| DYDX/USDT:USDT |        1 |       25.3521 |          0.075 |
| GALA/USDT:USDT |        1 |       21.3121 |          0.063 |
| APE/USDT:USDT  |        1 |       20.2861 |          0.06  |
| SAND/USDT:USDT |        1 |       19.4796 |          0.057 |

### Remove Top Contributors

| scenario     |   trades |   profit_usdt |   profit_share |   trade_share |   drawdown_abs_usdt |   drawdown_share | status             | removed_pairs                                                              |
|:-------------|---------:|--------------:|---------------:|--------------:|--------------------:|-----------------:|:-------------------|:---------------------------------------------------------------------------|
| remove_top_1 |       11 |       304.486 |          0.896 |         0.917 |                   0 |                0 | survives           | ATOM/USDT:USDT                                                             |
| remove_top_3 |        9 |       234.969 |          0.692 |         0.75  |                   0 |                0 | survives           | ATOM/USDT:USDT, DOT/USDT:USDT, AXS/USDT:USDT                               |
| remove_top_5 |        7 |       168.052 |          0.495 |         0.583 |                   0 |                0 | weakens materially | ATOM/USDT:USDT, DOT/USDT:USDT, AXS/USDT:USDT, FET/USDT:USDT, CRV/USDT:USDT |

### Leave-One-Pair-Out

| scenario       |   trades |   profit_usdt |   profit_share |   trade_share |   drawdown_abs_usdt |   drawdown_share | status   |
|:---------------|---------:|--------------:|---------------:|--------------:|--------------------:|-----------------:|:---------|
| ATOM/USDT:USDT |       11 |       304.486 |          0.896 |         0.917 |                   0 |                0 | survives |
| DOT/USDT:USDT  |       11 |       304.822 |          0.897 |         0.917 |                   0 |                0 | survives |
| AXS/USDT:USDT  |       11 |       305.217 |          0.898 |         0.917 |                   0 |                0 | survives |
| FET/USDT:USDT  |       11 |       305.645 |          0.9   |         0.917 |                   0 |                0 | survives |
| CRV/USDT:USDT  |       11 |       306.993 |          0.904 |         0.917 |                   0 |                0 | survives |
| FIL/USDT:USDT  |       11 |       310.782 |          0.915 |         0.917 |                   0 |                0 | survives |
| SOL/USDT:USDT  |       11 |       313.455 |          0.923 |         0.917 |                   0 |                0 | survives |
| INJ/USDT:USDT  |       11 |       313.474 |          0.923 |         0.917 |                   0 |                0 | survives |
| DYDX/USDT:USDT |       11 |       314.426 |          0.925 |         0.917 |                   0 |                0 | survives |
| GALA/USDT:USDT |       11 |       318.466 |          0.937 |         0.917 |                   0 |                0 | survives |
| APE/USDT:USDT  |       11 |       319.492 |          0.94  |         0.917 |                   0 |                0 | survives |
| SAND/USDT:USDT |       11 |       320.298 |          0.943 |         0.917 |                   0 |                0 | survives |

### Leave-One-Anchor-Out

| scenario   |   trades |   profit_usdt |   profit_share |   trade_share |   drawdown_abs_usdt |   drawdown_share | status             |
|:-----------|---------:|--------------:|---------------:|--------------:|--------------------:|-----------------:|:-------------------|
| 2024-01-01 |        1 |        28.996 |          0.085 |         0.083 |                   0 |                0 | weakens materially |
| 2022-01-01 |       11 |       310.782 |          0.915 |         0.917 |                   0 |                0 | survives           |

### Leave-One-Month-Out

| scenario   |   trades |   profit_usdt |   profit_share |   trade_share |   drawdown_abs_usdt |   drawdown_share | status             |
|:-----------|---------:|--------------:|---------------:|--------------:|--------------------:|-----------------:|:-------------------|
| 2024-01    |        2 |        55.318 |          0.163 |         0.167 |                   0 |                0 | weakens materially |
| 2022-04    |       11 |       310.782 |          0.915 |         0.917 |                   0 |                0 | survives           |
| 2024-03    |       11 |       313.455 |          0.923 |         0.917 |                   0 |                0 | survives           |

### Monthly Contribution

| month   |   trades |   profit_usdt |   profit_share |
|:--------|---------:|--------------:|---------------:|
| 2022-04 |        1 |       28.9962 |          0.085 |
| 2024-01 |       10 |      284.459  |          0.837 |
| 2024-03 |        1 |       26.3222 |          0.077 |

## diagnostic_long_only

| strategy_variant     |   raw_trade_count |   window_raw_trade_count |   profit_usdt |   drawdown_abs_usdt |   top1_pair_share |   top3_pair_share |   top5_pair_share |   pair_profit_hhi |   pair_trade_hhi |
|:---------------------|------------------:|-------------------------:|--------------:|--------------------:|------------------:|------------------:|------------------:|------------------:|-----------------:|
| diagnostic_long_only |                38 |                       38 |       768.682 |             111.933 |             0.077 |             0.218 |             0.318 |             0.044 |            0.046 |

### Pair Contribution

| pair               |   trades |   profit_usdt |   profit_share |
|:-------------------|---------:|--------------:|---------------:|
| FIL/USDT:USDT      |        2 |       59.4792 |          0.077 |
| AXS/USDT:USDT      |        2 |       55.7931 |          0.073 |
| SOL/USDT:USDT      |        2 |       51.9651 |          0.068 |
| GALA/USDT:USDT     |        2 |       39.9009 |          0.052 |
| NEO/USDT:USDT      |        1 |       37.0089 |          0.048 |
| 1000SHIB/USDT:USDT |        1 |       36.6402 |          0.048 |
| AAVE/USDT:USDT     |        1 |       36.2959 |          0.047 |
| UNI/USDT:USDT      |        1 |       36.228  |          0.047 |
| ATOM/USDT:USDT     |        1 |       36.1674 |          0.047 |
| LTC/USDT:USDT      |        1 |       35.8237 |          0.047 |
| FET/USDT:USDT      |        1 |       35.3318 |          0.046 |
| XRP/USDT:USDT      |        1 |       35.2836 |          0.046 |

### Remove Top Contributors

| scenario     |   trades |   profit_usdt |   profit_share |   trade_share |   drawdown_abs_usdt |   drawdown_share | status   | removed_pairs                                                              |
|:-------------|---------:|--------------:|---------------:|--------------:|--------------------:|-----------------:|:---------|:---------------------------------------------------------------------------|
| remove_top_1 |       36 |       709.203 |          0.923 |         0.947 |              62.626 |             0.56 | survives | FIL/USDT:USDT                                                              |
| remove_top_3 |       32 |       601.445 |          0.782 |         0.842 |              62.626 |             0.56 | survives | FIL/USDT:USDT, AXS/USDT:USDT, SOL/USDT:USDT                                |
| remove_top_5 |       29 |       524.535 |          0.682 |         0.763 |              62.626 |             0.56 | survives | FIL/USDT:USDT, AXS/USDT:USDT, SOL/USDT:USDT, GALA/USDT:USDT, NEO/USDT:USDT |

### Leave-One-Pair-Out

| scenario           |   trades |   profit_usdt |   profit_share |   trade_share |   drawdown_abs_usdt |   drawdown_share | status   |
|:-------------------|---------:|--------------:|---------------:|--------------:|--------------------:|-----------------:|:---------|
| FIL/USDT:USDT      |       36 |       709.203 |          0.923 |         0.947 |              62.626 |             0.56 | survives |
| AXS/USDT:USDT      |       36 |       712.889 |          0.927 |         0.947 |             111.933 |             1    | survives |
| SOL/USDT:USDT      |       36 |       716.717 |          0.932 |         0.947 |             111.933 |             1    | survives |
| GALA/USDT:USDT     |       36 |       728.781 |          0.948 |         0.947 |             111.933 |             1    | survives |
| NEO/USDT:USDT      |       37 |       731.673 |          0.952 |         0.974 |             111.933 |             1    | survives |
| 1000SHIB/USDT:USDT |       37 |       732.042 |          0.952 |         0.974 |             111.933 |             1    | survives |
| AAVE/USDT:USDT     |       37 |       732.386 |          0.953 |         0.974 |             111.933 |             1    | survives |
| UNI/USDT:USDT      |       37 |       732.454 |          0.953 |         0.974 |             111.933 |             1    | survives |
| ATOM/USDT:USDT     |       37 |       732.515 |          0.953 |         0.974 |             111.933 |             1    | survives |
| LTC/USDT:USDT      |       37 |       732.859 |          0.953 |         0.974 |             111.933 |             1    | survives |
| FET/USDT:USDT      |       37 |       733.35  |          0.954 |         0.974 |             111.933 |             1    | survives |
| XRP/USDT:USDT      |       37 |       733.399 |          0.954 |         0.974 |             111.933 |             1    | survives |
| AVAX/USDT:USDT     |       37 |       733.636 |          0.954 |         0.974 |             111.933 |             1    | survives |
| ALGO/USDT:USDT     |       37 |       733.724 |          0.955 |         0.974 |             111.933 |             1    | survives |
| OP/USDT:USDT       |       37 |       737.113 |          0.959 |         0.974 |             111.933 |             1    | survives |

### Leave-One-Anchor-Out

| scenario   |   trades |   profit_usdt |   profit_share |   trade_share |   drawdown_abs_usdt |   drawdown_share | status             |
|:-----------|---------:|--------------:|---------------:|--------------:|--------------------:|-----------------:|:-------------------|
| 2024-01-01 |       11 |        35.453 |          0.046 |         0.289 |             111.933 |            1     | weakens materially |
| 2023-01-01 |       36 |       703.887 |          0.916 |         0.947 |             111.933 |            1     | survives           |
| 2022-07-01 |       36 |       719.807 |          0.936 |         0.947 |             111.933 |            1     | survives           |
| 2023-07-01 |       36 |       778.048 |          1.012 |         0.947 |             111.933 |            1     | survives           |
| 2022-01-01 |       33 |       837.534 |          1.09  |         0.868 |              54.376 |            0.486 | survives           |

### Leave-One-Month-Out

| scenario   |   trades |   profit_usdt |   profit_share |   trade_share |   drawdown_abs_usdt |   drawdown_share | status             |
|:-----------|---------:|--------------:|---------------:|--------------:|--------------------:|-----------------:|:-------------------|
| 2024-01    |       15 |        46.275 |          0.06  |         0.395 |             111.933 |            1     | weakens materially |
| 2023-06    |       36 |       703.887 |          0.916 |         0.947 |             111.933 |            1     | survives           |
| 2024-03    |       36 |       710.633 |          0.924 |         0.947 |             111.933 |            1     | survives           |
| 2022-11    |       36 |       719.807 |          0.936 |         0.947 |             111.933 |            1     | survives           |
| 2022-04    |       37 |       739.686 |          0.962 |         0.974 |              62.626 |            0.56  | survives           |
| 2023-11    |       37 |       772.176 |          1.005 |         0.974 |             111.933 |            1     | survives           |
| 2023-12    |       37 |       774.554 |          1.008 |         0.974 |             111.933 |            1     | survives           |
| 2024-06    |       36 |       815.91  |          1.061 |         0.947 |             111.933 |            1     | survives           |
| 2022-05    |       34 |       866.531 |          1.127 |         0.895 |              54.376 |            0.486 | survives           |

### Monthly Contribution

| month   |   trades |   profit_usdt |   profit_share |
|:--------|---------:|--------------:|---------------:|
| 2022-04 |        1 |      28.9962  |          0.038 |
| 2022-05 |        4 |     -97.8484  |         -0.127 |
| 2022-11 |        2 |      48.8752  |          0.064 |
| 2023-06 |        2 |      64.7954  |          0.084 |
| 2023-11 |        1 |      -3.49388 |         -0.005 |
| 2023-12 |        1 |      -5.87158 |         -0.008 |
| 2024-01 |       23 |     722.407   |          0.94  |
| 2024-03 |        2 |      58.0495  |          0.076 |
| 2024-06 |        2 |     -47.2277  |         -0.061 |

## Cross-Variant Summary

| strategy_variant     |   raw_trade_count |   window_raw_trade_count |   profit_usdt |   drawdown_abs_usdt |   top1_pair_share |   top3_pair_share |   top5_pair_share |   pair_profit_hhi |   pair_trade_hhi |
|:---------------------|------------------:|-------------------------:|--------------:|--------------------:|------------------:|------------------:|------------------:|------------------:|-----------------:|
| baseline_long_only   |                12 |                       12 |       339.778 |               0     |             0.104 |             0.309 |             0.505 |             0.087 |            0.083 |
| diagnostic_long_only |                38 |                       38 |       768.682 |             111.933 |             0.077 |             0.218 |             0.318 |             0.044 |            0.046 |

## Decision Rule

`survives` means the remaining edge stays positive and retains most of its sample.
`weakens materially` means the edge remains positive but loses enough profit or sample to become fragile.
`collapses` means the remaining edge turns non-positive or nearly disappears.
