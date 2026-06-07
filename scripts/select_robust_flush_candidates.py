from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REQUIRED_SURFACE_COLUMNS = {
    "decision",
    "is_duplicate_signal_set",
    "passes_train",
    "passes_validation",
    "signal_set_hash",
    "cell_id",
}

MANIFEST_COLUMNS = [
    "candidate_id",
    "selection_bucket",
    "selection_buckets",
    "selection_rank",
    "cell_id",
    "signal_set_hash",
    "price_z_threshold",
    "rsi_threshold",
    "vol_z_min",
    "bb_width_min",
    "use_weak_trend",
    "use_breakout_block",
    "require_close_below_bb",
    "simplicity_score",
    "signals",
    "independent_clusters_72h",
    "cluster_excess_24h_median",
    "cluster_excess_72h_median",
    "cluster_excess_24h_p25",
    "cluster_excess_72h_p25",
    "train_excess_72h_median",
    "validation_excess_72h_median",
    "positive_pairs_72h",
    "positive_years_72h",
    "top_pair_signal_share",
    "top_year_signal_share",
]

ORIGINAL_SEED = {
    "price_z_threshold": 2.8,
    "rsi_threshold": 18.0,
    "vol_z_min": 1.0,
    "bb_width_min": 0.02,
    "use_weak_trend": True,
    "use_breakout_block": True,
    "require_close_below_bb": True,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze robust major-11 flush surface candidates before baseline comparison.")
    parser.add_argument("--surface-csv", default="docs/validation/analysis/major_11_flush_threshold_surface.csv")
    parser.add_argument("--output-csv", default="docs/validation/analysis/major_11_robust_flush_candidate_manifest.csv")
    parser.add_argument("--output-md", default="docs/validation/analysis/major_11_robust_flush_candidate_manifest.md")
    parser.add_argument("--top-n-per-bucket", type=int, default=10)
    return parser.parse_args()


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def load_unique_robust_surface(path: Path) -> pd.DataFrame:
    surface = pd.read_csv(path)
    missing = REQUIRED_SURFACE_COLUMNS - set(surface.columns)
    if missing:
        raise ValueError(f"Surface CSV missing required columns: {sorted(missing)}")

    for column in ("is_duplicate_signal_set", "passes_train", "passes_validation"):
        surface[column] = surface[column].map(as_bool)

    filtered = surface[
        (surface["decision"] == "ROBUST_RESEARCH_CANDIDATE")
        & (~surface["is_duplicate_signal_set"])
        & (surface["passes_train"])
        & (surface["passes_validation"])
    ].copy()
    return add_simplicity_score(filtered)


def add_simplicity_score(surface: pd.DataFrame) -> pd.DataFrame:
    surface = surface.copy()
    bool_columns = ["use_weak_trend", "use_breakout_block", "require_close_below_bb"]
    for column in bool_columns:
        surface[column] = surface[column].map(as_bool)
    surface["simplicity_score"] = (
        surface[bool_columns].sum(axis=1).astype(int)
        + (pd.to_numeric(surface["vol_z_min"], errors="coerce").fillna(0) > 0).astype(int)
        + (pd.to_numeric(surface["bb_width_min"], errors="coerce").fillna(0) > 0).astype(int)
    )
    return surface


def sorted_bucket(surface: pd.DataFrame, bucket: str) -> pd.DataFrame:
    if bucket == "top_cluster_excess_72h":
        return surface.sort_values(
            ["cluster_excess_72h_median", "independent_clusters_72h", "signals", "cell_id"],
            ascending=[False, False, False, True],
        )
    if bucket == "top_cluster_excess_24h":
        return surface.sort_values(
            ["cluster_excess_24h_median", "independent_clusters_72h", "signals", "cell_id"],
            ascending=[False, False, False, True],
        )
    if bucket == "highest_density":
        return surface.sort_values(
            ["independent_clusters_72h", "signals", "cluster_excess_72h_median", "cell_id"],
            ascending=[False, False, False, True],
        )
    if bucket == "lowest_pair_concentration":
        return surface.sort_values(
            ["top_pair_signal_share", "cluster_excess_72h_median", "independent_clusters_72h", "cell_id"],
            ascending=[True, False, False, True],
        )
    if bucket == "lowest_year_concentration":
        return surface.sort_values(
            ["top_year_signal_share", "cluster_excess_72h_median", "independent_clusters_72h", "cell_id"],
            ascending=[True, False, False, True],
        )
    if bucket == "simplest_definition":
        return surface.sort_values(
            ["simplicity_score", "cluster_excess_72h_median", "independent_clusters_72h", "cell_id"],
            ascending=[True, False, False, True],
        )
    raise ValueError(f"Unsupported selection bucket: {bucket}")


def original_seed_nearest(surface: pd.DataFrame) -> pd.DataFrame:
    if surface.empty:
        return surface
    bool_penalty = sum(
        surface[column].map(as_bool).ne(expected).astype(float)
        for column, expected in ORIGINAL_SEED.items()
        if isinstance(expected, bool)
    )
    numeric_penalty = sum(
        (
            pd.to_numeric(surface[column], errors="coerce").astype(float) - float(expected)
        ).abs()
        for column, expected in ORIGINAL_SEED.items()
        if not isinstance(expected, bool)
    )
    ranked = surface.copy()
    ranked["_seed_distance"] = numeric_penalty + bool_penalty
    return ranked.sort_values(
        ["_seed_distance", "cluster_excess_72h_median", "independent_clusters_72h", "cell_id"],
        ascending=[True, False, False, True],
    ).head(1)


def freeze_manifest(surface: pd.DataFrame, top_n_per_bucket: int) -> pd.DataFrame:
    buckets = [
        "top_cluster_excess_72h",
        "top_cluster_excess_24h",
        "highest_density",
        "lowest_pair_concentration",
        "lowest_year_concentration",
        "simplest_definition",
    ]
    selected: dict[str, dict[str, Any]] = {}

    def remember(row: pd.Series, bucket: str, rank: int) -> None:
        key = str(row["signal_set_hash"])
        payload = selected.setdefault(key, row.to_dict())
        buckets_for_row = str(payload.get("selection_buckets", "")).split(";") if payload.get("selection_buckets") else []
        if bucket not in buckets_for_row:
            buckets_for_row.append(bucket)
        payload["selection_buckets"] = ";".join(buckets_for_row)
        payload.setdefault("selection_bucket", bucket)
        payload["selection_rank"] = min(int(payload.get("selection_rank", rank)), rank)

    for bucket in buckets:
        ranked = sorted_bucket(surface, bucket).head(top_n_per_bucket)
        for rank, (_, row) in enumerate(ranked.iterrows(), start=1):
            remember(row, bucket, rank)

    nearest = original_seed_nearest(surface)
    for _, row in nearest.iterrows():
        remember(row, "original_seed_nearest", 1)

    manifest = pd.DataFrame(selected.values())
    if manifest.empty:
        return pd.DataFrame(columns=MANIFEST_COLUMNS)
    manifest = manifest.sort_values(["selection_rank", "cluster_excess_72h_median", "cell_id"], ascending=[True, False, True])
    manifest.insert(0, "candidate_id", [f"RFC{i:03d}" for i in range(1, len(manifest) + 1)])
    for column in MANIFEST_COLUMNS:
        if column not in manifest:
            manifest[column] = np.nan
    return manifest[MANIFEST_COLUMNS]


def table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    return frame.to_markdown(index=False, floatfmt=".4f")


def markdown_report(manifest: pd.DataFrame, robust_count: int, args: argparse.Namespace) -> str:
    bucket_summary = (
        manifest.assign(selection_bucket=manifest["selection_buckets"].str.split(";"))
        .explode("selection_bucket")
        .groupby("selection_bucket", as_index=False)
        .agg(candidates=("candidate_id", "nunique"))
        .sort_values("selection_bucket")
    )
    columns = [
        "candidate_id",
        "selection_buckets",
        "cell_id",
        "signals",
        "independent_clusters_72h",
        "cluster_excess_24h_median",
        "cluster_excess_72h_median",
        "train_excess_72h_median",
        "validation_excess_72h_median",
        "positive_pairs_72h",
        "positive_years_72h",
        "top_pair_signal_share",
        "top_year_signal_share",
        "price_z_threshold",
        "rsi_threshold",
        "vol_z_min",
        "bb_width_min",
        "use_weak_trend",
        "use_breakout_block",
        "require_close_below_bb",
        "simplicity_score",
        "signal_set_hash",
    ]
    lines = [
        "# Major 11 Robust Flush Candidate Manifest",
        "",
        "> Frozen candidate-selection manifest for baseline comparison. Do not revise this list after inspecting baseline-comparison results.",
        "",
        "## Scope",
        "",
        f"- Source surface: `{args.surface_csv}`",
        f"- Robust unique candidates available before selection: `{robust_count}`",
        f"- Top N per bucket: `{args.top_n_per_bucket}`",
        f"- Frozen manifest candidates: `{len(manifest)}`",
        "",
        "## Selection Rule",
        "",
        "- Filter to `ROBUST_RESEARCH_CANDIDATE` rows.",
        "- Exclude duplicate signal sets.",
        "- Require both train and validation split checks to pass.",
        "- Select fixed top-N buckets before baseline comparison.",
        "- Deduplicate by `signal_set_hash`.",
        "- Include the nearest robust row to the original flush-rebound seed, if present.",
        "",
        "## Bucket Summary",
        "",
        table(bucket_summary),
        "",
        "## Manifest",
        "",
        table(manifest[columns]),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    surface = load_unique_robust_surface(Path(args.surface_csv))
    manifest = freeze_manifest(surface, args.top_n_per_bucket)

    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(output_csv, index=False, float_format="%.6g")
    output_md.write_text(markdown_report(manifest, len(surface), args), encoding="utf-8")
    print(f"Robust unique candidates: {len(surface)}")
    print(f"Frozen manifest candidates: {len(manifest)}")
    print(f"Candidate manifest written to {output_md}")


if __name__ == "__main__":
    main()
