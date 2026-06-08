from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_INPUT = "docs/validation/analysis/major_11_flush_fixed_candidate_set.csv"
DEFAULT_OUTPUT_CSV = "docs/validation/analysis/major_11_immediate_flush_canonical_manifest.csv"
DEFAULT_OUTPUT_MD = "docs/validation/analysis/major_11_immediate_flush_canonical_manifest.md"

MANIFEST_COLUMNS = [
    "canonical_fixed_candidate_id",
    "alias_fixed_candidate_ids",
    "source_candidate_ids",
    "signal_set_hash",
    "price_z_threshold",
    "rsi_threshold",
    "vol_z_min",
    "bb_width_min",
    "use_weak_trend",
    "use_breakout_block",
    "require_close_below_bb",
    "signals",
    "independent_clusters_72h",
    "active_pairs",
    "active_years",
    "cluster_excess_72h_median",
    "cluster_excess_72h_median_ci_low",
    "validation_excess_72h_median",
    "validation_excess_72h_median_ci_low",
    "net_excess_72h_median_20bps",
    "diagnostic_decision",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the canonical Major 11 immediate-flush manifest from fixed-candidate diagnostics."
    )
    parser.add_argument("--input-csv", default=DEFAULT_INPUT)
    parser.add_argument("--output-csv", default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--output-md", default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def safe_float(value: Any) -> float:
    try:
        if pd.isna(value):
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def add_canonical_columns(summary: pd.DataFrame) -> pd.DataFrame:
    if {
        "canonical_fixed_candidate_id",
        "is_duplicate_signal_set",
        "alias_fixed_candidate_ids",
    }.issubset(summary.columns):
        return summary

    summary = summary.copy()
    canonical_by_hash: dict[str, str] = {}
    aliases_by_hash: dict[str, str] = {}
    for signal_hash, group in summary.groupby("signal_set_hash", dropna=False):
        ordered = group.assign(
            _canonical_action_rank=(
                group["fixed_action"].astype(str) != "KEEP_ORIGINAL_IMMEDIATE_FLUSH"
            ).astype(int),
            _canonical_excess_rank=-pd.to_numeric(group["cluster_excess_72h_median"], errors="coerce").fillna(
                float("-inf")
            ),
            _canonical_id_rank=group["fixed_candidate_id"].astype(str),
        ).sort_values(
            ["_canonical_action_rank", "_canonical_excess_rank", "_canonical_id_rank"],
            ascending=[True, True, True],
        )
        canonical_id = str(ordered.iloc[0]["fixed_candidate_id"])
        canonical_by_hash[str(signal_hash)] = canonical_id
        aliases_by_hash[str(signal_hash)] = ",".join(sorted(group["fixed_candidate_id"].astype(str)))

    summary["canonical_fixed_candidate_id"] = summary["signal_set_hash"].astype(str).map(canonical_by_hash)
    summary["is_duplicate_signal_set"] = (
        summary["fixed_candidate_id"].astype(str) != summary["canonical_fixed_candidate_id"].astype(str)
    )
    summary["duplicate_of_fixed_candidate_id"] = np.where(
        summary["is_duplicate_signal_set"],
        summary["canonical_fixed_candidate_id"],
        "",
    )
    summary["alias_fixed_candidate_ids"] = summary["signal_set_hash"].astype(str).map(aliases_by_hash)
    summary["unique_signal_set_count"] = int(summary["signal_set_hash"].nunique(dropna=False))
    return summary


def validate_input(summary: pd.DataFrame) -> None:
    required = {
        "fixed_candidate_id",
        "source_candidate_id",
        "fixed_action",
        "signal_set_hash",
        "cluster_excess_72h_median",
    } | set(MANIFEST_COLUMNS) - {"canonical_fixed_candidate_id", "alias_fixed_candidate_ids", "source_candidate_ids"}
    missing = required - set(summary.columns)
    if missing:
        raise ValueError(f"Fixed-candidate summary missing required columns: {sorted(missing)}")


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    columns = [str(column) for column in frame.columns]
    rows = [
        [
            ""
            if pd.isna(value)
            else f"{value:.4f}"
            if isinstance(value, (float, np.floating))
            else str(value)
            for value in row
        ]
        for row in frame.itertuples(index=False, name=None)
    ]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def build_manifest(summary: pd.DataFrame) -> pd.DataFrame:
    summary = add_canonical_columns(summary)
    validate_input(summary)

    source_ids = (
        summary.groupby("signal_set_hash")["source_candidate_id"]
        .apply(lambda values: ",".join(sorted(set(values.astype(str)))))
        .rename("source_candidate_ids")
        .reset_index()
    )

    canonical = summary[~summary["is_duplicate_signal_set"].map(as_bool)].copy()
    canonical = canonical.merge(source_ids, on="signal_set_hash", how="left")
    canonical["canonical_fixed_candidate_id"] = canonical["fixed_candidate_id"].astype(str)
    canonical = canonical[MANIFEST_COLUMNS]
    canonical = canonical.sort_values(
        ["diagnostic_decision", "cluster_excess_72h_median", "canonical_fixed_candidate_id"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    return canonical


def markdown_report(manifest: pd.DataFrame, input_csv: str) -> str:
    duplicate_aliases = int((manifest["alias_fixed_candidate_ids"].astype(str).str.contains(",")).sum())
    active_optional_gates = {
        "use_weak_trend": int(manifest["use_weak_trend"].map(as_bool).sum()),
        "use_breakout_block": int(manifest["use_breakout_block"].map(as_bool).sum()),
        "require_close_below_bb": int(manifest["require_close_below_bb"].map(as_bool).sum()),
    }
    compact_columns = [
        "canonical_fixed_candidate_id",
        "alias_fixed_candidate_ids",
        "source_candidate_ids",
        "price_z_threshold",
        "rsi_threshold",
        "vol_z_min",
        "bb_width_min",
        "signals",
        "independent_clusters_72h",
        "active_pairs",
        "active_years",
        "cluster_excess_72h_median",
        "validation_excess_72h_median",
        "net_excess_72h_median_20bps",
        "diagnostic_decision",
    ]
    return "\n".join(
        [
            "# Major 11 Immediate Flush Canonical Manifest",
            "",
            "> Research-only manifest for the next Freqtrade backtest layer. This is not a dry-run or live-trading approval.",
            "",
            "## Scope",
            "",
            f"- Source: `{input_csv}`",
            f"- Canonical signal sets: `{len(manifest)}`",
            f"- Canonical rows with aliases: `{duplicate_aliases}`",
            f"- Active optional gates: `{active_optional_gates}`",
            "",
            "## Canonical Entries",
            "",
            markdown_table(manifest[compact_columns]),
            "",
            "## Interpretation",
            "",
            "- Duplicate fixed-candidate labels are represented as aliases on one canonical row.",
            "- The current canonical set is an immediate extreme-flush research set; optional trend, breakout, and lower-band gates should remain disabled unless this manifest changes.",
            "- A downstream portfolio backtest should iterate these canonical rows, not every row in the fixed-candidate CSV.",
            "",
        ]
    )


def main() -> None:
    args = parse_args()
    input_csv = Path(args.input_csv)
    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)

    manifest = build_manifest(pd.read_csv(input_csv))
    for path in (output_csv, output_md):
        path.parent.mkdir(parents=True, exist_ok=True)

    manifest.to_csv(output_csv, index=False, float_format="%.6g", lineterminator="\n")
    output_md.write_text(markdown_report(manifest, args.input_csv), encoding="utf-8", newline="\n")

    print(f"Wrote canonical manifest CSV to {output_csv}")
    print(f"Wrote canonical manifest Markdown to {output_md}")
    print(f"Canonical signal sets: {len(manifest)}")


if __name__ == "__main__":
    main()
