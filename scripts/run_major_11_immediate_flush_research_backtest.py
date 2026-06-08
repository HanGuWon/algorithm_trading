from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from longonly_research_utils import parse_backtest_zip


EXIT_LABELS = {
    "Hold24h": "hold_24h",
    "Hold72h": "hold_72h",
    "Hold120h": "hold_120h",
    "ZscoreRevert72h": "zscore_revert_or_72h",
    "RsiRevert72h": "rsi_revert_or_72h",
    "BbMidReclaim72h": "bb_mid_reclaim_or_72h",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run research-only Freqtrade portfolio backtests for canonical immediate-flush candidates."
    )
    parser.add_argument(
        "--manifest",
        default="docs/validation/analysis/major_11_immediate_flush_canonical_manifest.csv",
    )
    parser.add_argument("--config", default="user_data/configs/volatility_rotation_mr_backtest_major_11.json")
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--timerange", default="20200109-20260603")
    parser.add_argument(
        "--output-csv",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_summary.csv",
    )
    parser.add_argument(
        "--output-md",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_summary.md",
    )
    parser.add_argument(
        "--trades-csv",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_trades.csv",
    )
    parser.add_argument("--logs-dir", default="docs/validation/logs/major_11_immediate_flush_backtest")
    parser.add_argument("--backtest-dir", default="user_data/backtest_results/major_11_immediate_flush")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--exit-labels", nargs="+", default=list(EXIT_LABELS))
    parser.add_argument("--candidate-ids", nargs="+", default=[])
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--max-runs", type=int, default=0, help="Optional smoke-test limit after matrix creation.")
    parser.add_argument("--validation-start", default="2024-01-01")
    parser.add_argument("--default-fee-per-side", type=float, default=0.0004)
    parser.add_argument("--round-trip-cost-bps", type=float, default=20.0)
    parser.add_argument("--adverse-funding-bps", type=float, default=10.0)
    parser.add_argument("--min-trades", type=int, default=200)
    parser.add_argument("--min-validation-trades", type=int, default=50)
    parser.add_argument("--min-active-pairs", type=int, default=8)
    parser.add_argument("--min-active-years", type=int, default=5)
    parser.add_argument("--max-top-pair-profit-share", type=float, default=0.35)
    parser.add_argument("--max-top-year-profit-share", type=float, default=0.40)
    parser.add_argument("--max-drawdown-pct", type=float, default=15.0)
    return parser.parse_args()


def strategy_class_name(candidate_id: str, exit_label: str) -> str:
    source_id = candidate_id.split("_", maxsplit=1)[0]
    return f"ImmediateFlushResearch{source_id}{exit_label}"


def load_manifest(path: Path, candidate_ids: list[str]) -> pd.DataFrame:
    manifest = pd.read_csv(path)
    if candidate_ids:
        manifest = manifest[manifest["canonical_fixed_candidate_id"].astype(str).isin(candidate_ids)].copy()
    if manifest.empty:
        raise SystemExit("No canonical candidates selected.")
    return manifest


def build_matrix(manifest: pd.DataFrame, exit_labels: list[str], max_runs: int) -> pd.DataFrame:
    unknown = sorted(set(exit_labels) - set(EXIT_LABELS))
    if unknown:
        raise ValueError(f"Unknown exit labels: {unknown}")

    rows: list[dict[str, Any]] = []
    for _, candidate in manifest.iterrows():
        candidate_id = str(candidate["canonical_fixed_candidate_id"])
        for exit_label in exit_labels:
            rows.append(
                {
                    "canonical_fixed_candidate_id": candidate_id,
                    "alias_fixed_candidate_ids": candidate.get("alias_fixed_candidate_ids", ""),
                    "signal_set_hash": candidate.get("signal_set_hash", ""),
                    "exit_label": exit_label,
                    "exit_mode": EXIT_LABELS[exit_label],
                    "strategy_class": strategy_class_name(candidate_id, exit_label),
                    "cost_scenario": "base",
                }
            )
    frame = pd.DataFrame(rows)
    return frame.head(max_runs).copy() if max_runs > 0 else frame


def subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    startup_path = str((Path(__file__).resolve().parent / "python_startup").resolve())
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = startup_path if not existing else startup_path + os.pathsep + existing
    return env


def run_command(command: list[str], log_path: Path) -> subprocess.CompletedProcess[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, capture_output=True, text=True, check=False, env=subprocess_env())
    output = (completed.stdout or "") + ("\n" if completed.stdout and completed.stderr else "") + (completed.stderr or "")
    log_path.write_text(output, encoding="utf-8")
    return completed


def latest_backtest_zip(backtest_dir: Path) -> Path | None:
    last_result = backtest_dir / ".last_result.json"
    if not last_result.exists():
        return None
    payload = json.loads(last_result.read_text(encoding="utf-8"))
    latest = payload.get("latest_backtest")
    if not latest:
        return None
    return backtest_dir / str(latest)


def profit_factor(profits: pd.Series) -> float:
    if profits.empty:
        return 0.0
    gross_profit = float(profits[profits > 0].sum())
    gross_loss = abs(float(profits[profits < 0].sum()))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def positive_share(values: pd.Series, total_positive: float) -> float:
    if values.empty or total_positive <= 0:
        return 1.0
    return max(float(values.sum()), 0.0) / total_positive


def trade_notional(trades: pd.DataFrame) -> pd.Series:
    if trades.empty:
        return pd.Series(dtype=float)
    amount = pd.to_numeric(trades.get("amount", 0.0), errors="coerce").fillna(0.0).abs()
    open_rate = pd.to_numeric(trades.get("open_rate", 0.0), errors="coerce").fillna(0.0)
    close_rate = pd.to_numeric(trades.get("close_rate", open_rate), errors="coerce").fillna(open_rate)
    notional = ((open_rate + close_rate) / 2.0) * amount
    if float(notional.sum()) <= 0 and "stake_amount" in trades:
        notional = pd.to_numeric(trades["stake_amount"], errors="coerce").fillna(0.0).abs()
    return notional


def extra_fee_2x_cost(trades: pd.DataFrame, default_fee_per_side: float) -> pd.Series:
    notional = trade_notional(trades)
    if trades.empty:
        return notional
    open_fee = pd.to_numeric(trades.get("fee_open", default_fee_per_side), errors="coerce").fillna(default_fee_per_side)
    close_fee = pd.to_numeric(trades.get("fee_close", default_fee_per_side), errors="coerce").fillna(default_fee_per_side)
    return notional * (open_fee + close_fee)


def classify(row: dict[str, Any], args: argparse.Namespace) -> str:
    if row["status"] != "pass":
        return "BACKTEST_FAILED"
    if row["trades"] < args.min_trades:
        return "INSUFFICIENT_TRADES"
    if row["validation_trades"] < args.min_validation_trades or row["validation_profit_pct"] <= 0:
        return "VALIDATION_FAIL"
    if row["active_pairs"] < args.min_active_pairs or row["active_years"] < args.min_active_years:
        return "INSUFFICIENT_BREADTH"
    if row["profit_after_fee_2x"] <= 0 or row["profit_after_20bps_cost_proxy"] <= 0:
        return "COST_SENSITIVE"
    if (
        row["top_pair_profit_share"] > args.max_top_pair_profit_share
        or row["top_year_profit_share"] > args.max_top_year_profit_share
    ):
        return "CONCENTRATED_EDGE"
    if row["max_drawdown_pct"] > args.max_drawdown_pct:
        return "EXIT_REDESIGN_NEEDED"
    if row["profit_usdt"] <= 0 or row["profit_pct"] <= 0:
        return "REJECT_PORTFOLIO"
    return "RESEARCH_STRATEGY_CANDIDATE"


def summarize_run(
    strategy_data: dict[str, Any],
    trades: pd.DataFrame,
    matrix_row: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[dict[str, Any], pd.DataFrame]:
    validation_start = pd.Timestamp(args.validation_start, tz="UTC")
    trades = trades.copy()
    if trades.empty:
        trades["profit_abs"] = pd.Series(dtype=float)
        trades["profit_ratio"] = pd.Series(dtype=float)

    profits = pd.to_numeric(trades.get("profit_abs", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    ratios = pd.to_numeric(trades.get("profit_ratio", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    if "open_date" in trades:
        open_dates = pd.to_datetime(trades["open_date"], utc=True)
        validation = trades[open_dates >= validation_start].copy()
        active_years = int(open_dates.dt.year.nunique())
    else:
        open_dates = pd.Series(dtype="datetime64[ns, UTC]")
        validation = pd.DataFrame()
        active_years = 0

    if "close_date" in trades and "open_date" in trades and not trades.empty:
        durations = pd.to_datetime(trades["close_date"], utc=True) - pd.to_datetime(trades["open_date"], utc=True)
        avg_duration_hours = float(durations.dt.total_seconds().mean() / 3600.0)
    else:
        avg_duration_hours = float("nan")

    total_positive = float(profits[profits > 0].sum())
    pair_profit = trades.assign(_profit=profits).groupby("pair")["_profit"].sum() if "pair" in trades else pd.Series(dtype=float)
    year_profit = (
        trades.assign(_profit=profits, _year=open_dates.dt.year).groupby("_year")["_profit"].sum()
        if not trades.empty and not open_dates.empty
        else pd.Series(dtype=float)
    )
    sorted_positive = profits[profits > 0].sort_values(ascending=False)

    notional = trade_notional(trades)
    fee_2x = extra_fee_2x_cost(trades, args.default_fee_per_side)
    cost_20bps = notional * (float(args.round_trip_cost_bps) / 10000.0)
    funding_proxy = notional * (float(args.adverse_funding_bps) / 10000.0)
    total_profit = float(profits.sum())

    row: dict[str, Any] = {
        **matrix_row,
        "status": "pass",
        "trades": int(strategy_data.get("total_trades", len(trades)) or len(trades)),
        "profit_usdt": float(strategy_data.get("profit_total_abs", total_profit) or total_profit),
        "profit_pct": float(strategy_data.get("profit_total", ratios.sum()) or ratios.sum()) * 100.0,
        "max_drawdown_pct": float(
            strategy_data.get("max_drawdown_account", strategy_data.get("max_drawdown", 0.0)) or 0.0
        )
        * 100.0,
        "profit_factor": float(strategy_data.get("profit_factor", profit_factor(profits)) or profit_factor(profits)),
        "expectancy": float(strategy_data.get("expectancy", profits.mean() if not profits.empty else 0.0) or 0.0),
        "avg_duration_hours": avg_duration_hours,
        "active_pairs": int(trades["pair"].nunique()) if "pair" in trades else 0,
        "active_years": active_years,
        "validation_trades": int(len(validation)),
        "validation_profit_usdt": float(pd.to_numeric(validation.get("profit_abs", pd.Series(dtype=float)), errors="coerce").sum())
        if not validation.empty
        else 0.0,
        "validation_profit_pct": float(
            pd.to_numeric(validation.get("profit_ratio", pd.Series(dtype=float)), errors="coerce").sum()
        )
        * 100.0
        if not validation.empty
        else 0.0,
        "top_pair_profit_share": positive_share(pair_profit.sort_values(ascending=False).head(1), total_positive),
        "top_year_profit_share": positive_share(year_profit.sort_values(ascending=False).head(1), total_positive),
        "top_1_trade_profit_share": positive_share(sorted_positive.head(1), total_positive),
        "top_5_trade_profit_share": positive_share(sorted_positive.head(5), total_positive),
        "profit_after_top_1_trade_removal": total_profit - float(sorted_positive.head(1).sum()),
        "profit_after_top_5_trade_removal": total_profit - float(sorted_positive.head(5).sum()),
        "profit_after_fee_2x": total_profit - float(fee_2x.sum()),
        "profit_after_20bps_cost_proxy": total_profit - float(cost_20bps.sum()),
        "profit_after_adverse_funding_proxy": total_profit - float(funding_proxy.sum()),
    }
    row["decision"] = classify(row, args)

    if not trades.empty:
        trades["strategy_class"] = matrix_row["strategy_class"]
        trades["canonical_fixed_candidate_id"] = matrix_row["canonical_fixed_candidate_id"]
        trades["exit_mode"] = matrix_row["exit_mode"]
    return row, trades


def run_backtest(matrix_row: dict[str, Any], args: argparse.Namespace) -> tuple[dict[str, Any], pd.DataFrame]:
    strategy = str(matrix_row["strategy_class"])
    run_dir = Path(args.backtest_dir) / strategy
    log_path = Path(args.logs_dir) / f"{strategy}.log"
    command = [
        args.python,
        "-m",
        "freqtrade",
        "backtesting",
        "--config",
        args.config,
        "--strategy",
        strategy,
        "--strategy-path",
        args.strategy_path,
        "--datadir",
        args.datadir,
        "--timeframe",
        "5m",
        "--timerange",
        args.timerange,
        "--export",
        "signals",
        "--backtest-directory",
        str(run_dir),
    ]
    completed = run_command(command, log_path)
    base_row = {**matrix_row, "log": str(log_path), "exit_code": completed.returncode}
    if completed.returncode != 0:
        return {**base_row, "status": "fail", "decision": "BACKTEST_FAILED"}, pd.DataFrame()

    zip_path = latest_backtest_zip(run_dir)
    if zip_path is None:
        return {**base_row, "status": "fail", "decision": "BACKTEST_RESULT_MISSING"}, pd.DataFrame()

    strategy_data, trades = parse_backtest_zip(zip_path, strategy)
    row, trades = summarize_run(strategy_data, trades, base_row, args)
    row["results_zip"] = str(zip_path)
    return row, trades


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    try:
        return frame.to_markdown(index=False, floatfmt=".4f")
    except ImportError:
        return "```csv\n" + frame.to_csv(index=False).replace("\r\n", "\n").strip() + "\n```"


def write_outputs(summary: pd.DataFrame, trades: pd.DataFrame, args: argparse.Namespace) -> None:
    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)
    trades_csv = Path(args.trades_csv)
    for path in (output_csv, output_md, trades_csv):
        path.parent.mkdir(parents=True, exist_ok=True)

    summary.to_csv(output_csv, index=False, float_format="%.6g", lineterminator="\n")
    if not trades.empty:
        trades.to_csv(trades_csv, index=False, float_format="%.6g", lineterminator="\n")

    decision_counts = (
        summary["decision"].value_counts().rename_axis("decision").reset_index(name="runs")
        if "decision" in summary
        else pd.DataFrame()
    )
    compact_columns = [
        "strategy_class",
        "canonical_fixed_candidate_id",
        "exit_mode",
        "status",
        "trades",
        "profit_usdt",
        "profit_pct",
        "max_drawdown_pct",
        "validation_trades",
        "validation_profit_pct",
        "profit_after_20bps_cost_proxy",
        "top_pair_profit_share",
        "top_year_profit_share",
        "decision",
    ]
    available_compact = [column for column in compact_columns if column in summary.columns]
    lines = [
        "# Major 11 Immediate Flush Research Backtest",
        "",
        "> Research-only Freqtrade portfolio backtest layer. Passing rows are not dry-run or live-trading approvals.",
        "",
        "## Scope",
        "",
        f"- Manifest: `{args.manifest}`",
        f"- Config: `{args.config}`",
        f"- Timerange: `{args.timerange}`",
        f"- Plan only: `{args.plan_only}`",
        f"- Runs: `{len(summary)}`",
        "",
        "## Decision Counts",
        "",
        markdown_table(decision_counts),
        "",
        "## Summary",
        "",
        markdown_table(summary[available_compact]) if available_compact else markdown_table(summary),
        "",
        "## Decision Gates",
        "",
        f"- trades >= `{args.min_trades}`",
        f"- validation_trades >= `{args.min_validation_trades}`",
        f"- active_pairs >= `{args.min_active_pairs}`",
        f"- active_years >= `{args.min_active_years}`",
        f"- validation_profit_pct > `0`",
        f"- profit_after_top_5_trade_removal > `0`",
        f"- profit_after_fee_2x > `0`",
        f"- profit_after_20bps_cost_proxy > `0`",
        f"- top_pair_profit_share <= `{args.max_top_pair_profit_share}`",
        f"- top_year_profit_share <= `{args.max_top_year_profit_share}`",
        f"- max_drawdown_pct <= `{args.max_drawdown_pct}`",
        "",
    ]
    output_md.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> None:
    args = parse_args()
    manifest = load_manifest(Path(args.manifest), args.candidate_ids)
    matrix = build_matrix(manifest, args.exit_labels, args.max_runs)
    if args.plan_only:
        planned = matrix.assign(status="planned", decision="NOT_RUN_PLAN_ONLY")
        write_outputs(planned, pd.DataFrame(), args)
        print(f"Wrote plan-only matrix to {args.output_md}")
        return

    rows: list[dict[str, Any]] = []
    trade_frames: list[pd.DataFrame] = []
    for _, matrix_row in matrix.iterrows():
        row, trades = run_backtest(matrix_row.to_dict(), args)
        rows.append(row)
        if not trades.empty:
            trade_frames.append(trades)

    summary = pd.DataFrame(rows)
    trades = pd.concat(trade_frames, ignore_index=True, sort=False) if trade_frames else pd.DataFrame()
    write_outputs(summary, trades, args)
    print(f"Wrote backtest summary to {args.output_md}")


if __name__ == "__main__":
    main()
