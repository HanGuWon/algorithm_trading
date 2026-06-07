# VolatilityRotationMR Workspace

Primary documentation lives in `README_VolatilityRotationMR.md`.

Primary broader alpha-validation path:
- `user_data/pairs/binance_usdt_futures_research_candidates.json`
- `user_data/pairs/binance_usdt_futures_snapshot_union_top50_2022-2025.json`
- `scripts/build_research_candidate_universe.py`
- `scripts/build_snapshot_sensitivity_matrix.py`
- `scripts/run_pti_validation_matrix_deduped.py`
- `scripts/run_side_ablation_matrix.py`
- `scripts/run_signal_event_study.py`
- `scripts/report_signal_indicator_diagnostics.py`
- `docs/validation/public_validation_summary.md`
- `docs/validation/final_decision_memo.md`
- `docs/validation/alpha_validation_matrix_deduped.md`
- `docs/validation/analysis/research_candidate_universe.md`
- `docs/validation/analysis/historical_snapshot_universe_sensitivity.md`
- `docs/validation/analysis/side_ablation_matrix.md`
- `docs/validation/analysis/signal_event_study.md`
- `docs/validation/analysis/signal_indicator_diagnostics.md`

Published long-only research path:
- `scripts/longonly_research_utils.py`
- `scripts/run_longonly_validation_matrix.py`
- `scripts/run_longonly_concentration_analysis.py`
- `scripts/run_longonly_regime_context.py`
- `scripts/run_longonly_signal_quality.py`
- `scripts/run_longonly_cost_stress.py`
- `scripts/run_longonly_promotion_study.py`
- `scripts/run_longonly_parameter_stability.py`
- `scripts/run_longonly_time_concentration_stress.py`
- `user_data/configs/volatility_rotation_mr_backtest_top50_longonly.json`
- `user_data/configs/volatility_rotation_mr_backtest_top50_diagnostic_longonly.json`
- `user_data/configs/volatility_rotation_mr_backtest_union_top50_pairs.json`
- `docs/validation/longonly_research_path.md`
- `docs/validation/alpha_validation_matrix_longonly.md`
- `docs/validation/longonly_promotion_study.md`
- `docs/validation/analysis/longonly_concentration_risk.md`
- `docs/validation/analysis/longonly_regime_context.md`
- `docs/validation/analysis/longonly_signal_quality.md`
- `docs/validation/analysis/longonly_cost_stress.md`
- `docs/validation/analysis/longonly_parameter_stability.md`
- `docs/validation/analysis/longonly_time_concentration_stress.md`

Current public endpoint:
- full long/short remains parked
- the only follow-up candidate tested beyond the broader PTI path is `VolatilityRotationMRDiagnosticLongOnly`
- the frozen-candidate promotion study failed its forward holdouts and ends at `No-go / Park` even for long-only

Current implementation follow-up:
- `VolatilityRotationMRFlushReboundLongOnly`
- `VolatilityRotationMRDelayedConfirmLongOnly`
- `scripts/run_strict_validation.py`
- `scripts/run_cloud_strict_validation.sh`
- `scripts/run_major_11_diagnostics.py`
- `scripts/run_major_11_bias_audit.py`
- `scripts/event_study_flush_rebound.py`
- `scripts/scan_flush_threshold_surface.py`
- `scripts/select_robust_flush_candidates.py`
- `scripts/compare_flush_surface_baselines.py`
- `scripts/diagnose_flush_rebound_components.py`
- `scripts/recommend_flush_candidate_simplifications.py`
- `scripts/report_flush_fixed_candidate_set.py`
- `scripts/check_hidden_unicode.py`
- `.github/workflows/strict-validation.yml`
- `docs/validation/strict_gate_spec.md`
- `docs/validation/cloud_strict_validation_runbook.md`
- `docs/validation/major_11_external_review_response.md`
- `docs/validation/analysis/major_11_concentration_diagnostics.md`
- `docs/validation/analysis/major_11_bias_audit.md`
- `docs/validation/analysis/major_11_flush_rebound_event_study.md`
- `docs/validation/analysis/major_11_flush_threshold_surface.md`
- `docs/validation/analysis/major_11_robust_flush_candidate_manifest.md`
- `docs/validation/analysis/major_11_flush_baseline_comparison.md`
- `docs/validation/analysis/major_11_flush_baseline_candidate_summary.md`
- `docs/validation/analysis/major_11_flush_rebound_component_diagnostics.md`
- `docs/validation/analysis/major_11_flush_candidate_simplification_recommendations.md`
- `docs/validation/analysis/major_11_flush_fixed_candidate_set.md`
- `docker-compose.yml`
- `docs/deployment/docker_vm_free_tier.md`

The major-11 flush threshold surface is a research-only diagnostic. It now reports
unique signal-set counts, duplicate grid masks, cluster-first matched-null excess,
and train/validation split checks before labeling robust research candidates.

The major-11 flush baseline comparison is also research-only. It freezes a robust
candidate manifest first, then compares those candidates against simpler oversold
definitions under the same next-open, cluster-first, matched-null, and
train/validation framework. The candidate summary separates CI-aware baseline
wins from point-estimate-only wins before any follow-up diagnostics. It is not a
strategy promotion gate by itself.

The major-11 flush/rebound component diagnostic then uses only the baseline-surviving
candidate set and fixed component definitions to distinguish immediate flush value,
filter ablation value, and short rebound-confirmation value. It is also research-only.

The major-11 flush simplification recommendation report reads the baseline-surviving
candidate summary and component diagnostic artifacts, then ranks fixed-scope next
steps such as keeping the original immediate flush or testing a breakout-block
removal candidate. It does not run a new grid search or create a deployable strategy.

The major-11 fixed candidate set report then evaluates only the retained original
immediate-flush candidates and recommended fixed simplifications. It includes
matched-null event-study metrics, validation-period behavior, top-removal
concentration stress, and round-trip cost stress without widening the search space.

These additions are research/deployment infrastructure only. They do not promote any strategy to
live use.

Single-anchor 2024 PTI reference path:
- `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json`
- `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json`
- `user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json`
- `scripts/build_historical_pair_snapshot.py`
- `scripts/diagnose_signal_funnel.py`
- `scripts/report_monthly_signal_clustering.py`
- `scripts/sweep_signal_density.py`
- `scripts/run_pti_validation_matrix.py`
- `docs/validation/alpha_validation_matrix.md`
- `docs/validation/analysis/pti_baseline_backtest_2024.md`
- `docs/validation/analysis/pti_diagnostic_backtest_2024.md`
- `docs/validation/analysis/signal_density_sweep_2024.md`

Generic static fallback only:
- `user_data/configs/volatility_rotation_mr_backtest_static.json`
- `user_data/pairs/binance_usdt_futures_snapshot.json`

Operational helpers:
- `scripts/bootstrap_freqtrade_env.ps1`
- `scripts/freqtrade_cmd.ps1`
- `scripts/preflight_binance.ps1`
- `scripts/python_startup/sitecustomize.py`
- `scripts/start_dryrun.ps1`
- `scripts/start_live.ps1`
- `scripts/run_strict_validation.py`

Deployment helpers:
- `docker-compose.yml`
- `.env.example`
- `docs/deployment/docker_vm_free_tier.md`
- `scripts/guard_live_readiness.py`
- `scripts/check_dryrun_container.sh`

GitHub validation:
- pull requests run `.github/workflows/strict-validation.yml` in smoke mode
- manual workflow dispatch with `mode=full` runs the Dockerized full strict gate
- smoke mode also verifies that live startup is blocked by default

Primary layered configs:
- `user_data/configs/volatility_rotation_mr_base.json`
- `user_data/configs/volatility_rotation_mr_binance_dryrun.json`
- `user_data/configs/volatility_rotation_mr_binance_live.json`
- `user_data/configs/volatility_rotation_mr_backtest_static.json`
- `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json`
- `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json`
- `user_data/configs/volatility_rotation_mr_analysis_market.json`

Compatibility alias only:
- `user_data/configs/volatility_rotation_mr_futures.json`

Strategy files:
- `user_data/strategies/VolatilityRotationMR.py`
