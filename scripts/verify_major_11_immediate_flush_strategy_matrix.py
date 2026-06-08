from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from run_major_11_immediate_flush_research_backtest import EXIT_LABELS, build_matrix, load_manifest


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
    parser = argparse.ArgumentParser(description="Verify the Major 11 immediate-flush strategy class matrix.")
    parser.add_argument(
        "--manifest",
        default="docs/validation/analysis/major_11_immediate_flush_canonical_manifest.csv",
    )
    parser.add_argument(
        "--strategy-file",
        default="user_data/strategies/VolatilityRotationMRImmediateFlushResearch.py",
    )
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--expected-manifest-rows", type=int, default=7)
    parser.add_argument("--require-runtime", action="store_true")
    parser.add_argument(
        "--output-csv",
        default="docs/validation/analysis/major_11_immediate_flush_strategy_matrix_verification.csv",
    )
    parser.add_argument(
        "--output-md",
        default="docs/validation/analysis/major_11_immediate_flush_strategy_matrix_verification.md",
    )
    parser.add_argument("--skip-freqtrade-discovery", action="store_true")
    return parser.parse_args()


def check_row(check: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"check": check, "status": status, "detail": detail, **extra}


def expected_matrix(args: argparse.Namespace) -> tuple[pd.DataFrame, list[str]]:
    manifest = load_manifest(Path(args.manifest), [])
    matrix = build_matrix(manifest, list(EXIT_LABELS), ["base"], 0)
    classes = sorted(matrix["strategy_class"].astype(str).unique())
    return matrix, classes


def static_strategy_file_checks(strategy_file: Path) -> list[dict[str, Any]]:
    text = strategy_file.read_text(encoding="utf-8")
    rows = []
    fallback_guard = all(
        marker in text
        for marker in (
            "ALLOW_DEFAULT_CANDIDATES = False",
            "raise FileNotFoundError",
            "raise ValueError",
        )
    )
    rows.append(
        check_row(
            "manifest_fallback_guard",
            "pass" if fallback_guard else "fail",
            "Manifest fallback is disabled by default and missing/empty manifest paths raise explicit errors.",
        )
    )

    callback_guard = all(
        marker in text
        for marker in (
            "fixed_leverage = 1.0",
            "def leverage(",
            "def custom_stake_amount(",
            "return proposed_stake",
        )
    )
    rows.append(
        check_row(
            "stake_leverage_callbacks_fixed",
            "pass" if callback_guard else "fail",
            "Research strategy fixes leverage to 1.0 and returns proposed_stake.",
        )
    )
    return rows


def import_strategy_module(strategy_file: Path, strategy_path: Path) -> tuple[str, str, list[str]]:
    strategy_path_text = str(strategy_path.resolve())
    if strategy_path_text not in sys.path:
        sys.path.insert(0, strategy_path_text)
    spec = importlib.util.spec_from_file_location("immediate_flush_strategy_verify", strategy_file)
    if spec is None or spec.loader is None:
        return "fail", f"Unable to create import spec for {strategy_file}", []

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        return "unavailable", f"Strategy import dependency is unavailable: {exc}", []
    except Exception as exc:  # noqa: BLE001 - verification report should preserve loader errors.
        return "fail", f"Strategy import failed: {type(exc).__name__}: {exc}", []

    discovered = sorted(
        name
        for name, value in vars(module).items()
        if name.startswith("ImmediateFlushResearchRFC") and isinstance(value, type)
    )
    return "pass", "Strategy module imported successfully.", discovered


def run_freqtrade_discovery(args: argparse.Namespace, expected_classes: list[str]) -> dict[str, Any]:
    if args.skip_freqtrade_discovery:
        return check_row("freqtrade_list_strategies", "skipped", "Skipped by --skip-freqtrade-discovery.")

    command = [
        args.python,
        "-m",
        "freqtrade",
        "list-strategies",
        "--strategy-path",
        args.strategy_path,
        "--recursive-strategy-search",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    output = (completed.stdout or "") + ("\n" if completed.stdout and completed.stderr else "") + (completed.stderr or "")
    if completed.returncode != 0 and "No module named freqtrade" in output:
        return check_row(
            "freqtrade_list_strategies",
            "unavailable",
            "Freqtrade is not installed in this Python environment.",
            command=" ".join(command),
        )
    missing = [class_name for class_name in expected_classes if class_name not in output]
    status = "pass" if completed.returncode == 0 and not missing else "fail"
    return check_row(
        "freqtrade_list_strategies",
        status,
        f"exit_code={completed.returncode}; missing_expected_classes={len(missing)}",
        command=" ".join(command),
        missing_classes=", ".join(missing),
    )


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    try:
        return frame.to_markdown(index=False)
    except ImportError:
        return "```csv\n" + frame.to_csv(index=False).replace("\r\n", "\n").strip() + "\n```"


def write_outputs(args: argparse.Namespace, frame: pd.DataFrame, expected_classes: list[str]) -> None:
    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_csv, index=False, lineterminator="\n")

    status_counts = frame["status"].value_counts().rename_axis("status").reset_index(name="checks")
    lines = [
        "# Major 11 Immediate Flush Strategy Matrix Verification",
        "",
        "> Loader/discovery readiness checks for the generated immediate-flush research strategy classes.",
        "",
        "## Scope",
        "",
        f"- Manifest: `{args.manifest}`",
        f"- Strategy file: `{args.strategy_file}`",
        f"- Strategy path: `{args.strategy_path}`",
        f"- Expected classes: `{len(expected_classes)}`",
        "",
        "## Status Counts",
        "",
        markdown_table(status_counts),
        "",
        "## Checks",
        "",
        markdown_table(frame),
        "",
    ]
    output_md.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> None:
    args = parse_args()
    matrix, expected_classes = expected_matrix(args)
    manifest_rows = int(matrix["canonical_fixed_candidate_id"].nunique())
    rows: list[dict[str, Any]] = [
        check_row(
            "manifest_row_count",
            "pass" if manifest_rows == args.expected_manifest_rows else "fail",
            f"manifest_rows={manifest_rows}; expected={args.expected_manifest_rows}",
        ),
        check_row(
            "expected_class_count",
            "pass" if len(expected_classes) == args.expected_manifest_rows * len(EXIT_LABELS) else "fail",
            f"expected_classes={len(expected_classes)}",
        ),
        check_row(
            "unique_strategy_class_names",
            "pass" if len(expected_classes) == len(set(expected_classes)) else "fail",
            f"unique_classes={len(set(expected_classes))}; total_classes={len(expected_classes)}",
        ),
    ]

    expected_set = set(expected_classes)
    missing_representative = sorted(set(REPRESENTATIVE_CLASSES) - expected_set)
    rows.append(
        check_row(
            "representative_exit_mode_classes_present",
            "pass" if not missing_representative else "fail",
            "All representative exit-mode smoke classes are present."
            if not missing_representative
            else f"Missing: {', '.join(missing_representative)}",
        )
    )

    missing_entry = sorted(set(ENTRY_MASK_COVERAGE_CLASSES) - expected_set)
    rows.append(
        check_row(
            "entry_mask_coverage_classes_present",
            "pass" if not missing_entry else "fail",
            "All entry-mask coverage classes are present." if not missing_entry else f"Missing: {', '.join(missing_entry)}",
        )
    )

    strategy_file = Path(args.strategy_file)
    rows.extend(static_strategy_file_checks(strategy_file))
    import_status, import_detail, imported_classes = import_strategy_module(strategy_file, Path(args.strategy_path))
    missing_imported = sorted(expected_set - set(imported_classes)) if imported_classes else expected_classes
    rows.append(
        check_row(
            "strategy_module_import",
            import_status,
            import_detail,
            imported_class_count=len(imported_classes),
            missing_imported_class_count=len(missing_imported),
        )
    )
    if import_status == "pass":
        rows.append(
            check_row(
                "imported_class_matrix_matches_expected",
                "pass" if not missing_imported else "fail",
                "Imported strategy module exposes all expected classes."
                if not missing_imported
                else f"Missing imported classes: {', '.join(missing_imported)}",
            )
        )

    rows.append(run_freqtrade_discovery(args, expected_classes))
    frame = pd.DataFrame(rows)
    write_outputs(args, frame, expected_classes)
    if args.require_runtime and not frame["status"].eq("pass").all():
        counts = frame["status"].value_counts().to_dict()
        raise SystemExit(f"Runtime verification did not fully pass: {counts}")
    print(f"Wrote strategy matrix verification to {args.output_md}")


if __name__ == "__main__":
    main()
