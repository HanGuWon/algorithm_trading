from __future__ import annotations

import argparse
import json
import py_compile
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from longonly_research_utils import (
    StrategyVariant,
    load_snapshot_pairs,
    make_timerange,
    parse_backtest_zip,
    run_backtest,
    snapshot_path,
    write_temp_config,
)


DEFAULT_ANCHORS = [
    "2022-01-01",
    "2022-07-01",
    "2023-01-01",
    "2023-07-01",
    "2024-01-01",
    "2024-07-01",
    "2025-01-01",
]

DEFAULT_CANDIDATES = [
    StrategyVariant(
        label="flush_rebound_long_only",
        strategy="VolatilityRotationMRFlushReboundLongOnly",
        config_path="user_data/configs/volatility_rotation_mr_backtest_top50_flush_rebound_longonly.json",
    ),
    StrategyVariant(
        label="delayed_confirm_long_only",
        strategy="VolatilityRotationMRDelayedConfirmLongOnly",
        config_path="user_data/configs/volatility_rotation_mr_backtest_top50_delayed_confirm_longonly.json",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the strict go/no-go validation gate for research candidates.")
    parser.add_argument("--anchors", nargs="+", default=DEFAULT_ANCHORS)
    parser.add_argument("--window-months", type=int, default=6)
    parser.add_argument("--snapshot-dir", default="user_data/pairs")
    parser.add_argument("--snapshot-top-n", type=int, default=50)
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--base-config", default="user_data/configs/volatility_rotation_mr_base.json")
    parser.add_argument("--pairs-file", default="user_data/pairs/binance_usdt_futures_snapshot_union_top50_2022-2025.json")
    parser.add_argument("--timeframes", nargs="+", default=["5m", "1h"])
    parser.add_argument("--download-data", action="store_true")
    parser.add_argument("--download-timerange", default="")
    parser.add_argument("--skip-static-checks", action="store_true")
    parser.add_argument("--skip-freqtrade-checks", action="store_true")
    parser.add_argument("--skip-backtests", action="store_true")
    parser.add_argument("--skip-bias", action="store_true")
    parser.add_argument("--output-md", default="docs/validation/strict_validation_gate.md")
    parser.add_argument("--output-csv", default="docs/validation/strict_validation_gate.csv")
    parser.add_argument("--logs-dir", default="docs/validation/logs/strict_validation")
    parser.add_argument("--backtest-dir", default="user_data/backtest_results/strict_validation")
    parser.add_argument("--db-url", default="sqlite:///user_data/tradesv3_volatility_rotation_mr_strict_validation.sqlite")
    parser.add_argument("--min-total-trades", type=int, default=150)
    parser.add_argument("--min-window-trades", type=int, default=20)
    parser.add_argument("--min-usable-windows", type=int, default=4)
    parser.add_argument("--latest-window-count", type=int, default=6)
    parser.add_argument("--min-latest-positive-windows", type=int, default=4)
    parser.add_argument("--max-drawdown-pct", type=float, default=12.0)
    parser.add_argument("--min-profit-factor", type=float, default=1.20)
    parser.add_argument("--max-month-profit-share", type=float, default=0.35)
    parser.add_argument("--max-pair-profit-share", type=float, default=0.20)
    parser.add_argument("--stress-fee-per-side", type=float, default=0.0007)
    parser.add_argument("--stress-slippage-per-side", type=float, default=0.0005)
    parser.add_argument(
        "--candidate",
        nargs=2,
        action="append",
        metavar=("LABEL", "STRATEGY_CLASS"),
        help="Override default candidates. Can be repeated.",
    )
    return parser.parse_args()


def candidates_from_args(args: argparse.Namespace) -> list[StrategyVariant]:
    if not args.candidate:
        return list(DEFAULT_CANDIDATES)
    return [StrategyVariant(label=label, strategy=strategy, config_path="") for label, strategy in args.candidate]


def run_command(command: list[str], log_path: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    output = (completed.stdout or "") + ("\n" if completed.stdout and completed.stderr else "") + (completed.stderr or "")
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(output, encoding="utf-8")
    if check and completed.returncode != 0:
        target = f" See {log_path}" if log_path else ""
        raise RuntimeError(f"Command failed with exit code {completed.returncode}: {' '.join(command)}.{target}")
    return completed


def run_static_checks() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    python_files = list(Path("scripts").glob("*.py")) + list(Path("user_data/strategies").glob("*.py"))
    for path in python_files:
        py_compile.compile(str(path), doraise=True)
    rows.append({"check": "python_compile", "status": "pass", "detail": f"{len(python_files)} files"})

    json_files = list(Path("user_data/configs").glob("*.json")) + list(Path("user_data/pairs").glob("*.json"))
    for path in json_files:
        json.loads(path.read_text(encoding="utf-8"))
    rows.append({"check": "json_parse", "status": "pass", "detail": f"{len(json_files)} files"})
    return pd.DataFrame(rows)


def run_freqtrade_checks(args: argparse.Namespace, candidates: list[StrategyVariant]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    config = candidates[0].config_path or str(args.base_config)
    commands = [
        ("list_strategies", [sys.executable, "-m", "freqtrade", "list-strategies", "--config", config]),
        ("show_config", [sys.executable, "-m", "freqtrade", "show-config", "--config", config]),
        ("test_pairlist", [sys.executable, "-m", "freqtrade", "test-pairlist", "--config", config, "--quote", "USDT", "--print-json"]),
    ]
    for label, command in commands:
        completed = run_command(command, log_path=Path(args.logs_dir) / f"{label}.log", check=False)
        rows.append(
            {
                "check": label,
                "status": "pass" if completed.returncode == 0 else "fail",
                "detail": f"exit_code={completed.returncode}",
            }
        )
    return pd.DataFrame(rows)


def default_download_timerange(args: argparse.Namespace) -> str:
    starts = [pd.Timestamp(anchor, tz="UTC") for anchor in args.anchors]
    if not starts:
        return ""
    first = min(starts) - pd.Timedelta(days=20)
    last = max(starts) + pd.DateOffset(months=args.window_months)
    return f"{first.strftime('%Y%m%d')}-{last.strftime('%Y%m%d')}"


def download_data(args: argparse.Namespace) -> pd.DataFrame:
    timerange = args.download_timerange or default_download_timerange(args)
    command = [
        sys.executable,
        "-m",
        "freqtrade",
        "download-data",
        "--config",
        args.base_config,
        "--trading-mode",
        "futures",
        "--timerange",
        timerange,
        "--pairs-file",
        args.pairs_file,
        "--prepend",
        "--timeframes",
        *args.timeframes,
    ]
    completed = run_command(command, log_path=Path(args.logs_dir) / "download_data.log", check=False)
    return pd.DataFrame(
        [
            {
                "check": "download_data",
                "status": "pass" if completed.returncode == 0 else "fail",
                "detail": f"timerange={timerange}; timeframes={','.join(args.timeframes)}; exit_code={completed.returncode}",
            }
        ]
    )


def stressed_profit(frame: pd.DataFrame, target_fee: float, slippage_per_side: float) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=float)
    extra_open_fee = (target_fee - frame["fee_open"].astype(float)).clip(lower=0.0)
    extra_close_fee = (target_fee - frame["fee_close"].astype(float)).clip(lower=0.0)
    open_cost = frame["open_rate"].astype(float) * frame["amount"].astype(float)
    close_cost = frame["close_rate"].astype(float) * frame["amount"].astype(float)
    extra_cost = (open_cost * extra_open_fee) + (close_cost * extra_close_fee)
    extra_cost += (open_cost + close_cost) * float(slippage_per_side)
    return frame["profit_abs"].astype(float) - extra_cost


def profit_factor(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    gross_profit = float(series[series > 0].sum())
    gross_loss = abs(float(series[series < 0].sum()))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def max_contribution_share(trades: pd.DataFrame, group_column: str) -> float:
    if trades.empty:
        return 0.0
    total = float(trades["stressed_profit_abs"].sum())
    if total <= 0:
        return 1.0
    grouped = trades.groupby(group_column)["stressed_profit_abs"].sum()
    return max(float(grouped.max()), 0.0) / total if not grouped.empty else 0.0


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    try:
        return frame.to_markdown(index=False)
    except ImportError:
        csv_text = frame.to_csv(index=False).replace("\r\n", "\n").strip()
        return "```csv\n" + csv_text + "\n```"


def run_validation_matrix(args: argparse.Namespace, candidates: list[StrategyVariant]) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    rows: list[dict[str, Any]] = []
    trades_by_variant: dict[str, list[pd.DataFrame]] = {candidate.label: [] for candidate in candidates}

    with tempfile.TemporaryDirectory(prefix="strict_validation_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        for anchor_text in args.anchors:
            anchor = pd.Timestamp(anchor_text, tz="UTC")
            snapshot = snapshot_path(Path(args.snapshot_dir), anchor_text, args.snapshot_top_n)
            if not snapshot.exists():
                for candidate in candidates:
                    rows.append(
                        {
                            "anchor": anchor_text,
                            "strategy_variant": candidate.label,
                            "strategy": candidate.strategy,
                            "status": "missing_snapshot",
                            "snapshot": snapshot.name,
                        }
                    )
                continue

            pair_count = len(load_snapshot_pairs(snapshot))
            timerange, start, end = make_timerange(anchor, args.window_months)
            _ = (start, end)
            for candidate in candidates:
                config_path = write_temp_config(
                    temp_dir=temp_dir,
                    base_config=Path(args.base_config),
                    snapshot=snapshot,
                    variant=candidate,
                    db_url=args.db_url,
                )
                zip_path = run_backtest(
                    python_executable=Path(sys.executable),
                    config_path=config_path,
                    strategy_path=Path(args.strategy_path),
                    timerange=timerange,
                    logs_dir=Path(args.logs_dir),
                    backtest_dir=Path(args.backtest_dir),
                    anchor_label=anchor_text,
                    variant=candidate,
                )
                strategy_data, trades = parse_backtest_zip(zip_path, candidate.strategy)
                adjusted = stressed_profit(trades, args.stress_fee_per_side, args.stress_slippage_per_side)
                if not trades.empty:
                    trades = trades.copy()
                    trades["anchor"] = anchor_text
                    trades["stressed_profit_abs"] = adjusted
                    trades_by_variant[candidate.label].append(trades)

                rows.append(
                    {
                        "anchor": anchor_text,
                        "window_label": f"{args.window_months}m",
                        "strategy_variant": candidate.label,
                        "strategy": candidate.strategy,
                        "status": "backtested",
                        "snapshot": snapshot.name,
                        "pair_count": pair_count,
                        "timerange": timerange,
                        "raw_trade_count": int(strategy_data.get("total_trades", 0)),
                        "profit_usdt": round(float(strategy_data.get("profit_total_abs", 0.0)), 3),
                        "stressed_profit_usdt": round(float(adjusted.sum()), 3) if not adjusted.empty else 0.0,
                        "avg_stressed_trade_usdt": round(float(adjusted.mean()), 3) if not adjusted.empty else 0.0,
                        "drawdown_pct": round(float(strategy_data.get("max_drawdown_account", 0.0)) * 100.0, 2),
                        "profit_factor_stressed": round(profit_factor(adjusted), 3),
                        "results_zip": zip_path.name,
                    }
                )

    combined_trades = {
        label: pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        for label, frames in trades_by_variant.items()
    }
    return pd.DataFrame(rows), combined_trades


def evaluate_candidate(args: argparse.Namespace, label: str, matrix: pd.DataFrame, trades: pd.DataFrame) -> dict[str, object]:
    subset = matrix[(matrix["strategy_variant"] == label) & (matrix["status"] == "backtested")].copy()
    subset = subset.sort_values("anchor")
    total_trades = int(subset["raw_trade_count"].sum()) if not subset.empty else 0
    usable_windows = int((subset["raw_trade_count"] >= args.min_window_trades).sum()) if not subset.empty else 0
    latest = subset.tail(args.latest_window_count)
    latest_positive = int((latest["stressed_profit_usdt"] > 0).sum()) if not latest.empty else 0
    max_drawdown = float(subset["drawdown_pct"].max()) if not subset.empty else 0.0
    stressed_total = float(trades["stressed_profit_abs"].sum()) if not trades.empty else 0.0
    stressed_average = float(trades["stressed_profit_abs"].mean()) if not trades.empty else 0.0
    stressed_pf = profit_factor(trades["stressed_profit_abs"]) if not trades.empty else 0.0
    month_share = max_contribution_share(trades, "month")
    pair_share = max_contribution_share(trades, "pair")

    checks = {
        "total_trades": total_trades >= args.min_total_trades,
        "usable_windows": usable_windows >= args.min_usable_windows,
        "latest_positive_windows": latest_positive >= args.min_latest_positive_windows,
        "max_drawdown_pct": max_drawdown <= args.max_drawdown_pct,
        "profit_factor": stressed_pf >= args.min_profit_factor,
        "avg_stressed_trade": stressed_average > 0,
        "month_concentration": month_share <= args.max_month_profit_share,
        "pair_concentration": pair_share <= args.max_pair_profit_share,
    }
    return {
        "strategy_variant": label,
        "decision": "PROMOTE_PENDING_BIAS" if all(checks.values()) else "PARK",
        "total_trades": total_trades,
        "usable_windows": usable_windows,
        "latest_positive_windows": latest_positive,
        "stressed_profit_usdt": round(stressed_total, 3),
        "avg_stressed_trade_usdt": round(stressed_average, 3),
        "max_drawdown_pct": round(max_drawdown, 2),
        "profit_factor_stressed": round(stressed_pf, 3),
        "max_month_profit_share": round(month_share, 3),
        "max_pair_profit_share": round(pair_share, 3),
        "failed_checks": ", ".join(name for name, passed in checks.items() if not passed),
    }


def run_bias_checks(args: argparse.Namespace, candidate: StrategyVariant, anchor_text: str) -> pd.DataFrame:
    snapshot = snapshot_path(Path(args.snapshot_dir), anchor_text, args.snapshot_top_n)
    if not snapshot.exists():
        return pd.DataFrame([{"strategy_variant": candidate.label, "check": "bias", "status": "missing_snapshot"}])

    timerange, _, _ = make_timerange(pd.Timestamp(anchor_text, tz="UTC"), args.window_months)
    pairs = load_snapshot_pairs(snapshot)
    recursive_pair = pairs[0] if pairs else ""

    with tempfile.TemporaryDirectory(prefix="strict_bias_") as temp_dir_str:
        config_path = write_temp_config(
            temp_dir=Path(temp_dir_str),
            base_config=Path(args.base_config),
            snapshot=snapshot,
            variant=candidate,
            db_url=args.db_url,
        )
        lookahead_log = Path(args.logs_dir) / f"{candidate.label}_lookahead.log"
        recursive_log = Path(args.logs_dir) / f"{candidate.label}_recursive.log"
        lookahead = run_command(
            [
                sys.executable,
                "-m",
                "freqtrade",
                "lookahead-analysis",
                "--config",
                str(config_path),
                "--strategy",
                candidate.strategy,
                "--strategy-path",
                args.strategy_path,
                "--timeframe",
                "5m",
                "--timeframe-detail",
                "1m",
                "--timerange",
                timerange,
            ],
            log_path=lookahead_log,
            check=False,
        )
        recursive_command = [
            sys.executable,
            "-m",
            "freqtrade",
            "recursive-analysis",
            "--config",
            str(config_path),
            "--strategy",
            candidate.strategy,
            "--strategy-path",
            args.strategy_path,
            "--timeframe",
            "5m",
            "--timerange",
            timerange,
            "--startup-candle",
            "1600",
            "2000",
            "2400",
        ]
        if recursive_pair:
            recursive_command += ["--pairs", recursive_pair]
        recursive = run_command(
            recursive_command,
            log_path=recursive_log,
            check=False,
        )

    def classify_bias_result(completed: subprocess.CompletedProcess[str], log_path: Path) -> str:
        if completed.returncode == 0:
            return "pass"
        output = log_path.read_text(encoding="utf-8").lower() if log_path.exists() else ""
        insufficient_markers = ("not enough", "minimum", "too few", "no trades", "no signals")
        if any(marker in output for marker in insufficient_markers):
            return "inconclusive_insufficient_signals"
        return "fail"

    return pd.DataFrame(
        [
            {
                "strategy_variant": candidate.label,
                "check": "lookahead_analysis",
                "status": classify_bias_result(lookahead, lookahead_log),
                "detail": f"exit_code={lookahead.returncode}",
            },
            {
                "strategy_variant": candidate.label,
                "check": "recursive_analysis",
                "status": classify_bias_result(recursive, recursive_log),
                "detail": f"exit_code={recursive.returncode}",
            },
        ]
    )


def write_report(
    args: argparse.Namespace,
    candidates: list[StrategyVariant],
    preflight: pd.DataFrame,
    matrix: pd.DataFrame,
    decisions: pd.DataFrame,
    bias: pd.DataFrame,
) -> None:
    output_md = Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    promoted = (
        decisions[decisions["decision"].astype(str).str.startswith("PROMOTE")]
        if "decision" in decisions.columns
        else pd.DataFrame()
    )
    acceptable_bias = {"pass", "inconclusive_insufficient_signals"}
    if promoted.empty:
        final_status = "PARK"
    elif args.skip_bias or bias.empty:
        final_status = "PROMOTE_PENDING_BIAS"
    elif set(bias["status"].astype(str)).issubset(acceptable_bias):
        final_status = "PROMOTE"
    else:
        final_status = "PARK_BIAS_FAILED"
    if args.skip_backtests:
        final_status = "NOT_RUN"

    lines = [
        "# Strict Validation Gate",
        "",
        f"- Final status: `{final_status}`",
        f"- Candidates: `{', '.join(candidate.strategy for candidate in candidates)}`",
        f"- Stress: fee `{args.stress_fee_per_side}` per side plus slippage `{args.stress_slippage_per_side}` per side",
        f"- Window: `{args.window_months}m` non-overlapping anchors",
        "",
        "## Gate Thresholds",
        "",
        markdown_table(
            pd.DataFrame(
            [
                {"gate": "total_trades", "threshold": args.min_total_trades},
                {"gate": "window_trades", "threshold": f">= {args.min_window_trades} in {args.min_usable_windows} windows"},
                {"gate": "latest_positive_windows", "threshold": f">= {args.min_latest_positive_windows} of latest {args.latest_window_count}"},
                {"gate": "max_drawdown_pct", "threshold": f"<= {args.max_drawdown_pct}"},
                {"gate": "profit_factor", "threshold": f">= {args.min_profit_factor}"},
                {"gate": "month_profit_share", "threshold": f"<= {args.max_month_profit_share}"},
                {"gate": "pair_profit_share", "threshold": f"<= {args.max_pair_profit_share}"},
            ]
            )
        ),
        "",
        "## Preflight",
        "",
        markdown_table(preflight) if not preflight.empty else "No preflight checks were run.",
        "",
        "## Matrix",
        "",
        markdown_table(matrix) if not matrix.empty else "Backtests were not run.",
        "",
        "## Decisions",
        "",
        markdown_table(decisions) if not decisions.empty else "No candidate decisions were produced.",
        "",
        "## Bias Checks",
        "",
        markdown_table(bias) if not bias.empty else "Bias checks were not run because no candidate passed the preliminary gate or `--skip-bias` was used.",
        "",
        "## Candidate Definitions",
        "",
        markdown_table(pd.DataFrame([asdict(candidate) for candidate in candidates])),
        "",
    ]
    output_md.write_text("\n".join(lines), encoding="utf-8")

    if args.output_csv:
        output_csv = Path(args.output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        frames = []
        if not decisions.empty:
            frames.append(decisions.assign(section="decisions"))
        if not matrix.empty:
            frames.append(matrix.assign(section="matrix"))
        if not preflight.empty:
            frames.append(preflight.assign(section="preflight"))
        if not bias.empty:
            frames.append(bias.assign(section="bias"))
        if frames:
            pd.concat(frames, ignore_index=True, sort=False).to_csv(output_csv, index=False)


def main() -> None:
    args = parse_args()
    candidates = candidates_from_args(args)
    preflight_frames: list[pd.DataFrame] = []

    if not args.skip_static_checks:
        preflight_frames.append(run_static_checks())
    if not args.skip_freqtrade_checks:
        preflight_frames.append(run_freqtrade_checks(args, candidates))
    if args.download_data:
        preflight_frames.append(download_data(args))

    matrix = pd.DataFrame()
    trades_by_variant: dict[str, pd.DataFrame] = {}
    if not args.skip_backtests:
        matrix, trades_by_variant = run_validation_matrix(args, candidates)

    decision_rows = [
        evaluate_candidate(args, candidate.label, matrix, trades_by_variant.get(candidate.label, pd.DataFrame()))
        for candidate in candidates
        if not matrix.empty
    ]
    decisions = pd.DataFrame(decision_rows)

    bias_frames: list[pd.DataFrame] = []
    if not args.skip_bias and not decisions.empty:
        first_anchor = args.anchors[0]
        for candidate in candidates:
            row = decisions[decisions["strategy_variant"] == candidate.label]
            if not row.empty and str(row.iloc[0]["decision"]).startswith("PROMOTE"):
                bias_frames.append(run_bias_checks(args, candidate, first_anchor))

    preflight = pd.concat(preflight_frames, ignore_index=True, sort=False) if preflight_frames else pd.DataFrame()
    bias = pd.concat(bias_frames, ignore_index=True, sort=False) if bias_frames else pd.DataFrame()
    write_report(args, candidates, preflight, matrix, decisions, bias)
    print(f"Wrote {args.output_md}")


if __name__ == "__main__":
    main()
