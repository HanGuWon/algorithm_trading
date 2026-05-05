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
python scripts/run_strict_validation.py --download-data --build-missing-snapshots
```

On a Docker-only Linux validation VM, use the wrapper instead:

```bash
bash scripts/run_cloud_strict_validation.sh smoke
bash scripts/run_cloud_strict_validation.sh full
```

By default, anchors are generated from `2022-01-01` in non-overlapping 6-month windows through the
latest complete UTC month. Missing point-in-time pair snapshots fail the gate unless
`--allow-missing-snapshots` is explicitly used.

The runner is resumable by default. After each completed anchor/candidate backtest it writes:

- `user_data/backtest_results/strict_validation/strict_validation_checkpoint.csv`
- the corresponding raw result zip under `user_data/backtest_results/strict_validation/`

If a full run stops partway through, rerun the same command and completed rows with an existing
result zip are reused. Use `--no-resume` only when strategy code, config, data, or gate inputs have
changed and the previous checkpoint should be ignored.

For a faster syntax/config-only pass:

```bash
python scripts/run_strict_validation.py --skip-freqtrade-checks --skip-backtests --skip-bias
```

GitHub Actions also provides a Dockerized Freqtrade runner:

- pull requests run a smoke gate plus strategy/config discovery
- manual `workflow_dispatch` with `mode=full` downloads Binance futures data, builds missing
  point-in-time snapshots, and runs the full strict gate
- workflow artifacts contain generated reports, logs, and raw backtest exports
- full workflow runs restore cached `user_data/data` and
  `user_data/backtest_results/strict_validation` when available, so reruns can reuse downloaded
  candles and the strict-validation checkpoint

The full workflow is intentionally manual because it downloads a large historical dataset and may
take hours.

## Runner Requirements

Full strict validation must run from a network that can reach Binance REST market endpoints.
GitHub-hosted runners may be allocated in regions where Binance returns HTTP `451` restricted
location. When that happens, the report status is `INFRA_DATA_FAILED`; this is not a strategy
performance result and must not be used to promote or park a candidate.

If GitHub-hosted runners are blocked, register a self-hosted Linux runner on a small cloud VM in a
Binance-supported region with Docker installed, then dispatch the workflow with:

- `mode=full`
- `full_runner=self-hosted`
- `anchors` empty for the default complete 6-month matrix, or a space-separated subset for a resume
- `upload_artifacts=true`

The self-hosted runner must have outbound access to Binance public REST APIs and enough disk for
`user_data/data` plus raw backtest exports. Keep Binance secrets out of GitHub; full validation uses
public market data only.

For a standalone cloud VM path without registering a GitHub runner, follow
`docs/validation/cloud_strict_validation_runbook.md`.

The full run writes:

- `docs/validation/strict_validation_gate.md`
- `docs/validation/strict_validation_gate.csv`
- logs under `docs/validation/logs/strict_validation/`
- raw backtest zips under `user_data/backtest_results/strict_validation/`
- resume checkpoint `user_data/backtest_results/strict_validation/strict_validation_checkpoint.csv`
