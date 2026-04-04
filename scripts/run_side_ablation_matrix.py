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
    StrategyVariant(label="baseline_long_short", strategy="VolatilityRotationMR"),
    StrategyVariant(label="diagnostic_long_short", strategy="VolatilityRotationMRDiagnostic"),
    StrategyVariant(label="baseline_long_only", strategy="VolatilityRotationMRLongOnly"),
    StrategyVariant(label="diagnostic_long_only", strategy="VolatilityRotationMRDiagnosticLongOnly"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run long-vs-short research-only ablation on PTI windows.")
    parser.add_argument("--anchors", nargs="+", required=True)
    parser.add_argument("--window-months", type=int, default=6)
    parser.add_argument("--snapshot-dir", default="user_data/pairs")
    parser.add_argument("--snapshot-top-n", type=int, default=50)
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--base-config", default="user_data/configs/volatility_rotation_mr_base.json")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--logs-dir", default="docs/validation/logs/side_ablation")
    parser.add_argument("--backtest-dir", default="user_data/backtest_results/side_ablation")
    return parser.parse_args()


def snapshot_path(snapshot_dir: Path, anchor: str, top_n: int) -> Path:
    if top_n == 20:
        return snapshot_dir / f"binance_usdt_futures_snapshot_{anchor}.json"
    return snapshot_dir / f"binance_usdt_futures_snapshot_{anchor}_top{top_n}.json"


def write_temp_config(temp_dir: Path, base_config: Path, snapshot: Path, variant: StrategyVariant) -> Path:
    payload = {
        "$schema": "https://schema.freqtrade.io/schema.json",
        "add_config_files": [str(base_config.resolve()), str(snapshot.resolve())],
        "strategy": variant.strategy,
        "dry_run": True,
        "db_url": "sqlite:///user_data/tradesv3_volatility_rotation_mr_side_ablation.sqlite",
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
        trades["month"] = trades["open_date"].dt.strftime("%Y-%m")
        trades["side"] = trades["is_short"].map({True: "short", False: "long"})
    return strategy_data, trades


def pair_contribution(trades: pd.DataFrame) -> str:
    if trades.empty:
        return ""
    grouped = trades.groupby("pair").size().sort_values(ascending=False).head(8)
    return ", ".join(f"{pair}:{count}" for pair, count in grouped.items())


def monthly_distribution(trades: pd.DataFrame) -> str:
    if trades.empty:
        return ""
    grouped = trades.groupby(["month", "side"]).size().sort_index()
    return ", ".join(f"{month}:{side}:{count}" for (month, side), count in grouped.items())


def main() -> None:
    args = parse_args()
    python_executable = Path(sys.executable)
    snapshot_dir = Path(args.snapshot_dir)
    strategy_path = Path(args.strategy_path)
    base_config = Path(args.base_config)
    rows: list[dict[str, object]] = []
    combined_trades: dict[str, list[pd.DataFrame]] = {variant.label: [] for variant in VARIANTS}

    with tempfile.TemporaryDirectory(prefix="side_ablation_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        for anchor_text in args.anchors:
            anchor = pd.Timestamp(anchor_text, tz="UTC")
            end = anchor + pd.DateOffset(months=args.window_months)
            timerange = f"{anchor.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"
            snapshot = snapshot_path(snapshot_dir, anchor_text, args.snapshot_top_n)
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
                combined_trades[variant.label].append(trades)
                rows.append(
                    {
                        "anchor": anchor_text,
                        "strategy_variant": variant.label,
                        "trades": int(strategy_data.get("total_trades", 0)),
                        "profit_pct": round(float(strategy_data.get("profit_total", 0.0)) * 100.0, 2),
                        "profit_usdt": round(float(strategy_data.get("profit_total_abs", 0.0)), 3),
                        "drawdown_pct": round(float(strategy_data.get("max_drawdown_account", 0.0)) * 100.0, 2),
                        "long_trades": int(strategy_data.get("trade_count_long", 0)),
                        "short_trades": int(strategy_data.get("trade_count_short", 0)),
                        "monthly_distribution": monthly_distribution(trades),
                        "pair_contribution": pair_contribution(trades),
                        "results_zip": zip_path.name,
                    }
                )

    frame = pd.DataFrame(rows).sort_values(["anchor", "strategy_variant"]).reset_index(drop=True)
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_csv, index=False)

    summary_rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        trades = pd.concat(combined_trades[variant.label], ignore_index=True) if combined_trades[variant.label] else pd.DataFrame()
        summary_rows.append(
            {
                "strategy_variant": variant.label,
                "trades": int(frame.loc[frame["strategy_variant"] == variant.label, "trades"].sum()),
                "profit_usdt": round(float(frame.loc[frame["strategy_variant"] == variant.label, "profit_usdt"].sum()), 3),
                "drawdown_pct_max": round(float(frame.loc[frame["strategy_variant"] == variant.label, "drawdown_pct"].max()), 2),
                "long_trades": int(frame.loc[frame["strategy_variant"] == variant.label, "long_trades"].sum()),
                "short_trades": int(frame.loc[frame["strategy_variant"] == variant.label, "short_trades"].sum()),
                "monthly_distribution": monthly_distribution(trades),
                "pair_contribution": pair_contribution(trades),
            }
        )
    summary = pd.DataFrame(summary_rows)

    lines = [
        "# Side Ablation Matrix",
        "",
        f"- Anchors: `{', '.join(args.anchors)}`",
        f"- Window design: non-overlapping `{args.window_months}m` windows",
        f"- Snapshot top_n: `{args.snapshot_top_n}`",
        "",
        "## Window Results",
        "",
        frame.to_markdown(index=False),
        "",
        "## Variant Totals",
        "",
        summary.to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        "Compare long+short against long-only to quantify whether the short side adds usable sample density or mostly noise.",
        "",
    ]
    Path(args.output_md).write_text("\n".join(lines), encoding="utf-8")
    print(frame.to_string(index=False))
    print("")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
