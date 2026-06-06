from __future__ import annotations

import argparse
import itertools
from pathlib import Path
from typing import Any

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


PRICE_Z_THRESHOLDS = [1.5, 1.8, 2.0, 2.2, 2.5, 2.8, 3.1]
RSI_THRESHOLDS = [18, 22, 26, 30, 34]
VOL_Z_MINS = [0.0, 0.5, 1.0, 1.5]
BB_WIDTH_MINS = [0.0, 0.01, 0.02, 0.04]
WEAK_TREND_GATES = [False, True]
BREAKOUT_BLOCK_GATES = [False, True]
CLOSE_BELOW_BB_LOWER_GATES = [False, True]

RESEARCH_GATES = {
    "signals": 100,
    "independent_clusters_72h": 50,
    "active_pairs": 6,
    "active_years": 4,
    "top_pair_signal_share": 0.40,
    "top_year_signal_share": 0.50,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan simplified major-11 flush thresholds as a research diagnostic.")
    parser.add_argument("--pairs-file", default="user_data/pairs/binance_usdt_futures_major_11.json")
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--strategy-file", default="user_data/strategies/VolatilityRotationMRCandidates.py")
    parser.add_argument("--strategy-class", default="VolatilityRotationMRFlushReboundLongOnly")
    parser.add_argument("--start", default="2020-01-09")
    parser.add_argument("--end", default="2026-06-03")
    parser.add_argument("--entry-price-mode", choices=["signal_close", "next_open"], default="next_open")
    parser.add_argument("--cluster-horizon", default="72h")
    parser.add_argument("--null-samples-per-event", type=int, default=100)
    parser.add_argument("--null-match", default="pair,year,vol_bucket")
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--max-combinations", type=int, default=0, help="Optional smoke-test limit. Zero scans the full grid.")
    parser.add_argument("--output-md", default="docs/validation/analysis/major_11_flush_threshold_surface.md")
    parser.add_argument("--output-csv", default="docs/validation/analysis/major_11_flush_threshold_surface.csv")
    return parser.parse_args()


def bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(False, index=frame.index)
    return frame[column].fillna(False).astype(bool)


def future_window_extreme(series: pd.Series, start_offset: int, candles: int, method: str) -> pd.Series:
    shifted = series.shift(-start_offset)
    reversed_shifted = shifted.iloc[::-1]
    rolling = reversed_shifted.rolling(candles, min_periods=1)
    if method == "max":
        value = rolling.max()
    elif method == "min":
        value = rolling.min()
    else:
        raise ValueError(f"Unsupported future-window method: {method}")
    return value.iloc[::-1]


def build_candidate_events(
    prepared_frames: dict[str, pd.DataFrame],
    start: pd.Timestamp,
    end: pd.Timestamp,
    entry_price_mode: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    max_rsi = max(RSI_THRESHOLDS)
    min_price_z = min(PRICE_Z_THRESHOLDS)
    min_vol_z = min(VOL_Z_MINS)
    min_bb_width = min(BB_WIDTH_MINS)

    for pair, frame in prepared_frames.items():
        signal_window = (frame["date"] >= start) & (frame["date"] < end)
        candidate_mask = (
            signal_window
            & (frame["volume"] > 0)
            & (frame["rsi"] < max_rsi)
            & (frame["price_z"] < -min_price_z)
            & (frame["vol_z"] > min_vol_z)
            & (frame["bb_width"] > min_bb_width)
        ).fillna(False)
        selected = frame.loc[candidate_mask].copy()
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
                "strategy": "major_11_flush_threshold_surface",
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
                "price_z_abs": (-selected["price_z"]).clip(lower=0.0),
                "vol_z": selected["vol_z"],
                "vol_bucket": selected["vol_bucket"].astype(int),
                "natr": selected["natr"],
                "bb_width": selected["bb_width"],
                "weak_trend_regime": bool_series(selected, "weak_trend_regime"),
                "breakout_block_long": bool_series(selected, "breakout_block_long"),
                "close_below_bb_lower": (selected["close"] < selected["bb_lower"]).fillna(False),
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


def build_flush_mask(
    candidates: pd.DataFrame,
    price_z_threshold: float,
    rsi_threshold: float,
    vol_z_min: float,
    bb_width_min: float,
    use_weak_trend: bool,
    use_breakout_block: bool,
    require_close_below_bb: bool,
) -> pd.Series:
    mask = (
        (candidates["rsi"] < rsi_threshold)
        & (candidates["price_z"] < -price_z_threshold)
        & (candidates["vol_z"] > vol_z_min)
        & (candidates["bb_width"] > bb_width_min)
    )
    if require_close_below_bb:
        mask &= candidates["close_below_bb_lower"]
    if use_weak_trend:
        mask &= candidates["weak_trend_regime"]
    if use_breakout_block:
        mask &= ~candidates["breakout_block_long"]
    return mask.fillna(False)


def pct_positive(values: pd.Series) -> float:
    clean = values.dropna()
    if clean.empty:
        return float("nan")
    return float((clean > 0).mean())


def signal_share(values: pd.Series) -> float:
    if values.empty:
        return float("nan")
    return float(values.value_counts(normalize=True).iloc[0])


def independent_cluster_count(events: pd.DataFrame, horizon: str) -> int:
    if events.empty:
        return 0
    gap = pd.Timedelta(horizon)
    pair_changed = events["pair"].ne(events["pair"].shift())
    time_gap = events["signal_timestamp"].diff() > gap
    return int((pair_changed | time_gap.fillna(True)).sum())


def classify_decision(row: dict[str, Any]) -> str:
    if row["signals"] < RESEARCH_GATES["signals"] or row["independent_clusters_72h"] < RESEARCH_GATES["independent_clusters_72h"]:
        return "REJECT_LOW_DENSITY"
    if (
        row["active_pairs"] < RESEARCH_GATES["active_pairs"]
        or row["active_years"] < RESEARCH_GATES["active_years"]
        or row["top_pair_signal_share"] > RESEARCH_GATES["top_pair_signal_share"]
        or row["top_year_signal_share"] > RESEARCH_GATES["top_year_signal_share"]
    ):
        return "REJECT_CONCENTRATED"
    if (
        row["forward_24h_median"] <= 0
        or row["forward_72h_median"] <= 0
        or row["excess_24h_median"] <= 0
        or row["excess_72h_median"] <= 0
    ):
        return "REJECT_NO_FORWARD_EDGE"
    return "RESEARCH_CANDIDATE"


def evaluate_thresholds(
    candidates: pd.DataFrame,
    price_z_threshold: float,
    rsi_threshold: float,
    vol_z_min: float,
    bb_width_min: float,
    use_weak_trend: bool,
    use_breakout_block: bool,
    require_close_below_bb: bool,
    cluster_horizon: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "price_z_threshold": price_z_threshold,
        "rsi_threshold": rsi_threshold,
        "vol_z_min": vol_z_min,
        "bb_width_min": bb_width_min,
        "use_weak_trend": use_weak_trend,
        "use_breakout_block": use_breakout_block,
        "require_close_below_bb": require_close_below_bb,
    }
    if candidates.empty:
        row.update(empty_metrics())
        row["decision"] = classify_decision(row)
        return row

    selected = candidates[
        build_flush_mask(
            candidates,
            price_z_threshold,
            rsi_threshold,
            vol_z_min,
            bb_width_min,
            use_weak_trend,
            use_breakout_block,
            require_close_below_bb,
        )
    ].copy()
    if selected.empty:
        row.update(empty_metrics())
        row["decision"] = classify_decision(row)
        return row

    row.update(
        {
            "signals": int(len(selected)),
            "independent_clusters_72h": independent_cluster_count(selected, cluster_horizon),
            "active_pairs": int(selected["pair"].nunique()),
            "active_years": int(selected["year"].nunique()),
            "active_months": int(selected["month"].nunique()),
            "top_pair_signal_share": signal_share(selected["pair"]),
            "top_year_signal_share": signal_share(selected["year"]),
            "mfe_72h_median": float(selected["mfe_72h"].median()),
            "mae_72h_median": float(selected["mae_72h"].median()),
            "mae_72h_p10": float(selected["mae_72h"].quantile(0.10)),
            "null_matched_24h_median": float(selected["null_forward_24h_median"].median()),
            "null_matched_72h_median": float(selected["null_forward_72h_median"].median()),
            "excess_24h_median": float(selected["excess_forward_24h"].median()),
            "excess_72h_median": float(selected["excess_forward_72h"].median()),
        }
    )
    for label in FORWARD_CANDLES:
        row[f"valid_forward_{label}"] = int(selected[f"has_forward_{label}"].sum())
        row[f"forward_{label}_median"] = float(selected[f"forward_{label}"].median())
    row["forward_24h_win_rate"] = pct_positive(selected["forward_24h"])
    row["forward_72h_win_rate"] = pct_positive(selected["forward_72h"])
    row["decision"] = classify_decision(row)
    return row


def empty_metrics() -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "signals": 0,
        "independent_clusters_72h": 0,
        "active_pairs": 0,
        "active_years": 0,
        "active_months": 0,
        "top_pair_signal_share": float("nan"),
        "top_year_signal_share": float("nan"),
        "forward_24h_win_rate": float("nan"),
        "forward_72h_win_rate": float("nan"),
        "mfe_72h_median": float("nan"),
        "mae_72h_median": float("nan"),
        "mae_72h_p10": float("nan"),
        "null_matched_24h_median": float("nan"),
        "null_matched_72h_median": float("nan"),
        "excess_24h_median": float("nan"),
        "excess_72h_median": float("nan"),
    }
    for label in FORWARD_CANDLES:
        metrics[f"valid_forward_{label}"] = 0
        metrics[f"forward_{label}_median"] = float("nan")
    return metrics


def grid_rows() -> list[tuple[float, int, float, float, bool, bool, bool]]:
    return list(
        itertools.product(
            PRICE_Z_THRESHOLDS,
            RSI_THRESHOLDS,
            VOL_Z_MINS,
            BB_WIDTH_MINS,
            WEAK_TREND_GATES,
            BREAKOUT_BLOCK_GATES,
            CLOSE_BELOW_BB_LOWER_GATES,
        )
    )


def table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    return frame.to_markdown(index=False, floatfmt=".4f")


def markdown_report(surface: pd.DataFrame, candidate_count: int, args: argparse.Namespace) -> str:
    decision_counts = surface["decision"].value_counts().rename_axis("decision").reset_index(name="grid_cells")
    columns = [
        "decision",
        "signals",
        "independent_clusters_72h",
        "active_pairs",
        "active_years",
        "top_pair_signal_share",
        "top_year_signal_share",
        "forward_24h_median",
        "forward_72h_median",
        "null_matched_24h_median",
        "null_matched_72h_median",
        "excess_24h_median",
        "excess_72h_median",
        "price_z_threshold",
        "rsi_threshold",
        "vol_z_min",
        "bb_width_min",
        "use_weak_trend",
        "use_breakout_block",
        "require_close_below_bb",
    ]
    candidates = surface.sort_values(
        ["decision", "excess_72h_median", "signals"], ascending=[True, False, False]
    )
    research_candidates = surface[surface["decision"] == "RESEARCH_CANDIDATE"].sort_values(
        ["excess_72h_median", "signals"], ascending=[False, False]
    )
    high_density = surface.sort_values(["signals", "independent_clusters_72h"], ascending=[False, False]).head(20)

    lines = [
        "# Major 11 Flush Threshold Surface",
        "",
        "> Research diagnostic only. This scans simplified flush definitions and does not add or promote any live/deployable strategy class.",
        "",
        "## Scope",
        "",
        f"- Start: `{args.start}`",
        f"- End: `{args.end}` exclusive for signal timestamps",
        f"- Strategy indicators: `{args.strategy_class}`",
        f"- Entry price mode: `{args.entry_price_mode}`",
        f"- Cluster horizon: `{args.cluster_horizon}`",
        f"- Candidate events in loosened universe: `{candidate_count}`",
        f"- Grid cells scanned: `{len(surface)}`",
        f"- Matched-null samples per event: `{args.null_samples_per_event}`",
        f"- Matched-null fields: `{args.null_match}`",
        "",
        "## Research Gates",
        "",
        "- `signals >= 100`",
        "- `independent_clusters_72h >= 50`",
        "- `active_pairs >= 6`",
        "- `active_years >= 4`",
        "- `top_pair_signal_share <= 0.40`",
        "- `top_year_signal_share <= 0.50`",
        "- `forward_24h_median`, `forward_72h_median`, `excess_24h_median`, and `excess_72h_median` all positive",
        "",
        "## Decision Counts",
        "",
        table(decision_counts),
        "",
        "## Research Candidates",
        "",
        table(research_candidates[columns].head(20)),
        "",
        "## Highest Density Cells",
        "",
        table(high_density[columns]),
        "",
        "## Best Excess-72h Cells",
        "",
        table(candidates[columns].head(20)),
        "",
        "## Interpretation",
        "",
        "- `REJECT_LOW_DENSITY` means the sample remains below research scale even after loosening.",
        "- `REJECT_CONCENTRATED` means the surface is too dependent on a small set of pairs or years.",
        "- `REJECT_NO_FORWARD_EDGE` means density is adequate but raw or matched-null excess forward returns are not positive.",
        "- `RESEARCH_CANDIDATE` is still a diagnostic label, not a tradable-strategy approval.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    start = pd.Timestamp(args.start, tz="UTC")
    end = pd.Timestamp(args.end, tz="UTC")
    pairs = load_pairs(Path(args.pairs_file))
    strategy = load_strategy(Path(args.strategy_file), Path(args.strategy_path), args.strategy_class)
    prepared_frames = prepare_pair_frames(strategy, pairs, Path(args.datadir), start, end)
    candidates = build_candidate_events(prepared_frames, start, end, args.entry_price_mode)
    null_pool = build_null_pool(prepared_frames, args.entry_price_mode)
    candidates = attach_matched_null_controls(
        candidates,
        null_pool,
        parse_null_match(args.null_match),
        args.null_samples_per_event,
        args.random_seed,
    )

    combinations = grid_rows()
    if args.max_combinations > 0:
        combinations = combinations[: args.max_combinations]

    rows = [
        evaluate_thresholds(
            candidates,
            price_z_threshold,
            rsi_threshold,
            vol_z_min,
            bb_width_min,
            use_weak_trend,
            use_breakout_block,
            require_close_below_bb,
            args.cluster_horizon,
        )
        for (
            price_z_threshold,
            rsi_threshold,
            vol_z_min,
            bb_width_min,
            use_weak_trend,
            use_breakout_block,
            require_close_below_bb,
        ) in combinations
    ]

    surface = pd.DataFrame(rows)
    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    surface.to_csv(output_csv, index=False, float_format="%.6g")
    output_md.write_text(markdown_report(surface, len(candidates), args), encoding="utf-8")
    print(f"Candidate events: {len(candidates)}")
    print(f"Grid cells scanned: {len(surface)}")
    print(f"Threshold surface written to {output_md}")


if __name__ == "__main__":
    main()
