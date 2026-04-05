# Public Validation Summary

This repository commits only small, safe validation artifacts.
Large raw backtest blobs, exchange secrets, private overlays, and live credentials must not be committed.

Validation status as of `2026-04-05`:

- Freqtrade version: `2026.2`
- Python version: `3.13.3`
- CCXT version: `4.5.46`
- Workspace environment: pinned local venv at `.venv-freqtrade`

## A. Engineering Validation

### Environment and config layering

- Layered configs still validate for PTI research, Binance dry-run, and Binance live.
- The live Binance safety model remains unchanged:
  - isolated futures
  - orderbook pricing
  - `stoploss_on_exchange = true`
  - `stoploss_price_type = mark`
  - private overlays / environment-variable secrets only

### Bias and determinism checks

The strategy logic itself was not redesigned in this pass.
Only research-only helper scripts and long-only research subclasses were added.

Latest recorded bias checks:

| Profile | Config | Recursive | Lookahead |
| --- | --- | --- | --- |
| PTI top50 baseline | `user_data/configs/temp_pti_2024_top50_base.json` (temporary run config) | clean | `No bias`, `11` signals |
| PTI top50 diagnostic | `user_data/configs/temp_pti_2024_top50_diag.json` (temporary run config) | clean | `No bias`, `20` signals |

### Binance dry-run/live safety

- `scripts/preflight_binance.ps1` remains valid for dry-run and live preflight checks.
- No Binance live profile, no secret handling path, and no stoploss-on-exchange behavior were changed in this pass.

## B. Alpha Validation

## 1. Legacy Current-Market Snapshot Failure

- Config: `user_data/configs/volatility_rotation_mr_backtest_static.json`
- Snapshot: `user_data/pairs/binance_usdt_futures_snapshot.json`
- Timerange: `20240101-20241231`
- Trades: `0`
- Profit: `0.00%`
- Drawdown: `0.00%`
- Interpretation: engineering-valid but historically misaligned because the runtime universe had drifted away from the 2024 research window.

## 2. Narrow Single-Anchor PTI Reference

This remains a useful reference run, but it is no longer the primary optimization decision path.

| Profile | Config | Snapshot | Timerange | Trades | Profit | Drawdown | Lookahead | Recursive |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| PTI baseline | `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json` | `user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json` | `20240101-20241231` | `3` | `+0.96%` / `95.690 USDT` | `0.00%` | inconclusive | clean |
| PTI diagnostic | `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json` | `user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json` | `20240101-20241231` | `11` | `+3.03%` / `302.645 USDT` | `0.00%` | `No bias` | clean |

Interpretation:

- The PTI snapshot fixed the zero-trade universe-drift problem.
- The sample was still too narrow to justify full optimization.

## 3. Expanded Historical Research Universe

Primary broadened-universe artifacts:

- `user_data/pairs/binance_usdt_futures_research_candidates.json`
- `docs/validation/analysis/research_candidate_universe.md`
- `docs/validation/analysis/historical_snapshot_universe_sensitivity.md`
- `user_data/pairs/binance_usdt_futures_snapshot_union_top50_2022-2025.json`

Candidate-universe summary:

- Exchange universe queried: Binance USDT-M perpetuals
- Research candidates retained: `90`
- Current active-and-evaluable rows in the selection pass: `469`
- Explicit exclusions:
  - listed after `2025-01-01`: `254`
  - inactive on exchange: `101`
  - stock/index/commodity proxies: `21`
  - non-ASCII novelty symbols: `3`

Snapshot sensitivity summary:

- Quarterly PTI anchors: `2022-01-01` through `2025-01-01`
- `top_n = 20`: always `20` selected pairs after the initial anchor
- `top_n = 35`: always `35` selected pairs after the initial anchor
- `top_n = 50`: ranged from `44` to `50` selected pairs by anchor
- Top-50 union used for broad research downloads: `85` pairs

Interpretation:

- Expanding the candidate universe materially improved the opportunity set.
- The retained PTI universe is now broad enough to test whether sample sparsity comes from the thesis itself rather than from a narrow candidate list.

## 4. Primary De-Overlapped Alpha Matrix

Primary artifact:

- `docs/validation/alpha_validation_matrix_deduped.md`

Primary design:

- non-overlapping forward `6m` windows
- anchors: `2022-01-01`, `2022-07-01`, `2023-01-01`, `2023-07-01`, `2024-01-01`, `2024-07-01`, `2025-01-01`
- PTI snapshot size: `top_n = 50`

Headline results:

| Variant | Raw trades | Unique trades | Profit | Long trades | Short trades | Usable window reached? |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| baseline | `15` | `15` | `376.381 USDT` | `12` | `3` | only `No` |
| diagnostic | `45` | `45` | `908.870 USDT` | `38` | `7` | `Yes`, but only in `2024-01 -> 2024-07` |

Most important window detail:

- `2024-01-01` diagnostic window: `27` trades, `733.229 USDT`, `0.50%` drawdown
- Every other diagnostic window: `0` to `8` trades
- Every baseline window except `2022-01`, `2024-01`, and `2025-01`: `0` trades

Interpretation:

- Expanding the universe solved the old zero-trade bottleneck and made the thesis statistically testable enough to diagnose.
- Deduping also exposed the real limitation: only one non-overlapping window carries a genuinely usable sample.
- The evidence is cleaner than the older overlapping matrix because the 2024-01 burst is no longer counted twice.

## 5. Side Ablation

Primary artifact:

- `docs/validation/analysis/side_ablation_matrix.md`

Summary:

| Variant | Trades | Profit | Long trades | Short trades |
| --- | ---: | ---: | ---: | ---: |
| baseline long+short | `15` | `376.381 USDT` | `12` | `3` |
| baseline long-only | `12` | `339.778 USDT` | `12` | `0` |
| diagnostic long+short | `45` | `908.870 USDT` | `38` | `7` |
| diagnostic long-only | `38` | `768.682 USDT` | `38` | `0` |

Interpretation:

- Long-only retains most of the baseline and diagnostic edge.
- The short side does add a small number of profitable realized trades, but the entire strategy still remains overwhelmingly long-dominated.
- In practical research terms, the long side is the only side with enough recurring structure to justify further thesis work.

## 6. Signal Event Study

Primary artifact:

- `docs/validation/analysis/signal_event_study.md`

Mean forward returns:

| Variant | Side | ret_12 | ret_24 | ret_48 | MFE_48 | MAE_48 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| baseline | long | `+0.0637` | `+0.0515` | `+0.0797` | `+0.0920` | `-0.0026` |
| baseline | short | `-0.0042` | `+0.0047` | `-0.0101` | `+0.0515` | `-0.0399` |
| diagnostic | long | `+0.0610` | `+0.0535` | `+0.0661` | `+0.0958` | `-0.0136` |
| diagnostic | short | `-0.0055` | `-0.0191` | `-0.0481` | `+0.0557` | `-0.0964` |

Mean-hit probability:

| Variant | Side | mean_hit_12 | mean_hit_24 | mean_hit_48 |
| --- | --- | ---: | ---: | ---: |
| baseline | long | `0.0000` | `0.0000` | `0.0000` |
| baseline | short | `0.0000` | `0.0000` | `0.0000` |
| diagnostic | long | `0.0526` | `0.0526` | `0.1053` |
| diagnostic | short | `0.0000` | `0.0000` | `0.0000` |

Interpretation:

- Raw long signals have positive forward return behavior across horizons.
- Raw short signals are weak to negative after `12`, `24`, and `48` candles, especially in the diagnostic profile.
- The short side is therefore not only sparse in realized trades; it also looks structurally worse at the raw-signal level.

## 7. Indicator Diagnostics and Backtesting-Analysis

Primary artifacts:

- `docs/validation/analysis/signal_indicator_diagnostics.md`
- `docs/validation/analysis/2024_pti_top50_base/group_*.csv`
- `docs/validation/analysis/2024_pti_top50_diag/group_*.csv`

Signal-candle indicator summary:

- Baseline long signals: `12`
- Baseline short signals: `3`
- Diagnostic long signals: `38`
- Diagnostic short signals: `7`
- Baseline near-miss rows: `28` long / `7` short
- Diagnostic near-miss rows: `74` long / `21` short

Observed signal-candle regimes:

- Long signals sit around:
  - `vol_z` ≈ `2.20` to `2.58`
  - `natr` ≈ `3.16%` to `3.21%`
  - `adx_1h` ≈ `17.7` to `19.6`
  - `rsi` ≈ `20.8` to `21.0`
  - `price_z` ≈ `-2.39` to `-2.47`
- Short signals are scarcer and less attractive:
  - `7` diagnostic short signals versus `21` diagnostic short near-misses
  - higher `rsi` and positive `price_z`, but weaker forward event-study behavior

Tag-level backtesting-analysis on the expanded 2024 top50 reference run:

- baseline:
  - `mr_long_extreme = 11`
  - exit split: `roi = 7`, `mean_hit = 4`
- diagnostic:
  - `mr_long_extreme = 26`
  - `mr_short_extreme = 1`
  - exit split: `roi = 21`, `mean_hit = 5`, `vol_decay = 1`

Interpretation:

- The gate stack is finding a coherent long-side oversold/reversal regime.
- The short side remains both scarce and lower-quality.

## 8. Long-Only Robustness Pass

Primary artifacts:

- `docs/validation/longonly_research_path.md`
- `docs/validation/alpha_validation_matrix_longonly.md`
- `docs/validation/longonly_promotion_study.md`
- `docs/validation/analysis/longonly_concentration_risk.md`
- `docs/validation/analysis/longonly_regime_context.md`
- `docs/validation/analysis/longonly_signal_quality.md`
- `docs/validation/analysis/longonly_cost_stress.md`
- `docs/validation/analysis/longonly_parameter_stability.md`
- `docs/validation/analysis/longonly_time_concentration_stress.md`

Headline long-only matrix:

| Variant | Raw trades | Unique trades | Profit | Usable windows |
| --- | ---: | ---: | ---: | ---: |
| baseline long-only | `12` | `12` | `339.778 USDT` | `0` |
| diagnostic long-only | `38` | `38` | `768.682 USDT` | `1` |

Concentration summary:

- Pair concentration is not the main failure mode:
  - diagnostic long-only top-1 pair share: `7.7%`
  - diagnostic long-only top-5 pair share: `31.8%`
  - diagnostic long-only remove-top-5 still leaves `524.535 USDT`
- Time concentration remains the main weakness:
  - removing the `2024-01-01 -> 2024-07-01` anchor leaves only `35.453 USDT` on `11` trades
  - removing month `2024-01` leaves only `46.275 USDT` on `15` trades

Regime summary:

- The edge is not broad across contexts.
- Baseline long-only signals land entirely in `flush_high` / `oversold_high`.
- Diagnostic long-only signals also land entirely in `flush_high` / `oversold_high`.
- Diagnostic long-only is strongest in `btc_neutral` and `btc_downtrend`; the lone `btc_uptrend` trade lost money.

Signal-quality summary:

- Long-only is not obviously blocked by raw opportunity scarcity alone:
  - baseline raw signals: `12`
  - diagnostic raw signals: `38`
- Structurally valid near-misses are abundant:
  - baseline good near-misses: `30`
  - diagnostic good near-misses: `83`
- The dominant missed-entry blocker is `bullish_reversal`, not pair availability.

Cost-stress summary:

- The long-only edge survives reasonable stress.
- Diagnostic long-only stays positive from `768.682 USDT` baseline to `716.009 USDT` under worse fee plus slippage stress.

## 9. Frozen Long-Only Promotion Study

This pass did not reopen optimization.
It froze `VolatilityRotationMRDiagnosticLongOnly` at the published diagnostic-long-only defaults and separated candidate-selection evidence from promotion evidence.

Promotion artifacts:

- `docs/validation/longonly_promotion_study.md`
- `docs/validation/longonly_promotion_study.csv`
- `docs/validation/analysis/longonly_parameter_stability.md`
- `docs/validation/analysis/longonly_time_concentration_stress.md`

Forward holdouts:

| Window | Trades | Profit | Drawdown |
| --- | ---: | ---: | ---: |
| `2024-07-01 -> 2025-01-01` | `0` | `0.000 USDT` | `0.00%` |
| `2025-01-01 -> 2025-07-01` | `0` | `0.000 USDT` | `0.00%` |
| `2024-07-01 -> 2025-07-01` (12m view) | `0` | `0.000 USDT` | `0.00%` |

Interpretation:

- the only follow-up candidate tested after the broader PTI path was `VolatilityRotationMRDiagnosticLongOnly`
- the frozen candidate had no forward promotion sample at all
- the broader local long-only package remains publishable and reproducible, but it is not promotable on current holdout evidence

Parameter-stability summary:

- the `2024-01-01 -> 2024-07-01` burst was locally stable under mild one-parameter perturbations
- `vol_z_min` and `adx_1h_max` moved realized trade count and PnL, but the edge did not collapse inside that profitable window
- local threshold stability does not rescue the missing forward sample

Time-concentration summary:

- remove best month `2024-01`: `15` trades, `46.275 USDT`
- remove best 2 months: `13` trades, `-18.521 USDT`
- remove best anchor `2024-01-01 -> 2024-07-01`: `11` trades, `35.453 USDT`
- forward holdout windows: `0` trades, `0.000 USDT`

## Final Recommendation

Expanded candidate-universe research materially improved sample density.
The thesis is no longer blocked by universe drift or engineering scaffolding.

However:

- only one non-overlapping diagnostic window reaches a usable sample on its own
- long-side evidence dominates almost completely
- short-side raw signals remain weak even when they occasionally produce realized profits
- long-only survives pair concentration and cost stress, but remains heavily concentrated in the `2024-01` flush-rebound environment
- the frozen long-only candidate produced `0` trades across both forward holdouts and the 12m forward view

Decision:

- `No-go` for full long/short optimization right now.
- `No-go / Park` for `VolatilityRotationMRDiagnosticLongOnly` in its current frozen form.
- no additional context-gated subclass was added because the current context labels mostly relabel the same flush / oversold burst and do not improve distribution.
- `Park` the strategy family until materially new evidence or a clearly distinct, better-distributed context design appears.
