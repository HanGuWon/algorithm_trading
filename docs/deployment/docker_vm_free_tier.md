# Docker VM Free-Tier Deployment

This deployment path is intentionally dry-run first. The live Docker service is behind an explicit
Compose profile and should stay unused until a strategy passes the strict validation gate and a
14-day dry-run soak.

## Host Assumptions

- Small Linux VM, such as an Oracle/AWS/GCP free-tier instance.
- Docker Engine and Docker Compose plugin installed.
- NTP/time sync enabled on the host.
- Repository contents copied to the VM.

## First Boot

```bash
cp .env.example .env
docker compose pull
docker compose up -d freqtrade-dryrun
docker compose logs -f freqtrade-dryrun
```

Dry-run uses:

- `user_data/configs/volatility_rotation_mr_binance_dryrun.json`
- `FREQTRADE_STRATEGY=VolatilityRotationMR`
- the persisted local `./user_data` directory mounted into `/freqtrade/user_data`

## API Keys

Set keys only on the host in `.env` or in the ignored private config overlay. Never commit them.

```bash
FREQTRADE__EXCHANGE__KEY=replace_on_host
FREQTRADE__EXCHANGE__SECRET=replace_on_host
```

For live keys, keep withdrawals disabled and use Binance USDT-M futures permissions for read plus
place/cancel orders. IP allowlisting is strongly recommended.

## Preflight

Before dry-run or live operation from a Windows workstation:

```powershell
.\scripts\preflight_binance.ps1 -Mode dryrun
```

On Linux hosts, use the Docker logs plus Freqtrade config checks:

```bash
docker compose run --rm freqtrade-dryrun list-strategies \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json

docker compose run --rm freqtrade-dryrun show-config \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json

docker compose run --rm freqtrade-dryrun test-pairlist \
  --config user_data/configs/volatility_rotation_mr_binance_dryrun.json \
  --quote USDT --print-json
```

## Live Guardrail

Live is not part of the default `docker compose up`. It requires both the explicit profile and a
promoted strategy:

```bash
docker compose --profile live up -d freqtrade-live
```

Do not run this until:

- `docs/validation/strict_validation_gate.md` reports `PROMOTE`.
- Dry-run has been stable for 14 days.
- Binance account mode is One-way and Single-Asset.
- Existing exchange-side stop orders have been checked after restart.

Rollback is:

```bash
docker compose --profile live stop freqtrade-live
docker compose up -d freqtrade-dryrun
```

## Resource Notes

The default deployment runs one Freqtrade process and stores SQLite/data files under `./user_data`.
For a free-tier VM, keep the API server disabled, avoid hyperopt on the VM, and run large research
matrices on a larger machine or in short, supervised batches.
