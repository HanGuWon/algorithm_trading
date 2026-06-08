from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd


EXIT_LABELS = {
    "Hold24h": "hold_24h",
    "Hold72h": "hold_72h",
    "Hold120h": "hold_120h",
    "ZscoreRevert72h": "zscore_revert_or_72h",
    "RsiRevert72h": "rsi_revert_or_72h",
    "BbMidReclaim72h": "bb_mid_reclaim_or_72h",
}

REPRESENTATIVE_CLASSES = [
    "ImmediateFlushResearchRFC008Hold72h",
    "ImmediateFlushResearchRFC008ZscoreRevert72h",
    "ImmediateFlushResearchRFC008RsiRevert72h",
    "ImmediateFlushResearchRFC008BbMidReclaim72h",
]

ENTRY_MASK_COVERAGE_CLASSES = [
    "ImmediateFlushResearchRFC008Hold72h",
    "ImmediateFlushResearchRFC019Hold72h",
    "ImmediateFlushResearchRFC001Hold72h",
    "ImmediateFlushResearchRFC025Hold72h",
    "ImmediateFlushResearchRFC002Hold72h",
    "ImmediateFlushResearchRFC009Hold72h",
    "ImmediateFlushResearchRFC015Hold72h",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run or plan Freqtrade lookahead/recursive audits for immediate-flush research classes."
    )
    parser.add_argument(
        "--manifest",
        default="docs/validation/analysis/major_11_immediate_flush_canonical_manifest.csv",
    )
    parser.add_argument("--config", default="user_data/configs/volatility_rotation_mr_backtest_major_11.json")
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--timerange", default="20200109-20260603")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--output-csv",
        default="docs/validation/analysis/major_11_immediate_flush_research_bias_audit.csv",
    )
    parser.add_argument(
        "--output-md",
        default="docs/validation/analysis/major_11_immediate_flush_research_bias_audit.md",
    )
    parser.add_argument(
        "--lookahead-prefix",
        default="docs/validation/analysis/major_11_immediate_flush_lookahead",
    )
    parser.add_argument(
        "--recursive-prefix",
        default="docs/validation/analysis/major_11_immediate_flush_recursive",
    )
    parser.add_argument("--logs-dir", default="docs/validation/logs/major_11_immediate_flush_bias_audit")
    parser.add_argument("--strategy-classes", nargs="+", default=[])
    parser.add_argument("--strict-all", action="store_true", help="Audit all manifest x exit-mode strategy classes.")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--write-placeholder-results", action="store_true")
    parser.add_argument("--max-recursive-variance-pct", type=float, default=0.0)
    return parser.parse_args()


def strategy_class_name(candidate_id: str, exit_label: str) -> str:
    safe_id = (
        candidate_id.replace("_original", "")
        .replace("_drop_breakout_block", "NoBreakout")
        .replace("_", "")
    )
    return f"ImmediateFlushResearch{safe_id}{exit_label}"


def subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    startup_path = str((Path(__file__).resolve().parent / "python_startup").resolve())
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = startup_path if not existing else startup_path + os.pathsep + existing
    return env


def all_manifest_classes(manifest: pd.DataFrame) -> list[str]:
    classes: list[str] = []
    for candidate_id in manifest["canonical_fixed_candidate_id"].astype(str):
        for exit_label in EXIT_LABELS:
            classes.append(strategy_class_name(candidate_id, exit_label))
    return classes


def select_strategy_classes(args: argparse.Namespace, manifest: pd.DataFrame) -> list[str]:
    all_classes = all_manifest_classes(manifest)
    if args.strategy_classes:
        selected = args.strategy_classes
    elif args.strict_all:
        selected = all_classes
    else:
        selected = list(dict.fromkeys(REPRESENTATIVE_CLASSES + ENTRY_MASK_COVERAGE_CLASSES))

    missing = sorted(set(selected) - set(all_classes))
    if missing:
        raise SystemExit(f"Selected strategy classes are not in the manifest matrix: {missing}")
    return selected


def result_path(prefix: str, check_type: str, strategy_class: str) -> Path:
    _ = check_type
    return Path(f"{prefix}_{strategy_class}.csv")


def command_for(args: argparse.Namespace, check_type: str, strategy_class: str, output_csv: Path) -> list[str]:
    if check_type == "lookahead":
        return [
            args.python,
            "-m",
            "freqtrade",
            "lookahead-analysis",
            "--config",
            args.config,
            "--datadir",
            args.datadir,
            "--strategy",
            strategy_class,
            "--strategy-path",
            args.strategy_path,
            "--timeframe",
            "5m",
            "--timerange",
            args.timerange,
            "--minimum-trade-amount",
            "1",
            "--targeted-trade-amount",
            "25",
            "--export",
            "none",
            "--lookahead-analysis-exportfilename",
            str(output_csv),
        ]

    return [
        args.python,
        "-m",
        "freqtrade",
        "recursive-analysis",
        "--config",
        args.config,
        "--datadir",
        args.datadir,
        "--strategy",
        strategy_class,
        "--strategy-path",
        args.strategy_path,
        "--timeframe",
        "5m",
        "--timerange",
        args.timerange,
        "--startup-candle",
        "1200",
        "1800",
        "2400",
    ]


def freqtrade_available(args: argparse.Namespace) -> bool:
    completed = subprocess.run(
        [args.python, "-m", "freqtrade", "--version"],
        capture_output=True,
        text=True,
        check=False,
        env=subprocess_env(),
    )
    return completed.returncode == 0


def write_placeholder(output_csv: Path, row: dict[str, Any]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(output_csv, index=False, lineterminator="\n")


def has_insufficient_signal_marker(text: str) -> bool:
    lowered = text.lower()
    markers = ("not enough", "minimum", "too few", "no trades", "no signals", "no entries")
    return any(marker in lowered for marker in markers)


def truthy_series(series: pd.Series) -> pd.Series:
    return series.fillna(False).astype(str).str.strip().str.lower().isin({"1", "true", "yes", "y"})


def numeric_sum(frame: pd.DataFrame, column: str) -> float:
    if column not in frame:
        return 0.0
    return float(pd.to_numeric(frame[column], errors="coerce").fillna(0.0).sum())


def classify_lookahead_result(row: dict[str, Any], completed: subprocess.CompletedProcess[str], log_text: str) -> dict[str, Any]:
    output_csv = Path(str(row["output_csv"]))
    result = {
        **row,
        "exit_code": completed.returncode,
        "has_bias": "",
        "biased_entry_signals": "",
        "biased_exit_signals": "",
        "recursive_max_variance_pct": "",
    }
    if completed.returncode != 0:
        status = "inconclusive_insufficient_signals" if has_insufficient_signal_marker(log_text) else "fail"
        decision = "LOOKAHEAD_INCONCLUSIVE" if status.startswith("inconclusive") else "LOOKAHEAD_FAILED"
        return {**result, "status": status, "decision": decision}
    if not output_csv.exists():
        return {**result, "status": "schema_fail", "decision": "LOOKAHEAD_EXPORT_MISSING"}

    try:
        frame = pd.read_csv(output_csv)
    except (OSError, pd.errors.ParserError) as exc:
        return {**result, "status": "schema_fail", "decision": f"LOOKAHEAD_EXPORT_PARSE_FAIL:{type(exc).__name__}"}

    known_columns = {"has_bias", "biased_entry_signals", "biased_exit_signals"}
    if not known_columns.intersection(frame.columns):
        return {**result, "status": "schema_fail", "decision": "LOOKAHEAD_EXPORT_SCHEMA_FAIL"}

    has_bias = bool(truthy_series(frame["has_bias"]).any()) if "has_bias" in frame else False
    biased_entry = numeric_sum(frame, "biased_entry_signals")
    biased_exit = numeric_sum(frame, "biased_exit_signals")
    status = "fail" if has_bias or biased_entry > 0 or biased_exit > 0 else "pass"
    decision = "LOOKAHEAD_BIAS_DETECTED" if status == "fail" else "LOOKAHEAD_CLEAN"
    return {
        **result,
        "status": status,
        "decision": decision,
        "has_bias": has_bias,
        "biased_entry_signals": biased_entry,
        "biased_exit_signals": biased_exit,
    }


def recursive_variances(log_text: str) -> list[float]:
    variances: list[float] = []
    for line in log_text.splitlines():
        lowered = line.lower()
        if "variance" not in lowered and "var %" not in lowered and "variance %" not in lowered:
            continue
        for value in re.findall(r"[-+]?\d+(?:\.\d+)?", line):
            variances.append(abs(float(value)))
    return variances


def classify_recursive_result(
    args: argparse.Namespace,
    row: dict[str, Any],
    completed: subprocess.CompletedProcess[str],
    log_text: str,
) -> dict[str, Any]:
    result = {
        **row,
        "exit_code": completed.returncode,
        "has_bias": "",
        "biased_entry_signals": "",
        "biased_exit_signals": "",
        "recursive_max_variance_pct": "",
    }
    if completed.returncode != 0:
        status = "inconclusive_insufficient_signals" if has_insufficient_signal_marker(log_text) else "fail"
        decision = "RECURSIVE_INCONCLUSIVE" if status.startswith("inconclusive") else "RECURSIVE_FAILED"
        return {**result, "status": status, "decision": decision}

    variances = recursive_variances(log_text)
    if not variances:
        return {**result, "status": "schema_fail", "decision": "RECURSIVE_VARIANCE_PARSE_FAIL"}

    max_variance = max(variances)
    status = "pass" if max_variance <= float(args.max_recursive_variance_pct) else "fail"
    decision = "RECURSIVE_CLEAN" if status == "pass" else "RECURSIVE_VARIANCE_DETECTED"
    return {
        **result,
        "status": status,
        "decision": decision,
        "recursive_max_variance_pct": max_variance,
    }


def run_check(args: argparse.Namespace, row: dict[str, Any]) -> dict[str, Any]:
    command = str(row["command"]).split("\t")
    log_path = Path(row["log"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, capture_output=True, text=True, check=False, env=subprocess_env())
    output = "$ " + " ".join(command) + "\n\n"
    output += (completed.stdout or "") + ("\n" if completed.stdout and completed.stderr else "") + (completed.stderr or "")
    log_path.write_text(output, encoding="utf-8", newline="\n")
    if row["check_type"] == "lookahead":
        result_row = classify_lookahead_result(row, completed, output)
    else:
        result_row = classify_recursive_result(args, row, completed, output)
    output_csv = Path(str(row["output_csv"]))
    if not output_csv.exists():
        write_placeholder(output_csv, result_row)
    return result_row


def build_plan(args: argparse.Namespace, selected_classes: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for strategy_class in selected_classes:
        for check_type, prefix in (
            ("lookahead", args.lookahead_prefix),
            ("recursive", args.recursive_prefix),
        ):
            output_csv = result_path(prefix, check_type, strategy_class)
            log_path = Path(args.logs_dir) / f"{check_type}_{strategy_class}.log"
            command = command_for(args, check_type, strategy_class, output_csv)
            rows.append(
                {
                    "strategy_class": strategy_class,
                    "check_type": check_type,
                    "status": "planned",
                    "decision": "NOT_RUN_PLAN_ONLY",
                    "exit_code": "",
                    "output_csv": str(output_csv),
                    "log": str(log_path),
                    "command": "\t".join(command),
                    "has_bias": "",
                    "biased_entry_signals": "",
                    "biased_exit_signals": "",
                    "recursive_max_variance_pct": "",
                }
            )
    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    try:
        return frame.to_markdown(index=False)
    except ImportError:
        return "```csv\n" + frame.to_csv(index=False).replace("\r\n", "\n").strip() + "\n```"


def write_outputs(args: argparse.Namespace, frame: pd.DataFrame, selected_classes: list[str], all_classes: list[str]) -> None:
    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_csv, index=False, lineterminator="\n")

    status_counts = frame["status"].value_counts().rename_axis("status").reset_index(name="checks")
    compact_columns = [
        "strategy_class",
        "check_type",
        "status",
        "decision",
        "has_bias",
        "biased_entry_signals",
        "biased_exit_signals",
        "recursive_max_variance_pct",
        "output_csv",
        "log",
    ]
    compact = frame[[column for column in compact_columns if column in frame.columns]].copy()
    lines = [
        "# Major 11 Immediate Flush Bias Audit",
        "",
        "> Research-only lookahead and recursive-analysis audit plan/results for the immediate-flush strategy matrix.",
        "",
        "## Scope",
        "",
        f"- Manifest: `{args.manifest}`",
        f"- Config: `{args.config}`",
        f"- Timerange: `{args.timerange}`",
        f"- Plan only: `{args.plan_only}`",
        f"- Strict all classes: `{args.strict_all}`",
        f"- Selected classes: `{len(selected_classes)}`",
        f"- Full manifest classes: `{len(all_classes)}`",
        f"- Checks: `{len(frame)}`",
        "",
        "## Status Counts",
        "",
        markdown_table(status_counts),
        "",
        "## Checks",
        "",
        markdown_table(compact),
        "",
    ]
    output_md.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> None:
    args = parse_args()
    manifest = pd.read_csv(args.manifest)
    all_classes = all_manifest_classes(manifest)
    selected_classes = select_strategy_classes(args, manifest)
    plan = build_plan(args, selected_classes)

    if args.plan_only:
        if args.write_placeholder_results:
            for row in plan.to_dict("records"):
                write_placeholder(Path(row["output_csv"]), row)
        write_outputs(args, plan, selected_classes, all_classes)
        print(f"Wrote bias-audit plan to {args.output_md}")
        return

    if not freqtrade_available(args):
        unavailable = plan.assign(status="fail", decision="FREQTRADE_UNAVAILABLE", exit_code="")
        write_outputs(args, unavailable, selected_classes, all_classes)
        print(f"Wrote bias-audit unavailable result to {args.output_md}")
        return

    rows: list[dict[str, Any]] = []
    for row in plan.to_dict("records"):
        rows.append(run_check(args, {**row, "decision": "EXECUTED"}))
    result = pd.DataFrame(rows)
    write_outputs(args, result, selected_classes, all_classes)
    print(f"Wrote bias-audit result to {args.output_md}")


if __name__ == "__main__":
    main()
