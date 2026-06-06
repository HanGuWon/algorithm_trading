# Major 11 Bias Audit

> Follow-up validation after the external review requested mandatory lookahead, recursive, and static leakage checks.

## Scope

- Timerange: `20200109-20260603`
- Strategies: `VolatilityRotationMRFlushReboundLongOnly, VolatilityRotationMRDelayedConfirmLongOnly`
- Config: `user_data/configs/volatility_rotation_mr_backtest_major_11.json`
- Lookahead overlay: `user_data/configs/volatility_rotation_mr_analysis_market.json`
- Data directory: `C:\Users\user\Desktop\algorithm_trading-main\algorithm_trading-main\user_data\data\binance`

## Result Summary

| check                         | target                                     | status   | detail                                                                                                                              |
|:------------------------------|:-------------------------------------------|:---------|:------------------------------------------------------------------------------------------------------------------------------------|
| static_strategy_files_present | strategy_files                             | pass     | All expected strategy files are present.                                                                                            |
| static_negative_shift         | strategy_files                             | pass     | No negative shift usage found.                                                                                                      |
| static_whole_dataframe_stats  | strategy_files                             | pass     | No unconstrained whole-dataframe statistic usage found in strategy files.                                                           |
| static_iloc_last              | strategy_files                             | info     | iloc[-1] appears only in live/analyzed-candle helper paths; not in indicator generation.                                            |
| static_informative_merge      | strategy_files                             | pass     | merge_informative_pair is used for 1h informative data; Freqtrade shifts informative candles to avoid using unfinished HTF candles. |
| static_rotation_ranking       | strategy_files                             | pass     | No groupby().transform() ranking pattern found in strategy files.                                                                   |
| freqtrade_lookahead_analysis  | VolatilityRotationMRFlushReboundLongOnly   | pass     | lookahead-analysis completed with has_bias=False and zero biased entry/exit signals.                                                |
| freqtrade_recursive_analysis  | VolatilityRotationMRFlushReboundLongOnly   | pass     | freqtrade_recursive_analysis completed without obvious bias/error markers.                                                          |
| freqtrade_lookahead_analysis  | VolatilityRotationMRDelayedConfirmLongOnly | pass     | lookahead-analysis completed with has_bias=False and zero biased entry/exit signals.                                                |
| freqtrade_recursive_analysis  | VolatilityRotationMRDelayedConfirmLongOnly | pass     | freqtrade_recursive_analysis completed without obvious bias/error markers.                                                          |

## Static Audit

| check                         | status   | detail                                                                                                                              |
|:------------------------------|:---------|:------------------------------------------------------------------------------------------------------------------------------------|
| static_strategy_files_present | pass     | All expected strategy files are present.                                                                                            |
| static_negative_shift         | pass     | No negative shift usage found.                                                                                                      |
| static_whole_dataframe_stats  | pass     | No unconstrained whole-dataframe statistic usage found in strategy files.                                                           |
| static_iloc_last              | info     | iloc[-1] appears only in live/analyzed-candle helper paths; not in indicator generation.                                            |
| static_informative_merge      | pass     | merge_informative_pair is used for 1h informative data; Freqtrade shifts informative candles to avoid using unfinished HTF candles. |
| static_rotation_ranking       | pass     | No groupby().transform() ranking pattern found in strategy files.                                                                   |

## Freqtrade Command Logs

| check                        | target                                     | status   | log_path                                                                                          | export_path                                                                                |
|:-----------------------------|:-------------------------------------------|:---------|:--------------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------|
| freqtrade_lookahead_analysis | VolatilityRotationMRFlushReboundLongOnly   | pass     | docs/validation/logs/major_11_bias_audit/VolatilityRotationMRFlushReboundLongOnly_lookahead.log   | docs/validation/analysis/major_11_lookahead_VolatilityRotationMRFlushReboundLongOnly.csv   |
| freqtrade_recursive_analysis | VolatilityRotationMRFlushReboundLongOnly   | pass     | docs/validation/logs/major_11_bias_audit/VolatilityRotationMRFlushReboundLongOnly_recursive.log   | nan                                                                                        |
| freqtrade_lookahead_analysis | VolatilityRotationMRDelayedConfirmLongOnly | pass     | docs/validation/logs/major_11_bias_audit/VolatilityRotationMRDelayedConfirmLongOnly_lookahead.log | docs/validation/analysis/major_11_lookahead_VolatilityRotationMRDelayedConfirmLongOnly.csv |
| freqtrade_recursive_analysis | VolatilityRotationMRDelayedConfirmLongOnly | pass     | docs/validation/logs/major_11_bias_audit/VolatilityRotationMRDelayedConfirmLongOnly_recursive.log | nan                                                                                        |

## Interpretation

- Passing static checks do not prove profitability; they only reduce the risk that the current backtest is contaminated by obvious future-data patterns.
- `recursive-analysis` is included because indicator stability can differ between long historical backtests and live incremental operation.
- Strategy promotion remains blocked until the raw signal event study and baseline comparisons show durable forward expectancy.
