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
    load_manifest,
    median,
    stable_seed,
    table,
    validation_cluster_values,
)
from event_study_flush_rebound import (
    FORWARD_CANDLES,
    attach_matched_null_controls,
    build_null_pool,
    load_pairs,
    load_strategy,
    parse_null_match,
    prepare_pair_frames,
)
from scan_flush_threshold_surface import build_flush_mask, first_cluster_events, split_cluster_metrics


SURVIVING_DECISIONS = {"SURVIVES_BASELINES_STRONG", "SURVIVES_BASELINES_WEAK"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose whether robust flush value comes from flush severity, filters, or rebound confirmation.")
    parser.add_argument("--candidate-summary", default="docs/validation/analysis/major_11_flush_baseline_candidate_summary.csv")
    parser.add_argument("--candidate-manifest", default="docs/validation/analysis/major_11_robust_flush_candidate_manifest.csv")
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
    parser.add_argument("--strong-limit", type=int, default=10)
    parser.add_argument("--weak-limit", type=int, default=5)
    parser.add_argument("--max-candidates", type=int, default=0, help="Optional smoke-test limit after fixed candidate selection.")
    parser.add_argument("--output-csv", default="docs/validation/analysis/major_11_flush_rebound_component_diagnostics.csv")
    parser.add_argument("--output-md", default="docs/validation/analysis/major_11_flush_rebound_component_diagnostics.md")
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


def load_selected_candidates(args: argparse.Namespace) -> pd.DataFrame:
    summary = pd.read_csv(args.candidate_summary)
    manifest = load_manifest(Path(args.candidate_manifest), 0)
    required = {"candidate_id", "candidate_baseline_decision"}
    missing = required - set(summary.columns)
    if missing:
        raise ValueError(f"Candidate summary missing required columns: {sorted(missing)}")

    strong = summary[summary["candidate_baseline_decision"] == "SURVIVES_BASELINES_STRONG"].sort_values(
        ["baseline_beater_ci_count", "cluster_excess_72h_median"], ascending=[False, False]
    ).head(args.strong_limit)
    weak = summary[summary["candidate_baseline_decision"] == "SURVIVES_BASELINES_WEAK"].sort_values(
        ["baseline_beater_point_count", "cluster_excess_72h_median"], ascending=[False, False]
    ).head(args.weak_limit)
    selected_ids = list(pd.concat([strong, weak], ignore_index=True)["candidate_id"])

    original_seed = manifest[manifest.get("selection_buckets", "").astype(str).str.contains("original_seed_nearest", regex=False)]
    if not original_seed.empty:
        selected_ids.extend(original_seed["candidate_id"].astype(str).tolist())

    selected_ids = list(dict.fromkeys(selected_ids))
    if args.max_candidates > 0:
        selected_ids = selected_ids[: args.max_candidates]

    selected = manifest[manifest["candidate_id"].isin(selected_ids)].copy()
    selected = selected.merge(
        summary[["candidate_id", "candidate_baseline_decision", "baseline_beater_ci_count", "baseline_beater_point_count"]],
        on="candidate_id",
        how="left",
    )
    for column in ("use_weak_trend", "use_breakout_block", "require_close_below_bb"):
        selected[column] = selected[column].map(as_bool)
    return selected.reset_index(drop=True)


def add_frame_component_columns(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    enriched["close_below_bb_lower"] = (enriched["close"] < enriched["bb_lower"]).fillna(False)
    return enriched


def candidate_frame_mask(frame: pd.DataFrame, candidate: pd.Series) -> pd.Series:
    return build_flush_mask(
        add_frame_component_columns(frame),
        safe_float(candidate["price_z_threshold"]),
        int(candidate["rsi_threshold"]),
        safe_float(candidate["vol_z_min"]),
        safe_float(candidate["bb_width_min"]),
        as_bool(candidate["use_weak_trend"]),
        as_bool(candidate["use_breakout_block"]),
        as_bool(candidate["require_close_below_bb"]),
    )


def confirmation_passes(frame: pd.DataFrame, index: int) -> bool:
    if index >= len(frame):
        return False
    close = safe_float(frame.at[index, "close"])
    open_price = safe_float(frame.at[index, "open"])
    bb_lower = safe_float(frame.at[index, "bb_lower"])
    return bool(np.isfinite(close) and np.isfinite(open_price) and np.isfinite(bb_lower) and close > open_price and close > bb_lower)


def forward_row(frame: pd.DataFrame, entry_index: int, entry_price: float) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for label, candles in FORWARD_CANDLES.items():
        target = entry_index + candles
        has_forward = target < len(frame)
        row[f"has_forward_{label}"] = bool(has_forward)
        row[f"forward_{label}"] = (safe_float(frame.at[target, "close"]) / entry_price) - 1.0 if has_forward else float("nan")
    future = frame.iloc[entry_index + 1 : entry_index + 1 + max(FORWARD_CANDLES.values())]
    if future.empty:
        row["mfe_72h"] = float("nan")
        row["mae_72h"] = float("nan")
    else:
        row["mfe_72h"] = (float(future["high"].max()) / entry_price) - 1.0
        row["mae_72h"] = (float(future["low"].min()) / entry_price) - 1.0
    return row


def build_rebound_confirmation_events(
    prepared_frames: dict[str, pd.DataFrame],
    candidates: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, candidate in candidates.iterrows():
        candidate_id = str(candidate["candidate_id"])
        for pair, raw_frame in prepared_frames.items():
            frame = add_frame_component_columns(raw_frame)
            signal_window = (frame["date"] >= start) & (frame["date"] < end)
            flush_indices = frame.index[signal_window & candidate_frame_mask(frame, candidate)]
            for flush_index in flush_indices:
                for component_name, max_delay in (("rebound_1c_confirmation", 1), ("rebound_3c_confirmation", 3)):
                    confirmation_index = None
                    for delay in range(1, max_delay + 1):
                        candidate_confirmation = int(flush_index) + delay
                        if confirmation_passes(frame, candidate_confirmation):
                            confirmation_index = candidate_confirmation
                            break
                    if confirmation_index is None:
                        continue
                    entry_index = confirmation_index + 1
                    if entry_index >= len(frame):
                        continue
                    entry_price = safe_float(frame.at[entry_index, "open"])
                    immediate_entry_price = safe_float(frame.at[int(flush_index) + 1, "open"]) if int(flush_index) + 1 < len(frame) else float("nan")
                    if not np.isfinite(entry_price) or entry_price <= 0:
                        continue

                    row = {
                        "candidate_id": candidate_id,
                        "component_name": component_name,
                        "strategy": component_name,
                        "pair": pair,
                        "timestamp": frame.at[confirmation_index, "date"],
                        "signal_timestamp": frame.at[confirmation_index, "date"],
                        "flush_timestamp": frame.at[int(flush_index), "date"],
                        "entry_timestamp": frame.at[entry_index, "date"],
                        "year": frame.at[confirmation_index, "year"],
                        "month": frame.at[confirmation_index, "month"],
                        "quarter": frame.at[confirmation_index, "quarter"],
                        "signal_index": int(confirmation_index),
                        "flush_index": int(flush_index),
                        "entry_index": int(entry_index),
                        "entry_price_mode": "next_open_after_confirmation",
                        "entry_price": entry_price,
                        "rsi": safe_float(frame.at[int(flush_index), "rsi"]),
                        "price_z": safe_float(frame.at[int(flush_index), "price_z"]),
                        "vol_z": safe_float(frame.at[int(flush_index), "vol_z"]),
                        "vol_bucket": int(frame.at[confirmation_index, "vol_bucket"]),
                        "natr": safe_float(frame.at[confirmation_index, "natr"]),
                        "bb_width": safe_float(frame.at[int(flush_index), "bb_width"]),
                        "confirmation_delay_candles": int(confirmation_index - int(flush_index)),
                        "missed_move_from_flush_entry": (entry_price / immediate_entry_price) - 1.0
                        if np.isfinite(immediate_entry_price) and immediate_entry_price > 0
                        else float("nan"),
                    }
                    row.update(forward_row(frame, entry_index, entry_price))
                    rows.append(row)
    return pd.DataFrame(rows)


def immediate_component_masks(events: pd.DataFrame, candidate: pd.Series) -> dict[str, pd.Series]:
    return {
        "candidate_flush_immediate": candidate_mask(events, candidate),
        "candidate_no_weak_trend_gate": build_flush_mask(
            events,
            safe_float(candidate["price_z_threshold"]),
            int(candidate["rsi_threshold"]),
            safe_float(candidate["vol_z_min"]),
            safe_float(candidate["bb_width_min"]),
            False,
            as_bool(candidate["use_breakout_block"]),
            as_bool(candidate["require_close_below_bb"]),
        ),
        "candidate_no_breakout_block": build_flush_mask(
            events,
            safe_float(candidate["price_z_threshold"]),
            int(candidate["rsi_threshold"]),
            safe_float(candidate["vol_z_min"]),
            safe_float(candidate["bb_width_min"]),
            as_bool(candidate["use_weak_trend"]),
            False,
            as_bool(candidate["require_close_below_bb"]),
        ),
        "candidate_price_z_rsi_only": (events["price_z"] < -safe_float(candidate["price_z_threshold"]))
        & (events["rsi"] < int(candidate["rsi_threshold"])),
    }


def evaluate_component(
    events: pd.DataFrame,
    mask: pd.Series,
    label: str,
    cluster_horizon: str,
    validation_start: pd.Timestamp,
    bootstrap_samples: int,
    random_seed: int,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    selected = events.loc[mask.fillna(False)].copy()
    clusters = first_cluster_events(selected, cluster_horizon)
    split = split_cluster_metrics(clusters, validation_start)
    ci_low, ci_high = bootstrap_median_ci(
        clusters["excess_forward_72h"] if "excess_forward_72h" in clusters else pd.Series(dtype=float),
        n_boot=bootstrap_samples,
        seed=stable_seed(label, random_seed),
    )
    validation_ci_low, validation_ci_high = bootstrap_median_ci(
        validation_cluster_values(clusters, validation_start),
        n_boot=bootstrap_samples,
        seed=stable_seed(f"{label}|validation", random_seed),
    )
    metrics: dict[str, Any] = {
        "signals": int(len(selected)),
        "independent_clusters_72h": int(len(clusters)),
        "active_pairs": int(selected["pair"].nunique()) if not selected.empty else 0,
        "active_years": int(selected["year"].nunique()) if not selected.empty else 0,
        "top_pair_signal_share": float(selected["pair"].value_counts(normalize=True).iloc[0]) if not selected.empty else float("nan"),
        "top_year_signal_share": float(selected["year"].value_counts(normalize=True).iloc[0]) if not selected.empty else float("nan"),
        "cluster_excess_24h_median": median(clusters, "excess_forward_24h"),
        "cluster_excess_72h_median": median(clusters, "excess_forward_72h"),
        "cluster_excess_72h_median_ci_low": ci_low,
        "cluster_excess_72h_median_ci_high": ci_high,
        "validation_excess_72h_median_ci_low": validation_ci_low,
        "validation_excess_72h_median_ci_high": validation_ci_high,
        "mae_72h_median": median(selected, "mae_72h"),
        "mfe_72h_median": median(selected, "mfe_72h"),
        "forward_24h_win_rate": float((pd.to_numeric(selected["forward_24h"], errors="coerce").dropna() > 0).mean()) if not selected.empty else float("nan"),
        "forward_72h_win_rate": float((pd.to_numeric(selected["forward_72h"], errors="coerce").dropna() > 0).mean()) if not selected.empty else float("nan"),
        "confirmation_delay_median": median(selected, "confirmation_delay_candles"),
        "missed_move_median": median(selected, "missed_move_from_flush_entry"),
    }
    metrics.update(split)
    return metrics, selected, clusters


def classify_component(row: dict[str, Any]) -> str:
    if row["independent_clusters_72h"] < 200:
        return "INSUFFICIENT_COMPONENT_SAMPLE"
    if row["cluster_excess_72h_median_ci_low"] <= 0:
        return "DROP_COMPONENT"
    if (
        str(row["component_name"]).startswith("rebound")
        and row["mae_72h_median"] > row["immediate_mae_72h_median"]
        and row["cluster_excess_72h_median"] >= row["immediate_cluster_excess_72h_median"] - 0.0025
    ):
        return "KEEP_REBOUND_CONFIRMATION"
    if (
        str(row["component_name"]).startswith("candidate_no_")
        and row["cluster_excess_72h_median"] >= row["immediate_cluster_excess_72h_median"] - 0.0025
        and row["independent_clusters_72h"] > row["immediate_clusters"]
    ):
        return "SIMPLIFY_FILTERS"
    return "KEEP_IMMEDIATE_FLUSH"


def component_rows(
    events: pd.DataFrame,
    rebound_events: pd.DataFrame,
    candidates: pd.DataFrame,
    args: argparse.Namespace,
    validation_start: pd.Timestamp,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, candidate in candidates.iterrows():
        candidate_id = str(candidate["candidate_id"])
        immediate_metrics, _, _ = evaluate_component(
            events,
            candidate_mask(events, candidate),
            f"{candidate_id}|candidate_flush_immediate",
            args.cluster_horizon,
            validation_start,
            args.bootstrap_samples,
            args.random_seed,
        )
        masks = immediate_component_masks(events, candidate)
        for component_name, mask in masks.items():
            metrics, _, _ = evaluate_component(
                events,
                mask,
                f"{candidate_id}|{component_name}",
                args.cluster_horizon,
                validation_start,
                args.bootstrap_samples,
                args.random_seed,
            )
            rows.append(component_row(candidate, component_name, metrics, immediate_metrics))

        for component_name in ("rebound_1c_confirmation", "rebound_3c_confirmation"):
            component_events = rebound_events[
                (rebound_events["candidate_id"] == candidate_id) & (rebound_events["component_name"] == component_name)
            ]
            mask = pd.Series(True, index=component_events.index)
            metrics, _, _ = evaluate_component(
                component_events,
                mask,
                f"{candidate_id}|{component_name}",
                args.cluster_horizon,
                validation_start,
                args.bootstrap_samples,
                args.random_seed,
            )
            rows.append(component_row(candidate, component_name, metrics, immediate_metrics))
    return pd.DataFrame(rows)


def component_row(candidate: pd.Series, component_name: str, metrics: dict[str, Any], immediate: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "candidate_id": candidate["candidate_id"],
        "candidate_baseline_decision": candidate.get("candidate_baseline_decision", ""),
        "component_name": component_name,
        "signals": metrics["signals"],
        "independent_clusters_72h": metrics["independent_clusters_72h"],
        "active_pairs": metrics["active_pairs"],
        "active_years": metrics["active_years"],
        "top_pair_signal_share": metrics["top_pair_signal_share"],
        "top_year_signal_share": metrics["top_year_signal_share"],
        "cluster_excess_24h_median": metrics["cluster_excess_24h_median"],
        "cluster_excess_72h_median": metrics["cluster_excess_72h_median"],
        "cluster_excess_72h_median_ci_low": metrics["cluster_excess_72h_median_ci_low"],
        "cluster_excess_72h_median_ci_high": metrics["cluster_excess_72h_median_ci_high"],
        "validation_excess_72h_median": metrics["validation_excess_72h_median"],
        "validation_excess_72h_median_ci_low": metrics["validation_excess_72h_median_ci_low"],
        "validation_excess_72h_median_ci_high": metrics["validation_excess_72h_median_ci_high"],
        "mae_72h_median": metrics["mae_72h_median"],
        "mfe_72h_median": metrics["mfe_72h_median"],
        "forward_24h_win_rate": metrics["forward_24h_win_rate"],
        "forward_72h_win_rate": metrics["forward_72h_win_rate"],
        "confirmation_delay_median": metrics["confirmation_delay_median"],
        "missed_move_median": metrics["missed_move_median"],
        "immediate_clusters": immediate["independent_clusters_72h"],
        "immediate_cluster_excess_72h_median": immediate["cluster_excess_72h_median"],
        "immediate_mae_72h_median": immediate["mae_72h_median"],
        "price_z_threshold": safe_float(candidate["price_z_threshold"]),
        "rsi_threshold": int(candidate["rsi_threshold"]),
        "vol_z_min": safe_float(candidate["vol_z_min"]),
        "bb_width_min": safe_float(candidate["bb_width_min"]),
        "use_weak_trend": as_bool(candidate["use_weak_trend"]),
        "use_breakout_block": as_bool(candidate["use_breakout_block"]),
        "require_close_below_bb": as_bool(candidate["require_close_below_bb"]),
    }
    row["decision"] = classify_component(row)
    return row


def markdown_report(results: pd.DataFrame, candidates: pd.DataFrame, rebound_event_count: int, args: argparse.Namespace) -> str:
    decision_counts = results["decision"].value_counts().rename_axis("decision").reset_index(name="component_rows")
    component_counts = (
        results.groupby(["component_name", "decision"], as_index=False)
        .agg(component_rows=("candidate_id", "size"))
        .sort_values(["component_name", "decision"])
    )
    columns = [
        "candidate_id",
        "component_name",
        "decision",
        "signals",
        "independent_clusters_72h",
        "cluster_excess_72h_median",
        "cluster_excess_72h_median_ci_low",
        "validation_excess_72h_median",
        "validation_excess_72h_median_ci_low",
        "mae_72h_median",
        "confirmation_delay_median",
        "missed_move_median",
        "immediate_cluster_excess_72h_median",
        "immediate_mae_72h_median",
    ]
    lines = [
        "# Major 11 Flush/Rebound Component Diagnostics",
        "",
        "> Research diagnostic only. This uses the frozen baseline-surviving candidates and fixed component definitions; it does not add or promote a live/deployable strategy class.",
        "",
        "## Scope",
        "",
        f"- Candidate summary: `{args.candidate_summary}`",
        f"- Candidate manifest: `{args.candidate_manifest}`",
        f"- Selected candidates: `{len(candidates)}`",
        f"- Rebound-confirmation events before component slicing: `{rebound_event_count}`",
        f"- Entry price mode: `{args.entry_price_mode}`",
        f"- Cluster horizon: `{args.cluster_horizon}`",
        f"- Matched-null samples per event: `{args.null_samples_per_event}`",
        f"- Bootstrap samples: `{args.bootstrap_samples}`",
        "",
        "## Candidate Set",
        "",
        table(candidates[["candidate_id", "candidate_baseline_decision", "baseline_beater_ci_count", "baseline_beater_point_count", "selection_buckets"]]),
        "",
        "## Decision Counts",
        "",
        table(decision_counts),
        "",
        "## Component Decision Counts",
        "",
        table(component_counts),
        "",
        "## Keep Rebound Confirmation Rows",
        "",
        table(results[results["decision"] == "KEEP_REBOUND_CONFIRMATION"][columns].head(60)),
        "",
        "## Simplify Filter Rows",
        "",
        table(results[results["decision"] == "SIMPLIFY_FILTERS"][columns].head(60)),
        "",
        "## Immediate / Drop / Insufficient Rows",
        "",
        table(results[results["decision"].isin(["KEEP_IMMEDIATE_FLUSH", "DROP_COMPONENT", "INSUFFICIENT_COMPONENT_SAMPLE"])][columns].head(80)),
        "",
        "## Interpretation",
        "",
        "- `KEEP_REBOUND_CONFIRMATION` means a rebound confirmation improves MAE and keeps 72h cluster excess close to the immediate flush reference.",
        "- `SIMPLIFY_FILTERS` means removing a filter keeps 72h cluster excess within 25 bps of the immediate reference while increasing independent clusters.",
        "- `KEEP_IMMEDIATE_FLUSH` means the immediate flush remains the better diagnostic reference for that component.",
        "- `DROP_COMPONENT` means the component fails the positive 72h cluster-excess bootstrap lower-bound gate.",
        "- `INSUFFICIENT_COMPONENT_SAMPLE` means the component has fewer than 200 independent 72h clusters.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    start = pd.Timestamp(args.start, tz="UTC")
    end = pd.Timestamp(args.end, tz="UTC")
    validation_start = pd.Timestamp(args.validation_start, tz="UTC")
    candidates = load_selected_candidates(args)
    pairs = load_pairs(Path(args.pairs_file))
    strategy = load_strategy(Path(args.strategy_file), Path(args.strategy_path), args.strategy_class)
    prepared_frames = prepare_pair_frames(strategy, pairs, Path(args.datadir), start, end)

    events = build_research_event_universe(prepared_frames, start, end, args.entry_price_mode, candidates)
    null_pool = build_null_pool(prepared_frames, args.entry_price_mode)
    match_fields = parse_null_match(args.null_match)
    events = attach_matched_null_controls(
        events,
        null_pool,
        match_fields,
        args.null_samples_per_event,
        args.random_seed,
        args.null_exclude_horizon,
        args.null_exclude_same_timestamp,
    )
    rebound_events = build_rebound_confirmation_events(prepared_frames, candidates, start, end)
    rebound_events = attach_matched_null_controls(
        rebound_events,
        null_pool,
        match_fields,
        args.null_samples_per_event,
        args.random_seed,
        args.null_exclude_horizon,
        args.null_exclude_same_timestamp,
    )
    results = component_rows(events, rebound_events, candidates, args, validation_start)

    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_csv, index=False, float_format="%.6g")
    output_md.write_text(markdown_report(results, candidates, len(rebound_events), args), encoding="utf-8")
    print(f"Selected candidates: {len(candidates)}")
    print(f"Component rows: {len(results)}")
    print(f"Rebound confirmation events: {len(rebound_events)}")
    print(f"Component diagnostics written to {output_md}")


if __name__ == "__main__":
    main()
