# Long-Only Regime Context

> Research-only context study over the existing long-only subclasses. The goal is to identify whether the edge is broad or concentrated in flush-rebound environments.

## baseline_long_only

- signal count: `12`
- realized trade count: `12`
- realized profit: `339.778 USDT`

### btc_trend_regime

| strategy_variant   | feature          | bucket        |   signal_count |   signal_ret_12 |   signal_ret_24 |   signal_ret_48 |   signal_mean_hit_24 |   signal_mean_hit_48 |   trade_count |   win_rate |   profit_usdt |   drawdown_abs_usdt |   trade_ret_12 |   trade_ret_24 |   trade_ret_48 |
|:-------------------|:-----------------|:--------------|---------------:|----------------:|----------------:|----------------:|---------------------:|---------------------:|--------------:|-----------:|--------------:|--------------------:|---------------:|---------------:|---------------:|
| baseline_long_only | btc_trend_regime | btc_downtrend |              1 |       0.0834966 |       0.0810098 |       0.10098   |                    0 |                    0 |             1 |          1 |        28.996 |                   0 |         0.0835 |         0.081  |         0.101  |
| baseline_long_only | btc_trend_regime | btc_neutral   |             11 |       0.0619357 |       0.0488548 |       0.0777637 |                    0 |                    0 |            11 |          1 |       310.782 |                   0 |         0.0619 |         0.0489 |         0.0778 |

### btc_realized_vol_bucket

| strategy_variant   | feature                 | bucket       |   signal_count |   signal_ret_12 |   signal_ret_24 |   signal_ret_48 |   signal_mean_hit_24 |   signal_mean_hit_48 |   trade_count |   win_rate |   profit_usdt |   drawdown_abs_usdt |   trade_ret_12 |   trade_ret_24 |   trade_ret_48 |
|:-------------------|:------------------------|:-------------|---------------:|----------------:|----------------:|----------------:|---------------------:|---------------------:|--------------:|-----------:|--------------:|--------------------:|---------------:|---------------:|---------------:|
| baseline_long_only | btc_realized_vol_bucket | btc_vol_high |             11 |       0.0619357 |       0.0488548 |       0.0777637 |                    0 |                    0 |            11 |          1 |       310.782 |                   0 |         0.0619 |         0.0489 |         0.0778 |
| baseline_long_only | btc_realized_vol_bucket | btc_vol_low  |              1 |       0.0834966 |       0.0810098 |       0.10098   |                    0 |                    0 |             1 |          1 |        28.996 |                   0 |         0.0835 |         0.081  |         0.101  |

### flush_breadth_bucket

| strategy_variant   | feature              | bucket     |   signal_count |   signal_ret_12 |   signal_ret_24 |   signal_ret_48 |   signal_mean_hit_24 |   signal_mean_hit_48 |   trade_count |   win_rate |   profit_usdt |   drawdown_abs_usdt |   trade_ret_12 |   trade_ret_24 |   trade_ret_48 |
|:-------------------|:---------------------|:-----------|---------------:|----------------:|----------------:|----------------:|---------------------:|---------------------:|--------------:|-----------:|--------------:|--------------------:|---------------:|---------------:|---------------:|
| baseline_long_only | flush_breadth_bucket | flush_high |             12 |       0.0637324 |       0.0515344 |       0.0796984 |                    0 |                    0 |            12 |          1 |       339.778 |                   0 |         0.0637 |         0.0515 |         0.0797 |

### oversold_breadth_bucket

| strategy_variant   | feature                 | bucket        |   signal_count |   signal_ret_12 |   signal_ret_24 |   signal_ret_48 |   signal_mean_hit_24 |   signal_mean_hit_48 |   trade_count |   win_rate |   profit_usdt |   drawdown_abs_usdt |   trade_ret_12 |   trade_ret_24 |   trade_ret_48 |
|:-------------------|:------------------------|:--------------|---------------:|----------------:|----------------:|----------------:|---------------------:|---------------------:|--------------:|-----------:|--------------:|--------------------:|---------------:|---------------:|---------------:|
| baseline_long_only | oversold_breadth_bucket | oversold_high |             12 |       0.0637324 |       0.0515344 |       0.0796984 |                    0 |                    0 |            12 |          1 |       339.778 |                   0 |         0.0637 |         0.0515 |         0.0797 |

### active_breadth_bucket

| strategy_variant   | feature               | bucket      |   signal_count |   signal_ret_12 |   signal_ret_24 |   signal_ret_48 |   signal_mean_hit_24 |   signal_mean_hit_48 |   trade_count |   win_rate |   profit_usdt |   drawdown_abs_usdt |   trade_ret_12 |   trade_ret_24 |   trade_ret_48 |
|:-------------------|:----------------------|:------------|---------------:|----------------:|----------------:|----------------:|---------------------:|---------------------:|--------------:|-----------:|--------------:|--------------------:|---------------:|---------------:|---------------:|
| baseline_long_only | active_breadth_bucket | active_high |             12 |       0.0637324 |       0.0515344 |       0.0796984 |                    0 |                    0 |             0 |          0 |             0 |                   0 |              0 |              0 |              0 |

### Interpretation

- Highest-profit flush bucket: `flush_high` with `339.778 USDT`.
- Highest-profit oversold bucket: `oversold_high` with `339.778 USDT`.

## diagnostic_long_only

- signal count: `38`
- realized trade count: `38`
- realized profit: `768.682 USDT`

### btc_trend_regime

| strategy_variant     | feature          | bucket        |   signal_count |   signal_ret_12 |   signal_ret_24 |   signal_ret_48 |   signal_mean_hit_24 |   signal_mean_hit_48 |   trade_count |   win_rate |   profit_usdt |   drawdown_abs_usdt |   trade_ret_12 |   trade_ret_24 |   trade_ret_48 |
|:---------------------|:-----------------|:--------------|---------------:|----------------:|----------------:|----------------:|---------------------:|---------------------:|--------------:|-----------:|--------------:|--------------------:|---------------:|---------------:|---------------:|
| diagnostic_long_only | btc_trend_regime | btc_downtrend |             10 |       0.0854821 |      0.0868675  |       0.0668073 |                  0.2 |             0.3      |            10 |      0.7   |        51.967 |             111.933 |         0.0855 |         0.0869 |         0.0668 |
| diagnostic_long_only | btc_trend_regime | btc_neutral   |             27 |       0.0547142 |      0.0434293  |       0.0691795 |                  0   |             0.037037 |            27 |      0.926 |       720.209 |              54.376 |         0.0547 |         0.0434 |         0.0692 |
| diagnostic_long_only | btc_trend_regime | btc_uptrend   |              1 |      -0.0141001 |     -0.00697085 |      -0.0245564 |                  0   |             0        |             1 |      0     |        -3.494 |               0     |        -0.0141 |        -0.007  |        -0.0246 |

### btc_realized_vol_bucket

| strategy_variant     | feature                 | bucket       |   signal_count |   signal_ret_12 |   signal_ret_24 |   signal_ret_48 |   signal_mean_hit_24 |   signal_mean_hit_48 |   trade_count |   win_rate |   profit_usdt |   drawdown_abs_usdt |   trade_ret_12 |   trade_ret_24 |   trade_ret_48 |
|:---------------------|:------------------------|:-------------|---------------:|----------------:|----------------:|----------------:|---------------------:|---------------------:|--------------:|-----------:|--------------:|--------------------:|---------------:|---------------:|---------------:|
| diagnostic_long_only | btc_realized_vol_bucket | btc_vol_high |             33 |       0.0615856 |       0.0529274 |       0.0640568 |            0.0606061 |            0.0909091 |            34 |      0.824 |       656.983 |              62.626 |         0.0596 |         0.0518 |         0.0633 |
| diagnostic_long_only | btc_realized_vol_bucket | btc_vol_low  |              2 |       0.104204  |       0.113753  |       0.137185  |            0         |            0.5       |             2 |      1     |        46.904 |               0     |         0.1042 |         0.1138 |         0.1372 |
| diagnostic_long_only | btc_realized_vol_bucket | btc_vol_mid  |              3 |       0.0257573 |       0.0200618 |       0.0410396 |            0         |            0         |             2 |      1     |        64.795 |               0     |         0.0423 |         0.0227 |         0.0418 |

### flush_breadth_bucket

| strategy_variant     | feature              | bucket     |   signal_count |   signal_ret_12 |   signal_ret_24 |   signal_ret_48 |   signal_mean_hit_24 |   signal_mean_hit_48 |   trade_count |   win_rate |   profit_usdt |   drawdown_abs_usdt |   trade_ret_12 |   trade_ret_24 |   trade_ret_48 |
|:---------------------|:---------------------|:-----------|---------------:|----------------:|----------------:|----------------:|---------------------:|---------------------:|--------------:|-----------:|--------------:|--------------------:|---------------:|---------------:|---------------:|
| diagnostic_long_only | flush_breadth_bucket | flush_high |             38 |       0.0610001 |       0.0535341 |       0.0660885 |            0.0526316 |             0.105263 |            37 |      0.838 |       761.534 |             111.933 |         0.0619 |         0.0539 |         0.0661 |

### oversold_breadth_bucket

| strategy_variant     | feature                 | bucket        |   signal_count |   signal_ret_12 |   signal_ret_24 |   signal_ret_48 |   signal_mean_hit_24 |   signal_mean_hit_48 |   trade_count |   win_rate |   profit_usdt |   drawdown_abs_usdt |   trade_ret_12 |   trade_ret_24 |   trade_ret_48 |
|:---------------------|:------------------------|:--------------|---------------:|----------------:|----------------:|----------------:|---------------------:|---------------------:|--------------:|-----------:|--------------:|--------------------:|---------------:|---------------:|---------------:|
| diagnostic_long_only | oversold_breadth_bucket | oversold_high |             38 |       0.0610001 |       0.0535341 |       0.0660885 |            0.0526316 |             0.105263 |            38 |      0.842 |       768.682 |             111.933 |          0.061 |         0.0535 |         0.0661 |

### active_breadth_bucket

| strategy_variant     | feature               | bucket      |   signal_count |   signal_ret_12 |   signal_ret_24 |   signal_ret_48 |   signal_mean_hit_24 |   signal_mean_hit_48 |   trade_count |   win_rate |   profit_usdt |   drawdown_abs_usdt |   trade_ret_12 |   trade_ret_24 |   trade_ret_48 |
|:---------------------|:----------------------|:------------|---------------:|----------------:|----------------:|----------------:|---------------------:|---------------------:|--------------:|-----------:|--------------:|--------------------:|---------------:|---------------:|---------------:|
| diagnostic_long_only | active_breadth_bucket | active_high |             38 |       0.0610001 |       0.0535341 |       0.0660885 |            0.0526316 |             0.105263 |            37 |      0.838 |       739.686 |              62.626 |         0.0604 |         0.0528 |         0.0651 |

### Interpretation

- Highest-profit flush bucket: `flush_high` with `761.534 USDT`.
- Highest-profit oversold bucket: `oversold_high` with `768.682 USDT`.
