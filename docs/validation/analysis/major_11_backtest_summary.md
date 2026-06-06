# Major 11 Binance Futures Backtest

- Requested UTC timerange: `2016-06-04` to `2026-06-04` exclusive
- Pairs: `BTC/USDT:USDT, ETH/USDT:USDT, BNB/USDT:USDT, SOL/USDT:USDT, XRP/USDT:USDT, ADA/USDT:USDT, DOGE/USDT:USDT, TRX/USDT:USDT, LINK/USDT:USDT, AVAX/USDT:USDT, LTC/USDT:USDT`

## Results

| strategy                                   | status   |   exit_code | timerange         |   pairs | results_zip                             | log                                                                                   |   trades |   profit_abs |   profit_pct |   max_drawdown_pct |
|:-------------------------------------------|:---------|------------:|:------------------|--------:|:----------------------------------------|:--------------------------------------------------------------------------------------|---------:|-------------:|-------------:|-------------------:|
| VolatilityRotationMRFlushReboundLongOnly   | pass     |           0 | 20160604-20260604 |      11 | backtest-result-2026-06-04_05-52-02.zip | docs\validation\logs\major_11_backtest\VolatilityRotationMRFlushReboundLongOnly.log   |       19 |     159.953  |     1.59953  |           0.880288 |
| VolatilityRotationMRDelayedConfirmLongOnly | pass     |           0 | 20160604-20260604 |      11 | backtest-result-2026-06-04_05-53-20.zip | docs\validation\logs\major_11_backtest\VolatilityRotationMRDelayedConfirmLongOnly.log |       10 |     -20.5671 |    -0.205671 |           0.499745 |

## Notes

The requested 10-year window is longer than Binance USDT-M futures history for these markets.
The adapter writes each market from its earliest available Binance futures candle inside the requested range.

## Follow-Up Diagnostics

- Concentration, calendar, pair, and baseline diagnostics: `docs/validation/analysis/major_11_concentration_diagnostics.md`
