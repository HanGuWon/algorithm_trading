# VolatilityRotationMR

## Summary

VolatilityRotationMR is a Freqtrade v3 futures strategy for short-horizon mean reversion on active
perpetual contracts. It rotates across liquid symbols, treats volume and volatility as activation
filters, and only enters after local price extension, a reversal candle, and a weak higher-timeframe
trend regime all align.

This is not pure market making.
This is a directional long/short reversal strategy with next-candle reversal only.

## Core Hypothesis

- short-term mean reversion exists, but it degrades quickly inside strong trend regimes
- volume is more reliable as a universe and activity filter than as a standalone alpha source
- the entry shape should be extension plus reversal confirmation plus weak 1h trend gating
- if the 1h trend strengthens, the trade should stop behaving like a reversion trade

## Design

- main timeframe: `5m`
- informative timeframe: `1h`
- `can_short = True`
- futures mode only
- isolated margin only
- `liquidation_buffer = 0.08`
- `startup_candle_count = 2400`
- no same-candle exit and reverse hacks

The implementation relies on standard Freqtrade mechanics:

- no position stacking
- conflicting entry and exit signals are not used to force instant flips
- reversal therefore only happens on a later candle if the opposite setup is still valid

## Indicator Set

### 5m

- Bollinger Bands `(20, 2)`
- RSI `(14)`
- Stoch RSI
- ATR `(14)`
- NATR
- ADX `(14)`
- EMA20
- EMA50
- rolling 20-bar price z-score
- rolling 20-bar volume z-score
- Bollinger bandwidth
- session VWAP

### 1h

- ADX `(14)`
- EMA50
- EMA200
- ATR `(14)`
- NATR
- Bollinger Bands `(20, 2)`
- EMA50 slope proxy

## Entry Logic

### Long

- active pair gate passes: `vol_z`, `natr`, `bb_width`
- 1h weak trend regime passes
- no downside breakout block
- close below lower Bollinger Band
- RSI below threshold
- price z-score below threshold
- bullish reversal candle

Tag:
- `mr_long_extreme`

### Short

- active pair gate passes
- 1h weak trend regime passes
- no upside breakout block
- close above upper Bollinger Band
- RSI above threshold
- price z-score above threshold
- bearish reversal candle

Tag:
- `mr_short_extreme`

## Exit Logic

Vectorized exits in `populate_exit_trend()`:

- `mean_hit`: BB mid, EMA20, VWAP, exit RSI, or exit z-score reached
- `vol_decay`: active-pair state disappears
- `trend_expand`: 1h trend expands against the trade

Callback exit:

- `time_stop`: trade duration exceeds `time_stop_candles`

## Risk Management

- `custom_stoploss()` uses ATR distance via `stoploss_from_absolute()`
- `custom_roi()` maps ATR ratio into a clamped ROI range of `0.008` to `0.035`
- `leverage()` defaults to a conservative tier and drops to `1x` when volatility or spread is too high
- `custom_stake_amount()` uses ATR stop distance and a fixed risk fraction when enough wallet context exists

## Protections

The strategy uses:

- `StoplossGuard`
- `LowProfitPairs`

Both are side-aware where supported with `only_per_side = True`.
A blanket `CooldownPeriod` is intentionally not used because it would interfere with next-candle reversal.

## Dynamic Universe Rotation

The research config uses this pairlist chain:

1. `VolumePairList`
2. `AgeFilter`
3. `SpreadFilter`
4. `RangeStabilityFilter`
5. `VolatilityFilter`

`PercentChangePairList` is intentionally excluded from the baseline.

## Live-Only Enhancements

`confirm_trade_entry()` supports optional live-only filters, all disabled by default:

- live spread gate
- live orderbook imbalance gate
- live funding-rate gate

These are runmode-guarded so backtests remain deterministic.
Current funding rate is never used as a historical feature in the baseline.

## Futures Pair Naming

For Binance futures, use the Freqtrade futures naming convention:

- `BTC/USDT:USDT`
- `ETH/USDT:USDT`
- `SOL/USDT:USDT`

## Research Commands

### 1. Create a strategy template reference

```bash
freqtrade new-strategy --strategy VolatilityRotationMR --template advanced
```

### 2. Download futures data for 5m and 1h

Dynamic pairlists are excellent at runtime, but data download is easier to control with explicit seed pairs.

```bash
freqtrade download-data \
  --config user_data/configs/volatility_rotation_mr_futures.json \
  --trading-mode futures \
  --timeframes 5m 1h \
  --pairs BTC/USDT:USDT ETH/USDT:USDT SOL/USDT:USDT XRP/USDT:USDT BNB/USDT:USDT DOGE/USDT:USDT ADA/USDT:USDT LINK/USDT:USDT AVAX/USDT:USDT TRX/USDT:USDT
```

### 3. Backtesting

```bash
freqtrade backtesting \
  --config user_data/configs/volatility_rotation_mr_futures.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --timeframe-detail 1m \
  --timerange 20240101-20241231 \
  --enable-protections \
  --enable-dynamic-pairlist \
  --export signals \
  --export-filename user_data/backtest_results/volatility_rotation_mr_signals.json
```

### 4. Lookahead analysis

```bash
freqtrade lookahead-analysis \
  --config user_data/configs/volatility_rotation_mr_futures.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --timerange 20240101-20241231
```

### 5. Recursive analysis

```bash
freqtrade recursive-analysis \
  --config user_data/configs/volatility_rotation_mr_futures.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --timerange 20240101-20241231
```

### 6. Hyperopt

```bash
freqtrade hyperopt \
  --config user_data/configs/volatility_rotation_mr_futures.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --spaces buy sell \
  --hyperopt-loss SharpeHyperOptLossDaily \
  --timerange 20240101-20241231 \
  -e 200
```

### 7. Backtesting analysis grouped by entry and exit tags

```bash
freqtrade backtesting-analysis \
  --config user_data/configs/volatility_rotation_mr_futures.json \
  --analysis-to-csv \
  --enter-reason-list mr_long_extreme mr_short_extreme \
  --exit-reason-list mean_hit time_stop vol_decay trend_expand
```

## Bias and Stability Checks

- run `lookahead-analysis` before trusting results
- run `recursive-analysis` after any indicator or startup candle changes
- inspect exported entry and exit tags to see whether the edge comes from one side or one exit path only

## Trade-Offs and Known Limitations

- breakout blocking is intentionally simple and rule-based
- VWAP is session-based and practical, not a perfect venue-specific futures session model
- `custom_stake_amount()` is conservative but still simplified
- dynamic pairlists improve rotation realism, but they also make research comparison less stable across windows
- live spread, orderbook, and funding filters are disabled by default to preserve deterministic backtests
- same-candle reversal is intentionally not attempted
