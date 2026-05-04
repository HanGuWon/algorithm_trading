from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path


ALLOW_TOKEN = "STRICT_GATE_PROMOTED_AND_DRYRUN_STABLE"
PARKED_STRATEGIES = {"VolatilityRotationMR"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Block live Freqtrade startup until the deployment gate is satisfied.")
    parser.add_argument("--strategy", default=os.environ.get("FREQTRADE_STRATEGY", ""))
    parser.add_argument("--report", default=os.environ.get("STRICT_VALIDATION_REPORT", "docs/validation/strict_validation_gate.md"))
    parser.add_argument("--allow-token", default=os.environ.get("ALLOW_LIVE_TRADING", ""))
    parser.add_argument("--dryrun-started-at", default=os.environ.get("DRYRUN_STARTED_AT", ""))
    parser.add_argument("--min-dryrun-days", type=int, default=int(os.environ.get("LIVE_DRYRUN_MIN_DAYS", "14")))
    parser.add_argument("--today", default="", help="Test hook in YYYY-MM-DD format. Defaults to current UTC date.")
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"LIVE READINESS: blocked - {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_day(value: str, field_name: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format") from exc


def report_promotes_strategy(report_text: str, strategy: str) -> bool:
    final_status = re.search(r"Final status:\s*`([^`]+)`", report_text)
    if not final_status or final_status.group(1).strip() != "PROMOTE":
        return False
    return strategy in report_text


def main() -> None:
    args = parse_args()
    strategy = args.strategy.strip()
    if not strategy:
        fail("FREQTRADE_STRATEGY is required")
    if strategy in PARKED_STRATEGIES:
        fail(f"{strategy} is parked and cannot be used for live trading")
    if args.allow_token != ALLOW_TOKEN:
        fail(f"ALLOW_LIVE_TRADING must equal {ALLOW_TOKEN}")

    report_path = Path(args.report)
    if not report_path.exists():
        fail(f"strict validation report not found: {report_path}")
    report_text = report_path.read_text(encoding="utf-8")
    if not report_promotes_strategy(report_text, strategy):
        fail(f"{report_path} must contain Final status `PROMOTE` and the strategy name {strategy}")

    if not args.dryrun_started_at:
        fail("DRYRUN_STARTED_AT is required before live startup")
    try:
        dryrun_start = parse_day(args.dryrun_started_at, "DRYRUN_STARTED_AT")
        today = parse_day(args.today, "--today") if args.today else datetime.now(timezone.utc).date()
    except ValueError as exc:
        fail(str(exc))
    dryrun_days = (today - dryrun_start).days
    if dryrun_days < args.min_dryrun_days:
        fail(f"dry-run age is {dryrun_days} days, below required {args.min_dryrun_days} days")

    print(f"LIVE READINESS: pass - {strategy} passed strict validation and dry-run age is {dryrun_days} days")


if __name__ == "__main__":
    main()
