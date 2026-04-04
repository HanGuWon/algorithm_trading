from __future__ import annotations

import argparse
import json
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
    parser = argparse.ArgumentParser(description="Run a de-overlapped PTI alpha validation matrix.")
    parser.add_argument("--anchors", nargs="+", required=True, help="Non-overlapping window anchors in YYYY-MM-DD format.")
    parser.add_argument("--window-months", type=int, default=6)
    parser.add_argument("--snapshot-dir", default="user_data/pairs")
    parser.add_argument("--snapshot-top-n", type=int, default=50)
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--base-config", default="user_data/configs/volatility_rotation_mr_base.json")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--logs-dir", default="docs/validation/logs/matrix_deduped")
    parser.add_argument("--backtest-dir", default="user_data/backtest_results/matrix_deduped")
    parser.add_argument("--usable-trade-threshold", type=int, default=20)
    return parser.parse_args()


def snapshot_path(snapshot_dir: Path, anchor: str, top_n: int) -> Path:
    if top_n == 20:
        return snapshot_dir / f"binance_usdt_futures_snapshot_{anchor}.json"
    return snapshot_dir / f"binance_usdt_futures_snapshot_{anchor}_top{top_n}.json"


def make_timerange(anchor: pd.Timestamp, months: int) -> tuple[str, pd.Timestamp, pd.Timestamp]:
    end = anchor + pd.DateOffset(months=months)
    return f"{anchor.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}", anchor, end


def write_temp_config(temp_dir: Path, base_config: Path, snapshot: Path, variant: StrategyVariant) -> Path:
    payload = {
        "$schema": "https://schema.freqtrade.io/schema.json",
        "add_config_files": [str(base_config.resolve()), str(snapshot.resolve())],
        "strategy": variant.strategy,
        "dry_run": True,
        "db_url": "sqlite:///user_data/tradesv3_volatility_rotation_mr_matrix_deduped.sqlite",
        "exchange": {"key": "", "secret": "", "password": ""},
        "pairlists": [{"method": "StaticPairList"}],
    }
    path = temp_dir / f"{snapshot.stem}_{variant.label}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def run_backtest(
    python_executable: Path,
    config_path: Path,
    strategy_path: Path,
    timerange: str,
    logs_dir: Path,
    backtest_dir: Path,
    anchor_label: str,
    variant: StrategyVariant,
) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    backtest_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{anchor_label}_{variant.label}.log"
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
        "--export",
        "signals",
        "--backtest-directory",
        str(backtest_dir),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    log_path.write_text((completed.stdout or "") + ("\n" if completed.stdout else "") + (completed.stderr or ""), encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"Backtest failed for {anchor_label} {variant.label}. See {log_path}")
    last_result = json.loads((backtest_dir / ".last_result.json").read_text(encoding="utf-8"))
    return backtest_dir / last_result["latest_backtest"]


def parse_backtest_zip(zip_path: Path, strategy_name: str) -> tuple[dict[str, object], pd.DataFrame]:
    with zipfile.ZipFile(zip_path) as archive:
        json_name = next(name for name in archive.namelist() if name.endswith(".json") and not name.endswith("_config.json"))
        payload = json.loads(archive.read(json_name).decode("utf-8"))
    strategy_data = payload["strategy"][strategy_name]
    trades = pd.DataFrame(strategy_data.get("trades", []))
    if not trades.empty:
        trades["open_date"] = pd.to_datetime(trades["open_date"], utc=True)
        trades["close_date"] = pd.to_datetime(trades["close_date"], utc=True)
        trades["trade_signature"] = (
            trades["pair"].astype(str)
            + "|"
            + trades["open_date"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            + "|"
            + trades["is_short"].astype(str)
        )
        trades["month"] = trades["open_date"].dt.strftime("%Y-%m")
    return strategy_data, trades


def monthly_distribution(trades: pd.DataFrame) -> str:
    if trades.empty:
        return ""
    grouped = trades.groupby("month").size().sort_index()
    return ", ".join(f"{month}:{count}" for month, count in grouped.items())


def pair_contribution(trades: pd.DataFrame, top_n: int = 8) -> str:
    if trades.empty:
        return ""
    grouped = trades.groupby("pair").size().sort_values(ascending=False).head(top_n)
    return ", ".join(f"{pair}:{count}" for pair, count in grouped.items())


def main() -> None:
    args = parse_args()
    python_executable = Path(sys.executable)
    snapshot_dir = Path(args.snapshot_dir)
    strategy_path = Path(args.strategy_path)
    base_config = Path(args.base_config)
    rows: list[dict[str, object]] = []
    trades_by_variant: dict[str, list[pd.DataFrame]] = {variant.label: [] for variant in VARIANTS}

    with tempfile.TemporaryDirectory(prefix="pti_matrix_deduped_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        for anchor_text in args.anchors:
            anchor = pd.Timestamp(anchor_text, tz="UTC")
            snapshot = snapshot_path(snapshot_dir, anchor_text, args.snapshot_top_n)
            if not snapshot.exists():
                raise FileNotFoundError(f"Missing snapshot: {snapshot}")
            pair_count = len(json.loads(snapshot.read_text(encoding="utf-8"))["exchange"]["pair_whitelist"])
            timerange, start, end = make_timerange(anchor, args.window_months)

            for variant in VARIANTS:
                config_path = write_temp_config(temp_dir, base_config, snapshot, variant)
                zip_path = run_backtest(
                    python_executable=python_executable,
                    config_path=config_path,
                    strategy_path=strategy_path,
                    timerange=timerange,
                    logs_dir=Path(args.logs_dir),
                    backtest_dir=Path(args.backtest_dir),
                    anchor_label=anchor_text,
                    variant=variant,
                )
                strategy_data, trades = parse_backtest_zip(zip_path, variant.strategy)
                trades_by_variant[variant.label].append(trades)
                rows.append(
                    {
                        "anchor": anchor_text,
                        "window_label": f"{args.window_months}m",
                        "strategy_variant": variant.label,
                        "strategy": variant.strategy,
                        "snapshot": snapshot.name,
                        "pair_count": pair_count,
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
                        "monthly_distribution": monthly_distribution(trades),
                        "pair_contribution": pair_contribution(trades),
                        "results_zip": zip_path.name,
                    }
                )

    frame = pd.DataFrame(rows).sort_values(["anchor", "strategy_variant"]).reset_index(drop=True)
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_csv, index=False)

    totals_rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        trades = pd.concat(trades_by_variant[variant.label], ignore_index=True) if trades_by_variant[variant.label] else pd.DataFrame()
        raw_trades = int(frame.loc[frame["strategy_variant"] == variant.label, "trades"].sum())
        unique_trades = int(trades["trade_signature"].nunique()) if not trades.empty else 0
        totals_rows.append(
            {
                "strategy_variant": variant.label,
                "raw_trades": raw_trades,
                "unique_trades": unique_trades,
                "profit_usdt": round(float(frame.loc[frame["strategy_variant"] == variant.label, "profit_usdt"].sum()), 3),
                "long_trades": int(frame.loc[frame["strategy_variant"] == variant.label, "long_trades"].sum()),
                "short_trades": int(frame.loc[frame["strategy_variant"] == variant.label, "short_trades"].sum()),
            }
        )
    totals = pd.DataFrame(totals_rows)

    lines = [
        "# Deduped PTI Alpha Validation Matrix",
        "",
        f"- Anchors: `{', '.join(args.anchors)}`",
        f"- Window design: non-overlapping forward `{args.window_months}m` windows",
        f"- Snapshot top_n: `{args.snapshot_top_n}`",
        f"- Usable-sample threshold: `{args.usable_trade_threshold}` trades per window",
        "",
        "## Matrix",
        "",
        frame[
            [
                "anchor",
                "window_label",
                "strategy_variant",
                "pair_count",
                "trades",
                "profit_pct",
                "profit_usdt",
                "drawdown_pct",
                "long_trades",
                "short_trades",
                "usable_sample",
                "monthly_distribution",
                "pair_contribution",
            ]
        ].to_markdown(index=False),
        "",
        "## Raw vs Unique Totals",
        "",
        totals.to_markdown(index=False),
        "",
        "## Notes",
        "",
        "This matrix uses non-overlapping windows, so raw and unique trade totals should match unless a trade signature is duplicated unexpectedly.",
        "Use this artifact as the primary de-overlapped alpha-validation path instead of the older overlapping 3m/6m matrix.",
        "",
    ]
    Path(args.output_md).write_text("\n".join(lines), encoding="utf-8")
    print(frame.to_string(index=False))
    print("")
    print(totals.to_string(index=False))


if __name__ == "__main__":
    main()
