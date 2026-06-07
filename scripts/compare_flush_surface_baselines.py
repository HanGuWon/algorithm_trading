from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from event_study_flush_rebound import (
    FORWARD_CANDLES,
    attach_matched_null_controls,
    build_null_pool,
    load_pairs,
    load_strategy,
    parse_null_match,
    prepare_pair_frames,
)
from scan_flush_threshold_surface import (
    add_event_identity,
    bool_series,
    build_flush_mask,
    first_cluster_events,
    future_window_extreme,
    positive_group_count,
    signal_share,
    split_cluster_metrics,
)


MetricResult = tuple[dict[str, Any], pd.DataFrame]
MaskBuilder = Callable[[pd.DataFrame], pd.Series]


@dataclass(frozen=True)
class BaselineSpec:
    name: str
    description: str
    mask_builder: MaskBuilder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare robust major-11 flush candidates with simple baseline masks.")
    parser.add_argument("--surface-csv", default="docs/validation/analysis/major_11_flush_threshold_surface.csv")
    parser.add_argument("--candidate-manifest", default="docs/validation/analysis/major_11_robust_flush_candidate_manifest.csv")
    parser.add_argument("--pairs-file", default="user_data/pairs/binance_usdt_futures_major_11.json")
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--strategy-file", default="user_data/strategies/VolatilityRotationMRCandidates.py")
    parser.add_argument("--strategy-class", default="VolatilityRotationMRFlushReboundLongOnly")
    parser.add_argument("--start", default="2020-01-09")
    parser.add_argument("--end", default="2026-06-03")
    parser.add_argument("--entry-price-mode", choices=["signal_close", "next_open"], default="next_open")
    parser.add_argument("--cluster-horizon", default="72h")
    parser.add_argument("--validation-start", default="2024-01-01")
    parser.add_argument("--null-samples-per-event", type=int, default=100)
    parser.add_argument("--null-match", default="pair,year,vol_bucket")
    parser.add_argument("--null-exclude-horizon", default="72h")
    parser.add_argument("--null-exclude-same-timestamp", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--max-candidates", type=int, default=0, help="Optional smoke-test limit. Zero evaluates the full manifest.")
    parser.add_argument("--output-csv", default="docs/validation/analysis/major_11_flush_baseline_comparison.csv")
    parser.add_argument("--output-md", default="docs/validation/analysis/major_11_flush_baseline_comparison.md")
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


def stable_seed(label: str, base_seed: int) -> int:
    digest = hashlib.blake2b(label.encode("utf-8"), digest_size=4).hexdigest()
    return int((base_seed + int(digest, 16)) % (2**32 - 1))


def token(value: Any) -> str:
    if isinstance(value, (float, np.floating)):
        return f"{float(value):g}".replace(".", "p").replace("-", "m")
    return str(value).replace(".", "p").replace("-", "m")


def load_manifest(path: Path, max_candidates: int) -> pd.DataFrame:
    manifest = pd.read_csv(path)
    required = {
        "candidate_id",
        "cell_id",
        "price_z_threshold",
        "rsi_threshold",
        "vol_z_min",
        "bb_width_min",
        "use_weak_trend",
        "use_breakout_block",
        "require_close_below_bb",
        "signal_set_hash",
    }
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"Candidate manifest missing required columns: {sorted(missing)}")
    for column in ("use_weak_trend", "use_breakout_block", "require_close_below_bb"):
        manifest[column] = manifest[column].map(as_bool)
    if max_candidates > 0:
        manifest = manifest.head(max_candidates).copy()
    return manifest


def manifest_threshold_bounds(manifest: pd.DataFrame) -> dict[str, float]:
    return {
        "max_rsi": float(pd.to_numeric(manifest["rsi_threshold"], errors="coerce").max()),
        "min_price_z": float(pd.to_numeric(manifest["price_z_threshold"], errors="coerce").min()),
    }


def build_research_event_universe(
    prepared_frames: dict[str, pd.DataFrame],
    start: pd.Timestamp,
    end: pd.Timestamp,
    entry_price_mode: str,
    manifest: pd.DataFrame,
) -> pd.DataFrame:
    bounds = manifest_threshold_bounds(manifest)
    max_rsi = bounds["max_rsi"]
    min_price_z = bounds["min_price_z"]
    rows: list[pd.DataFrame] = []

    for pair, frame in prepared_frames.items():
        signal_window = (frame["date"] >= start) & (frame["date"] < end)
        close_below_bb_lower = (frame["close"] < frame["bb_lower"]).fillna(False)
        broad_mask = (
            signal_window
            & (frame["volume"] > 0)
            & (
                (frame["rsi"] < max_rsi)
                | (frame["price_z"] < -min_price_z)
                | close_below_bb_lower
            )
        ).fillna(False)
        selected = frame.loc[broad_mask].copy()
        if selected.empty:
            continue

        if entry_price_mode == "next_open":
            entry_offset = 1
            entry_price = frame["open"].shift(-1)
            entry_open = frame["open"].shift(-1)
            entry_timestamp = frame["date"].shift(-1)
        elif entry_price_mode == "signal_close":
            entry_offset = 0
            entry_price = frame["close"]
            entry_open = frame["open"]
            entry_timestamp = frame["date"]
        else:
            raise ValueError(f"Unsupported entry price mode: {entry_price_mode}")

        valid_entry = entry_price.replace([np.inf, -np.inf], np.nan).gt(0) & entry_timestamp.notna()
        selected = selected.loc[valid_entry.loc[selected.index]].copy()
        if selected.empty:
            continue

        event = pd.DataFrame(
            {
                "strategy": "major_11_flush_baseline_universe",
                "pair": pair,
                "timestamp": selected["date"],
                "signal_timestamp": selected["date"],
                "entry_timestamp": entry_timestamp.loc[selected.index],
                "year": selected["year"],
                "month": selected["month"],
                "quarter": selected["quarter"],
                "signal_index": selected.index.astype(int),
                "entry_index": selected.index.astype(int) + entry_offset,
                "signal_close": selected["close"],
                "entry_open": entry_open.loc[selected.index],
                "entry_price_mode": entry_price_mode,
                "entry_price": entry_price.loc[selected.index],
                "rsi": selected["rsi"],
                "price_z": selected["price_z"],
                "vol_z": selected["vol_z"],
                "vol_bucket": selected["vol_bucket"].astype(int),
                "natr": selected["natr"],
                "bb_width": selected["bb_width"],
                "active_pair": bool_series(selected, "active_pair"),
                "weak_trend_regime": bool_series(selected, "weak_trend_regime"),
                "breakout_block_long": bool_series(selected, "breakout_block_long"),
                "close_below_bb_lower": close_below_bb_lower.loc[selected.index],
            }
        )
        for label, candles in FORWARD_CANDLES.items():
            target = frame["close"].shift(-(entry_offset + candles))
            event[f"has_forward_{label}"] = target.loc[selected.index].notna()
            event[f"forward_{label}"] = (target.loc[selected.index] / event["entry_price"]) - 1.0

        max_candles = max(FORWARD_CANDLES.values())
        future_high = future_window_extreme(frame["high"], entry_offset + 1, max_candles, "max")
        future_low = future_window_extreme(frame["low"], entry_offset + 1, max_candles, "min")
        event["mfe_72h"] = (future_high.loc[selected.index] / event["entry_price"]) - 1.0
        event["mae_72h"] = (future_low.loc[selected.index] / event["entry_price"]) - 1.0
        rows.append(event)

    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def candidate_mask(events: pd.DataFrame, candidate: pd.Series) -> pd.Series:
    return build_flush_mask(
        events,
        safe_float(candidate["price_z_threshold"]),
        int(candidate["rsi_threshold"]),
        safe_float(candidate["vol_z_min"]),
        safe_float(candidate["bb_width_min"]),
        as_bool(candidate["use_weak_trend"]),
        as_bool(candidate["use_breakout_block"]),
        as_bool(candidate["require_close_below_bb"]),
    )


def baseline_specs(candidate: pd.Series) -> list[BaselineSpec]:
    price_z = safe_float(candidate["price_z_threshold"])
    rsi = int(candidate["rsi_threshold"])
    vol_z = safe_float(candidate["vol_z_min"])

    return [
        BaselineSpec(
            f"price_z_only_{token(price_z)}",
            f"price_z < -{price_z:g}",
            lambda events, z=price_z: events["price_z"] < -z,
        ),
        BaselineSpec(
            f"rsi_only_{token(rsi)}",
            f"rsi < {rsi}",
            lambda events, threshold=rsi: events["rsi"] < threshold,
        ),
        BaselineSpec(
            "bollinger_only",
            "close < bb_lower",
            lambda events: events["close_below_bb_lower"],
        ),
        BaselineSpec(
            f"price_z_{token(price_z)}_plus_rsi_{token(rsi)}",
            f"price_z < -{price_z:g} and rsi < {rsi}",
            lambda events, z=price_z, threshold=rsi: (events["price_z"] < -z) & (events["rsi"] < threshold),
        ),
        BaselineSpec(
            f"price_z_{token(price_z)}_plus_bb",
            f"price_z < -{price_z:g} and close < bb_lower",
            lambda events, z=price_z: (events["price_z"] < -z) & events["close_below_bb_lower"],
        ),
        BaselineSpec(
            f"price_z_{token(price_z)}_plus_vol_{token(vol_z)}",
            f"price_z < -{price_z:g} and vol_z > {vol_z:g}",
            lambda events, z=price_z, vol=vol_z: (events["price_z"] < -z) & (events["vol_z"] > vol),
        ),
        BaselineSpec(
            f"rsi_{token(rsi)}_plus_bollinger",
            f"rsi < {rsi} and close < bb_lower",
            lambda events, threshold=rsi: (events["rsi"] < threshold) & events["close_below_bb_lower"],
        ),
    ]


def pct_positive(values: pd.Series) -> float:
    clean = values.dropna()
    if clean.empty:
        return float("nan")
    return float((clean > 0).mean())


def bootstrap_median_ci(
    values: pd.Series,
    *,
    n_boot: int,
    seed: int,
    alpha: float = 0.05,
) -> tuple[float, float]:
    clean = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if len(clean) == 0 or n_boot <= 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    samples = rng.choice(clean, size=(n_boot, len(clean)), replace=True)
    medians = np.median(samples, axis=1)
    return float(np.quantile(medians, alpha / 2)), float(np.quantile(medians, 1 - alpha / 2))


def bootstrap_delta_median_ci(
    candidate_values: pd.Series,
    baseline_values: pd.Series,
    *,
    n_boot: int,
    seed: int,
    alpha: float = 0.05,
) -> tuple[float, float]:
    candidate_clean = pd.to_numeric(candidate_values, errors="coerce").dropna().to_numpy(dtype=float)
    baseline_clean = pd.to_numeric(baseline_values, errors="coerce").dropna().to_numpy(dtype=float)
    if len(candidate_clean) == 0 or len(baseline_clean) == 0 or n_boot <= 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    candidate_samples = rng.choice(candidate_clean, size=(n_boot, len(candidate_clean)), replace=True)
    baseline_samples = rng.choice(baseline_clean, size=(n_boot, len(baseline_clean)), replace=True)
    deltas = np.median(candidate_samples, axis=1) - np.median(baseline_samples, axis=1)
    return float(np.quantile(deltas, alpha / 2)), float(np.quantile(deltas, 1 - alpha / 2))


def median(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame:
        return float("nan")
    return float(pd.to_numeric(frame[column], errors="coerce").median())


def evaluate_signal_set(
    events: pd.DataFrame,
    mask: pd.Series,
    label: str,
    cluster_horizon: str,
    validation_start: pd.Timestamp,
    bootstrap_samples: int,
    random_seed: int,
) -> MetricResult:
    selected = events.loc[mask.fillna(False)].copy()
    cluster_events = first_cluster_events(selected, cluster_horizon)
    split_metrics = split_cluster_metrics(cluster_events, validation_start)
    ci_low, ci_high = bootstrap_median_ci(
        cluster_events["excess_forward_72h"] if "excess_forward_72h" in cluster_events else pd.Series(dtype=float),
        n_boot=bootstrap_samples,
        seed=stable_seed(label, random_seed),
    )

    metrics: dict[str, Any] = {
        "signals": int(len(selected)),
        "independent_clusters_72h": int(len(cluster_events)),
        "active_pairs": int(selected["pair"].nunique()) if not selected.empty else 0,
        "active_years": int(selected["year"].nunique()) if not selected.empty else 0,
        "active_months": int(selected["month"].nunique()) if not selected.empty else 0,
        "top_pair_signal_share": signal_share(selected["pair"]) if not selected.empty else float("nan"),
        "top_year_signal_share": signal_share(selected["year"]) if not selected.empty else float("nan"),
        "positive_pairs_72h": positive_group_count(cluster_events, "pair", "excess_forward_72h"),
        "positive_years_72h": positive_group_count(cluster_events, "year", "excess_forward_72h"),
        "cluster_forward_24h_median": median(cluster_events, "forward_24h"),
        "cluster_forward_72h_median": median(cluster_events, "forward_72h"),
        "cluster_null_24h_median": median(cluster_events, "null_forward_24h_median"),
        "cluster_null_72h_median": median(cluster_events, "null_forward_72h_median"),
        "cluster_excess_24h_median": median(cluster_events, "excess_forward_24h"),
        "cluster_excess_72h_median": median(cluster_events, "excess_forward_72h"),
        "cluster_excess_24h_p25": float(cluster_events["excess_forward_24h"].quantile(0.25)) if not cluster_events.empty else float("nan"),
        "cluster_excess_72h_p25": float(cluster_events["excess_forward_72h"].quantile(0.25)) if not cluster_events.empty else float("nan"),
        "cluster_excess_72h_median_ci_low": ci_low,
        "cluster_excess_72h_median_ci_high": ci_high,
        "forward_24h_win_rate": pct_positive(selected["forward_24h"]) if "forward_24h" in selected else float("nan"),
        "forward_72h_win_rate": pct_positive(selected["forward_72h"]) if "forward_72h" in selected else float("nan"),
        "mfe_72h_median": median(selected, "mfe_72h"),
        "mae_72h_median": median(selected, "mae_72h"),
        "null_sample_count_median": median(selected, "null_sample_count"),
    }
    metrics.update(split_metrics)
    return metrics, cluster_events


def comparable_delta(candidate: dict[str, Any], baseline: dict[str, Any], key: str) -> float:
    left = safe_float(candidate.get(key, float("nan")))
    right = safe_float(baseline.get(key, float("nan")))
    if np.isnan(left) or np.isnan(right):
        return float("nan")
    return left - right


def classify_baseline_comparison(row: dict[str, Any]) -> str:
    if row["candidate_clusters"] < 200:
        return "INSUFFICIENT_CANDIDATE_SAMPLE"
    if row["baseline_clusters"] < 200:
        return "INSUFFICIENT_BASELINE_SAMPLE"

    required = [
        "delta_cluster_excess_24h_median",
        "delta_cluster_excess_72h_median",
        "delta_validation_excess_72h_median",
    ]
    if any(pd.isna(row[key]) for key in required):
        return "BASELINE_UNDERPERFORMER"

    beats_24h = row["delta_cluster_excess_24h_median"] > 0
    beats_72h = row["delta_cluster_excess_72h_median"] > 0
    beats_validation = row["delta_validation_excess_72h_median"] > 0
    no_worse_breadth = (
        row["candidate_positive_pairs_72h"] >= row["baseline_positive_pairs_72h"] - 1
        and row["candidate_positive_years_72h"] >= row["baseline_positive_years_72h"] - 1
    )

    if beats_24h and beats_72h and beats_validation and no_worse_breadth:
        return "BASELINE_BEATER"

    if (
        abs(row["delta_cluster_excess_72h_median"]) <= 0.0025
        and abs(row["delta_validation_excess_72h_median"]) <= 0.0025
    ):
        return "BASELINE_EQUIVALENT"

    return "BASELINE_UNDERPERFORMER"


def comparison_row(
    candidate: pd.Series,
    baseline: BaselineSpec,
    candidate_metrics: dict[str, Any],
    baseline_metrics: dict[str, Any],
    candidate_clusters: pd.DataFrame,
    baseline_clusters: pd.DataFrame,
    bootstrap_samples: int,
    random_seed: int,
) -> dict[str, Any]:
    delta_ci_low, delta_ci_high = bootstrap_delta_median_ci(
        candidate_clusters["excess_forward_72h"] if "excess_forward_72h" in candidate_clusters else pd.Series(dtype=float),
        baseline_clusters["excess_forward_72h"] if "excess_forward_72h" in baseline_clusters else pd.Series(dtype=float),
        n_boot=bootstrap_samples,
        seed=stable_seed(f"{candidate['candidate_id']}|{baseline.name}", random_seed),
    )
    row: dict[str, Any] = {
        "candidate_id": candidate["candidate_id"],
        "selection_bucket": candidate.get("selection_bucket", ""),
        "selection_buckets": candidate.get("selection_buckets", ""),
        "cell_id": int(candidate["cell_id"]),
        "signal_set_hash": candidate["signal_set_hash"],
        "baseline_name": baseline.name,
        "baseline_description": baseline.description,
        "price_z_threshold": safe_float(candidate["price_z_threshold"]),
        "rsi_threshold": int(candidate["rsi_threshold"]),
        "vol_z_min": safe_float(candidate["vol_z_min"]),
        "bb_width_min": safe_float(candidate["bb_width_min"]),
        "use_weak_trend": as_bool(candidate["use_weak_trend"]),
        "use_breakout_block": as_bool(candidate["use_breakout_block"]),
        "require_close_below_bb": as_bool(candidate["require_close_below_bb"]),
        "candidate_signals": candidate_metrics["signals"],
        "baseline_signals": baseline_metrics["signals"],
        "candidate_clusters": candidate_metrics["independent_clusters_72h"],
        "baseline_clusters": baseline_metrics["independent_clusters_72h"],
        "candidate_cluster_excess_24h_median": candidate_metrics["cluster_excess_24h_median"],
        "baseline_cluster_excess_24h_median": baseline_metrics["cluster_excess_24h_median"],
        "candidate_cluster_excess_72h_median": candidate_metrics["cluster_excess_72h_median"],
        "baseline_cluster_excess_72h_median": baseline_metrics["cluster_excess_72h_median"],
        "candidate_validation_excess_72h_median": candidate_metrics["validation_excess_72h_median"],
        "baseline_validation_excess_72h_median": baseline_metrics["validation_excess_72h_median"],
        "candidate_positive_pairs_72h": candidate_metrics["positive_pairs_72h"],
        "baseline_positive_pairs_72h": baseline_metrics["positive_pairs_72h"],
        "candidate_positive_years_72h": candidate_metrics["positive_years_72h"],
        "baseline_positive_years_72h": baseline_metrics["positive_years_72h"],
        "candidate_top_pair_signal_share": candidate_metrics["top_pair_signal_share"],
        "baseline_top_pair_signal_share": baseline_metrics["top_pair_signal_share"],
        "candidate_top_year_signal_share": candidate_metrics["top_year_signal_share"],
        "baseline_top_year_signal_share": baseline_metrics["top_year_signal_share"],
        "candidate_cluster_excess_72h_median_ci_low": candidate_metrics["cluster_excess_72h_median_ci_low"],
        "candidate_cluster_excess_72h_median_ci_high": candidate_metrics["cluster_excess_72h_median_ci_high"],
        "baseline_cluster_excess_72h_median_ci_low": baseline_metrics["cluster_excess_72h_median_ci_low"],
        "baseline_cluster_excess_72h_median_ci_high": baseline_metrics["cluster_excess_72h_median_ci_high"],
        "delta_cluster_excess_72h_median_ci_low": delta_ci_low,
        "delta_cluster_excess_72h_median_ci_high": delta_ci_high,
    }
    row["delta_cluster_excess_24h_median"] = comparable_delta(
        candidate_metrics, baseline_metrics, "cluster_excess_24h_median"
    )
    row["delta_cluster_excess_72h_median"] = comparable_delta(
        candidate_metrics, baseline_metrics, "cluster_excess_72h_median"
    )
    row["delta_validation_excess_72h_median"] = comparable_delta(
        candidate_metrics, baseline_metrics, "validation_excess_72h_median"
    )
    row["decision"] = classify_baseline_comparison(row)
    return row


def run_comparisons(
    events: pd.DataFrame,
    manifest: pd.DataFrame,
    cluster_horizon: str,
    validation_start: pd.Timestamp,
    bootstrap_samples: int,
    random_seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    baseline_cache: dict[str, MetricResult] = {}
    candidate_summary_rows: list[dict[str, Any]] = []

    for _, candidate in manifest.iterrows():
        candidate_label = f"candidate:{candidate['candidate_id']}"
        candidate_metrics, candidate_clusters = evaluate_signal_set(
            events,
            candidate_mask(events, candidate),
            candidate_label,
            cluster_horizon,
            validation_start,
            bootstrap_samples,
            random_seed,
        )
        candidate_summary_rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "cell_id": int(candidate["cell_id"]),
                "signal_set_hash": candidate["signal_set_hash"],
                "signals": candidate_metrics["signals"],
                "independent_clusters_72h": candidate_metrics["independent_clusters_72h"],
                "cluster_excess_24h_median": candidate_metrics["cluster_excess_24h_median"],
                "cluster_excess_72h_median": candidate_metrics["cluster_excess_72h_median"],
                "validation_excess_72h_median": candidate_metrics["validation_excess_72h_median"],
                "positive_pairs_72h": candidate_metrics["positive_pairs_72h"],
                "positive_years_72h": candidate_metrics["positive_years_72h"],
                "selection_buckets": candidate.get("selection_buckets", ""),
            }
        )

        for baseline in baseline_specs(candidate):
            if baseline.name not in baseline_cache:
                baseline_cache[baseline.name] = evaluate_signal_set(
                    events,
                    baseline.mask_builder(events),
                    f"baseline:{baseline.name}",
                    cluster_horizon,
                    validation_start,
                    bootstrap_samples,
                    random_seed,
                )
            baseline_metrics, baseline_clusters = baseline_cache[baseline.name]
            rows.append(
                comparison_row(
                    candidate,
                    baseline,
                    candidate_metrics,
                    baseline_metrics,
                    candidate_clusters,
                    baseline_clusters,
                    bootstrap_samples,
                    random_seed,
                )
            )

    return pd.DataFrame(rows), pd.DataFrame(candidate_summary_rows)


def table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    return frame.to_markdown(index=False, floatfmt=".4f")


def markdown_report(
    comparisons: pd.DataFrame,
    candidate_summary: pd.DataFrame,
    manifest: pd.DataFrame,
    event_count: int,
    args: argparse.Namespace,
) -> str:
    decision_counts = comparisons["decision"].value_counts().rename_axis("decision").reset_index(name="comparisons")
    baseline_counts = (
        comparisons.groupby(["baseline_name", "decision"], as_index=False)
        .agg(comparisons=("candidate_id", "size"))
        .sort_values(["baseline_name", "decision"])
    )
    summary_by_candidate = (
        comparisons.groupby("candidate_id", as_index=False)
        .agg(
            baseline_beaters=("decision", lambda values: int((values == "BASELINE_BEATER").sum())),
            baseline_equivalents=("decision", lambda values: int((values == "BASELINE_EQUIVALENT").sum())),
            baseline_underperformers=("decision", lambda values: int((values == "BASELINE_UNDERPERFORMER").sum())),
            insufficient_samples=("decision", lambda values: int(values.astype(str).str.startswith("INSUFFICIENT").sum())),
        )
        .merge(candidate_summary, on="candidate_id", how="left")
        .sort_values(["baseline_beaters", "cluster_excess_72h_median"], ascending=[False, False])
    )
    display_columns = [
        "candidate_id",
        "baseline_name",
        "decision",
        "candidate_clusters",
        "baseline_clusters",
        "delta_cluster_excess_24h_median",
        "delta_cluster_excess_72h_median",
        "delta_validation_excess_72h_median",
        "delta_cluster_excess_72h_median_ci_low",
        "delta_cluster_excess_72h_median_ci_high",
        "candidate_positive_pairs_72h",
        "baseline_positive_pairs_72h",
        "candidate_positive_years_72h",
        "baseline_positive_years_72h",
        "cell_id",
    ]
    beater_rows = comparisons[comparisons["decision"] == "BASELINE_BEATER"].sort_values(
        ["delta_validation_excess_72h_median", "delta_cluster_excess_72h_median"], ascending=[False, False]
    )
    equivalent_rows = comparisons[comparisons["decision"] == "BASELINE_EQUIVALENT"].sort_values(
        ["candidate_id", "baseline_name"]
    )
    underperformer_rows = comparisons[comparisons["decision"] == "BASELINE_UNDERPERFORMER"].sort_values(
        ["delta_validation_excess_72h_median", "delta_cluster_excess_72h_median"], ascending=[True, True]
    )
    insufficient_rows = comparisons[comparisons["decision"].astype(str).str.startswith("INSUFFICIENT")].sort_values(
        ["decision", "candidate_id", "baseline_name"]
    )
    baseline_definitions = (
        comparisons[["baseline_name", "baseline_description"]]
        .drop_duplicates()
        .sort_values("baseline_name")
    )

    lines = [
        "# Major 11 Flush Baseline Comparison",
        "",
        "> Research diagnostic only. This compares frozen robust flush-surface candidates against simpler oversold/flush masks and does not add or promote any live/deployable strategy class.",
        "",
        "## Scope",
        "",
        f"- Surface CSV: `{args.surface_csv}`",
        f"- Frozen candidate manifest: `{args.candidate_manifest}`",
        f"- Manifest candidates evaluated: `{len(manifest)}`",
        f"- Broad event universe after anchored baseline prefilter: `{event_count}`",
        f"- Entry price mode: `{args.entry_price_mode}`",
        f"- Cluster horizon: `{args.cluster_horizon}`",
        f"- Matched-null samples per event: `{args.null_samples_per_event}`",
        f"- Matched-null fields: `{args.null_match}`",
        f"- Matched-null exclusion horizon: `{args.null_exclude_horizon}`",
        f"- Matched-null same-timestamp exclusion: `{args.null_exclude_same_timestamp}`",
        f"- Validation split start: `{args.validation_start}`",
        f"- Bootstrap samples: `{args.bootstrap_samples}`",
        "",
        "## Frozen Candidate Summary",
        "",
        table(candidate_summary),
        "",
        "## Baseline Definitions",
        "",
        table(baseline_definitions),
        "",
        "## Decision Counts",
        "",
        table(decision_counts),
        "",
        "## Baseline Decision Counts",
        "",
        table(baseline_counts),
        "",
        "## Candidate Summary",
        "",
        table(summary_by_candidate.head(40)),
        "",
        "## Baseline Beater Rows",
        "",
        table(beater_rows[display_columns].head(40)),
        "",
        "## Baseline Equivalent Rows",
        "",
        table(equivalent_rows[display_columns].head(40)),
        "",
        "## Baseline Underperformer Rows",
        "",
        table(underperformer_rows[display_columns].head(40)),
        "",
        "## Insufficient Sample Rows",
        "",
        table(insufficient_rows[display_columns].head(40)),
        "",
        "## Interpretation",
        "",
        "- `BASELINE_BEATER` means the robust candidate beats the anchored simple baseline at 24h cluster excess, 72h cluster excess, validation 72h excess, and is not materially worse on breadth.",
        "- `BASELINE_EQUIVALENT` means the candidate is within 25 bps of the baseline on both 72h cluster excess and validation excess.",
        "- `BASELINE_UNDERPERFORMER` means the added surface filters do not justify their complexity against that baseline.",
        "- `INSUFFICIENT_BASELINE_SAMPLE` means the simple baseline did not reach 200 independent 72h clusters.",
        "- Bootstrap intervals are resampled over first signals per pair/72h cluster, the effective research observations.",
        "",
        "## Next Decision Gate",
        "",
        "- If robust candidates beat simple baselines across cluster, validation, breadth, and null-excess metrics, proceed to flush-vs-rebound diagnostics.",
        "- If robust candidates are mostly equivalent to simple baselines, keep the simpler baseline as the research object.",
        "- If robust candidates mostly underperform simple baselines, retire the current flush-surface architecture rather than redesigning a live strategy.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    start = pd.Timestamp(args.start, tz="UTC")
    end = pd.Timestamp(args.end, tz="UTC")
    validation_start = pd.Timestamp(args.validation_start, tz="UTC")
    manifest = load_manifest(Path(args.candidate_manifest), args.max_candidates)
    pairs = load_pairs(Path(args.pairs_file))
    strategy = load_strategy(Path(args.strategy_file), Path(args.strategy_path), args.strategy_class)
    prepared_frames = prepare_pair_frames(strategy, pairs, Path(args.datadir), start, end)
    events = build_research_event_universe(prepared_frames, start, end, args.entry_price_mode, manifest)
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
    events = add_event_identity(events)
    comparisons, candidate_summary = run_comparisons(
        events,
        manifest,
        args.cluster_horizon,
        validation_start,
        args.bootstrap_samples,
        args.random_seed,
    )

    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    comparisons.to_csv(output_csv, index=False, float_format="%.6g")
    output_md.write_text(markdown_report(comparisons, candidate_summary, manifest, len(events), args), encoding="utf-8")
    print(f"Event universe: {len(events)}")
    print(f"Candidates evaluated: {len(manifest)}")
    print(f"Baseline comparisons: {len(comparisons)}")
    print(f"Baseline comparison written to {output_md}")


if __name__ == "__main__":
    main()
