#!/usr/bin/env bash
set -euo pipefail

SERVICE="${1:-freqtrade-dryrun}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required on the dry-run host" >&2
  exit 69
fi

if ! docker compose config >/tmp/freqtrade-compose-config.txt; then
  cat /tmp/freqtrade-compose-config.txt
  exit 1
fi

docker compose run --rm "${SERVICE}" list-strategies \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json

docker compose run --rm "${SERVICE}" show-config \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json >/tmp/freqtrade-show-config.txt

docker compose run --rm "${SERVICE}" test-pairlist \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json \
  --quote USDT \
  --print-json >/tmp/freqtrade-test-pairlist.json

echo "Dry-run container checks passed for ${SERVICE}."
