# Cloud Strict Validation Runbook

Use this runbook when GitHub-hosted runners cannot reach Binance public REST endpoints and the
workflow report ends with `INFRA_DATA_FAILED`.

## Requirements

- Linux VM in a Binance-supported region.
- Docker Engine with the Compose plugin.
- Outbound HTTPS access to Binance public market APIs.
- At least enough disk for `user_data/data` and `user_data/backtest_results/strict_validation`.
- No Binance API keys are required for validation.

## One-Time Host Setup

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker
```

Clone the repository and enter it:

```bash
git clone https://github.com/HanGuWon/algorithm_trading.git
cd algorithm_trading
```

## Connectivity Probe

```bash
docker run --rm freqtradeorg/freqtrade:2026.2 python - <<'PY'
import urllib.request
for url in [
    "https://fapi.binance.com/fapi/v1/exchangeInfo",
    "https://api.binance.com/api/v3/exchangeInfo",
]:
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            print(url, response.status)
    except Exception as exc:
        print(url, type(exc).__name__, exc)
PY
```

If either endpoint returns a Binance restricted-location error, move the validation run to another
host. Do not treat that as a strategy result.

## Smoke Then Full Gate

```bash
bash scripts/run_cloud_strict_validation.sh smoke
bash scripts/run_cloud_strict_validation.sh full
```

The full run is resumable. If the VM stops or the command times out, rerun the same full command.
Completed rows with existing result zips are reused through
`user_data/backtest_results/strict_validation/strict_validation_checkpoint.csv`.

## Required Outputs

Review these files after the full run:

- `docs/validation/strict_validation_gate.md`
- `docs/validation/strict_validation_gate.csv`
- `docs/validation/logs/strict_validation/`
- `user_data/backtest_results/strict_validation/`

Only `Final status: PROMOTE` allows a later promotion PR. `PARK`, `PARK_BIAS_FAILED`, and
`INFRA_DATA_FAILED` keep live trading blocked.

## Optional GitHub Self-Hosted Runner Path

If the VM is registered as a GitHub self-hosted runner, dispatch the `Strict validation` workflow
with:

- `mode=full`
- `full_runner=self-hosted`
- `anchors` empty
- `upload_artifacts=true`
