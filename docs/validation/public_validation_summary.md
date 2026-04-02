# Public Validation Summary

This repository commits only small, safe validation artifacts.
Large raw backtest blobs, exchange secrets, private overlays, and live credentials must not be committed.

Validation status as of `2026-04-02`:

- Freqtrade version: `2026.2`
- Python version: `3.13.3`
- CCXT version: `4.5.46`
- Workspace environment: pinned local venv at `.venv-freqtrade`

## A. Engineering Validation

### Environment and config layering

- The repository loads in a real Freqtrade environment built from the pinned local venv.
- Layered configs remain intact for PTI research, Binance dry-run, and Binance live.
- `show-config` validation succeeded for:
  - `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json`
  - `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json`
  - `user_data/configs/volatility_rotation_mr_binance_dryrun.json` plus private overlay
  - `user_data/configs/volatility_rotation_mr_binance_live.json` plus private overlay

### Bias and determinism checks

- PTI baseline recursive analysis on `ETH/USDT:USDT`: clean
- PTI diagnostic recursive analysis on `ETH/USDT:USDT`: clean
- Result in both cases: `No lookahead bias on indicators found.`

### Binance dry-run/live safety

- Existing Binance dry-run/live architecture remains unchanged.
- `scripts/preflight_binance.ps1` still passes in dry-run and live modes when layered with a private overlay.
- `stoploss_price_type = mark` remains accepted by startup validation.
- No Binance live safety settings were changed in this validation pass.

## B. Alpha Validation

### Published research path

The repository now treats the point-in-time research workflow as the primary alpha-validation path:

- PTI baseline config: `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json`
- PTI diagnostic config: `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json`
- PTI snapshot: `user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json`

The old generic static config remains available only as a fallback:

- `user_data/configs/volatility_rotation_mr_backtest_static.json`
- `user_data/pairs/binance_usdt_futures_snapshot.json`

### 1. Old Current-Market Snapshot Run

- Config: `user_data/configs/volatility_rotation_mr_backtest_static.json`
- Snapshot: `user_data/pairs/binance_usdt_futures_snapshot.json`
- Timerange: `20240101-20241231`
- Trades: `0`
- Total profit: `0.00%`
- Drawdown: `0.00%`
- Entry tags: `mr_long_extreme = 0`, `mr_short_extreme = 0`
- Exit tags: `mean_hit = 0`, `time_stop = 0`, `vol_decay = 0`, `trend_expand = 0`, `roi = 0`
- Lookahead verdict: `too few trades caught (0/10). Test failed.`
- Recursive verdict: clean

Interpretation:

- This run was operationally valid, but the snapshot had drifted toward a current-market runtime universe dominated by pairs that were historically misaligned with the 2024 test window.

### 2. PTI Baseline Run

- Config: `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json`
- Snapshot: `user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json`
- Timerange: `20240101-20241231`
- Trades: `3`
- Total profit: `0.96%` / `95.690 USDT`
- Drawdown: `0.00%`
- Entry tags:
  - `mr_long_extreme = 3`
  - `mr_short_extreme = 0`
- Exit tags:
  - `roi = 2`
  - `mean_hit = 1`
  - `vol_decay = 0`
  - `trend_expand = 0`
- Lookahead verdict: `too few trades caught (0/10). Test failed.`
- Recursive verdict: clean
- Published artifact: `docs/validation/analysis/pti_baseline_backtest_2024.md`

Interpretation:

- The PTI snapshot fixed the original universe-drift failure mode and moved the research result from `0` to `3` trades.
- The zero-trade issue was reduced, but the baseline remains too sparse for optimization-grade statistics.

### 3. PTI Diagnostic Run

- Config: `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json`
- Snapshot: `user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json`
- Timerange: `20240101-20241231`
- Trades: `11`
- Total profit: `3.03%` / `302.645 USDT`
- Drawdown: `0.00%`
- Entry tags:
  - `mr_long_extreme = 10`
  - `mr_short_extreme = 1`
- Exit tags:
  - `roi = 8`
  - `mean_hit = 2`
  - `vol_decay = 1`
  - `trend_expand = 0`
- Lookahead verdict: `No bias` on `11` signals
- Recursive verdict: clean
- Published artifact: `docs/validation/analysis/pti_diagnostic_backtest_2024.md`

Interpretation:

- The research-only diagnostic relaxation improves the PTI sample from `3` to `11` trades.
- It is useful for diagnosis and lookahead validation, but the sample is still small for serious optimization.

## Alpha Diagnosis

### Universe drift vs signal sparsity

- Universe drift was fixed by the PTI snapshot.
- The remaining bottleneck is signal sparsity, not engineering.
- The PTI baseline funnel confirms the main binding gates:
  - `active_pair` collapses `2,102,100` volume-positive rows down to `75`
  - `weak_trend_regime` then collapses those to `4`
  - short-side BB breach and bearish reversal remain extremely rare

### Monthly clustering

Published clustering artifacts:

- `docs/validation/analysis/monthly_signal_clustering_2024.md`
- `docs/validation/analysis/monthly_signal_clustering_2024_diagnostic.md`

Observed clustering:

- PTI baseline signals cluster entirely in `2024-01` and `2024-03`
- PTI diagnostic signals cluster in `2024-01`, `2024-03`, and a single short in `2024-08`
- This is a structural sample-distribution problem, not just a point estimate issue

### Density sweep

Published artifact:

- `docs/validation/analysis/signal_density_sweep_2024.md`

Observed density sweep:

- baseline: `3` total signals
- regime_relaxed: `8`
- combined_mild: `8`
- diagnostic: `11`
- diagnostic_plus: `11`
- exploratory_plus: `12`

Interpretation:

- Relaxing regime gates helps more than relaxing `price_z_threshold` or `bb_width_min` in isolation.
- Even after wider research-only relaxations, the tested PTI 2024 sample still fails to reach `20` signals.

## Walk-Forward PTI Matrix

Published artifact:

- `docs/validation/alpha_validation_matrix.md`

Matrix execution note:

- The walk-forward matrix uses `5m` backtests without `--timeframe-detail 1m` to keep the broader anchor/window sweep tractable.
- The published PTI baseline and PTI diagnostic headline runs above remain the higher-fidelity single-window reference runs.

Anchors tested:

- `2023-07-01`
- `2024-01-01`
- `2024-04-01`
- `2024-07-01`
- `2024-10-01`
- `2025-01-01`

Windows tested:

- next `3` months
- next `6` months

Summary:

| Variant | Total trades across matrix | Total profit USDT | Best single run | Usable sample reached? |
| --- | ---: | ---: | --- | --- |
| baseline | `6` | `191.626` | `2024-01-01 + 3m` with `3` trades | `No` |
| diagnostic | `25` | `822.403` | `2024-01-01 + 3m` and `+6m` with `10` trades | `No` |

Observed pattern:

- Only the `2024-01-01` anchor produces a multi-trade burst.
- `2024-04-01` and `2024-07-01` diagnostic windows produce only a single short trade each.
- `2024-10-01` and `2025-01-01` produce no trades in either variant.
- No tested anchor/window/variant reaches the `20`-trade usable-sample threshold.

## Decision Memo

Decision:

- `diagnostic is only viable as a research profile`
- `thesis is coherent but too sparse for optimization-grade statistics in the tested windows`

Practical recommendation:

- Keep live and Binance safety settings unchanged.
- Do not spend more time on aggressive hyperopt yet.
- If optimization is revisited, do it only after expanding the historical window or historically aligned universe enough to produce a materially denser sample.
