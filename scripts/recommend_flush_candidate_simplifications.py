from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SURVIVOR_DECISIONS = {"SURVIVES_BASELINES_STRONG", "SURVIVES_BASELINES_WEAK"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize baseline-surviving flush candidates into fixed-scope "
            "simplification recommendations."
        )
    )
    parser.add_argument(
        "--candidate-summary",
        default="docs/validation/analysis/major_11_flush_baseline_candidate_summary.csv",
    )
    parser.add_argument(
        "--component-diagnostics",
        default="docs/validation/analysis/major_11_flush_rebound_component_diagnostics.csv",
    )
    parser.add_argument(
        "--output-csv",
        default="docs/validation/analysis/major_11_flush_candidate_simplification_recommendations.csv",
    )
    parser.add_argument(
        "--output-md",
        default="docs/validation/analysis/major_11_flush_candidate_simplification_recommendations.md",
    )
    parser.add_argument(
        "--include-non-survivors",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Also emit baseline-equivalent, failed, or insufficient candidates when present in diagnostics.",
    )
    return parser.parse_args()


def safe_float(value: Any) -> float:
    try:
        if pd.isna(value):
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def safe_int(value: Any) -> int:
    try:
        if pd.isna(value):
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def first_value(frame: pd.DataFrame, column: str, default: Any = "") -> Any:
    if frame.empty or column not in frame.columns:
        return default
    value = frame.iloc[0][column]
    if pd.isna(value):
        return default
    return value


def component_row(components: pd.DataFrame, name: str) -> pd.Series | None:
    matches = components.loc[components["component_name"] == name]
    if matches.empty:
        return None
    return matches.iloc[0]


def component_decision(components: pd.DataFrame, name: str) -> str:
    row = component_row(components, name)
    if row is None:
        return "MISSING_COMPONENT"
    value = row.get("decision", "")
    return str(value) if not pd.isna(value) else "MISSING_COMPONENT"


def component_metric(components: pd.DataFrame, name: str, column: str) -> float:
    row = component_row(components, name)
    if row is None:
        return float("nan")
    return safe_float(row.get(column))


def recommend_candidate(summary_row: pd.Series, components: pd.DataFrame) -> dict[str, Any]:
    candidate_id = str(summary_row["candidate_id"])
    baseline_decision = str(summary_row["candidate_baseline_decision"])

    immediate_decision = component_decision(components, "candidate_flush_immediate")
    no_weak_decision = component_decision(components, "candidate_no_weak_trend_gate")
    no_breakout_decision = component_decision(components, "candidate_no_breakout_block")
    price_z_rsi_decision = component_decision(components, "candidate_price_z_rsi_only")
    rebound_1c_decision = component_decision(components, "rebound_1c_confirmation")
    rebound_3c_decision = component_decision(components, "rebound_3c_confirmation")

    simplifications: list[str] = []
    if no_weak_decision == "SIMPLIFY_FILTERS":
        simplifications.append("DROP_WEAK_TREND_GATE")
    if no_breakout_decision == "SIMPLIFY_FILTERS":
        simplifications.append("DROP_BREAKOUT_BLOCK")

    rebound_kept = any(
        decision == "KEEP_REBOUND_CONFIRMATION"
        for decision in (rebound_1c_decision, rebound_3c_decision)
    )

    if baseline_decision not in SURVIVOR_DECISIONS:
        next_step = "DO_NOT_ADVANCE_BASELINE_GATE"
        rationale = "Candidate did not survive the candidate-level baseline gate."
    elif immediate_decision == "DROP_COMPONENT":
        next_step = "REJECT_COMPONENT_FAILURE"
        rationale = "Immediate flush component did not clear the component diagnostic gate."
    elif rebound_kept:
        next_step = "RETEST_REBOUND_CONFIRMATION"
        rationale = "At least one rebound-confirmation variant survived component diagnostics."
    elif simplifications:
        next_step = "TEST_SIMPLIFIED_IMMEDIATE_FLUSH"
        rationale = "A fixed filter ablation preserved the immediate-flush edge while increasing or preserving sample quality."
    elif immediate_decision == "KEEP_IMMEDIATE_FLUSH":
        next_step = "KEEP_ORIGINAL_IMMEDIATE_FLUSH"
        rationale = "Immediate flush survived; rebound confirmation and pure price_z+rsi simplification did not add value."
    elif immediate_decision == "INSUFFICIENT_COMPONENT_SAMPLE":
        next_step = "HOLD_FOR_MORE_SAMPLE"
        rationale = "Immediate flush component was under-sampled in the component diagnostic."
    else:
        next_step = "NO_RESEARCH_ADVANCE"
        rationale = "No fixed component variant produced an actionable diagnostic decision."

    immediate_clusters = safe_int(component_metric(components, "candidate_flush_immediate", "independent_clusters_72h"))
    immediate_excess_72h = component_metric(components, "candidate_flush_immediate", "cluster_excess_72h_median")
    immediate_ci_low = component_metric(components, "candidate_flush_immediate", "cluster_excess_72h_median_ci_low")
    validation_excess_72h = component_metric(components, "candidate_flush_immediate", "validation_excess_72h_median")
    validation_ci_low = component_metric(components, "candidate_flush_immediate", "validation_excess_72h_median_ci_low")
    mae_72h = component_metric(components, "candidate_flush_immediate", "mae_72h_median")
    mfe_72h = component_metric(components, "candidate_flush_immediate", "mfe_72h_median")

    return {
        "candidate_id": candidate_id,
        "candidate_baseline_decision": baseline_decision,
        "recommended_next_step": next_step,
        "recommended_simplification": ";".join(simplifications) if simplifications else "NONE",
        "rationale": rationale,
        "eligible_baselines": safe_int(summary_row.get("eligible_baselines")),
        "baseline_beater_ci_count": safe_int(summary_row.get("baseline_beater_ci_count")),
        "baseline_beater_point_count": safe_int(summary_row.get("baseline_beater_point_count")),
        "worst_delta_cluster_excess_72h_median": safe_float(summary_row.get("worst_delta_cluster_excess_72h_median")),
        "worst_delta_validation_excess_72h_median": safe_float(summary_row.get("worst_delta_validation_excess_72h_median")),
        "immediate_decision": immediate_decision,
        "no_weak_trend_gate_decision": no_weak_decision,
        "no_breakout_block_decision": no_breakout_decision,
        "price_z_rsi_only_decision": price_z_rsi_decision,
        "rebound_1c_confirmation_decision": rebound_1c_decision,
        "rebound_3c_confirmation_decision": rebound_3c_decision,
        "immediate_clusters_72h": immediate_clusters,
        "immediate_cluster_excess_72h_median": immediate_excess_72h,
        "immediate_cluster_excess_72h_median_ci_low": immediate_ci_low,
        "immediate_validation_excess_72h_median": validation_excess_72h,
        "immediate_validation_excess_72h_median_ci_low": validation_ci_low,
        "immediate_mae_72h_median": mae_72h,
        "immediate_mfe_72h_median": mfe_72h,
        "price_z_threshold": first_value(components, "price_z_threshold", summary_row.get("price_z_threshold", "")),
        "rsi_threshold": first_value(components, "rsi_threshold", summary_row.get("rsi_threshold", "")),
        "vol_z_min": first_value(components, "vol_z_min", summary_row.get("vol_z_min", "")),
        "bb_width_min": first_value(components, "bb_width_min", summary_row.get("bb_width_min", "")),
        "use_weak_trend": first_value(components, "use_weak_trend", summary_row.get("use_weak_trend", "")),
        "use_breakout_block": first_value(components, "use_breakout_block", summary_row.get("use_breakout_block", "")),
        "require_close_below_bb": first_value(components, "require_close_below_bb", summary_row.get("require_close_below_bb", "")),
        "selection_buckets": summary_row.get("selection_buckets", ""),
    }


def rank_recommendations(frame: pd.DataFrame) -> pd.DataFrame:
    baseline_rank = {
        "SURVIVES_BASELINES_STRONG": 0,
        "SURVIVES_BASELINES_WEAK": 1,
        "BASELINE_EQUIVALENT": 2,
        "INSUFFICIENT_BASELINE_COVERAGE": 3,
        "FAILS_BASELINES": 4,
    }
    next_step_rank = {
        "TEST_SIMPLIFIED_IMMEDIATE_FLUSH": 0,
        "KEEP_ORIGINAL_IMMEDIATE_FLUSH": 1,
        "RETEST_REBOUND_CONFIRMATION": 2,
        "HOLD_FOR_MORE_SAMPLE": 3,
        "DO_NOT_ADVANCE_BASELINE_GATE": 4,
        "REJECT_COMPONENT_FAILURE": 5,
        "NO_RESEARCH_ADVANCE": 6,
    }
    ranked = frame.copy()
    ranked["_baseline_rank"] = ranked["candidate_baseline_decision"].map(baseline_rank).fillna(9)
    ranked["_next_step_rank"] = ranked["recommended_next_step"].map(next_step_rank).fillna(9)
    ranked["_ci_low_sort"] = ranked["immediate_cluster_excess_72h_median_ci_low"].replace({np.nan: -999.0})
    ranked["_excess_sort"] = ranked["immediate_cluster_excess_72h_median"].replace({np.nan: -999.0})
    ranked = ranked.sort_values(
        [
            "_baseline_rank",
            "_next_step_rank",
            "baseline_beater_ci_count",
            "_ci_low_sort",
            "_excess_sort",
            "immediate_clusters_72h",
            "candidate_id",
        ],
        ascending=[True, True, False, False, False, False, True],
    )
    return ranked.drop(columns=["_baseline_rank", "_next_step_rank", "_ci_low_sort", "_excess_sort"])


def build_recommendations(args: argparse.Namespace) -> pd.DataFrame:
    summary = pd.read_csv(args.candidate_summary)
    diagnostics = pd.read_csv(args.component_diagnostics)
    if not args.include_non_survivors:
        summary = summary.loc[summary["candidate_baseline_decision"].isin(SURVIVOR_DECISIONS)].copy()

    rows = []
    for _, summary_row in summary.iterrows():
        candidate_id = str(summary_row["candidate_id"])
        components = diagnostics.loc[diagnostics["candidate_id"].astype(str) == candidate_id].copy()
        if components.empty:
            continue
        rows.append(recommend_candidate(summary_row, components))

    if not rows:
        return pd.DataFrame()
    return rank_recommendations(pd.DataFrame(rows))


def table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.to_markdown(index=False, floatfmt=".4f")


def markdown_report(recommendations: pd.DataFrame, args: argparse.Namespace) -> str:
    decision_counts = (
        recommendations["recommended_next_step"].value_counts().rename_axis("recommended_next_step").reset_index(name="candidates")
        if not recommendations.empty
        else pd.DataFrame(columns=["recommended_next_step", "candidates"])
    )
    simplification_counts = (
        recommendations["recommended_simplification"].value_counts().rename_axis("recommended_simplification").reset_index(name="candidates")
        if not recommendations.empty
        else pd.DataFrame(columns=["recommended_simplification", "candidates"])
    )

    summary_cols = [
        "candidate_id",
        "candidate_baseline_decision",
        "recommended_next_step",
        "recommended_simplification",
        "baseline_beater_ci_count",
        "immediate_clusters_72h",
        "immediate_cluster_excess_72h_median",
        "immediate_cluster_excess_72h_median_ci_low",
        "immediate_validation_excess_72h_median",
        "no_breakout_block_decision",
        "price_z_rsi_only_decision",
        "rebound_1c_confirmation_decision",
        "rebound_3c_confirmation_decision",
    ]
    top = recommendations.loc[:, summary_cols].head(20) if not recommendations.empty else recommendations

    return "\n".join(
        [
            "# Major 11 Flush Candidate Simplification Recommendations",
            "",
            "Research-only decision summary derived from the frozen baseline candidate summary and fixed flush/rebound component diagnostics.",
            "",
            "## Scope",
            "",
            f"- Candidate summary: `{args.candidate_summary}`",
            f"- Component diagnostics: `{args.component_diagnostics}`",
            "- Default scope: candidates with `SURVIVES_BASELINES_STRONG` or `SURVIVES_BASELINES_WEAK` only.",
            "- This report does not create or promote a live strategy.",
            "",
            "## Recommendation Counts",
            "",
            table(decision_counts),
            "",
            "## Simplification Counts",
            "",
            table(simplification_counts),
            "",
            "## Ranked Recommendations",
            "",
            table(top),
            "",
            "## Interpretation",
            "",
            "- `TEST_SIMPLIFIED_IMMEDIATE_FLUSH` means a fixed filter ablation preserved the immediate-flush edge and should be considered for the next diagnostic-only candidate definition.",
            "- `KEEP_ORIGINAL_IMMEDIATE_FLUSH` means the immediate flush survived, while tested simplifications or rebound confirmations did not add enough value.",
            "- `RETEST_REBOUND_CONFIRMATION` is reserved for candidates where a rebound-confirmation variant survived the component gate.",
            "- `DO_NOT_ADVANCE_BASELINE_GATE` keeps non-survivors out of the next research step.",
            "",
        ]
    )


def main() -> None:
    args = parse_args()
    recommendations = build_recommendations(args)

    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    recommendations.to_csv(output_csv, index=False)
    output_md.write_text(markdown_report(recommendations, args), encoding="utf-8")

    counts = recommendations["recommended_next_step"].value_counts().to_dict() if not recommendations.empty else {}
    print(f"Wrote {len(recommendations)} recommendations to {output_csv}")
    print(f"Wrote markdown report to {output_md}")
    print(f"Recommendation counts: {counts}")


if __name__ == "__main__":
    main()
