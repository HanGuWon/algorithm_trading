from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_STRATEGIES = [
    "VolatilityRotationMRFlushReboundLongOnly",
    "VolatilityRotationMRDelayedConfirmLongOnly",
]

STATIC_FILES = [
    Path("user_data/strategies/VolatilityRotationMR.py"),
    Path("user_data/strategies/VolatilityRotationMRCandidates.py"),
]

WHOLE_FRAME_METHOD_PATTERN = r"\.(max|min|mean|quantile|median|std|var|rank|idxmax|idxmin|nlargest|nsmallest)\s*\("
NP_WHOLE_FRAME_PATTERN = r"\bnp\.(nanmax|nanmin|nanmean|nanmedian|nanstd|nanvar)\s*\("
SAFE_WINDOW_CONTEXTS = (".rolling(", ".groupby(", ".expanding(", ".ewm(")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run major-11 lookahead, recursive, and static leakage audits.")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--config", default="user_data/configs/volatility_rotation_mr_backtest_major_11.json")
    parser.add_argument("--lookahead-config-overlay", default="user_data/configs/volatility_rotation_mr_analysis_market.json")
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--strategies", nargs="+", default=DEFAULT_STRATEGIES)
    parser.add_argument("--timerange", default="20200109-20260603")
    parser.add_argument("--logs-dir", default="docs/validation/logs/major_11_bias_audit")
    parser.add_argument("--output-md", default="docs/validation/analysis/major_11_bias_audit.md")
    parser.add_argument("--output-csv", default="docs/validation/analysis/major_11_bias_audit.csv")
    parser.add_argument("--skip-freqtrade", action="store_true")
    parser.add_argument("--reuse-freqtrade-results", action="store_true")
    return parser.parse_args()


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


def line_numbered_matches(path: Path, pattern: str) -> list[str]:
    regex = re.compile(pattern)
    matches: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if regex.search(line):
            matches.append(f"{path.as_posix()}:{number}: {line.strip()}")
    return matches


def static_audit() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    missing_files = [path.as_posix() for path in STATIC_FILES if not path.exists()]
    files = [path for path in STATIC_FILES if path.exists()]

    negative_shifts: list[str] = []
    whole_frame_stats: list[str] = []
    iloc_last: list[str] = []
    informative_merges: list[str] = []
    groupby_transform: list[str] = []

    rows.append(
        {
            "check": "static_strategy_files_present",
            "target": "strategy_files",
            "status": "pass" if not missing_files else "fail",
            "detail": "All expected strategy files are present." if not missing_files else "\n".join(missing_files),
        }
    )

    for path in files:
        negative_shifts.extend(line_numbered_matches(path, r"\.shift\(\s*-\d+"))
        for match in line_numbered_matches(path, WHOLE_FRAME_METHOD_PATTERN):
            if not any(context in match for context in SAFE_WINDOW_CONTEXTS):
                whole_frame_stats.append(match)
        for match in line_numbered_matches(path, NP_WHOLE_FRAME_PATTERN):
            if not any(context in match for context in SAFE_WINDOW_CONTEXTS):
                whole_frame_stats.append(match)
        iloc_last.extend(line_numbered_matches(path, r"\.iloc\[\s*-1\s*\]"))
        informative_merges.extend(line_numbered_matches(path, r"merge_informative_pair\("))
        groupby_transform.extend(line_numbered_matches(path, r"\.groupby\(.*\.transform\("))

    rows.append(
        {
            "check": "static_negative_shift",
            "target": "strategy_files",
            "status": "pass" if not negative_shifts else "fail",
            "detail": "No negative shift usage found." if not negative_shifts else "\n".join(negative_shifts),
        }
    )
    rows.append(
        {
            "check": "static_whole_dataframe_stats",
            "target": "strategy_files",
            "status": "pass" if not whole_frame_stats else "review",
            "detail": "No unconstrained whole-dataframe statistic usage found in strategy files."
            if not whole_frame_stats
            else "\n".join(whole_frame_stats),
        }
    )
    rows.append(
        {
            "check": "static_iloc_last",
            "target": "strategy_files",
            "status": "info" if iloc_last else "pass",
            "detail": "iloc[-1] appears only in live/analyzed-candle helper paths; not in indicator generation."
            if iloc_last
            else "No iloc[-1] usage found.",
        }
    )
    rows.append(
        {
            "check": "static_informative_merge",
            "target": "strategy_files",
            "status": "pass" if informative_merges else "review",
            "detail": "merge_informative_pair is used for 1h informative data; Freqtrade shifts informative candles to avoid using unfinished HTF candles."
            if informative_merges
            else "No merge_informative_pair usage found.",
        }
    )
    rows.append(
        {
            "check": "static_rotation_ranking",
            "target": "strategy_files",
            "status": "pass" if not groupby_transform else "review",
            "detail": "No groupby().transform() ranking pattern found in strategy files."
            if not groupby_transform
            else "\n".join(groupby_transform),
        }
    )
    return rows


def classify_freqtrade_result(
    kind: str,
    strategy: str,
    completed: subprocess.CompletedProcess[str],
    log_path: Path,
    export_path: Path | None = None,
) -> dict[str, Any]:
    text = log_path.read_text(encoding="utf-8").lower()
    if completed.returncode != 0:
        status = "fail"
        detail = f"{kind} exited with code {completed.returncode}. See log."
    elif kind == "freqtrade_lookahead_analysis":
        if export_path is None or not export_path.exists():
            status = "fail"
            detail = "lookahead-analysis did not produce the expected CSV export; has_bias could not be verified."
        else:
            result = pd.read_csv(export_path)
            missing = {"has_bias"} - set(result.columns)
            if missing:
                status = "review"
                detail = f"lookahead export missing required columns: {sorted(missing)}"
            else:
                has_bias = result["has_bias"].astype(str).str.lower().eq("true").any()
                biased_signal_total = 0.0
                for column in ("biased_entry_signals", "biased_exit_signals"):
                    if column in result.columns:
                        biased_signal_total += float(pd.to_numeric(result[column], errors="coerce").fillna(0).sum())
                if has_bias or biased_signal_total > 0:
                    status = "fail"
                    detail = (
                        "lookahead-analysis reported has_bias=True or nonzero biased entry/exit signal counts."
                    )
                else:
                    status = "pass"
                    detail = "lookahead-analysis completed with has_bias=False and zero biased entry/exit signals."
    elif any(marker in text for marker in ("bias detected", "failed", "error")):
        status = "review"
        detail = f"{kind} completed but log contains review markers."
    else:
        status = "pass"
        detail = f"{kind} completed without obvious bias/error markers."
    return {
        "check": kind,
        "target": strategy,
        "status": status,
        "detail": detail,
        "log_path": log_path.as_posix(),
    }


def freqtrade_audit(args: argparse.Namespace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    logs_dir = Path(args.logs_dir)
    lookahead_config_args = ["--config", args.config]
    if args.lookahead_config_overlay and Path(args.lookahead_config_overlay).exists():
        lookahead_config_args.extend(["--config", args.lookahead_config_overlay])
    for strategy in args.strategies:
        safe_strategy = strategy.replace("/", "_")
        lookahead_csv = Path("docs/validation/analysis") / f"major_11_lookahead_{safe_strategy}.csv"
        lookahead_log = logs_dir / f"{safe_strategy}_lookahead.log"
        recursive_log = logs_dir / f"{safe_strategy}_recursive.log"

        if args.reuse_freqtrade_results:
            if lookahead_log.exists():
                reused = subprocess.CompletedProcess(args=[], returncode=0)
                row = classify_freqtrade_result(
                    "freqtrade_lookahead_analysis",
                    strategy,
                    reused,
                    lookahead_log,
                    lookahead_csv,
                )
            else:
                row = {
                    "check": "freqtrade_lookahead_analysis",
                    "target": strategy,
                    "status": "fail",
                    "detail": "No reusable lookahead log found.",
                    "log_path": lookahead_log.as_posix(),
                }
            row["export_path"] = lookahead_csv.as_posix()
            rows.append(row)

            if recursive_log.exists():
                rows.append(
                    classify_freqtrade_result(
                        "freqtrade_recursive_analysis",
                        strategy,
                        subprocess.CompletedProcess(args=[], returncode=0),
                        recursive_log,
                    )
                )
            else:
                rows.append(
                    {
                        "check": "freqtrade_recursive_analysis",
                        "target": strategy,
                        "status": "fail",
                        "detail": "No reusable recursive log found.",
                        "log_path": recursive_log.as_posix(),
                    }
                )
            continue

        lookahead_command = [
            args.python,
            "-m",
            "freqtrade",
            "lookahead-analysis",
            *lookahead_config_args,
            "--datadir",
            args.datadir,
            "--strategy",
            strategy,
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
            str(lookahead_csv),
        ]
        lookahead = run_command(lookahead_command, lookahead_log)
        row = classify_freqtrade_result(
            "freqtrade_lookahead_analysis",
            strategy,
            lookahead,
            lookahead_log,
            lookahead_csv,
        )
        row["export_path"] = lookahead_csv.as_posix()
        rows.append(row)

        recursive_command = [
            args.python,
            "-m",
            "freqtrade",
            "recursive-analysis",
            "--config",
            args.config,
            "--datadir",
            args.datadir,
            "--strategy",
            strategy,
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
        recursive = run_command(recursive_command, recursive_log)
        rows.append(classify_freqtrade_result("freqtrade_recursive_analysis", strategy, recursive, recursive_log))
    return rows


def markdown_report(frame: pd.DataFrame, args: argparse.Namespace) -> str:
    command_rows = frame[frame["check"].str.startswith("freqtrade_")].copy()
    static_rows = frame[~frame["check"].str.startswith("freqtrade_")].copy()
    lines = [
        "# Major 11 Bias Audit",
        "",
        "> Follow-up validation after the external review requested mandatory lookahead, recursive, and static leakage checks.",
        "",
        "## Scope",
        "",
        f"- Timerange: `{args.timerange}`",
        f"- Strategies: `{', '.join(args.strategies)}`",
        f"- Config: `{args.config}`",
        f"- Lookahead overlay: `{args.lookahead_config_overlay}`",
        f"- Data directory: `{args.datadir}`",
        "",
        "## Result Summary",
        "",
        frame[["check", "target", "status", "detail"]].to_markdown(index=False) if not frame.empty else "No rows produced.",
        "",
        "## Static Audit",
        "",
        static_rows[["check", "status", "detail"]].to_markdown(index=False) if not static_rows.empty else "No static rows.",
        "",
        "## Freqtrade Command Logs",
        "",
        command_rows[["check", "target", "status", "log_path", "export_path"]].to_markdown(index=False)
        if not command_rows.empty
        else "Freqtrade commands were skipped.",
        "",
        "## Interpretation",
        "",
        "- Passing static checks do not prove profitability; they only reduce the risk that the current backtest is contaminated by obvious future-data patterns.",
        "- `recursive-analysis` is included because indicator stability can differ between long historical backtests and live incremental operation.",
        "- Strategy promotion remains blocked until the raw signal event study and baseline comparisons show durable forward expectancy.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    rows = static_audit()
    if args.skip_freqtrade:
        rows.append(
            {
                "check": "freqtrade_runtime",
                "target": "all",
                "status": "skipped",
                "detail": "Freqtrade runtime checks skipped by --skip-freqtrade.",
            }
        )
    else:
        rows.extend(freqtrade_audit(args))

    frame = pd.DataFrame(rows)
    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_csv, index=False)
    output_md.write_text(markdown_report(frame, args), encoding="utf-8")
    print(frame[["check", "target", "status"]].to_markdown(index=False))
    print(f"Bias audit written to {output_md}")


if __name__ == "__main__":
    main()
