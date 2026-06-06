from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEFAULT_PAIRS = [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "BNB/USDT:USDT",
    "SOL/USDT:USDT",
    "XRP/USDT:USDT",
    "ADA/USDT:USDT",
    "DOGE/USDT:USDT",
    "TRX/USDT:USDT",
    "LINK/USDT:USDT",
    "AVAX/USDT:USDT",
    "LTC/USDT:USDT",
]

DEFAULT_STRATEGIES = [
    "VolatilityRotationMRFlushReboundLongOnly",
    "VolatilityRotationMRDelayedConfirmLongOnly",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill Binance major futures data and run Freqtrade backtests.")
    parser.add_argument("--pairs", nargs="+", default=DEFAULT_PAIRS)
    parser.add_argument("--strategies", nargs="+", default=DEFAULT_STRATEGIES)
    parser.add_argument("--start", default="2016-06-04")
    parser.add_argument(
        "--end",
        default="",
        help="Exclusive UTC date YYYY-MM-DD. Defaults to tomorrow UTC so the latest complete day is included when present.",
    )
    parser.add_argument("--timeframes", nargs="+", default=["5m", "1h"])
    parser.add_argument("--skip-backfill", action="store_true")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--pairlist", default="user_data/pairs/binance_usdt_futures_major_11.json")
    parser.add_argument("--config", default="user_data/configs/volatility_rotation_mr_backtest_major_11.json")
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--backtest-dir", default="user_data/backtest_results/major_11")
    parser.add_argument("--logs-dir", default="docs/validation/logs/major_11_backtest")
    parser.add_argument("--summary-csv", default="docs/validation/analysis/major_11_backtest_summary.csv")
    parser.add_argument("--summary-md", default="docs/validation/analysis/major_11_backtest_summary.md")
    parser.add_argument("--diagnostics-csv", default="docs/validation/analysis/major_11_concentration_diagnostics.csv")
    parser.add_argument("--diagnostics-md", default="docs/validation/analysis/major_11_concentration_diagnostics.md")
    parser.add_argument("--skip-diagnostics", action="store_true")
    return parser.parse_args()


def default_end_date() -> str:
    return (pd.Timestamp(datetime.now(timezone.utc)).normalize() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")


def freqtrade_timerange(start: str, end: str) -> str:
    return start.replace("-", "") + "-" + end.replace("-", "")


def subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    startup_path = str((Path(__file__).resolve().parent / "python_startup").resolve())
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = startup_path if not existing else startup_path + os.pathsep + existing
    return env


def run_command(command: list[str], log_path: Path) -> subprocess.CompletedProcess[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, capture_output=True, text=True, check=False, env=subprocess_env())
    log_path.write_text((completed.stdout or "") + ("\n" if completed.stdout and completed.stderr else "") + (completed.stderr or ""), encoding="utf-8")
    return completed


def write_pairlist(path: Path, pairs: list[str]) -> None:
    payload = {
        "$schema": "https://schema.freqtrade.io/schema.json",
        "exchange": {"pair_whitelist": pairs},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def write_config(path: Path, pairlist: Path) -> None:
    try:
        pairlist_ref = Path(os.path.relpath(pairlist.resolve(), start=path.parent.resolve())).as_posix()
    except ValueError:
        pairlist_ref = str(pairlist.resolve())
    payload = {
        "$schema": "https://schema.freqtrade.io/schema.json",
        "add_config_files": [
            "volatility_rotation_mr_base.json",
            pairlist_ref,
        ],
        "dry_run": True,
        "db_url": "sqlite:///user_data/tradesv3_volatility_rotation_mr_backtest_major_11.sqlite",
        "exchange": {
            "key": "",
            "secret": "",
            "password": "",
            "ccxt_config": {
                "options": {
                    "defaultType": "swap",
                    "fetchMarkets": {"types": ["linear"]},
                }
            },
            "ccxt_async_config": {
                "options": {
                    "defaultType": "swap",
                    "fetchMarkets": {"types": ["linear"]},
                }
            },
        },
        "pairlists": [{"method": "StaticPairList"}],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def latest_backtest_zip(backtest_dir: Path) -> str:
    last_result = backtest_dir / ".last_result.json"
    if not last_result.exists():
        return ""
    payload = json.loads(last_result.read_text(encoding="utf-8"))
    return str(payload.get("latest_backtest", ""))


def summarize_zip(zip_path: Path, strategy: str) -> dict[str, object]:
    if not zip_path.exists():
        return {}
    import zipfile

    with zipfile.ZipFile(zip_path) as archive:
        json_name = next(name for name in archive.namelist() if name.endswith(".json") and not name.endswith("_config.json"))
        payload = json.loads(archive.read(json_name).decode("utf-8"))
    strategy_data = payload.get("strategy", {}).get(strategy, {})
    profit_ratio = float(strategy_data.get("profit_total", 0.0) or 0.0)
    drawdown_ratio = float(
        strategy_data.get("max_drawdown_account", strategy_data.get("max_drawdown", 0.0)) or 0.0
    )
    return {
        "trades": strategy_data.get("total_trades", 0),
        "profit_abs": strategy_data.get("profit_total_abs", 0.0),
        "profit_pct": profit_ratio * 100.0,
        "max_drawdown_pct": drawdown_ratio * 100.0,
    }


def write_summary(
    rows: list[dict[str, object]],
    csv_path: Path,
    md_path: Path,
    pairs: list[str],
    start: str,
    end: str,
    diagnostics_md: str,
) -> None:
    frame = pd.DataFrame(rows)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False)
    lines = [
        "# Major 11 Binance Futures Backtest",
        "",
        f"- Requested UTC timerange: `{start}` to `{end}` exclusive",
        f"- Pairs: `{', '.join(pairs)}`",
        "",
        "## Results",
        "",
        frame.to_markdown(index=False) if not frame.empty else "No backtest rows were produced.",
        "",
        "## Notes",
        "",
        "The requested 10-year window is longer than Binance USDT-M futures history for these markets.",
        "The adapter writes each market from its earliest available Binance futures candle inside the requested range.",
        "",
        "## Follow-Up Diagnostics",
        "",
        f"- Concentration, calendar, pair, and baseline diagnostics: `{diagnostics_md}`",
        "",
    ]
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    end = args.end or default_end_date()
    pairlist = Path(args.pairlist)
    config = Path(args.config)
    write_pairlist(pairlist, args.pairs)
    write_config(config, pairlist)

    if not args.skip_backfill:
        backfill_command = [
            args.python,
            "scripts/binance_futures_to_freqtrade_feather.py",
            "--pairs-file",
            str(pairlist),
            "--start",
            args.start,
            "--end",
            end,
            "--datadir",
            args.datadir,
            "--timeframes",
            *args.timeframes,
        ]
        completed = run_command(backfill_command, Path(args.logs_dir) / "backfill.log")
        if completed.returncode != 0:
            raise SystemExit(f"Backfill failed. See {Path(args.logs_dir) / 'backfill.log'}")

    rows: list[dict[str, object]] = []
    timerange = freqtrade_timerange(args.start, end)
    for strategy in args.strategies:
        backtest_dir = Path(args.backtest_dir) / strategy
        backtest_dir.mkdir(parents=True, exist_ok=True)
        command = [
            args.python,
            "-m",
            "freqtrade",
            "backtesting",
            "--config",
            str(config),
            "--strategy",
            strategy,
            "--strategy-path",
            args.strategy_path,
            "--timeframe",
            "5m",
            "--timerange",
            timerange,
            "--enable-protections",
            "--export",
            "signals",
            "--backtest-directory",
            str(backtest_dir),
        ]
        log_path = Path(args.logs_dir) / f"{strategy}.log"
        completed = run_command(command, log_path)
        result_zip_name = latest_backtest_zip(backtest_dir) if completed.returncode == 0 else ""
        metrics = summarize_zip(backtest_dir / result_zip_name, strategy) if result_zip_name else {}
        rows.append(
            {
                "strategy": strategy,
                "status": "pass" if completed.returncode == 0 else "fail",
                "exit_code": completed.returncode,
                "timerange": timerange,
                "pairs": len(args.pairs),
                "results_zip": result_zip_name,
                "log": str(log_path),
                **metrics,
            }
        )

    write_summary(rows, Path(args.summary_csv), Path(args.summary_md), args.pairs, args.start, end, args.diagnostics_md)
    if not args.skip_diagnostics:
        diagnostics_command = [
            args.python,
            "scripts/run_major_11_diagnostics.py",
            "--summary-csv",
            args.summary_csv,
            "--backtest-root",
            args.backtest_dir,
            "--datadir",
            args.datadir,
            "--output-csv",
            args.diagnostics_csv,
            "--output-md",
            args.diagnostics_md,
        ]
        completed = run_command(diagnostics_command, Path(args.logs_dir) / "major_11_diagnostics.log")
        if completed.returncode != 0:
            raise SystemExit(f"Major-11 diagnostics failed. See {Path(args.logs_dir) / 'major_11_diagnostics.log'}")
    print(f"Summary written to {args.summary_md}")


if __name__ == "__main__":
    main()
