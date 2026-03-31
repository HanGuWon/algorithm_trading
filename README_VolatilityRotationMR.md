# VolatilityRotationMR

## Strategy Thesis

VolatilityRotationMR is a Freqtrade v3 futures strategy for short-horizon mean reversion on active
Binance USDT-margined perpetuals. It rotates into liquid contracts, treats volume and volatility as
universe and activation filters, and only enters when local extension, reversal confirmation, and a
weak 1h trend regime align.

This is not pure market making.
This is a directional long/short reversal strategy with next-candle reversal only.

Same-candle exit and reverse is intentionally unsupported because Freqtrade only keeps one position
per pair, ignores conflicting entry and exit signals on the same evaluation cycle, and models
exit-signal fills on the next candle in backtesting. This implementation stays aligned with those
mechanics instead of relying on unsupported flip hacks.

## Modes

### 1. Baseline backtesting mode

Use a static pair snapshot plus `StaticPairList` for reproducible backtests and hyperopt.

- config: `user_data/configs/volatility_rotation_mr_backtest_static.json`
- pair snapshot: `user_data/pairs/binance_usdt_futures_snapshot.json`
- purpose: stable research, bias checks, signal export, tag analysis

### 2. Binance dry-run mode

Use the runtime dynamic pairlist for realistic pair rotation without risking capital.

- config: `user_data/configs/volatility_rotation_mr_binance_dryrun.json`
- purpose: operational validation on live market data with safe defaults

### 3. Binance live mode

Use the live overlay plus a private config or environment variables for secrets.

- config: `user_data/configs/volatility_rotation_mr_binance_live.json`
- purpose: safer live execution with `stoploss_on_exchange` enabled

## Config Layout

- `user_data/configs/volatility_rotation_mr_base.json`
  Common strategy, futures, margin, pairlist, pricing, and protection settings.
- `user_data/configs/volatility_rotation_mr_binance_dryrun.json`
  Dry-run overlay for runtime testing.
- `user_data/configs/volatility_rotation_mr_binance_live.json`
  Live overlay with `stoploss_on_exchange = true`.
- `user_data/configs/volatility_rotation_mr_backtest_static.json`
  Research overlay that swaps the runtime dynamic pairlist for `StaticPairList`.
- `user_data/configs/volatility_rotation_mr_private.example.json`
  Placeholder-only secrets template. Never commit the real private file.
- `user_data/configs/volatility_rotation_mr_futures.json`
  Compatibility wrapper that resolves to the dry-run profile.

Freqtrade merges configs in sequence. CLI `--config` order and `add_config_files` both matter.
Use `freqtrade show-config` to inspect the final merged result before trading.

## Binance Futures Operational Notes

- Pair naming must follow `BASE/QUOTE:SETTLE`, for example `BTC/USDT:USDT`.
- Account mode must be `One-way Mode`.
- Asset mode must be `Single-Asset Mode`.
- The host clock must be NTP-synchronized before dry-run or live trading.
- Orderbook pricing must stay enabled for Binance futures.
- `check_depth_of_market` is available in config but disabled by default.
- `stoploss_on_exchange` is enabled only in the live profile.
- Never commit real API keys or RSA private keys.

Optional secret loading via environment variables is supported through Freqtrade's
`FREQTRADE__SECTION__KEY` convention. Example:

```powershell
$env:FREQTRADE__EXCHANGE__KEY = "your_api_key"
$env:FREQTRADE__EXCHANGE__SECRET = "your_api_secret_or_rsa_private_key"
```

For RSA private keys, Freqtrade expects the `exchange.secret` value. If you inject the key inline,
keep the literal `\n` newlines in the environment variable or private config.

## Strategy Structure

- main timeframe: `5m`
- informative timeframe: `1h`
- `can_short = True`
- futures mode only
- isolated margin only
- `liquidation_buffer = 0.08`
- `startup_candle_count = 2400`
- next-candle reversal only

## Indicators In Use

### 5m

- Bollinger Bands `(20, 2)`
- RSI `(14)`
- ATR `(14)`
- NATR
- EMA20
- rolling 20-bar price z-score
- rolling 20-bar volume z-score
- Bollinger bandwidth
- session VWAP

### 1h

- ADX `(14)`
- EMA50
- EMA200
- Bollinger Bands `(20, 2)`
- EMA50 slope proxy

Unused indicators from the first scaffold were removed to keep the baseline readable and to reduce
the chance of dead logic being mistaken for active signal logic.

## Research Universe vs Runtime Universe

### Dynamic runtime universe

The runtime profile uses:

1. `VolumePairList`
2. `AgeFilter`
3. `SpreadFilter`
4. `RangeStabilityFilter`
5. `VolatilityFilter`

This is appropriate for dry-run and live operation because it rotates into current high-attention
contracts.

### Static research universe

The research profile uses `StaticPairList` and a frozen pair snapshot file.
This is appropriate for backtesting and hyperopt because the universe is deterministic.

Regenerate the snapshot when you intentionally want to research a new universe.
Do not mix dynamic runtime pairlists with reproducibility-sensitive research runs.

## Exact Config Layering Examples

### Show the merged dry-run config

```bash
freqtrade show-config \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json \
  --config user_data/configs/volatility_rotation_mr_private.json \
  --strategy VolatilityRotationMR
```

### Show the merged live config

```bash
freqtrade show-config \
  --config user_data/configs/volatility_rotation_mr_binance_live.json \
  --config user_data/configs/volatility_rotation_mr_private.json \
  --strategy VolatilityRotationMR
```

### Use environment variables instead of a private config

```bash
freqtrade show-config \
  --config user_data/configs/volatility_rotation_mr_binance_live.json \
  --strategy VolatilityRotationMR
```

## Validation Commands

### Strategy load check

```bash
freqtrade list-strategies \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json \
  --strategy-path user_data/strategies
```

### Config sanity check

```bash
freqtrade show-config \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json \
  --strategy VolatilityRotationMR
```

### PowerShell helper

```powershell
.\scripts\validate_freqtrade.ps1 `
  -Config user_data/configs/volatility_rotation_mr_binance_dryrun.json `
  -AdditionalConfigs user_data/configs/volatility_rotation_mr_private.json
```

## Reproducible Research Workflow

The strategy needs `startup_candle_count = 2400`, which is about 8 days and 8 hours of 5m candles.
For downloads, include a buffer ahead of the evaluation window. The examples below use about two
weeks of warmup margin.

### 1. Generate a static pair snapshot from the runtime dynamic pairlist

```bash
freqtrade test-pairlist \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json \
  --quote USDT \
  --print-json
```

```powershell
.\scripts\save_pair_snapshot.ps1 `
  -Config user_data/configs/volatility_rotation_mr_binance_dryrun.json `
  -AdditionalConfigs user_data/configs/volatility_rotation_mr_private.json `
  -Output user_data/pairs/binance_usdt_futures_snapshot.json
```

### 2. Download futures data with explicit timeranges

```bash
freqtrade download-data \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --trading-mode futures \
  --timeframes 5m 1h \
  --timerange 20231215-20250115
```

### 3. Backtest on the static research universe

```bash
freqtrade backtesting \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --timeframe-detail 1m \
  --timerange 20240101-20241231 \
  --enable-protections \
  --export signals \
  --export-filename user_data/backtest_results/volatility_rotation_mr_signals.json
```

### 4. Lookahead analysis

```bash
freqtrade lookahead-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --timerange 20240101-20241231 \
  > user_data/backtest_results/lookahead-analysis.log
```

### 5. Recursive analysis

```bash
freqtrade recursive-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --timerange 20240101-20241231 \
  > user_data/backtest_results/recursive-analysis.log
```

### 6. Hyperopt on the same static universe

```bash
freqtrade hyperopt \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --spaces buy sell \
  --hyperopt-loss SharpeHyperOptLossDaily \
  --timerange 20240101-20241231 \
  -e 200
```

### 7. Backtesting analysis by entry and exit tags

```bash
freqtrade backtesting-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --analysis-to-csv \
  --enter-reason-list mr_long_extreme mr_short_extreme \
  --exit-reason-list mean_hit time_stop vol_decay trend_expand
```

### 8. Bias-check helper

```powershell
.\scripts\run_bias_checks.ps1 `
  -Config user_data/configs/volatility_rotation_mr_backtest_static.json `
  -Timerange 20240101-20241231
```

## Binance Dry-Run Launch

```bash
freqtrade trade \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json \
  --config user_data/configs/volatility_rotation_mr_private.json \
  --strategy VolatilityRotationMR
```

## Binance Live Launch

```bash
freqtrade trade \
  --config user_data/configs/volatility_rotation_mr_binance_live.json \
  --config user_data/configs/volatility_rotation_mr_private.json \
  --strategy VolatilityRotationMR
```

## Tag-Level Diagnostics

The strategy emits:

- entry tags: `mr_long_extreme`, `mr_short_extreme`
- exit tags: `mean_hit`, `time_stop`, `vol_decay`, `trend_expand`

Use `freqtrade backtesting-analysis` to check whether:

- one side dominates all returns
- one exit path is carrying the entire strategy
- `time_stop` is acting like a hidden stop rather than a neutral cleanup exit
- `vol_decay` is exiting too many trades before mean reversion has time to work

## Risk Management Notes

- `custom_stoploss()` remains ATR-based and futures-aware via `stoploss_from_absolute()`
- `custom_roi()` remains ATR-ratio-based and clamped to a conservative range
- `custom_stake_amount()` remains risk-based, but now explicitly guards against too-small Binance
  futures orders using `min_stake`, exchange market limits when available, and a Binance notional
  floor buffer
- `check_depth_of_market` is config-controlled and optional
- current live funding values remain restricted to optional runmode-guarded entry confirmation only

## Secrets Warning

Never commit:

- real API keys
- real API secrets
- RSA private keys
- `.env` files
- private config overlays

Use `user_data/configs/volatility_rotation_mr_private.example.json` only as a template.

## Known Limitations

- breakout blocking remains intentionally rule-based and simple
- VWAP is session-based and practical rather than exchange-microstructure-specific
- Binance futures minimums and quantitative rules vary by contract, so the stake guard is conservative
  but still not a substitute for exchange-side validation
- the static snapshot file is reproducible only until you intentionally regenerate it
- live spread, orderbook, and funding filters are still disabled by default to preserve reproducibility
- same-candle reversal remains unsupported by design
