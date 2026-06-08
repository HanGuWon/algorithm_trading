from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

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

FEE_SCENARIOS: dict[str, float | None] = {
    "base": None,
    "fee_2x_real": 0.0008,
    "fee_5bps_real": 0.0005,
    "fee_10bps_real": 0.0010,
}

REQUIRED_TRADE_COLUMNS = ["pair", "open_date", "close_date", "profit_abs", "profit_ratio"]

BREAKDOWN_COLUMNS = [
    "strategy_class",
    "canonical_fixed_candidate_id",
    "exit_mode",
    "pair",
    "year",
    "month",
    "exit_reason",
    "trades",
    "profit_usdt",
    "profit_pct_sum",
    "win_rate",
    "avg_profit_abs",
    "max_single_trade_profit",
    "max_single_trade_loss",
]

ROW_METADATA_KEYS = [
    "input_git_commit",
    "input_git_worktree_dirty",
    "manifest_sha256",
    "strategy_file_sha256",
    "config_sha256",
    "freqtrade_version",
    "expected_run_count",
    "manifest_row_count",
    "exit_mode_count",
    "fee_scenario_count",
    "strategy_class_count",
    "strategy_discovery_status",
    "strategy_discovery_missing_count",
    "artifact_mode",
    "is_backtest_result",
]


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
    parser.add_argument(
        "--strategy-file",
        default="user_data/strategies/VolatilityRotationMRImmediateFlushResearch.py",
    )
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
        "--plan-output-csv",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_plan_summary.csv",
    )
    parser.add_argument(
        "--plan-output-md",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_plan_summary.md",
    )
    parser.add_argument(
        "--trades-csv",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_trades.csv",
    )
    parser.add_argument(
        "--plan-trades-csv",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_plan_trades.csv",
    )
    parser.add_argument(
        "--pair-breakdown-csv",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_pair_breakdown.csv",
    )
    parser.add_argument(
        "--plan-pair-breakdown-csv",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_plan_pair_breakdown.csv",
    )
    parser.add_argument(
        "--year-breakdown-csv",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_year_breakdown.csv",
    )
    parser.add_argument(
        "--plan-year-breakdown-csv",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_plan_year_breakdown.csv",
    )
    parser.add_argument(
        "--month-breakdown-csv",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_month_breakdown.csv",
    )
    parser.add_argument(
        "--plan-month-breakdown-csv",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_plan_month_breakdown.csv",
    )
    parser.add_argument(
        "--exit-reason-breakdown-csv",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_exit_reason_breakdown.csv",
    )
    parser.add_argument(
        "--plan-exit-reason-breakdown-csv",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_plan_exit_reason_breakdown.csv",
    )
    parser.add_argument(
        "--metadata-json",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_metadata.json",
    )
    parser.add_argument(
        "--plan-metadata-json",
        default="docs/validation/analysis/major_11_immediate_flush_research_backtest_plan_metadata.json",
    )
    parser.add_argument(
        "--discovery-output",
        default="docs/validation/analysis/major_11_immediate_flush_strategy_discovery.txt",
    )
    parser.add_argument("--logs-dir", default="docs/validation/logs/major_11_immediate_flush_backtest")
    parser.add_argument("--backtest-dir", default="user_data/backtest_results/major_11_immediate_flush")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--exit-labels", nargs="+", default=list(EXIT_LABELS))
    parser.add_argument("--candidate-ids", nargs="+", default=[])
    parser.add_argument("--fee-scenarios", nargs="+", default=["base"], choices=list(FEE_SCENARIOS))
    parser.add_argument("--export-mode", default="trades", choices=["trades", "signals"])
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--discovery-only", action="store_true")
    parser.add_argument(
        "--allow-dirty-execution",
        action="store_true",
        help="Allow real backtests from a dirty worktree. Ignored by --plan-only.",
    )
    parser.add_argument(
        "--allow-discovery-failure",
        action="store_true",
        help="Allow real backtests even when strategy discovery did not pass.",
    )
    parser.add_argument("--skip-discovery", action="store_true")
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
    safe_id = (
        candidate_id.replace("_original", "")
        .replace("_drop_breakout_block", "NoBreakout")
        .replace("_", "")
    )
    return f"ImmediateFlushResearch{safe_id}{exit_label}"


def load_manifest(path: Path, candidate_ids: list[str]) -> pd.DataFrame:
    manifest = pd.read_csv(path)
    if candidate_ids:
        manifest = manifest[manifest["canonical_fixed_candidate_id"].astype(str).isin(candidate_ids)].copy()
    if manifest.empty:
        raise SystemExit("No canonical candidates selected.")
    return manifest


def build_matrix(
    manifest: pd.DataFrame,
    exit_labels: list[str],
    fee_scenarios: list[str],
    max_runs: int,
) -> pd.DataFrame:
    unknown_exits = sorted(set(exit_labels) - set(EXIT_LABELS))
    if unknown_exits:
        raise ValueError(f"Unknown exit labels: {unknown_exits}")

    unknown_fees = sorted(set(fee_scenarios) - set(FEE_SCENARIOS))
    if unknown_fees:
        raise ValueError(f"Unknown fee scenarios: {unknown_fees}")

    rows: list[dict[str, Any]] = []
    for _, candidate in manifest.iterrows():
        candidate_id = str(candidate["canonical_fixed_candidate_id"])
        for exit_label in exit_labels:
            strategy_class = strategy_class_name(candidate_id, exit_label)
            for fee_scenario in fee_scenarios:
                rows.append(
                    {
                        "canonical_fixed_candidate_id": candidate_id,
                        "alias_fixed_candidate_ids": candidate.get("alias_fixed_candidate_ids", ""),
                        "signal_set_hash": candidate.get("signal_set_hash", ""),
                        "exit_label": exit_label,
                        "exit_mode": EXIT_LABELS[exit_label],
                        "strategy_class": strategy_class,
                        "cost_scenario": fee_scenario,
                        "freqtrade_fee": FEE_SCENARIOS[fee_scenario],
                    }
                )

    frame = pd.DataFrame(rows)
    class_rows = frame[["canonical_fixed_candidate_id", "exit_label", "strategy_class"]].drop_duplicates()
    duplicated_classes = class_rows[class_rows["strategy_class"].duplicated(keep=False)]
    if not duplicated_classes.empty:
        raise ValueError(f"Strategy class name collision:\n{duplicated_classes.to_string(index=False)}")
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
    output = "$ " + " ".join(command) + "\n\n"
    output += (completed.stdout or "") + ("\n" if completed.stdout and completed.stderr else "") + (completed.stderr or "")
    log_path.write_text(output, encoding="utf-8", newline="\n")
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


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> tuple[str, bool]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return commit, bool(status)
    except (OSError, subprocess.CalledProcessError):
        return "", False


def freqtrade_version(python_executable: str) -> str:
    completed = subprocess.run(
        [python_executable, "-m", "freqtrade", "--version"],
        capture_output=True,
        text=True,
        check=False,
        env=subprocess_env(),
    )
    output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
    if completed.returncode != 0:
        return "unavailable" if not output else "unavailable: " + output.splitlines()[-1]
    return output.splitlines()[0] if output else "available"


def build_metadata(args: argparse.Namespace, manifest: pd.DataFrame, matrix: pd.DataFrame) -> dict[str, Any]:
    commit, dirty = git_commit()
    strategy_classes = sorted(matrix["strategy_class"].astype(str).unique())
    return {
        "input_git_commit": commit,
        "input_git_worktree_dirty": dirty,
        "manifest_sha256": sha256_file(Path(args.manifest)),
        "strategy_file_sha256": sha256_file(Path(args.strategy_file)),
        "config_sha256": sha256_file(Path(args.config)),
        "freqtrade_version": freqtrade_version(args.python),
        "expected_run_count": int(len(matrix)),
        "manifest_row_count": int(len(manifest)),
        "exit_mode_count": int(len(args.exit_labels)),
        "fee_scenario_count": int(len(args.fee_scenarios)),
        "strategy_class_count": int(len(strategy_classes)),
        "strategy_class_names": strategy_classes,
        "export_mode": args.export_mode,
        "fee_scenarios": list(args.fee_scenarios),
        "artifact_mode": "plan_only" if args.plan_only else "backtest_result",
        "is_backtest_result": not args.plan_only,
    }


def add_metadata_columns(frame: pd.DataFrame, metadata: dict[str, Any]) -> pd.DataFrame:
    frame = frame.copy()
    for key in ROW_METADATA_KEYS:
        frame[key] = metadata.get(key, "")
    return frame


def selected_output_paths(args: argparse.Namespace) -> dict[str, Path]:
    plan = bool(args.plan_only)
    return {
        "output_csv": Path(args.plan_output_csv if plan else args.output_csv),
        "output_md": Path(args.plan_output_md if plan else args.output_md),
        "trades_csv": Path(args.plan_trades_csv if plan else args.trades_csv),
        "pair_breakdown_csv": Path(args.plan_pair_breakdown_csv if plan else args.pair_breakdown_csv),
        "year_breakdown_csv": Path(args.plan_year_breakdown_csv if plan else args.year_breakdown_csv),
        "month_breakdown_csv": Path(args.plan_month_breakdown_csv if plan else args.month_breakdown_csv),
        "exit_reason_breakdown_csv": Path(
            args.plan_exit_reason_breakdown_csv if plan else args.exit_reason_breakdown_csv
        ),
        "metadata_json": Path(args.plan_metadata_json if plan else args.metadata_json),
    }


def write_strategy_discovery(args: argparse.Namespace, matrix: pd.DataFrame, metadata: dict[str, Any]) -> dict[str, Any]:
    output_path = Path(args.discovery_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    expected_classes = sorted(matrix["strategy_class"].astype(str).unique())
    command = [
        args.python,
        "-m",
        "freqtrade",
        "list-strategies",
        "--strategy-path",
        args.strategy_path,
        "--recursive-strategy-search",
    ]

    lines = [
        "# Major 11 Immediate Flush Strategy Discovery",
        "",
        f"expected_strategy_class_count: {len(expected_classes)}",
        f"expected_run_count: {metadata['expected_run_count']}",
        f"manifest_sha256: {metadata['manifest_sha256']}",
        f"command: {' '.join(command)}",
        "",
        "## Expected Classes",
        "",
        "\n".join(expected_classes),
        "",
    ]

    if args.skip_discovery:
        lines.extend(["## Result", "", "status: skipped"])
        output_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        return {"strategy_discovery_status": "skipped", "strategy_discovery_missing_count": ""}

    if args.plan_only:
        lines.extend(["## Result", "", "status: not_run_plan_only"])
        output_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        return {"strategy_discovery_status": "not_run_plan_only", "strategy_discovery_missing_count": ""}

    completed = subprocess.run(command, capture_output=True, text=True, check=False, env=subprocess_env())
    output = (completed.stdout or "") + ("\n" if completed.stdout and completed.stderr else "") + (completed.stderr or "")
    missing = [class_name for class_name in expected_classes if class_name not in output]
    status = "pass" if completed.returncode == 0 and not missing else "fail"
    lines.extend(
        [
            "## Result",
            "",
            f"status: {status}",
            f"exit_code: {completed.returncode}",
            f"missing_expected_class_count: {len(missing)}",
            "",
            "## Missing Expected Classes",
            "",
            "\n".join(missing) if missing else "_None._",
            "",
            "## Raw Output",
            "",
            "```",
            output.strip(),
            "```",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return {"strategy_discovery_status": status, "strategy_discovery_missing_count": len(missing)}


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


def first_numeric(mapping: dict[str, Any], keys: list[str], default: float = 0.0) -> float:
    for key in keys:
        value = mapping.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return default


def value_counts_text(trades: pd.DataFrame, column: str, limit: int = 12) -> str:
    if trades.empty or column not in trades:
        return ""
    counts = trades[column].fillna("UNKNOWN").astype(str).value_counts().head(limit)
    return ", ".join(f"{key}:{int(value)}" for key, value in counts.items())


def same_candle_collisions(trades: pd.DataFrame) -> int | str:
    if trades.empty or "open_date" not in trades or "close_date" not in trades:
        return ""
    open_dates = pd.to_datetime(trades["open_date"], utc=True, errors="coerce")
    close_dates = pd.to_datetime(trades["close_date"], utc=True, errors="coerce")
    return int((open_dates == close_dates).sum())


def missing_trade_columns(trades: pd.DataFrame) -> list[str]:
    if trades.empty:
        return []
    return [column for column in REQUIRED_TRADE_COLUMNS if column not in trades.columns]


def classify(row: dict[str, Any], args: argparse.Namespace) -> str:
    if row.get("decision") in {"BACKTEST_RESULT_MISSING", "BACKTEST_RESULT_SCHEMA_FAIL"}:
        return str(row["decision"])
    if row["status"] != "pass":
        return "BACKTEST_FAILED"
    if row["trades"] <= 0:
        return "NO_TRADES"
    if row["trades"] < args.min_trades:
        return "INSUFFICIENT_TRADES"
    if (
        row["validation_trades"] < args.min_validation_trades
        or row["validation_profit_usdt"] <= 0
        or row["validation_profit_pct_of_starting_balance"] <= 0
    ):
        return "VALIDATION_FAIL"
    if row["active_pairs"] < args.min_active_pairs or row["active_years"] < args.min_active_years:
        return "INSUFFICIENT_BREADTH"
    if row["profit_after_top_5_trade_removal"] <= 0:
        return "TOP_TRADE_CONCENTRATED"
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
        open_dates = pd.to_datetime(trades["open_date"], utc=True, errors="coerce")
        validation = trades[open_dates >= validation_start].copy()
        active_years = int(open_dates.dt.year.nunique())
    else:
        open_dates = pd.Series(dtype="datetime64[ns, UTC]")
        validation = pd.DataFrame()
        active_years = 0

    if "close_date" in trades and "open_date" in trades and not trades.empty:
        durations = pd.to_datetime(trades["close_date"], utc=True, errors="coerce") - pd.to_datetime(
            trades["open_date"], utc=True, errors="coerce"
        )
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
    validation_profit_usdt = (
        float(pd.to_numeric(validation.get("profit_abs", pd.Series(dtype=float)), errors="coerce").sum())
        if not validation.empty
        else 0.0
    )

    starting_balance = first_numeric(
        strategy_data,
        ["starting_balance", "backtest_start_balance", "dry_run_wallet", "start_balance"],
        0.0,
    )
    final_balance = first_numeric(
        strategy_data,
        ["final_balance", "backtest_end_balance", "end_balance"],
        starting_balance + total_profit if starting_balance > 0 else total_profit,
    )
    validation_pct_of_start = (validation_profit_usdt / starting_balance) * 100.0 if starting_balance > 0 else 0.0

    row: dict[str, Any] = {
        **matrix_row,
        "status": "pass",
        "trades": int(strategy_data.get("total_trades", len(trades)) or len(trades)),
        "starting_balance": starting_balance,
        "final_balance": final_balance,
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
        "validation_profit_usdt": validation_profit_usdt,
        "validation_profit_pct": float(
            pd.to_numeric(validation.get("profit_ratio", pd.Series(dtype=float)), errors="coerce").sum()
        )
        * 100.0
        if not validation.empty
        else 0.0,
        "validation_profit_pct_of_starting_balance": validation_pct_of_start,
        "top_pair_profit_share": positive_share(pair_profit.sort_values(ascending=False).head(1), total_positive),
        "top_year_profit_share": positive_share(year_profit.sort_values(ascending=False).head(1), total_positive),
        "top_1_trade_profit_share": positive_share(sorted_positive.head(1), total_positive),
        "top_5_trade_profit_share": positive_share(sorted_positive.head(5), total_positive),
        "profit_after_top_1_trade_removal": total_profit - float(sorted_positive.head(1).sum()),
        "profit_after_top_5_trade_removal": total_profit - float(sorted_positive.head(5).sum()),
        "profit_after_fee_2x": total_profit - float(fee_2x.sum()),
        "profit_after_20bps_cost_proxy": total_profit - float(cost_20bps.sum()),
        "profit_after_adverse_funding_proxy": total_profit - float(funding_proxy.sum()),
        "exit_reason_counts": value_counts_text(trades, "exit_reason"),
        "enter_tag_counts": value_counts_text(trades, "enter_tag"),
        "rejected_signal_count_if_available": "",
        "same_candle_entry_exit_collisions_if_available": same_candle_collisions(trades),
        "missing_trade_columns": "",
    }
    row["decision"] = classify(row, args)

    if not trades.empty:
        trades["strategy_class"] = matrix_row["strategy_class"]
        trades["canonical_fixed_candidate_id"] = matrix_row["canonical_fixed_candidate_id"]
        trades["exit_mode"] = matrix_row["exit_mode"]
        trades["cost_scenario"] = matrix_row["cost_scenario"]
    return row, trades


def run_backtest(matrix_row: dict[str, Any], args: argparse.Namespace) -> tuple[dict[str, Any], pd.DataFrame]:
    strategy = str(matrix_row["strategy_class"])
    cost_scenario = str(matrix_row["cost_scenario"])
    run_key = f"{strategy}__{cost_scenario}"
    run_dir = Path(args.backtest_dir) / run_key
    log_path = Path(args.logs_dir) / f"{run_key}.log"
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
        args.export_mode,
        "--backtest-directory",
        str(run_dir),
    ]
    if matrix_row.get("freqtrade_fee") is not None:
        command.extend(["--fee", str(matrix_row["freqtrade_fee"])])

    completed = run_command(command, log_path)
    base_row = {
        **matrix_row,
        "log": str(log_path),
        "exit_code": completed.returncode,
        "export_mode": args.export_mode,
    }
    if completed.returncode != 0:
        return {**base_row, "status": "fail", "decision": "BACKTEST_FAILED"}, pd.DataFrame()

    zip_path = latest_backtest_zip(run_dir)
    if zip_path is None:
        return {**base_row, "status": "fail", "decision": "BACKTEST_RESULT_MISSING"}, pd.DataFrame()

    try:
        strategy_data, trades = parse_backtest_zip(zip_path, strategy)
    except (KeyError, StopIteration, json.JSONDecodeError, OSError) as exc:
        return {
            **base_row,
            "status": "fail",
            "decision": "BACKTEST_RESULT_SCHEMA_FAIL",
            "missing_trade_columns": f"parse_error:{type(exc).__name__}",
            "results_zip": str(zip_path),
        }, pd.DataFrame()

    missing = missing_trade_columns(trades)
    row, trades = summarize_run(strategy_data, trades, base_row, args)
    if missing:
        row["status"] = "fail"
        row["decision"] = "BACKTEST_RESULT_SCHEMA_FAIL"
        row["missing_trade_columns"] = ",".join(missing)
        trades = pd.DataFrame()
    row["results_zip"] = str(zip_path)
    return row, trades


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    try:
        return frame.to_markdown(index=False, floatfmt=".4f")
    except ImportError:
        return "```csv\n" + frame.to_csv(index=False).replace("\r\n", "\n").strip() + "\n```"


def normalise_breakdown_trades(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    frame = trades.copy()
    frame["profit_abs"] = pd.to_numeric(frame.get("profit_abs", 0.0), errors="coerce").fillna(0.0)
    frame["profit_ratio"] = pd.to_numeric(frame.get("profit_ratio", 0.0), errors="coerce").fillna(0.0)
    open_dates = pd.to_datetime(frame.get("open_date", pd.Series(dtype=str)), utc=True, errors="coerce")
    frame["year"] = open_dates.dt.year.astype("Int64").astype(str).replace("<NA>", "UNKNOWN")
    frame["month"] = open_dates.dt.strftime("%Y-%m").fillna("UNKNOWN")
    if "exit_reason" not in frame:
        if "exit_tag" in frame:
            frame["exit_reason"] = frame["exit_tag"]
        elif "sell_reason" in frame:
            frame["exit_reason"] = frame["sell_reason"]
        else:
            frame["exit_reason"] = "UNKNOWN"
    frame["exit_reason"] = frame["exit_reason"].fillna("UNKNOWN").astype(str)
    return frame


def aggregate_breakdown(trades: pd.DataFrame, group_column: str) -> pd.DataFrame:
    frame = normalise_breakdown_trades(trades)
    output_columns = [
        "strategy_class",
        "canonical_fixed_candidate_id",
        "exit_mode",
        group_column,
        "trades",
        "profit_usdt",
        "profit_pct_sum",
        "win_rate",
        "avg_profit_abs",
        "max_single_trade_profit",
        "max_single_trade_loss",
    ]
    if frame.empty:
        return pd.DataFrame(columns=output_columns)

    keys = ["strategy_class", "canonical_fixed_candidate_id", "exit_mode", group_column]
    grouped = frame.groupby(keys, dropna=False)
    result = grouped.agg(
        trades=("profit_abs", "size"),
        profit_usdt=("profit_abs", "sum"),
        profit_pct_sum=("profit_ratio", lambda series: float(series.sum()) * 100.0),
        win_rate=("profit_abs", lambda series: float((series > 0).mean()) * 100.0),
        avg_profit_abs=("profit_abs", "mean"),
        max_single_trade_profit=("profit_abs", "max"),
        max_single_trade_loss=("profit_abs", "min"),
    )
    return result.reset_index()[output_columns]


def write_breakdown_outputs(trades: pd.DataFrame, args: argparse.Namespace, paths: dict[str, Path]) -> None:
    outputs = {
        "pair": paths["pair_breakdown_csv"],
        "year": paths["year_breakdown_csv"],
        "month": paths["month_breakdown_csv"],
        "exit_reason": paths["exit_reason_breakdown_csv"],
    }
    for group_column, path in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if args.plan_only:
            plan_only_artifact_frame(f"{group_column}_breakdown").to_csv(path, index=False, lineterminator="\n")
        else:
            aggregate_breakdown(trades, group_column).to_csv(path, index=False, float_format="%.6g", lineterminator="\n")


def plan_only_artifact_frame(artifact: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "artifact": artifact,
                "artifact_mode": "plan_only",
                "is_backtest_result": False,
                "note": "Placeholder created by --plan-only. Run without --plan-only to produce real backtest data.",
            }
        ]
    )


def write_outputs(summary: pd.DataFrame, trades: pd.DataFrame, args: argparse.Namespace, metadata: dict[str, Any]) -> None:
    paths = selected_output_paths(args)
    output_csv = paths["output_csv"]
    output_md = paths["output_md"]
    trades_csv = paths["trades_csv"]
    metadata_json = paths["metadata_json"]
    for path in (output_csv, output_md, trades_csv, metadata_json):
        path.parent.mkdir(parents=True, exist_ok=True)

    summary.to_csv(output_csv, index=False, float_format="%.6g", lineterminator="\n")
    if args.plan_only:
        plan_only_artifact_frame("trades").to_csv(trades_csv, index=False, lineterminator="\n")
    else:
        trades.to_csv(trades_csv, index=False, float_format="%.6g", lineterminator="\n")
    write_breakdown_outputs(trades, args, paths)
    metadata_json.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8", newline="\n")

    decision_counts = (
        summary["decision"].value_counts().rename_axis("decision").reset_index(name="runs")
        if "decision" in summary
        else pd.DataFrame()
    )
    compact_columns = [
        "strategy_class",
        "canonical_fixed_candidate_id",
        "exit_mode",
        "cost_scenario",
        "artifact_mode",
        "is_backtest_result",
        "status",
        "trades",
        "profit_usdt",
        "profit_pct",
        "max_drawdown_pct",
        "validation_trades",
        "validation_profit_usdt",
        "validation_profit_pct_of_starting_balance",
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
        f"- Export mode: `{args.export_mode}`",
        f"- Fee scenarios: `{', '.join(args.fee_scenarios)}`",
        f"- Plan only: `{args.plan_only}`",
        f"- Runs: `{len(summary)}`",
        f"- Manifest rows: `{metadata['manifest_row_count']}`",
        f"- Exit modes: `{metadata['exit_mode_count']}`",
        f"- Strategy classes: `{metadata['strategy_class_count']}`",
        f"- Artifact mode: `{metadata['artifact_mode']}`",
        f"- Is backtest result: `{metadata['is_backtest_result']}`",
        f"- Manifest SHA256: `{metadata['manifest_sha256']}`",
        f"- Strategy file SHA256: `{metadata['strategy_file_sha256']}`",
        f"- Config SHA256: `{metadata['config_sha256']}`",
        f"- Input git commit: `{metadata['input_git_commit']}`",
        f"- Input git worktree dirty at run time: `{metadata['input_git_worktree_dirty']}`",
        f"- Freqtrade version: `{metadata['freqtrade_version']}`",
        f"- Discovery status: `{metadata.get('strategy_discovery_status', '')}`",
        "",
        "## Artifacts",
        "",
        f"- Metadata: `{metadata_json}`",
        f"- Trades: `{trades_csv}`",
        f"- Pair breakdown: `{paths['pair_breakdown_csv']}`",
        f"- Year breakdown: `{paths['year_breakdown_csv']}`",
        f"- Month breakdown: `{paths['month_breakdown_csv']}`",
        f"- Exit reason breakdown: `{paths['exit_reason_breakdown_csv']}`",
        f"- Strategy discovery: `{args.discovery_output}`",
        "",
        "## Decision Counts",
        "",
        markdown_table(decision_counts),
        "",
        "## Plan-Only Guard",
        "",
        (
            "`--plan-only` was used. Summary rows are execution plans, and trades/breakdown CSVs are explicit "
            "placeholder artifacts, not backtest results."
            if args.plan_only
            else "Real backtest outputs were requested. Trades and breakdown CSVs are parsed from Freqtrade results."
        ),
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
        f"- validation_profit_usdt > `0`",
        f"- validation_profit_pct_of_starting_balance > `0`",
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
    matrix = build_matrix(manifest, args.exit_labels, args.fee_scenarios, args.max_runs)
    metadata = build_metadata(args, manifest, matrix)
    metadata.update(write_strategy_discovery(args, matrix, metadata))

    if args.discovery_only:
        if (
            not args.skip_discovery
            and metadata.get("strategy_discovery_status") != "pass"
            and not args.allow_discovery_failure
        ):
            raise SystemExit(
                "Strategy discovery failed; refusing discovery-only success. "
                f"status={metadata.get('strategy_discovery_status')}, "
                f"missing={metadata.get('strategy_discovery_missing_count')}"
            )
        print(f"Wrote strategy discovery to {args.discovery_output}")
        return

    if args.plan_only:
        planned = matrix.assign(
            status="planned",
            decision="NOT_RUN_PLAN_ONLY",
            export_mode=args.export_mode,
            artifact_mode="plan_only",
            is_backtest_result=False,
            plan_only_notice="Execution plan only; not a Freqtrade backtest result.",
        )
        planned = add_metadata_columns(planned, metadata)
        write_outputs(planned, pd.DataFrame(), args, metadata)
        print(f"Wrote plan-only matrix to {selected_output_paths(args)['output_md']}")
        return

    if (
        not args.skip_discovery
        and metadata.get("strategy_discovery_status") != "pass"
        and not args.allow_discovery_failure
    ):
        raise SystemExit(
            "Strategy discovery failed; refusing real backtest. "
            f"status={metadata.get('strategy_discovery_status')}, "
            f"missing={metadata.get('strategy_discovery_missing_count')}"
        )

    if metadata["input_git_worktree_dirty"] and not args.allow_dirty_execution:
        raise SystemExit(
            "Refusing to run real backtests from a dirty worktree. "
            "Commit/stash changes first, or pass --allow-dirty-execution."
        )

    rows: list[dict[str, Any]] = []
    trade_frames: list[pd.DataFrame] = []
    for _, matrix_row in matrix.iterrows():
        row, trades = run_backtest(matrix_row.to_dict(), args)
        rows.append(row)
        if not trades.empty:
            trade_frames.append(trades)

    summary = pd.DataFrame(rows)
    if not summary.empty:
        summary["artifact_mode"] = "backtest_result"
        summary["is_backtest_result"] = True
    summary = add_metadata_columns(summary, metadata)
    trades = pd.concat(trade_frames, ignore_index=True, sort=False) if trade_frames else pd.DataFrame()
    write_outputs(summary, trades, args, metadata)
    print(f"Wrote backtest summary to {selected_output_paths(args)['output_md']}")


if __name__ == "__main__":
    main()
