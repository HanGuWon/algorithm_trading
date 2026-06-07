from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from compare_flush_surface_baselines import (
    bootstrap_median_ci,
    build_research_event_universe,
    candidate_mask,
    median,
    stable_seed,
    validation_cluster_values,
)
from event_study_flush_rebound import (
    attach_matched_null_controls,
    build_null_pool,
    load_pairs,
    load_strategy,
    parse_null_match,
    prepare_pair_frames,
)
from scan_flush_threshold_surface import (
    first_cluster_events,
    positive_group_count,
    signal_set_hash,
    split_cluster_metrics,
)


ADVANCE_STEPS = {"KEEP_ORIGINAL_IMMEDIATE_FLUSH", "TEST_SIMPLIFIED_IMMEDIATE_FLUSH"}
SUMMARY_COLUMNS = [
    "fixed_candidate_id",
    "source_candidate_id",
    "fixed_action",
    "signals",
    "independent_clusters_72h",
    "cluster_excess_72h_median",
    "cluster_excess_72h_median_ci_low",
    "validation_excess_72h_median",
    "validation_excess_72h_median_ci_low",
    "net_excess_72h_median_20bps",
    "top_pair_cluster_share",
    "top_year_cluster_share",
    "positive_pairs_72h",
    "positive_years_72h",
    "diagnostic_decision",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Report fixed-scope follow-up diagnostics for retained original "
            "flush candidates and recommended simplifications."
        )
    )
    parser.add_argument(
        "--recommendations",
        default="docs/validation/analysis/major_11_flush_candidate_simplification_recommendations.csv",
    )
    parser.add_argument("--pairs-file", default="user_data/pairs/binance_usdt_futures_major_11.json")
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--strategy-file", default="user_data/strategies/VolatilityRotationMRCandidates.py")
    parser.add_argument("--strategy-class", default="VolatilityRotationMRFlushReboundLongOnly")
    parser.add_argument("--start", default="2020-01-09")
    parser.add_argument("--end", default="2026-06-03")
    parser.add_argument("--entry-price-mode", choices=["next_open"], default="next_open")
    parser.add_argument("--cluster-horizon", default="72h")
    parser.add_argument("--validation-start", default="2024-01-01")
    parser.add_argument("--null-samples-per-event", type=int, default=100)
    parser.add_argument("--null-match", default="pair,year,vol_bucket")
    parser.add_argument("--null-exclude-horizon", default="72h")
    parser.add_argument("--null-exclude-same-timestamp", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument(
        "--cost-bps",
        nargs="+",
        type=float,
        default=[0.0, 10.0, 20.0, 40.0],
        help="Round-trip cost stress levels in basis points.",
    )
    parser.add_argument("--max-candidates", type=int, default=0, help="Optional smoke-test limit after fixed selection.")
    parser.add_argument("--output-md", default="docs/validation/analysis/major_11_flush_fixed_candidate_set.md")
    parser.add_argument("--output-csv", default="docs/validation/analysis/major_11_flush_fixed_candidate_set.csv")
    parser.add_argument(
        "--concentration-csv",
        default="docs/validation/analysis/major_11_flush_fixed_candidate_set_concentration.csv",
    )
    parser.add_argument(
        "--cost-csv",
        default="docs/validation/analysis/major_11_flush_fixed_candidate_set_cost_stress.csv",
    )
    return parser.parse_args()


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def safe_float(value: Any) -> float:
    try:
        if pd.isna(value):
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def first_present(row: pd.Series, *columns: str, default: Any = "") -> Any:
    for column in columns:
        if column in row.index and not pd.isna(row[column]):
            return row[column]
    return default


def load_fixed_candidates(args: argparse.Namespace) -> pd.DataFrame:
    recommendations = pd.read_csv(args.recommendations)
    required = {
        "candidate_id",
        "recommended_next_step",
        "recommended_simplification",
        "price_z_threshold",
        "rsi_threshold",
        "vol_z_min",
        "bb_width_min",
        "use_weak_trend",
        "use_breakout_block",
        "require_close_below_bb",
    }
    missing = required - set(recommendations.columns)
    if missing:
        raise ValueError(f"Recommendations missing required columns: {sorted(missing)}")

    selected = recommendations[recommendations["recommended_next_step"].isin(ADVANCE_STEPS)].copy()
    if args.max_candidates > 0:
        selected = selected.head(args.max_candidates).copy()

    rows: list[dict[str, Any]] = []
    for _, row in selected.iterrows():
        source_id = str(row["candidate_id"])
        simplification = str(row["recommended_simplification"])
        action = str(row["recommended_next_step"])
        use_weak_trend = as_bool(row["use_weak_trend"])
        use_breakout_block = as_bool(row["use_breakout_block"])

        suffix = "original"
        if "DROP_WEAK_TREND_GATE" in simplification:
            use_weak_trend = False
            suffix = "drop_weak_trend_gate"
        if "DROP_BREAKOUT_BLOCK" in simplification:
            use_breakout_block = False
            suffix = "drop_breakout_block"

        rows.append(
            {
                "fixed_candidate_id": f"{source_id}_{suffix}",
                "source_candidate_id": source_id,
                "fixed_action": action,
                "recommended_simplification": simplification,
                "candidate_baseline_decision": first_present(row, "candidate_baseline_decision"),
                "price_z_threshold": safe_float(row["price_z_threshold"]),
                "rsi_threshold": int(float(row["rsi_threshold"])),
                "vol_z_min": safe_float(row["vol_z_min"]),
                "bb_width_min": safe_float(row["bb_width_min"]),
                "use_weak_trend": use_weak_trend,
                "use_breakout_block": use_breakout_block,
                "require_close_below_bb": as_bool(row["require_close_below_bb"]),
                "selection_buckets": first_present(row, "selection_buckets"),
                "source_immediate_clusters_72h": int(float(first_present(row, "immediate_clusters_72h", default=0))),
                "source_immediate_cluster_excess_72h_median": safe_float(
                    first_present(row, "immediate_cluster_excess_72h_median", default=np.nan)
                ),
            }
        )

    return pd.DataFrame(rows)


def numeric_median(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame:
        return float("nan")
    return float(pd.to_numeric(frame[column], errors="coerce").median())


def share(values: pd.Series) -> float:
    counts = values.value_counts(normalize=True, dropna=False)
    return float(counts.iloc[0]) if not counts.empty else float("nan")


def cluster_share(clusters: pd.DataFrame, column: str) -> float:
    if clusters.empty or column not in clusters:
        return float("nan")
    return share(clusters[column])


def evaluate_fixed_candidate(
    events: pd.DataFrame,
    candidate: pd.Series,
    args: argparse.Namespace,
    validation_start: pd.Timestamp,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    selected = events.loc[candidate_mask(events, candidate).fillna(False)].copy()
    clusters = first_cluster_events(selected, args.cluster_horizon)
    split_metrics = split_cluster_metrics(clusters, validation_start)
    label = str(candidate["fixed_candidate_id"])
    ci_low, ci_high = bootstrap_median_ci(
        clusters["excess_forward_72h"] if "excess_forward_72h" in clusters else pd.Series(dtype=float),
        n_boot=args.bootstrap_samples,
        seed=stable_seed(label, args.random_seed),
    )
    validation_ci_low, validation_ci_high = bootstrap_median_ci(
        validation_cluster_values(clusters, validation_start),
        n_boot=args.bootstrap_samples,
        seed=stable_seed(f"{label}|validation", args.random_seed),
    )

    metrics: dict[str, Any] = {
        "fixed_candidate_id": candidate["fixed_candidate_id"],
        "source_candidate_id": candidate["source_candidate_id"],
        "fixed_action": candidate["fixed_action"],
        "recommended_simplification": candidate["recommended_simplification"],
        "candidate_baseline_decision": candidate["candidate_baseline_decision"],
        "signals": int(len(selected)),
        "independent_clusters_72h": int(len(clusters)),
        "active_pairs": int(selected["pair"].nunique()) if not selected.empty else 0,
        "active_years": int(selected["year"].nunique()) if not selected.empty else 0,
        "active_months": int(selected["month"].nunique()) if not selected.empty else 0,
        "top_pair_signal_share": share(selected["pair"]) if not selected.empty else float("nan"),
        "top_pair_cluster_share": cluster_share(clusters, "pair"),
        "top_year_cluster_share": cluster_share(clusters, "year"),
        "positive_pairs_72h": positive_group_count(clusters, "pair", "excess_forward_72h"),
        "positive_years_72h": positive_group_count(clusters, "year", "excess_forward_72h"),
        "cluster_forward_24h_median": numeric_median(clusters, "forward_24h"),
        "cluster_forward_72h_median": numeric_median(clusters, "forward_72h"),
        "cluster_null_24h_median": numeric_median(clusters, "null_forward_24h_median"),
        "cluster_null_72h_median": numeric_median(clusters, "null_forward_72h_median"),
        "cluster_excess_24h_median": numeric_median(clusters, "excess_forward_24h"),
        "cluster_excess_72h_median": numeric_median(clusters, "excess_forward_72h"),
        "cluster_excess_72h_median_ci_low": ci_low,
        "cluster_excess_72h_median_ci_high": ci_high,
        "validation_excess_72h_median_ci_low": validation_ci_low,
        "validation_excess_72h_median_ci_high": validation_ci_high,
        "forward_24h_win_rate": float((pd.to_numeric(selected["forward_24h"], errors="coerce").dropna() > 0).mean())
        if not selected.empty
        else float("nan"),
        "forward_72h_win_rate": float((pd.to_numeric(selected["forward_72h"], errors="coerce").dropna() > 0).mean())
        if not selected.empty
        else float("nan"),
        "mfe_72h_median": median(selected, "mfe_72h"),
        "mae_72h_median": median(selected, "mae_72h"),
        "signal_set_hash": signal_set_hash(selected),
        "price_z_threshold": safe_float(candidate["price_z_threshold"]),
        "rsi_threshold": int(candidate["rsi_threshold"]),
        "vol_z_min": safe_float(candidate["vol_z_min"]),
        "bb_width_min": safe_float(candidate["bb_width_min"]),
        "use_weak_trend": as_bool(candidate["use_weak_trend"]),
        "use_breakout_block": as_bool(candidate["use_breakout_block"]),
        "require_close_below_bb": as_bool(candidate["require_close_below_bb"]),
        "source_immediate_clusters_72h": int(candidate["source_immediate_clusters_72h"]),
        "source_immediate_cluster_excess_72h_median": safe_float(
            candidate["source_immediate_cluster_excess_72h_median"]
        ),
    }
    metrics.update(split_metrics)
    return metrics, selected, clusters


def cost_rows(summary: dict[str, Any], clusters: pd.DataFrame, costs_bps: list[float], validation_start: pd.Timestamp) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    timestamps = pd.to_datetime(clusters["signal_timestamp"], utc=True) if "signal_timestamp" in clusters else pd.Series([], dtype="datetime64[ns]")
    validation = clusters.loc[timestamps >= validation_start].copy() if not clusters.empty else clusters.copy()
    for cost_bps in costs_bps:
        cost = float(cost_bps) / 10000.0
        net_forward = pd.to_numeric(clusters.get("forward_72h", pd.Series(dtype=float)), errors="coerce") - cost
        net_excess = pd.to_numeric(clusters.get("excess_forward_72h", pd.Series(dtype=float)), errors="coerce") - cost
        validation_net_excess = (
            pd.to_numeric(validation.get("excess_forward_72h", pd.Series(dtype=float)), errors="coerce") - cost
        )
        rows.append(
            {
                "fixed_candidate_id": summary["fixed_candidate_id"],
                "source_candidate_id": summary["source_candidate_id"],
                "cost_bps": cost_bps,
                "cluster_count": int(len(clusters)),
                "net_forward_72h_median": float(net_forward.median()) if not net_forward.empty else float("nan"),
                "net_excess_72h_median": float(net_excess.median()) if not net_excess.empty else float("nan"),
                "net_validation_excess_72h_median": float(validation_net_excess.median())
                if not validation_net_excess.empty
                else float("nan"),
                "net_forward_72h_win_rate": float((net_forward.dropna() > 0).mean()) if not net_forward.empty else float("nan"),
                "survives_cost": bool(
                    len(clusters) >= 200
                    and pd.notna(net_excess.median())
                    and net_excess.median() > 0
                    and pd.notna(validation_net_excess.median())
                    and validation_net_excess.median() > 0
                ),
            }
        )
    return rows


def grouped_concentration_rows(
    candidate_id: str,
    clusters: pd.DataFrame,
    group_column: str,
    analysis: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if clusters.empty or group_column not in clusters:
        return rows
    counts = clusters[group_column].value_counts(dropna=False).head(limit)
    total = max(len(clusters), 1)
    for value, count in counts.items():
        subset = clusters[clusters[group_column] == value]
        rows.append(
            {
                "fixed_candidate_id": candidate_id,
                "analysis": analysis,
                "group": str(value),
                "clusters": int(count),
                "cluster_share": float(count / total),
                "cluster_excess_72h_median": numeric_median(subset, "excess_forward_72h"),
                "cluster_forward_72h_median": numeric_median(subset, "forward_72h"),
                "validation_excess_72h_median": float("nan"),
                "removed_groups": "",
                "decision": "",
            }
        )
    return rows


def removal_concentration_rows(
    candidate_id: str,
    clusters: pd.DataFrame,
    validation_start: pd.Timestamp,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if clusters.empty:
        return rows

    pair_rank = clusters["pair"].value_counts().index.tolist() if "pair" in clusters else []
    month_rank = clusters["month"].value_counts().index.tolist() if "month" in clusters else []
    removal_specs = [
        ("remove_top_1_pair", "pair", pair_rank[:1]),
        ("remove_top_3_pairs", "pair", pair_rank[:3]),
        ("remove_top_1_month", "month", month_rank[:1]),
    ]
    for analysis, column, values in removal_specs:
        if not values or column not in clusters:
            continue
        retained = clusters[~clusters[column].isin(values)].copy()
        validation_values = validation_cluster_values(retained, validation_start)
        cluster_median = numeric_median(retained, "excess_forward_72h")
        validation_median = float(validation_values.median()) if not validation_values.empty else float("nan")
        rows.append(
            {
                "fixed_candidate_id": candidate_id,
                "analysis": analysis,
                "group": column,
                "clusters": int(len(retained)),
                "cluster_share": float(len(retained) / max(len(clusters), 1)),
                "cluster_excess_72h_median": cluster_median,
                "cluster_forward_72h_median": numeric_median(retained, "forward_72h"),
                "validation_excess_72h_median": validation_median,
                "removed_groups": ", ".join(str(value) for value in values),
                "decision": "survives" if cluster_median > 0 and validation_median > 0 else "weakens",
            }
        )

    for pair in pair_rank:
        retained = clusters[clusters["pair"] != pair].copy()
        validation_values = validation_cluster_values(retained, validation_start)
        cluster_median = numeric_median(retained, "excess_forward_72h")
        validation_median = float(validation_values.median()) if not validation_values.empty else float("nan")
        rows.append(
            {
                "fixed_candidate_id": candidate_id,
                "analysis": "leave_one_pair_out",
                "group": str(pair),
                "clusters": int(len(retained)),
                "cluster_share": float(len(retained) / max(len(clusters), 1)),
                "cluster_excess_72h_median": cluster_median,
                "cluster_forward_72h_median": numeric_median(retained, "forward_72h"),
                "validation_excess_72h_median": validation_median,
                "removed_groups": str(pair),
                "decision": "survives" if cluster_median > 0 and validation_median > 0 else "weakens",
            }
        )
    return rows


def classify_summary(row: dict[str, Any], cost_20bps: float) -> str:
    if row["independent_clusters_72h"] < 200:
        return "REJECT_LOW_DENSITY"
    if row["cluster_excess_72h_median_ci_low"] <= 0:
        return "REJECT_CI_FRAGILITY"
    if row["validation_excess_72h_median_ci_low"] <= 0:
        return "RESEARCH_ADVANCE_VALIDATION_WATCH"
    if row["top_pair_cluster_share"] > 0.30 or row["top_year_cluster_share"] > 0.40:
        return "RESEARCH_ADVANCE_CONCENTRATION_WATCH"
    if pd.notna(cost_20bps) and cost_20bps <= 0:
        return "RESEARCH_ADVANCE_COST_WATCH"
    return "FIXED_RESEARCH_CANDIDATE"


def add_cost_decisions(summaries: list[dict[str, Any]], cost_frame: pd.DataFrame) -> pd.DataFrame:
    summary_frame = pd.DataFrame(summaries)
    if summary_frame.empty:
        return summary_frame

    cost_20 = cost_frame[cost_frame["cost_bps"] == 20.0][["fixed_candidate_id", "net_excess_72h_median"]].rename(
        columns={"net_excess_72h_median": "net_excess_72h_median_20bps"}
    )
    summary_frame = summary_frame.merge(cost_20, on="fixed_candidate_id", how="left")
    summary_frame["diagnostic_decision"] = summary_frame.apply(
        lambda row: classify_summary(row.to_dict(), safe_float(row.get("net_excess_72h_median_20bps"))),
        axis=1,
    )
    return summary_frame


def table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.to_markdown(index=False, floatfmt=".4f")


def markdown_report(
    summary: pd.DataFrame,
    concentration: pd.DataFrame,
    cost: pd.DataFrame,
    fixed_candidates: pd.DataFrame,
    args: argparse.Namespace,
) -> str:
    decision_counts = (
        summary["diagnostic_decision"].value_counts().rename_axis("diagnostic_decision").reset_index(name="candidates")
        if not summary.empty
        else pd.DataFrame(columns=["diagnostic_decision", "candidates"])
    )
    candidate_defs = fixed_candidates[
        [
            "fixed_candidate_id",
            "source_candidate_id",
            "fixed_action",
            "recommended_simplification",
            "price_z_threshold",
            "rsi_threshold",
            "vol_z_min",
            "bb_width_min",
            "use_weak_trend",
            "use_breakout_block",
            "require_close_below_bb",
        ]
    ]
    removal = concentration[concentration["analysis"].isin(["remove_top_1_pair", "remove_top_3_pairs", "remove_top_1_month"])]
    top_pairs = concentration[concentration["analysis"] == "top_pair_clusters"].head(40)
    cost_pivot = cost.pivot_table(
        index="fixed_candidate_id",
        columns="cost_bps",
        values="net_excess_72h_median",
        aggfunc="first",
    ).reset_index()

    return "\n".join(
        [
            "# Major 11 Flush Fixed Candidate Set",
            "",
            "> Research-only fixed-scope follow-up. This does not broaden the threshold search, revive rebound confirmation, or promote any strategy to dry-run/live use.",
            "",
            "## Scope",
            "",
            f"- Recommendations: `{args.recommendations}`",
            f"- Selected fixed candidates: `{len(fixed_candidates)}`",
            f"- Start: `{args.start}`",
            f"- End: `{args.end}` exclusive for signal timestamps",
            f"- Entry price mode: `{args.entry_price_mode}`",
            f"- Cluster horizon: `{args.cluster_horizon}`",
            f"- Validation split start: `{args.validation_start}`",
            f"- Matched-null samples per event: `{args.null_samples_per_event}`",
            f"- Cost stress bps: `{', '.join(str(float(value)) for value in args.cost_bps)}`",
            "",
            "## Fixed Candidate Definitions",
            "",
            table(candidate_defs),
            "",
            "## Diagnostic Decision Counts",
            "",
            table(decision_counts),
            "",
            "## Summary",
            "",
            table(summary[SUMMARY_COLUMNS].sort_values(["diagnostic_decision", "cluster_excess_72h_median"], ascending=[True, False])),
            "",
            "## Cost Stress",
            "",
            table(cost_pivot),
            "",
            "## Top-Removal Stress",
            "",
            table(removal.sort_values(["fixed_candidate_id", "analysis"])),
            "",
            "## Top Pair Concentration",
            "",
            table(top_pairs),
            "",
            "## Interpretation",
            "",
            "- `FIXED_RESEARCH_CANDIDATE` means the fixed definition passes sample, CI, validation, concentration, and 20 bps cost diagnostics for this event-study layer only.",
            "- `RESEARCH_ADVANCE_*_WATCH` means the candidate remains research-only but needs explicit attention before any backtest-class or strict-gate work.",
            "- `REJECT_*` means this fixed follow-up should not advance without new evidence.",
            "- Costs are applied as round-trip bps against event-study 72h forward and matched-null excess returns; they are not a replacement for a Freqtrade backtest.",
            "",
        ]
    )


def main() -> None:
    args = parse_args()
    start = pd.Timestamp(args.start, tz="UTC")
    end = pd.Timestamp(args.end, tz="UTC")
    validation_start = pd.Timestamp(args.validation_start, tz="UTC")
    fixed_candidates = load_fixed_candidates(args)
    if fixed_candidates.empty:
        raise SystemExit("No fixed candidates selected from recommendations.")

    pairs = load_pairs(Path(args.pairs_file))
    strategy = load_strategy(Path(args.strategy_file), Path(args.strategy_path), args.strategy_class)
    prepared_frames = prepare_pair_frames(strategy, pairs, Path(args.datadir), start, end)
    events = build_research_event_universe(prepared_frames, start, end, args.entry_price_mode, fixed_candidates)
    null_pool = build_null_pool(prepared_frames, args.entry_price_mode)
    events = attach_matched_null_controls(
        events,
        null_pool,
        parse_null_match(args.null_match),
        args.null_samples_per_event,
        args.random_seed,
        args.null_exclude_horizon,
        args.null_exclude_same_timestamp,
    )

    summaries: list[dict[str, Any]] = []
    concentration_rows: list[dict[str, Any]] = []
    cost_stress_rows: list[dict[str, Any]] = []
    for _, candidate in fixed_candidates.iterrows():
        summary, _, clusters = evaluate_fixed_candidate(events, candidate, args, validation_start)
        summaries.append(summary)
        cost_stress_rows.extend(cost_rows(summary, clusters, args.cost_bps, validation_start))
        concentration_rows.extend(grouped_concentration_rows(summary["fixed_candidate_id"], clusters, "pair", "top_pair_clusters"))
        concentration_rows.extend(grouped_concentration_rows(summary["fixed_candidate_id"], clusters, "year", "top_year_clusters"))
        concentration_rows.extend(grouped_concentration_rows(summary["fixed_candidate_id"], clusters, "month", "top_month_clusters"))
        concentration_rows.extend(removal_concentration_rows(summary["fixed_candidate_id"], clusters, validation_start))

    cost_frame = pd.DataFrame(cost_stress_rows)
    summary_frame = add_cost_decisions(summaries, cost_frame)
    concentration_frame = pd.DataFrame(concentration_rows)

    output_csv = Path(args.output_csv)
    concentration_csv = Path(args.concentration_csv)
    cost_csv = Path(args.cost_csv)
    output_md = Path(args.output_md)
    for path in (output_csv, concentration_csv, cost_csv, output_md):
        path.parent.mkdir(parents=True, exist_ok=True)

    summary_frame.to_csv(output_csv, index=False, float_format="%.6g", lineterminator="\n")
    concentration_frame.to_csv(concentration_csv, index=False, float_format="%.6g", lineterminator="\n")
    cost_frame.to_csv(cost_csv, index=False, float_format="%.6g", lineterminator="\n")
    output_md.write_text(
        markdown_report(summary_frame, concentration_frame, cost_frame, fixed_candidates, args),
        encoding="utf-8",
        newline="\n",
    )

    print(f"Wrote fixed candidate summary to {output_csv}")
    print(f"Wrote concentration diagnostics to {concentration_csv}")
    print(f"Wrote cost stress diagnostics to {cost_csv}")
    print(f"Wrote markdown report to {output_md}")
    print(f"Diagnostic decisions: {summary_frame['diagnostic_decision'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
