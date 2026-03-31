# VolatilityRotationMR

## Strategy Thesis

VolatilityRotationMR is a Freqtrade v3 futures strategy for short-horizon mean reversion on active
Binance USDT-margined perpetuals. It rotates into liquid contracts, treats volume and volatility as
universe and activation filters, and only enters when local extension, reversal confirmation, and a
weak 1h trend regime align.

This is not pure market making.
This is a directional long/short reversal strategy with next-candle reversal only.

Same-candle exit and reverse is intentionally unsupported because vanilla Freqtrade keeps one
position per pair, ignores conflicting entry and exit signals within the same evaluation cycle, and
models exit-signal fills on the next candle in backtesting.

## Config Model

Primary configs:

- `user_data/configs/volatility_rotation_mr_base.json`
- `user_data/configs/volatility_rotation_mr_binance_dryrun.json`
- `user_data/configs/volatility_rotation_mr_binance_live.json`
- `user_data/configs/volatility_rotation_mr_backtest_static.json`
- `user_data/configs/volatility_rotation_mr_private.example.json`

Compatibility alias:

- `user_data/configs/volatility_rotation_mr_futures.json`
  This is only a thin wrapper for the dry-run profile. Do not use it as the primary research or live
  config in new workflows.

Layering works in 2 equivalent ways:

1. `add_config_files` inside config JSON:

```json
{
  "add_config_files": [
    "volatility_rotation_mr_base.json"
  ]
}
```

2. Multiple CLI configs where the last file wins:

```bash
freqtrade trade \
  --config user_data/configs/volatility_rotation_mr_base.json \
  --config user_data/configs/volatility_rotation_mr_binance_live.json \
  --config user_data/configs/volatility_rotation_mr_private.json \
  --strategy VolatilityRotationMR
```

Always confirm the final merged result with `freqtrade show-config`.

## Binance Futures Prerequisites

- Pair naming must follow `BASE/QUOTE:SETTLE`, for example `BTC/USDT:USDT`.
- Account `Position Mode` must be `One-way Mode`.
- Account `Asset Mode` must be `Single-Asset Mode`.
- The host clock must be NTP-synchronized before dry-run or live trading.
- Orderbook pricing must remain enabled for Binance futures.
- Binance-side API labels change over time, but in practice you need read access plus the ability to
  place and cancel USDT-M futures orders. Keep withdrawals disabled.
- IP whitelisting is strongly recommended for live keys.
- Never commit API keys, secrets, RSA private keys, `.env` files, or private overlays.

## Secrets Handling

### Private config overlay

Create a local file such as `user_data/configs/volatility_rotation_mr_private.json` based on
`user_data/configs/volatility_rotation_mr_private.example.json`. This file is gitignored.

### Environment-variable secrets

Freqtrade supports `FREQTRADE__SECTION__KEY` environment variables. Examples:

```powershell
$env:FREQTRADE__EXCHANGE__KEY = "your_api_key"
$env:FREQTRADE__EXCHANGE__SECRET = "your_api_secret"
```

Binance RSA example:

```powershell
$env:FREQTRADE__EXCHANGE__KEY = "your_api_key"
$env:FREQTRADE__EXCHANGE__SECRET = (Get-Content -Raw .\rsa_binance.private)
```

If the RSA private key is injected as a single string, preserve embedded newlines.

## Research-Safe Static Backtesting Mode

Use the static research profile for reproducible backtests, hyperopt, and bias checks.

- config: `user_data/configs/volatility_rotation_mr_backtest_static.json`
- pair snapshot: `user_data/pairs/binance_usdt_futures_snapshot.json`
- pairlist mode: `StaticPairList`

### Show the merged research config

```bash
freqtrade show-config \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --strategy VolatilityRotationMR
```

### Regenerate the static pair snapshot from the runtime dynamic pairlist

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

### Download futures data with explicit startup buffer

`startup_candle_count = 2400`, which is about 8 days and 8 hours of 5m candles. The download range
must start earlier than the analysis range because `download-data` does not add that buffer.

Example research window:

- analysis start: `2024-01-01`
- download start: `2023-12-18`

```bash
freqtrade download-data \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --trading-mode futures \
  --timeframes 5m 1h \
  --timerange 20231218-20250115
```

### Backtesting

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

### Lookahead analysis

```bash
freqtrade lookahead-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --timerange 20240101-20241231 \
  > user_data/backtest_results/lookahead-analysis.log
```

### Recursive analysis

```bash
freqtrade recursive-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --strategy VolatilityRotationMR \
  --timeframe 5m \
  --timerange 20240101-20241231 \
  > user_data/backtest_results/recursive-analysis.log
```

### Hyperopt

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

### Backtesting analysis by tag

```bash
freqtrade backtesting-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --analysis-to-csv \
  --enter-reason-list mr_long_extreme mr_short_extreme \
  --exit-reason-list mean_hit time_stop vol_decay trend_expand
```

### Helper scripts

```powershell
.\scripts\validate_freqtrade.ps1 `
  -Config user_data/configs/volatility_rotation_mr_backtest_static.json
```

```powershell
.\scripts\run_bias_checks.ps1 `
  -Config user_data/configs/volatility_rotation_mr_backtest_static.json `
  -Timerange 20240101-20241231
```

## Binance Futures Dry-Run Mode

Use dry-run for operational testing on the live dynamic universe.

- config: `user_data/configs/volatility_rotation_mr_binance_dryrun.json`
- pairlist mode: `VolumePairList + filters`
- stoploss_on_exchange: disabled

### Show the merged dry-run config

```bash
freqtrade show-config \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json \
  --config user_data/configs/volatility_rotation_mr_private.json \
  --strategy VolatilityRotationMR
```

### Dry-run launch

```bash
freqtrade trade \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json \
  --config user_data/configs/volatility_rotation_mr_private.json \
  --strategy VolatilityRotationMR
```

## Binance Futures Live Mode

Use the live profile only after dry-run behavior is understood.

- config: `user_data/configs/volatility_rotation_mr_binance_live.json`
- pairlist mode: dynamic runtime pairlist
- stoploss_on_exchange: enabled
- stoploss_on_exchange_interval: `60`
- stoploss_price_type: `mark`

`stoploss_price_type` must be validated by Freqtrade startup checks against Binance futures support.
If the exchange or Freqtrade rejects it, startup should fail fast and you should correct the value
before trading live.

### Show the merged live config

```bash
freqtrade show-config \
  --config user_data/configs/volatility_rotation_mr_binance_live.json \
  --config user_data/configs/volatility_rotation_mr_private.json \
  --strategy VolatilityRotationMR
```

### Live launch with private overlay

```bash
freqtrade trade \
  --config user_data/configs/volatility_rotation_mr_binance_live.json \
  --config user_data/configs/volatility_rotation_mr_private.json \
  --strategy VolatilityRotationMR
```

### Live startup runbook

After startup:

1. Verify Binance account mode is still `One-way Mode`.
2. Verify Binance asset mode is still `Single-Asset Mode`.
3. Verify the final merged config with `freqtrade show-config`.
4. Verify the number of exchange-side stop orders equals the number of open positions.
5. Verify no orphaned conditional stop orders remain after reconnects or restarts.

## Validation Artifact

The public validation template lives at:

- `docs/validation/public_validation_summary.md`

This file is intentionally small and safe to commit. It is the place to record:

- merged config used
- pair snapshot generation command
- backtest command
- lookahead command
- recursive command
- headline metrics
- `enter_tag` and `exit_tag` breakdown
- limitations and unresolved caveats

## Strategy Notes

- main timeframe: `5m`
- informative timeframe: `1h`
- futures only
- isolated margin only
- `liquidation_buffer = 0.08`
- next-candle reversal only
- live funding data remains restricted to optional runmode-guarded entry confirmation, never as a
  historical baseline feature

## Known Limitations

- breakout blocking remains intentionally simple and rule-based
- VWAP is session-based and practical rather than exchange-microstructure-specific
- the Binance order-size guard is conservative when exchange metadata is missing
- the static pair snapshot is reproducible only until you intentionally regenerate it
- live spread, orderbook, and funding filters remain disabled by default to preserve reproducibility
