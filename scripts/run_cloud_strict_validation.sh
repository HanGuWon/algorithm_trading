#!/usr/bin/env bash
set -euo pipefail

IMAGE="${FREQTRADE_IMAGE:-freqtradeorg/freqtrade:2026.2}"
MODE="${1:-full}"

if [[ "${MODE}" != "full" && "${MODE}" != "smoke" ]]; then
  echo "Usage: $0 [full|smoke]" >&2
  exit 64
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required on the validation host" >&2
  exit 69
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

mkdir -p docs/validation/logs/strict_validation user_data/backtest_results/strict_validation user_data/data
chmod -R a+rwX docs user_data scripts

docker pull "${IMAGE}"

COMMON_ARGS=(
  --rm
  -e PYTHONPYCACHEPREFIX=/tmp/pycache
  --entrypoint python
  -v "${ROOT_DIR}:/workspace"
  -w /workspace
  "${IMAGE}"
  scripts/run_strict_validation.py
)

if [[ "${MODE}" == "smoke" ]]; then
  docker run "${COMMON_ARGS[@]}" \
    --skip-freqtrade-checks \
    --skip-backtests \
    --skip-bias \
    --output-md docs/validation/strict_validation_smoke.md \
    --output-csv docs/validation/strict_validation_smoke.csv
else
  docker run "${COMMON_ARGS[@]}" \
    --download-data \
    --build-missing-snapshots \
    --output-md docs/validation/strict_validation_gate.md \
    --output-csv docs/validation/strict_validation_gate.csv
fi
