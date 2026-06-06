# External Review Request: Crypto Futures Trading Project

Please review this cryptocurrency futures trading project end to end, with particular focus on whether the current strategy logic, validation design, and recent backtest evidence justify further research, refactoring, or retirement.

## Project Context

This repository is a Freqtrade-based Binance USDT-M futures strategy project.

Primary strategy files:

- `user_data/strategies/VolatilityRotationMR.py`
- `user_data/strategies/VolatilityRotationMRCandidates.py`

Primary recent data/backtest utilities:

- `scripts/binance_futures_to_freqtrade_feather.py`
- `scripts/run_major_futures_backtest.py`
- `scripts/python_startup/sitecustomize.py`

Primary recent config/pairlist:

- `user_data/configs/volatility_rotation_mr_backtest_major_11.json`
- `user_data/pairs/binance_usdt_futures_major_11.json`

Recent validation outputs:

- `docs/validation/analysis/binance_major_backfill_summary.md`
- `docs/validation/analysis/major_11_backtest_summary.md`

## Recent Data Pipeline Work

We added a Binance USDT-M futures candle adapter that downloads official Binance public archive kline data and writes Freqtrade-compatible feather files.

The requested research window was approximately ten years:

- Requested range: `2016-06-04` to `2026-06-04` exclusive
- Actual available Binance USDT-M futures data starts around 2020, depending on the symbol
- Data was written for both `5m` and `1h` timeframes
- Total output: `22` feather files
- Total rows: `7,782,847`

Major 11 test universe:

- `BTC/USDT:USDT`
- `ETH/USDT:USDT`
- `BNB/USDT:USDT`
- `SOL/USDT:USDT`
- `XRP/USDT:USDT`
- `ADA/USDT:USDT`
- `DOGE/USDT:USDT`
- `TRX/USDT:USDT`
- `LINK/USDT:USDT`
- `AVAX/USDT:USDT`
- `LTC/USDT:USDT`

Actual data coverage summary:

| Pair | 5m Start | 5m End |
| --- | --- | --- |
| BTC/USDT:USDT | 2020-01-01 00:00 UTC | 2026-06-02 23:55 UTC |
| ETH/USDT:USDT | 2020-01-01 00:00 UTC | 2026-06-02 23:55 UTC |
| XRP/USDT:USDT | 2020-01-06 08:20 UTC | 2026-06-02 23:55 UTC |
| LTC/USDT:USDT | 2020-01-09 08:05 UTC | 2026-06-02 23:55 UTC |
| TRX/USDT:USDT | 2020-01-15 08:05 UTC | 2026-06-02 23:55 UTC |
| LINK/USDT:USDT | 2020-01-17 08:00 UTC | 2026-06-02 23:55 UTC |
| ADA/USDT:USDT | 2020-01-31 08:00 UTC | 2026-06-02 23:55 UTC |
| BNB/USDT:USDT | 2020-02-10 08:00 UTC | 2026-06-02 23:55 UTC |
| DOGE/USDT:USDT | 2020-07-10 09:00 UTC | 2026-06-02 23:55 UTC |
| SOL/USDT:USDT | 2020-09-14 07:00 UTC | 2026-06-02 23:55 UTC |
| AVAX/USDT:USDT | 2020-09-23 07:00 UTC | 2026-06-02 23:55 UTC |

## Recent Backtest Results

Backtest command range:

- `20160604-20260604`

Actual Freqtrade backtest coverage:

- Approximately `2020-01-09 08:00:00` to `2026-06-02 23:55:00`
- The earlier part of the requested window is unavailable because Binance USDT-M futures did not exist for these symbols for the full ten-year period

Backtested candidate strategies:

| Strategy | Status | Trades | Profit USDT | Profit % | Max Drawdown % | Result Zip |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `VolatilityRotationMRFlushReboundLongOnly` | pass | 19 | +159.953 | +1.5995% | 0.8803% | `backtest-result-2026-06-04_05-52-02.zip` |
| `VolatilityRotationMRDelayedConfirmLongOnly` | pass | 10 | -20.567 | -0.2057% | 0.4997% | `backtest-result-2026-06-04_05-53-20.zip` |

High-level interpretation:

- The data/backtest infrastructure now works.
- `FlushReboundLongOnly` produced a small positive result, but the sample is very sparse: only 19 trades over more than six years of available data.
- `DelayedConfirmLongOnly` failed to produce positive performance.
- The current evidence does not justify live deployment.
- The result is better interpreted as a research diagnostic than as a validated trading edge.

## Existing Strategic Concern

Previous internal validation already suggested that the strategy had sparse signal density and weak forward robustness. The latest major-coin long-window test reinforces that concern:

- Too few trades for strong statistical confidence
- Positive result concentrated in a very small number of events
- No evidence yet that the strategy has broad, durable behavior across assets and regimes
- The long-only flush candidate is more promising than delayed confirmation, but still far from deployment quality

## Specific Review Questions

Please review the project as if you were doing a rigorous quant/code audit.

1. Are there any implementation bugs, data leakage risks, lookahead risks, timeframe merge issues, or Freqtrade misuse patterns in:
   - `VolatilityRotationMR.py`
   - `VolatilityRotationMRCandidates.py`
   - the new Binance archive adapter
   - the new major-11 backtest runner

2. Is the latest backtest methodology sound?
   - Is the requested ten-year range handled honestly given Binance futures data availability?
   - Is using 5m execution candles plus 1h informative candles appropriate here?
   - Are funding-rate and mark-price warnings material for this specific strategy, or can they be ignored because the strategy does not explicitly depend on them?

3. Do the results imply:
   - continue researching this mean-reversion thesis,
   - radically simplify or redesign the entry logic,
   - broaden the universe,
   - lower thresholds to improve signal density,
   - switch to spot data for longer historical testing,
   - or park/retire the current candidates?

4. What next experiments would be most informative?
   Suggested areas:
   - monthly/yearly breakdown
   - per-pair contribution
   - signal event study on the major-11 universe
   - parameter sensitivity around `FlushReboundLongOnly`
   - transaction cost stress
   - comparison against buy-and-hold and simple volatility filters
   - comparison against a much simpler RSI/Bollinger mean-reversion baseline

5. Please propose concrete code-level changes or validation scripts that should be added next.

## Desired Output

Please respond with:

1. Critical findings first, ordered by severity
2. Whether the current strategy should be promoted, parked, or redesigned
3. The strongest reason for that recommendation
4. A prioritized next-action plan
5. Specific code or validation changes to make next

Please be direct. Do not overstate the small positive `FlushReboundLongOnly` result; treat the low trade count as a major concern unless you find strong evidence otherwise.
