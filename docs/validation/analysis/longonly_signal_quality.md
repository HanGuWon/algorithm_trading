# Long-Only Signal Quality

> Research-only report. Raw long-signal event-study and indicator rows are inherited from the existing baseline/diagnostic artifacts because the long-only subclasses only disable short entries.

## baseline_long_only

| strategy_variant   |   raw_signal_count |   realized_trade_count |   near_miss_count |   good_near_miss_count |   realized_profit_usdt |   realized_win_rate |
|:-------------------|-------------------:|-----------------------:|------------------:|-----------------------:|-----------------------:|--------------------:|
| baseline_long_only |                 12 |                     12 |                34 |                     30 |                339.778 |                   1 |

### Forward Quality

| bucket         |   count |   ret_12 |   ret_24 |   ret_48 |   mfe_48 |   mae_48 |   mean_hit_24 |   mean_hit_48 |
|:---------------|--------:|---------:|---------:|---------:|---------:|---------:|--------------:|--------------:|
| raw_signal     |      12 |   0.0637 |   0.0515 |   0.0797 |   0.092  |  -0.0026 |         0     |         0     |
| realized_trade |      12 |   0.0637 |   0.0515 |   0.0797 |   0.092  |  -0.0026 |         0     |         0     |
| near_miss      |      34 |   0.0812 |   0.0701 |   0.0641 |   0.1214 |  -0.0544 |         0.324 |         0.324 |
| good_near_miss |      30 |   0.0965 |   0.0845 |   0.0777 |   0.1356 |  -0.0447 |         0.367 |         0.367 |

### Indicator Distributions

|   vol_z |   natr |   bb_width |   adx_1h |   ema50_slope_1h |     rsi |   price_z | bucket         |
|--------:|-------:|-----------:|---------:|-----------------:|--------:|----------:|:---------------|
|  2.5772 | 0.0321 |     0.2276 |  17.7357 |          -0.0016 | 20.7865 |   -2.4735 | raw_signal     |
|  2.5772 | 0.0321 |     0.2276 |  17.7357 |          -0.0016 | 20.7865 |   -2.4735 | realized_trade |
|  3.2456 | 0.0291 |     0.1714 |  17.3234 |          -0.0013 | 10.8453 |   -3.4742 | near_miss      |
|  3.1875 | 0.0289 |     0.1621 |  17.2451 |          -0.0009 | 13.8632 |   -3.389  | good_near_miss |

### Good Near-Miss Gate Blockers

| first_failed_gate   |   rows |    ret_24 |   mean_hit_24 |
|:--------------------|-------:|----------:|--------------:|
| bullish_reversal    |     26 | 0.0941728 |      0.346154 |
| rsi                 |      4 | 0.0218121 |      0.5      |

## diagnostic_long_only

| strategy_variant     |   raw_signal_count |   realized_trade_count |   near_miss_count |   good_near_miss_count |   realized_profit_usdt |   realized_win_rate |
|:---------------------|-------------------:|-----------------------:|------------------:|-----------------------:|-----------------------:|--------------------:|
| diagnostic_long_only |                 38 |                     38 |                87 |                     83 |                768.682 |               0.842 |

### Forward Quality

| bucket         |   count |   ret_12 |   ret_24 |   ret_48 |   mfe_48 |   mae_48 |   mean_hit_24 |   mean_hit_48 |
|:---------------|--------:|---------:|---------:|---------:|---------:|---------:|--------------:|--------------:|
| raw_signal     |      38 |   0.061  |   0.0535 |   0.0661 |   0.0958 |  -0.0136 |         0.053 |         0.105 |
| realized_trade |      38 |   0.061  |   0.0535 |   0.0661 |   0.0958 |  -0.0136 |         0.053 |         0.105 |
| near_miss      |      87 |   0.0818 |   0.0826 |   0.0783 |   0.1345 |  -0.0492 |         0.287 |         0.31  |
| good_near_miss |      83 |   0.0873 |   0.0884 |   0.0839 |   0.1402 |  -0.0454 |         0.301 |         0.325 |

### Indicator Distributions

|   vol_z |   natr |   bb_width |   adx_1h |   ema50_slope_1h |     rsi |   price_z | bucket         |
|--------:|-------:|-----------:|---------:|-----------------:|--------:|----------:|:---------------|
|  2.2037 | 0.0316 |     0.2146 |  19.6123 |          -0.0018 | 21.0005 |   -2.391  | raw_signal     |
|  2.2037 | 0.0316 |     0.2146 |  19.6123 |          -0.0018 | 21.0005 |   -2.391  | realized_trade |
|  2.8865 | 0.0304 |     0.1807 |  19.3012 |          -0.0024 | 13.4487 |   -3.1748 | near_miss      |
|  2.7583 | 0.0301 |     0.1724 |  19.2961 |          -0.002  | 16.1995 |   -3.0644 | good_near_miss |

### Good Near-Miss Gate Blockers

| first_failed_gate   |   rows |    ret_24 |   mean_hit_24 |
|:--------------------|-------:|----------:|--------------:|
| bullish_reversal    |     72 | 0.097424  |      0.277778 |
| rsi                 |     11 | 0.0292635 |      0.454545 |

## Interpretation Rule

The raw long event-study rows come from the existing baseline/diagnostic artifacts because long-only does not alter long-entry logic.
Good near-miss rows identify structurally valid oversold setups that missed entry mainly because one of the last long gates failed.
Read pair and regime concentration together with the separate concentration and regime artifacts before deciding whether to continue research.
