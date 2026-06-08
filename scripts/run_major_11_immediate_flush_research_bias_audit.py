from __future__ import annotations

import argparse
import os
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
            "--enable-protections",
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


def run_check(args: argparse.Namespace, row: dict[str, Any]) -> dict[str, Any]:
    _ = args
    command = str(row["command"]).split("\t")
    log_path = Path(row["log"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, capture_output=True, text=True, check=False, env=subprocess_env())
    output = "$ " + " ".join(command) + "\n\n"
    output += (completed.stdout or "") + ("\n" if completed.stdout and completed.stderr else "") + (completed.stderr or "")
    log_path.write_text(output, encoding="utf-8", newline="\n")
    status = "pass" if completed.returncode == 0 else "fail"
    result_row = {**row, "status": status, "exit_code": completed.returncode}
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
    compact = frame[["strategy_class", "check_type", "status", "decision", "output_csv", "log"]].copy()
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
