# VolatilityRotationMR Workspace

Primary documentation lives in `README_VolatilityRotationMR.md`.

Primary 2024 alpha-validation path:
- `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01.json`
- `user_data/configs/volatility_rotation_mr_backtest_static_2024-01-01_diagnostic.json`
- `user_data/pairs/binance_usdt_futures_snapshot_2024-01-01.json`
- `scripts/build_historical_pair_snapshot.py`
- `scripts/diagnose_signal_funnel.py`
- `scripts/report_monthly_signal_clustering.py`
- `scripts/sweep_signal_density.py`
- `scripts/run_pti_validation_matrix.py`
- `docs/validation/public_validation_summary.md`
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
- `scripts/start_dryrun.ps1`
- `scripts/start_live.ps1`

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
