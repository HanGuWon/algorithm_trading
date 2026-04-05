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

Current research endpoint:

- full long/short remains parked
- `VolatilityRotationMRDiagnosticLongOnly` was the only follow-up candidate advanced into a frozen promotion study
- that frozen candidate failed forward holdouts and is currently parked as well
- Binance dry-run/live safety settings are unchanged

## Config Model

Primary configs:

- `user_data/configs/volatility_rotation_mr_base.json`
- `user_data/configs/volatility_rotation_mr_binance_dryrun.json`
- `user_data/configs/volatility_rotation_mr_binance_live.json`
- `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json`
- `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json`
- `user_data/configs/volatility_rotation_mr_analysis_market.json`
- `user_data/configs/volatility_rotation_mr_private.example.json`

Generic static fallback:

- `user_data/configs/volatility_rotation_mr_backtest_static.json`

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

If `freqtrade` is not installed globally, bootstrap a pinned local environment:

```powershell
.\scripts\bootstrap_freqtrade_env.ps1
```

Then use the wrapper:

```powershell
.\scripts\freqtrade_cmd.ps1 --version
```

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

## Primary Broader Alpha Research Path

The repository's primary alpha-validation workflow is now broader than the original single-anchor
2024 PTI run. It starts from a reproducible Binance USDT-M research candidate universe, rebuilds
quarterly PTI snapshots on historical candles, then judges the thesis on a non-overlapping 6-month
matrix plus side-ablation and event-study diagnostics.

Primary files:

- research candidates: `user_data/pairs/binance_usdt_futures_research_candidates.json`
- top-50 union for broad research downloads: `user_data/pairs/binance_usdt_futures_snapshot_union_top50_2022-2025.json`
- candidate universe builder: `scripts/build_research_candidate_universe.py`
- quarterly PTI sensitivity builder: `scripts/build_snapshot_sensitivity_matrix.py`
- de-overlapped matrix runner: `scripts/run_pti_validation_matrix_deduped.py`
- side-ablation runner: `scripts/run_side_ablation_matrix.py`
- signal event-study runner: `scripts/run_signal_event_study.py`
- indicator diagnostics: `scripts/report_signal_indicator_diagnostics.py`
- public summary: `docs/validation/public_validation_summary.md`
- final decision memo: `docs/validation/final_decision_memo.md`

Exact commands used for the broadened research pass:

```bash
python scripts/build_research_candidate_universe.py --target-size 90
```

```bash
freqtrade download-data \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json \
  --trading-mode futures \
  --timeframes 1h \
  --timerange 20211215-20250715 \
  --pairs-file user_data/pairs/binance_usdt_futures_research_candidates.json \
  --prepend
```

```bash
python scripts/build_snapshot_sensitivity_matrix.py \
  --pairs-file user_data/pairs/binance_usdt_futures_research_candidates.json \
  --anchor-start 2022-01-01 \
  --anchor-end 2025-01-01 \
  --top-n 20 35 50 \
  --union-top-n 50
```

```bash
freqtrade download-data \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json \
  --trading-mode futures \
  --timeframes 5m \
  --timerange 20211215-20250715 \
  --pairs-file user_data/pairs/binance_usdt_futures_snapshot_union_top50_2022-2025.json \
  --prepend
```

```bash
freqtrade download-data \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json \
  --trading-mode futures \
  --timeframes 5m \
  --timerange 20250115-20250715 \
  --pairs-file user_data/pairs/binance_usdt_futures_snapshot_union_top50_2022-2025.json
```

```bash
python scripts/run_pti_validation_matrix_deduped.py \
  --anchors 2022-01-01 2022-07-01 2023-01-01 2023-07-01 2024-01-01 2024-07-01 2025-01-01 \
  --window-months 6 \
  --snapshot-top-n 50 \
  --output-md docs/validation/alpha_validation_matrix_deduped.md \
  --output-csv docs/validation/alpha_validation_matrix_deduped.csv
```

```bash
python scripts/run_side_ablation_matrix.py \
  --anchors 2022-01-01 2022-07-01 2023-01-01 2023-07-01 2024-01-01 2024-07-01 2025-01-01 \
  --window-months 6 \
  --snapshot-top-n 50 \
  --output-md docs/validation/analysis/side_ablation_matrix.md \
  --output-csv docs/validation/analysis/side_ablation_matrix.csv
```

```bash
python scripts/run_signal_event_study.py \
  --anchors 2022-01-01 2022-07-01 2023-01-01 2023-07-01 2024-01-01 2024-07-01 2025-01-01 \
  --window-months 6 \
  --snapshot-top-n 50 \
  --output-md docs/validation/analysis/signal_event_study.md \
  --output-csv docs/validation/analysis/signal_event_study.csv
```

```bash
python scripts/report_signal_indicator_diagnostics.py \
  --anchors 2022-01-01 2022-07-01 2023-01-01 2023-07-01 2024-01-01 2024-07-01 2025-01-01 \
  --window-months 6 \
  --snapshot-top-n 50 \
  --output-md docs/validation/analysis/signal_indicator_diagnostics.md \
  --output-csv docs/validation/analysis/signal_indicator_diagnostics.csv
```

The broader path is the primary go/no-go workflow for optimization decisions.
The older 2024-only PTI flow remains useful as a narrow reference window, but it should not be used
alone to argue that the thesis is statistically sufficient.

## Frozen Long-Only Follow-Up

The long-only package is published in this repository for diagnosis and reproducibility only.

Primary files:

- long-only path and commands: `docs/validation/longonly_research_path.md`
- long-only matrix: `docs/validation/alpha_validation_matrix_longonly.md`
- frozen promotion study: `docs/validation/longonly_promotion_study.md`
- parameter stability: `docs/validation/analysis/longonly_parameter_stability.md`
- time concentration stress: `docs/validation/analysis/longonly_time_concentration_stress.md`

Current interpretation:

- `VolatilityRotationMRDiagnosticLongOnly` was the only follow-up research candidate after the broader PTI pass
- the candidate-selection evidence remained the same local package already summarized in the long-only matrix
- the frozen promotion holdouts `2024-07-01 -> 2025-01-01`, `2025-01-01 -> 2025-07-01`, and the `2024-07-01 -> 2025-07-01` 12m forward view all produced `0` trades
- local threshold perturbations around the frozen defaults were stable inside the profitable `2024-01 -> 2024-07` burst, but that did not convert into forward evidence
- no `VolatilityRotationMRDiagnosticLongOnlyContext` subclass was added because the observed flush / oversold context mostly relabeled the same exposure and did not clear the bar for a materially distinct, better-distributed filter

Result:

- `No-go / Park` for full long/short
- `No-go / Park` for the frozen long-only candidate in its current form

## Research-Safe 2024 PTI Backtesting Mode

This is the primary alpha-validation path for the repository.
It uses a point-in-time static universe aligned to `2024-01-01`, not the current runtime pairlist.

Primary files:

- baseline config: `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json`
- diagnostic config: `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json`
- PTI snapshot: `user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json`
- historical snapshot builder: `scripts/build_historical_pair_snapshot.py`
- signal funnel tool: `scripts/diagnose_signal_funnel.py`
- monthly clustering tool: `scripts/report_monthly_signal_clustering.py`
- density sweep tool: `scripts/sweep_signal_density.py`
- walk-forward matrix tool: `scripts/run_pti_validation_matrix.py`

The older generic static flow remains available as a fallback:

- fallback config: `user_data/configs/volatility_rotation_mr_backtest_static.json`
- fallback snapshot: `user_data/pairs/binance_usdt_futures_snapshot.json`

Use the fallback flow only when you need a generic static-pairlist example. For 2024 research, prefer
the PTI files above because the current-market snapshot drifts away from the historical window.

### Build or rebuild the PTI snapshot

This step ranks pairs from historical candles around the reference date instead of using current
exchange tickers.

```bash
freqtrade download-data \
  --config user_data/configs/volatility_rotation_mr_backtest_static.json \
  --trading-mode futures \
  --timeframes 1h \
  --timerange 20231218-20250115 \
  --pairs BTC/USDT:USDT ETH/USDT:USDT BNB/USDT:USDT SOL/USDT:USDT XRP/USDT:USDT DOGE/USDT:USDT ADA/USDT:USDT LINK/USDT:USDT AVAX/USDT:USDT TRX/USDT:USDT DOT/USDT:USDT LTC/USDT:USDT BCH/USDT:USDT ETC/USDT:USDT ATOM/USDT:USDT NEAR/USDT:USDT APT/USDT:USDT SUI/USDT:USDT UNI/USDT:USDT FIL/USDT:USDT ARB/USDT:USDT OP/USDT:USDT ICP/USDT:USDT TON/USDT:USDT PEPE/USDT:USDT
```

```bash
python scripts/build_historical_pair_snapshot.py \
  --datadir user_data/data/binance \
  --reference-date 2024-01-01 \
  --quote-currency USDT \
  --lookback 7d \
  --post-window 30d \
  --top-n 20 \
  --min-coverage-ratio 0.95 \
  --output-json user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json \
  --output-csv docs/validation/analysis/historical_snapshot_2024-01-01.csv \
  --output-md docs/validation/analysis/historical_snapshot_2024-01-01.md
```

### Show the merged PTI configs

`show-config` on Freqtrade `2026.2` reads the strategy from config, so the PTI research commands use
the config file directly.

```bash
freqtrade show-config \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json
```

```bash
freqtrade show-config \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json
```

### Download futures data with explicit startup buffer

`startup_candle_count = 2400`, which is about 8 days and 8 hours of 5m candles. `download-data`
does not add that buffer automatically, so the download range must start earlier than the research
window.

Example 2024 research window:

- analysis start: `2024-01-01`
- download start: `2023-12-18`

```bash
freqtrade download-data \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json \
  --trading-mode futures \
  --timeframes 1m 5m 1h \
  --timerange 20231218-20250115
```

### PTI baseline backtest

```bash
freqtrade backtesting \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json \
  --strategy VolatilityRotationMR \
  --strategy-path user_data/strategies \
  --timeframe 5m \
  --timeframe-detail 1m \
  --timerange 20240101-20241231 \
  --enable-protections \
  --export signals \
  --backtest-directory user_data/backtest_results
```

### PTI diagnostic backtest

This profile is for research diagnosis only. Do not use it for dry-run or live trading.

```bash
freqtrade backtesting \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json \
  --strategy VolatilityRotationMRDiagnostic \
  --strategy-path user_data/strategies \
  --timeframe 5m \
  --timeframe-detail 1m \
  --timerange 20240101-20241231 \
  --enable-protections \
  --export signals \
  --backtest-directory user_data/backtest_results
```

### PTI lookahead analysis

Baseline:

```bash
freqtrade lookahead-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json \
  --config user_data/configs/volatility_rotation_mr_analysis_market.json \
  --strategy VolatilityRotationMR \
  --strategy-path user_data/strategies \
  --timeframe 5m \
  --timeframe-detail 1m \
  --timerange 20240101-20241231 \
  --lookahead-analysis-exportfilename docs/validation/logs/lookahead-analysis-2024-pti.csv \
  --backtest-directory user_data/backtest_results
```

Diagnostic:

```bash
freqtrade lookahead-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json \
  --config user_data/configs/volatility_rotation_mr_analysis_market.json \
  --strategy VolatilityRotationMRDiagnostic \
  --strategy-path user_data/strategies \
  --timeframe 5m \
  --timeframe-detail 1m \
  --timerange 20240101-20241231 \
  --lookahead-analysis-exportfilename docs/validation/logs/lookahead-analysis-2024-pti-diagnostic.csv \
  --backtest-directory user_data/backtest_results
```

### PTI recursive analysis

Pin the pair explicitly for deterministic comparison.

Baseline:

```bash
freqtrade recursive-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json \
  --strategy VolatilityRotationMR \
  --strategy-path user_data/strategies \
  --timeframe 5m \
  --timerange 20240101-20241231 \
  --startup-candle 1600 2000 2400 \
  --pairs ETH/USDT:USDT
```

Diagnostic:

```bash
freqtrade recursive-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json \
  --strategy VolatilityRotationMRDiagnostic \
  --strategy-path user_data/strategies \
  --timeframe 5m \
  --timerange 20240101-20241231 \
  --startup-candle 1600 2000 2400 \
  --pairs ETH/USDT:USDT
```

### PTI backtesting analysis by tag

Baseline:

```bash
freqtrade backtesting-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json \
  --backtest-directory user_data/backtest_results \
  --analysis-groups 1 2 5 \
  --analysis-to-csv \
  --analysis-csv-path docs/validation/analysis/2024_pti \
  --enter-reason-list mr_long_extreme mr_short_extreme \
  --exit-reason-list mean_hit time_stop vol_decay trend_expand roi \
  --timerange 20240101-20241231
```

Diagnostic:

```bash
freqtrade backtesting-analysis \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json \
  --backtest-directory user_data/backtest_results \
  --analysis-groups 1 2 5 \
  --analysis-to-csv \
  --analysis-csv-path docs/validation/analysis/2024_pti_diagnostic \
  --enter-reason-list mr_long_extreme mr_short_extreme \
  --exit-reason-list mean_hit time_stop vol_decay trend_expand roi \
  --timerange 20240101-20241231
```

### PTI signal funnel and density diagnostics

Baseline funnel:

```bash
python scripts/diagnose_signal_funnel.py \
  --snapshot-json user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json \
  --datadir user_data/data/binance \
  --timerange 20240101-20241231 \
  --output-md docs/validation/analysis/signal_funnel_2024.md \
  --output-csv docs/validation/analysis/signal_funnel_2024.csv
```

Diagnostic funnel:

```bash
python scripts/diagnose_signal_funnel.py \
  --snapshot-json user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json \
  --strategy-class VolatilityRotationMRDiagnostic \
  --datadir user_data/data/binance \
  --timerange 20240101-20241231 \
  --output-md docs/validation/analysis/signal_funnel_2024_diagnostic.md \
  --output-csv docs/validation/analysis/signal_funnel_2024_diagnostic.csv
```

Density sweep:

```bash
python scripts/sweep_signal_density.py \
  --snapshot-json user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json \
  --datadir user_data/data/binance \
  --timerange 20240101-20241231 \
  --output-md docs/validation/analysis/signal_density_sweep_2024.md \
  --output-csv docs/validation/analysis/signal_density_sweep_2024.csv \
  --target-signals 20
```

Monthly clustering for the baseline run:

```bash
python scripts/report_monthly_signal_clustering.py \
  --snapshot-json user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json \
  --strategy-class VolatilityRotationMR \
  --datadir user_data/data/binance \
  --timerange 20240101-20241231 \
  --backtest-zip user_data/backtest_results/backtest-result-2026-04-02_12-44-18.zip \
  --output-md docs/validation/analysis/monthly_signal_clustering_2024.md \
  --output-csv docs/validation/analysis/monthly_signal_clustering_2024.csv
```

Monthly clustering for the diagnostic run:

```bash
python scripts/report_monthly_signal_clustering.py \
  --snapshot-json user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json \
  --strategy-class VolatilityRotationMRDiagnostic \
  --datadir user_data/data/binance \
  --timerange 20240101-20241231 \
  --backtest-zip user_data/backtest_results/backtest-result-2026-04-02_12-30-31.zip \
  --output-md docs/validation/analysis/monthly_signal_clustering_2024_diagnostic.md \
  --output-csv docs/validation/analysis/monthly_signal_clustering_2024_diagnostic.csv
```

### PTI walk-forward validation matrix

Use this only after the PTI baseline and diagnostic single-window runs are understood. The matrix is
meant to answer whether the thesis is structurally sparse across multiple point-in-time universes,
not to replace the published PTI 2024 baseline and diagnostic summaries.

```bash
python scripts/run_pti_validation_matrix.py \
  --anchors 2023-07-01 2024-01-01 2024-04-01 2024-07-01 2024-10-01 2025-01-01 \
  --windows 3 6 \
  --base-config user_data/configs/volatility_rotation_mr_base.json \
  --strategy-path user_data/strategies \
  --snapshot-dir user_data/pairs \
  --output-md docs/validation/alpha_validation_matrix.md \
  --output-csv docs/validation/alpha_validation_matrix.csv \
  --logs-dir docs/validation/logs/matrix \
  --backtest-dir user_data/backtest_results/matrix \
  --usable-trade-threshold 20
```

Primary published PTI artifacts:

- `docs/validation/analysis/pti_baseline_backtest_2024.md`
- `docs/validation/analysis/pti_diagnostic_backtest_2024.md`
- `docs/validation/analysis/monthly_signal_clustering_2024.md`
- `docs/validation/analysis/monthly_signal_clustering_2024_diagnostic.md`
- `docs/validation/analysis/signal_density_sweep_2024.md`
- `docs/validation/alpha_validation_matrix.md`

### PTI hyperopt

Run hyperopt only after the baseline produces a research-usable trade count.
The repository keeps the command for completeness, but PTI alpha validation currently relies on the
baseline and diagnostic backtests plus funnel diagnostics first.

```bash
freqtrade hyperopt \
  --config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json \
  --strategy VolatilityRotationMR \
  --strategy-path user_data/strategies \
  --timeframe 5m \
  --timeframe-detail 1m \
  --spaces buy sell \
  --hyperopt-loss SharpeHyperOptLossDaily \
  --timerange 20240101-20241231 \
  --random-state 42 \
  --job-workers 1 \
  -e 10
```

### Helper scripts

```powershell
.\scripts\validate_freqtrade.ps1 `
  -Config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json
```

```powershell
.\scripts\run_bias_checks.ps1 `
  -Config user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json `
  -Timerange 20240101-20241231 `
  -RecursivePair ETH/USDT:USDT
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
  --config user_data/configs/volatility_rotation_mr_private.json
```

### Dry-run launch

```bash
freqtrade trade \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json \
  --config user_data/configs/volatility_rotation_mr_private.json \
  --strategy VolatilityRotationMR
```

```powershell
.\scripts\preflight_binance.ps1 `
  -Mode dryrun `
  -PrivateConfig user_data/configs/volatility_rotation_mr_private.json
```

```powershell
.\scripts\start_dryrun.ps1 `
  -PrivateConfig user_data/configs/volatility_rotation_mr_private.json
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
  --config user_data/configs/volatility_rotation_mr_private.json
```

### Live launch with private overlay

```bash
freqtrade trade \
  --config user_data/configs/volatility_rotation_mr_binance_live.json \
  --config user_data/configs/volatility_rotation_mr_private.json \
  --strategy VolatilityRotationMR
```

```powershell
.\scripts\preflight_binance.ps1 `
  -Mode live `
  -PrivateConfig user_data/configs/volatility_rotation_mr_private.json
```

```powershell
.\scripts\start_live.ps1 `
  -PrivateConfig user_data/configs/volatility_rotation_mr_private.json
```

### Live startup runbook

After startup:

1. Verify Binance account mode is still `One-way Mode`.
2. Verify Binance asset mode is still `Single-Asset Mode`.
3. Verify the final merged config with `freqtrade show-config`.
4. Verify the number of exchange-side stop orders equals the number of open positions.
5. Verify no orphaned conditional stop orders remain after reconnects or restarts.
6. Verify `stoploss_price_type = mark` was accepted by startup and no exchange capability error was raised.

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
- a current-market snapshot can drift away from an older research window and reduce usable history
- live spread, orderbook, and funding filters remain disabled by default to preserve reproducibility
