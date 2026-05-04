# Strict Validation Gate Spec

This repository does not promote a research strategy to dry-run or live operation from a single
profitable burst. Promotion requires `scripts/run_strict_validation.py` to produce a passing
`docs/validation/strict_validation_gate.md` report.

## Default Candidates

- `VolatilityRotationMRFlushReboundLongOnly`
- `VolatilityRotationMRDelayedConfirmLongOnly`

Both are research-only mean-reversion candidates. The parked production strategy remains
`VolatilityRotationMR` unless a candidate passes this gate and is explicitly promoted in a later PR.

## Gate

A candidate must pass all checks after exported fees plus `7 bps` per-side fee stress and `5 bps`
per-side slippage stress:

- at least `150` total trades
- at least `20` trades in `4` or more non-overlapping 6-month windows
- net positive in at least `4` of the latest `6` windows
- max drawdown `<= 12%`
- stressed profit factor `>= 1.20`
- positive average stressed trade
- max month profit share `<= 35%`
- max pair profit share `<= 20%`
- lookahead and recursive analysis are clean, or explicitly inconclusive because of insufficient signals

## Reproduction

Run from a Freqtrade-capable Python environment:

```bash
python scripts/run_strict_validation.py --download-data
```

For a faster syntax/config-only pass:

```bash
python scripts/run_strict_validation.py --skip-freqtrade-checks --skip-backtests --skip-bias
```

GitHub Actions also provides a Dockerized Freqtrade runner:

- pull requests run a smoke gate plus strategy/config discovery
- manual `workflow_dispatch` with `mode=full` downloads Binance futures data and runs the full
  strict gate
- workflow artifacts contain generated reports, logs, and raw backtest exports

The full workflow is intentionally manual because it downloads a large historical dataset and may
take hours on GitHub-hosted runners.

The full run writes:

- `docs/validation/strict_validation_gate.md`
- `docs/validation/strict_validation_gate.csv`
- logs under `docs/validation/logs/strict_validation/`
- raw backtest zips under `user_data/backtest_results/strict_validation/`
