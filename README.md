# VolatilityRotationMR Workspace

Primary documentation lives in `README_VolatilityRotationMR.md`.

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
- `user_data/configs/volatility_rotation_mr_analysis_market.json`

Compatibility alias only:
- `user_data/configs/volatility_rotation_mr_futures.json`

Strategy files:
- `user_data/strategies/VolatilityRotationMR.py`
