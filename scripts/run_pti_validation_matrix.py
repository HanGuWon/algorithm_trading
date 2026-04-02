from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class StrategyVariant:
    label: str
    strategy: str


VARIANTS = [
    StrategyVariant(label="baseline", strategy="VolatilityRotationMR"),
    StrategyVariant(label="diagnostic", strategy="VolatilityRotationMRDiagnostic"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a PTI walk-forward alpha validation matrix.")
    parser.add_argument("--anchors", nargs="+", required=True, help="Anchor dates in YYYY-MM-DD format.")
    parser.add_argument("--windows", nargs="+", type=int, default=[3, 6], help="Forward windows in months.")
    parser.add_argument("--snapshot-dir", default="user_data/pairs")
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--base-config", default="user_data/configs/volatility_rotation_mr_base.json")
    parser.add_argument("--timerange-prefix-days", type=int, default=0)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--logs-dir", default="docs/validation/logs/matrix")
    parser.add_argument("--backtest-dir", default="user_data/backtest_results/matrix")
    parser.add_argument("--usable-trade-threshold", type=int, default=20)
    return parser.parse_args()


def make_timerange(anchor: pd.Timestamp, months: int, prefix_days: int) -> tuple[str, pd.Timestamp, pd.Timestamp]:
    start = anchor - pd.Timedelta(days=prefix_days)
    end = anchor + pd.DateOffset(months=months)
    return f"{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}", anchor, end


def load_snapshot(snapshot_path: Path) -> list[str]:
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    return list(payload["exchange"]["pair_whitelist"])


def write_temp_config(temp_dir: Path, base_config: Path, snapshot_path: Path, variant: StrategyVariant) -> Path:
    payload = {
        "$schema": "https://schema.freqtrade.io/schema.json",
        "add_config_files": [str(base_config.resolve()), str(snapshot_path.resolve())],
        "strategy": variant.strategy,
        "dry_run": True,
        "db_url": "sqlite:///user_data/tradesv3_volatility_rotation_mr_matrix.sqlite",
        "exchange": {"key": "", "secret": "", "password": ""},
        "pairlists": [{"method": "StaticPairList"}],
    }
    config_path = temp_dir / f"{snapshot_path.stem}_{variant.label}.json"
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return config_path


def run_backtest(
    python_executable: Path,
    config_path: Path,
    strategy_path: Path,
    timerange: str,
    logs_dir: Path,
    backtest_dir: Path,
    variant: StrategyVariant,
    anchor_label: str,
    months: int,
) -> Path:
    log_path = logs_dir / f"{anchor_label}_{months}m_{variant.label}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    backtest_dir.mkdir(parents=True, exist_ok=True)

    command = [
        str(python_executable),
        "-m",
        "freqtrade",
        "backtesting",
        "--config",
        str(config_path),
        "--strategy",
        variant.strategy,
        "--strategy-path",
        str(strategy_path),
        "--timeframe",
        "5m",
        "--timerange",
        timerange,
        "--enable-protections",
        "--backtest-directory",
        str(backtest_dir),
    ]

    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    log_path.write_text((completed.stdout or "") + ("\n" if completed.stdout else "") + (completed.stderr or ""), encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"Backtest failed for {anchor_label} {months}m {variant.label}. See {log_path}")

    last_result = json.loads((backtest_dir / ".last_result.json").read_text(encoding="utf-8"))
    zip_name = last_result["latest_backtest"]
    return backtest_dir / zip_name


def parse_backtest_zip(zip_path: Path, strategy_name: str) -> dict[str, object]:
    with zipfile.ZipFile(zip_path) as archive:
        json_name = next(
            name
            for name in archive.namelist()
            if name.endswith(".json") and not name.endswith("_config.json")
        )
        payload = json.loads(archive.read(json_name).decode("utf-8"))

    strategy_data = payload["strategy"][strategy_name]
    return strategy_data


def monthly_trade_distribution(trades: list[dict[str, object]]) -> str:
    if not trades:
        return ""
    frame = pd.DataFrame(trades)
    frame["open_date"] = pd.to_datetime(frame["open_date"], utc=True)
    frame["month"] = frame["open_date"].dt.strftime("%Y-%m")
    grouped = frame.groupby("month").size().sort_index()
    return ", ".join(f"{month}:{count}" for month, count in grouped.items())


def main() -> None:
    args = parse_args()
    python_executable = Path(sys.executable)
    snapshot_dir = Path(args.snapshot_dir)
    strategy_path = Path(args.strategy_path)
    base_config = Path(args.base_config)
    logs_dir = Path(args.logs_dir)
    backtest_dir = Path(args.backtest_dir)

    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="pti_matrix_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        for anchor_text in args.anchors:
            anchor = pd.Timestamp(anchor_text, tz="UTC")
            snapshot_path = snapshot_dir / f"binance_usdt_futures_snapshot_{anchor_text}.json"
            if not snapshot_path.exists():
                raise FileNotFoundError(f"Missing snapshot {snapshot_path}")
            pairs = load_snapshot(snapshot_path)

            for months in args.windows:
                timerange, start, end = make_timerange(anchor, months, args.timerange_prefix_days)

                for variant in VARIANTS:
                    config_path = write_temp_config(temp_dir, base_config, snapshot_path, variant)
                    zip_path = run_backtest(
                        python_executable=python_executable,
                        config_path=config_path,
                        strategy_path=strategy_path,
                        timerange=timerange,
                        logs_dir=logs_dir,
                        backtest_dir=backtest_dir,
                        variant=variant,
                        anchor_label=anchor_text,
                        months=months,
                    )
                    strategy_data = parse_backtest_zip(zip_path, variant.strategy)
                    trades = strategy_data.get("trades", [])

                    rows.append(
                        {
                            "anchor": anchor_text,
                            "window_months": months,
                            "window_label": f"{months}m",
                            "strategy_variant": variant.label,
                            "strategy": variant.strategy,
                            "snapshot": snapshot_path.name,
                            "pair_count": len(pairs),
                            "timerange": timerange,
                            "analysis_start": start.strftime("%Y-%m-%d"),
                            "analysis_end": end.strftime("%Y-%m-%d"),
                            "trades": int(strategy_data.get("total_trades", 0)),
                            "profit_pct": round(float(strategy_data.get("profit_total", 0.0)) * 100.0, 2),
                            "profit_usdt": round(float(strategy_data.get("profit_total_abs", 0.0)), 3),
                            "drawdown_pct": round(float(strategy_data.get("max_drawdown_account", 0.0)) * 100.0, 2),
                            "long_trades": int(strategy_data.get("trade_count_long", 0)),
                            "short_trades": int(strategy_data.get("trade_count_short", 0)),
                            "usable_sample": "yes" if int(strategy_data.get("total_trades", 0)) >= args.usable_trade_threshold else "no",
                            "monthly_distribution": monthly_trade_distribution(trades),
                            "results_zip": zip_path.name,
                        }
                    )

    frame = pd.DataFrame(rows).sort_values(["anchor", "window_months", "strategy_variant"]).reset_index(drop=True)
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_csv, index=False)

    summary = (
        frame.groupby("strategy_variant", as_index=False)[["trades", "profit_usdt"]]
        .agg({"trades": "sum", "profit_usdt": "sum"})
        .sort_values("strategy_variant")
        .reset_index(drop=True)
    )
    usable = frame[frame["usable_sample"] == "yes"]

    lines = [
        "# PTI Alpha Validation Matrix",
        "",
        f"- Anchors: `{', '.join(args.anchors)}`",
        f"- Windows: `{', '.join(f'{window}m' for window in args.windows)}`",
        f"- Trade-count threshold for usable sample: `{args.usable_trade_threshold}` trades",
        "",
        "## Matrix",
        "",
        frame[
            [
                "anchor",
                "window_label",
                "strategy_variant",
                "trades",
                "profit_pct",
                "profit_usdt",
                "drawdown_pct",
                "long_trades",
                "short_trades",
                "usable_sample",
                "monthly_distribution",
            ]
        ].to_markdown(index=False),
        "",
        "## Variant Totals",
        "",
        summary.to_markdown(index=False),
        "",
        "## Decision Notes",
        "",
    ]

    if usable.empty:
        lines.append("No tested anchor/window/variant combination reached the usable-sample threshold.")
    else:
        lines.append(usable.to_markdown(index=False))

    Path(args.output_md).write_text("\n".join(lines), encoding="utf-8")
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
