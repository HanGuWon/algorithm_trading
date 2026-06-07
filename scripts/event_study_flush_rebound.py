from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


FORWARD_CANDLES = {
    "1h": 12,
    "4h": 48,
    "12h": 144,
    "24h": 288,
    "72h": 864,
}

DEFAULT_STRATEGIES = [
    "VolatilityRotationMRFlushReboundLongOnly",
    "VolatilityRotationMRDelayedConfirmLongOnly",
]


class LocalDataProvider:
    def __init__(self, pair_frames: dict[tuple[str, str], pd.DataFrame], whitelist: list[str]) -> None:
        self._pair_frames = pair_frames
        self._whitelist = whitelist
        self.runmode = type("RunModeStub", (), {"value": "backtest"})()

    def current_whitelist(self) -> list[str]:
        return list(self._whitelist)

    def get_pair_dataframe(self, pair: str, timeframe: str) -> pd.DataFrame:
        frame = self._pair_frames.get((pair, timeframe))
        if frame is None:
            raise KeyError(f"Missing dataframe for {pair} {timeframe}")
        return frame.copy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a major-11 flush/rebound raw-signal event study.")
    parser.add_argument("--pairs-file", default="user_data/pairs/binance_usdt_futures_major_11.json")
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--strategy-file", default="user_data/strategies/VolatilityRotationMRCandidates.py")
    parser.add_argument("--strategies", nargs="+", default=DEFAULT_STRATEGIES)
    parser.add_argument("--start", default="2020-01-09")
    parser.add_argument("--end", default="2026-06-03")
    parser.add_argument("--entry-price-mode", choices=["signal_close", "next_open"], default="next_open")
    parser.add_argument("--cluster-horizon", default="72h")
    parser.add_argument("--null-samples-per-event", type=int, default=100)
    parser.add_argument("--null-match", default="pair,year,vol_bucket")
    parser.add_argument("--null-exclude-horizon", default="72h")
    parser.add_argument("--null-exclude-same-timestamp", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--output-md", default="docs/validation/analysis/major_11_flush_rebound_event_study.md")
    parser.add_argument("--output-csv", default="docs/validation/analysis/major_11_flush_rebound_event_study.csv")
    return parser.parse_args()


def parse_null_match(value: str) -> tuple[str, ...]:
    fields = tuple(field.strip() for field in value.split(",") if field.strip())
    allowed = {"pair", "year", "month", "quarter", "vol_bucket"}
    unsupported = sorted(set(fields) - allowed)
    if unsupported:
        raise ValueError(f"Unsupported --null-match fields: {unsupported}")
    return fields


def load_pairs(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload["exchange"]["pair_whitelist"])


def pair_to_file_stem(pair: str) -> str:
    base, rest = pair.split("/", maxsplit=1)
    quote, settle = rest.split(":", maxsplit=1)
    return f"{base}_{quote}_{settle}"


def load_ohlcv(datadir: Path, pair: str, timeframe: str) -> pd.DataFrame:
    path = datadir / "futures" / f"{pair_to_file_stem(pair)}-{timeframe}-futures.feather"
    frame = pd.read_feather(path)
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    return frame.sort_values("date").reset_index(drop=True)


def load_strategy(strategy_file: Path, strategy_path: Path, class_name: str) -> Any:
    strategy_path_text = str(strategy_path.resolve())
    if strategy_path_text not in sys.path:
        sys.path.insert(0, strategy_path_text)
    spec = importlib.util.spec_from_file_location("major11_candidates", strategy_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import {strategy_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    strategy_class = getattr(module, class_name)
    return strategy_class(config={})


def safe_float(value: Any) -> float:
    try:
        if pd.isna(value):
            return float("nan")
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def add_vol_bucket(frame: pd.DataFrame, column: str = "natr", buckets: int = 5) -> pd.DataFrame:
    frame = frame.copy()
    values = pd.to_numeric(frame[column], errors="coerce") if column in frame else pd.Series(np.nan, index=frame.index)
    result = pd.Series(-1, index=frame.index, dtype="int64")
    valid = values.replace([np.inf, -np.inf], np.nan).notna()
    if int(valid.sum()) >= 2:
        bucket_count = min(buckets, int(valid.sum()))
        ranked = values[valid].rank(method="first")
        result.loc[valid] = pd.qcut(ranked, q=bucket_count, labels=False, duplicates="drop").astype("int64")
    frame["vol_bucket"] = result
    return frame


def add_calendar_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["year"] = frame["date"].dt.strftime("%Y")
    frame["month"] = frame["date"].dt.strftime("%Y-%m")
    frame["quarter"] = frame["date"].dt.year.astype(str) + "Q" + frame["date"].dt.quarter.astype(str)
    return frame


def prepare_pair_frames(
    strategy: Any,
    pairs: list[str],
    datadir: Path,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict[str, pd.DataFrame]:
    timeframe_minutes = strategy._timeframe_to_minutes(strategy.timeframe)
    preload_start = start - pd.Timedelta(minutes=int(strategy.startup_candle_count) * timeframe_minutes)
    forward_padding = pd.Timedelta(minutes=max(FORWARD_CANDLES.values()) * timeframe_minutes)
    load_end = end + forward_padding + pd.Timedelta(minutes=timeframe_minutes)

    pair_frames: dict[tuple[str, str], pd.DataFrame] = {}
    for pair in pairs:
        pair_frames[(pair, strategy.timeframe)] = load_ohlcv(datadir, pair, strategy.timeframe)
        pair_frames[(pair, strategy.informative_timeframe)] = load_ohlcv(datadir, pair, strategy.informative_timeframe)

    strategy.dp = LocalDataProvider(pair_frames=pair_frames, whitelist=pairs)

    prepared: dict[str, pd.DataFrame] = {}
    for pair in pairs:
        raw_5m = pair_frames[(pair, strategy.timeframe)]
        raw_1h = pair_frames[(pair, strategy.informative_timeframe)]
        pair_frames[(pair, strategy.informative_timeframe)] = raw_1h[
            (raw_1h["date"] >= preload_start) & (raw_1h["date"] < load_end)
        ].copy()
        frame = raw_5m[(raw_5m["date"] >= preload_start) & (raw_5m["date"] < load_end)].copy()
        frame = strategy.populate_indicators(frame, {"pair": pair}).reset_index(drop=True)
        frame = add_calendar_columns(add_vol_bucket(frame))
        prepared[pair] = frame
    return prepared


def resolve_entry(frame: pd.DataFrame, signal_index: int, mode: str) -> dict[str, Any] | None:
    signal_close = safe_float(frame.at[signal_index, "close"])
    signal_timestamp = frame.at[signal_index, "date"]
    if mode == "signal_close":
        entry_index = signal_index
        entry_open = safe_float(frame.at[signal_index, "open"])
        entry_timestamp = signal_timestamp
        entry_price = signal_close
    elif mode == "next_open":
        entry_index = signal_index + 1
        if entry_index >= len(frame):
            return None
        entry_open = safe_float(frame.at[entry_index, "open"])
        entry_timestamp = frame.at[entry_index, "date"]
        entry_price = entry_open
    else:
        raise ValueError(f"Unsupported entry price mode: {mode}")

    if not np.isfinite(entry_price) or entry_price <= 0:
        return None
    return {
        "signal_index": signal_index,
        "entry_index": entry_index,
        "signal_timestamp": signal_timestamp,
        "entry_timestamp": entry_timestamp,
        "signal_close": signal_close,
        "entry_open": entry_open,
        "entry_price_mode": mode,
        "entry_price": entry_price,
    }


def compute_forward_row(frame: pd.DataFrame, entry_index: int, entry_price: float) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for label, candles in FORWARD_CANDLES.items():
        target = entry_index + candles
        has_forward = target < len(frame)
        row[f"has_forward_{label}"] = bool(has_forward)
        if not has_forward:
            row[f"forward_{label}"] = float("nan")
        else:
            row[f"forward_{label}"] = (float(frame.at[target, "close"]) / entry_price) - 1.0

    max_candles = max(FORWARD_CANDLES.values())
    future = frame.iloc[entry_index + 1 : entry_index + 1 + max_candles]
    if future.empty:
        row["mfe_72h"] = float("nan")
        row["mae_72h"] = float("nan")
    else:
        row["mfe_72h"] = (float(future["high"].max()) / entry_price) - 1.0
        row["mae_72h"] = (float(future["low"].min()) / entry_price) - 1.0
    return row


def signal_row(
    frame: pd.DataFrame,
    index: int,
    pair: str,
    strategy_name: str,
    entry_price_mode: str,
) -> dict[str, Any] | None:
    entry = resolve_entry(frame, index, entry_price_mode)
    if entry is None:
        return None

    close = safe_float(frame.at[index, "close"])
    open_price = safe_float(frame.at[index, "open"])
    prev_close = safe_float(frame.at[index - 1, "close"]) if index > 0 else float("nan")
    bb_lower = safe_float(frame.at[index, "bb_lower"])
    bb_mid = safe_float(frame.at[index, "bb_mid"])
    price_z = safe_float(frame.at[index, "price_z"])
    rsi = safe_float(frame.at[index, "rsi"])

    flush_score = max(-price_z, 0.0) if not np.isnan(price_z) else float("nan")
    lower_band_extension = ((bb_lower / close) - 1.0) if close > 0 and not np.isnan(bb_lower) else float("nan")
    candle_rebound = ((close / open_price) - 1.0) if open_price > 0 else float("nan")
    previous_close_rebound = ((close / prev_close) - 1.0) if prev_close > 0 else float("nan")
    rebound_score = max(candle_rebound, 0.0) + max(previous_close_rebound, 0.0)

    row: dict[str, Any] = {
        "strategy": strategy_name,
        "pair": pair,
        "timestamp": entry["signal_timestamp"],
        "signal_timestamp": entry["signal_timestamp"],
        "entry_timestamp": entry["entry_timestamp"],
        "year": frame.at[index, "year"],
        "month": frame.at[index, "month"],
        "quarter": frame.at[index, "quarter"],
        "signal_index": entry["signal_index"],
        "entry_index": entry["entry_index"],
        "signal_close": entry["signal_close"],
        "entry_open": entry["entry_open"],
        "entry_price_mode": entry["entry_price_mode"],
        "entry_price": entry["entry_price"],
        "flush_score": flush_score,
        "lower_band_extension": lower_band_extension,
        "rebound_score": rebound_score,
        "candle_rebound": candle_rebound,
        "previous_close_rebound": previous_close_rebound,
        "rsi": rsi,
        "price_z": price_z,
        "vol_z": safe_float(frame.at[index, "vol_z"]),
        "vol_bucket": int(frame.at[index, "vol_bucket"]),
        "natr": safe_float(frame.at[index, "natr"]),
        "bb_width": safe_float(frame.at[index, "bb_width"]),
        "bb_mid_distance": ((bb_mid / close) - 1.0) if close > 0 and not np.isnan(bb_mid) else float("nan"),
        "adx_1h": safe_float(frame.at[index, "adx_1h"]),
        "ema50_slope_1h": safe_float(frame.at[index, "ema50_slope_1h"]),
        "active_pair": bool(frame.at[index, "active_pair"]),
        "weak_trend_regime": bool(frame.at[index, "weak_trend_regime"]),
        "breakout_block_long": bool(frame.at[index, "breakout_block_long"]),
        "enter_tag": str(frame.at[index, "enter_tag"]),
    }
    row.update(compute_forward_row(frame, int(entry["entry_index"]), float(entry["entry_price"])))
    return row


def build_null_pool(prepared_frames: dict[str, pd.DataFrame], entry_price_mode: str) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for pair, frame in prepared_frames.items():
        pool = frame[["date", "year", "month", "quarter", "vol_bucket", "open", "close"]].copy()
        pool["pair"] = pair
        if entry_price_mode == "next_open":
            pool["entry_price"] = frame["open"].shift(-1)
            entry_offset = 1
        elif entry_price_mode == "signal_close":
            pool["entry_price"] = frame["close"]
            entry_offset = 0
        else:
            raise ValueError(f"Unsupported entry price mode: {entry_price_mode}")

        valid_entry = pool["entry_price"].replace([np.inf, -np.inf], np.nan).gt(0)
        for label, candles in FORWARD_CANDLES.items():
            target = frame["close"].shift(-(entry_offset + candles))
            pool[f"forward_{label}"] = (target / pool["entry_price"]) - 1.0
            pool[f"has_forward_{label}"] = valid_entry & target.notna()
        pool = pool[valid_entry & pool["has_forward_72h"]].copy()
        rows.append(
            pool[
                [
                    "pair",
                    "date",
                    "year",
                    "month",
                    "quarter",
                    "vol_bucket",
                    *[f"forward_{label}" for label in FORWARD_CANDLES],
                ]
            ]
        )
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _match_key(row: pd.Series, fields: tuple[str, ...]) -> tuple[Any, ...]:
    return tuple(row[field] for field in fields)


def _lookup_key(key: Any) -> tuple[Any, ...]:
    return key if isinstance(key, tuple) else (key,)


def attach_matched_null_controls(
    events: pd.DataFrame,
    null_pool: pd.DataFrame,
    match_fields: tuple[str, ...],
    samples_per_event: int,
    random_seed: int,
    exclude_horizon: str | None = "72h",
    exclude_same_timestamp: bool = True,
) -> pd.DataFrame:
    events = events.copy()
    for label in ("24h", "72h"):
        events[f"null_forward_{label}_median"] = np.nan
        events[f"excess_forward_{label}"] = np.nan
    events["null_sample_count"] = 0
    if events.empty or null_pool.empty or samples_per_event <= 0:
        return events

    required = set(match_fields) | {"forward_24h", "forward_72h"}
    if not required.issubset(null_pool.columns):
        return events

    rng = np.random.default_rng(random_seed)
    clean_pool = null_pool.dropna(subset=["forward_24h", "forward_72h"]).reset_index(drop=True)
    grouped = clean_pool.groupby(list(match_fields), dropna=False).indices
    forward_24h = clean_pool["forward_24h"].to_numpy(dtype=float)
    forward_72h = clean_pool["forward_72h"].to_numpy(dtype=float)
    pool_dates = pd.to_datetime(clean_pool["date"], utc=True).to_numpy(dtype="datetime64[ns]") if "date" in clean_pool else None
    pool_pairs = clean_pool["pair"].astype(str).to_numpy() if "pair" in clean_pool else None
    gap = pd.Timedelta(exclude_horizon) if exclude_horizon else pd.Timedelta(0)
    use_time_exclusion = pool_dates is not None and (exclude_same_timestamp or gap > pd.Timedelta(0))

    for key, event_indices in events.groupby(list(match_fields), dropna=False).groups.items():
        key = _lookup_key(key)
        candidate_indices = grouped.get(key)
        if candidate_indices is None or len(candidate_indices) == 0:
            continue
        candidate_indices = np.asarray(candidate_indices, dtype=np.int64)

        if not use_time_exclusion:
            take = rng.choice(candidate_indices, size=(len(event_indices), samples_per_event), replace=True)
            null_24h = np.nanmedian(forward_24h[take], axis=1)
            null_72h = np.nanmedian(forward_72h[take], axis=1)
            raw_24h = pd.to_numeric(events.loc[event_indices, "forward_24h"], errors="coerce").to_numpy(dtype=float)
            raw_72h = pd.to_numeric(events.loc[event_indices, "forward_72h"], errors="coerce").to_numpy(dtype=float)
            events.loc[event_indices, "null_sample_count"] = int(samples_per_event)
            events.loc[event_indices, "null_forward_24h_median"] = null_24h
            events.loc[event_indices, "null_forward_72h_median"] = null_72h
            events.loc[event_indices, "excess_forward_24h"] = raw_24h - null_24h
            events.loc[event_indices, "excess_forward_72h"] = raw_72h - null_72h
            continue

        same_pair_fast_path = "pair" in match_fields
        if same_pair_fast_path:
            order = np.argsort(pool_dates[candidate_indices])
            sorted_indices = candidate_indices[order]
            sorted_dates = pool_dates[sorted_indices]

        event_index_array = np.asarray(list(event_indices))
        event_frame = events.loc[event_index_array]
        event_timestamps = pd.to_datetime(event_frame["signal_timestamp"], utc=True).dt.tz_localize(None).to_numpy(
            dtype="datetime64[ns]"
        )
        raw_24h_values = pd.to_numeric(event_frame["forward_24h"], errors="coerce").to_numpy(dtype=float)
        raw_72h_values = pd.to_numeric(event_frame["forward_72h"], errors="coerce").to_numpy(dtype=float)
        event_pairs = event_frame["pair"].astype(str).to_numpy() if not same_pair_fast_path else None
        null_24h_values = np.full(len(event_index_array), np.nan, dtype=float)
        null_72h_values = np.full(len(event_index_array), np.nan, dtype=float)
        sample_counts = np.zeros(len(event_index_array), dtype=int)

        for offset, event_ts in enumerate(event_timestamps):
            left_bound = event_ts - np.timedelta64(gap.value, "ns")
            right_bound = event_ts + np.timedelta64(gap.value, "ns")

            if same_pair_fast_path:
                left = int(np.searchsorted(sorted_dates, left_bound, side="left"))
                right = int(np.searchsorted(sorted_dates, right_bound, side="right"))
                eligible_count = left + max(0, len(sorted_indices) - right)
                if eligible_count <= 0:
                    continue
                draw_slots = rng.integers(0, eligible_count, size=samples_per_event)
                take = np.where(draw_slots < left, sorted_indices[draw_slots], sorted_indices[right + (draw_slots - left)])
            else:
                event_pair = event_pairs[offset]
                exclude_mask = (pool_pairs[candidate_indices] == event_pair) & (
                    (pool_dates[candidate_indices] >= left_bound) & (pool_dates[candidate_indices] <= right_bound)
                )
                eligible = candidate_indices[~exclude_mask]
                if len(eligible) == 0:
                    continue
                take = rng.choice(eligible, size=samples_per_event, replace=True)

            null_24h_values[offset] = float(np.nanmedian(forward_24h[take]))
            null_72h_values[offset] = float(np.nanmedian(forward_72h[take]))
            sample_counts[offset] = int(samples_per_event)

        events.loc[event_index_array, "null_sample_count"] = sample_counts
        events.loc[event_index_array, "null_forward_24h_median"] = null_24h_values
        events.loc[event_index_array, "null_forward_72h_median"] = null_72h_values
        events.loc[event_index_array, "excess_forward_24h"] = raw_24h_values - null_24h_values
        events.loc[event_index_array, "excess_forward_72h"] = raw_72h_values - null_72h_values
    return events


def compute_strategy_events(
    strategy: Any,
    strategy_name: str,
    prepared_frames: dict[str, pd.DataFrame],
    start: pd.Timestamp,
    end: pd.Timestamp,
    entry_price_mode: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for pair, prepared in prepared_frames.items():
        frame = strategy.populate_entry_trend(prepared.copy(), {"pair": pair}).reset_index(drop=True)
        signal_indices = frame.index[(frame["date"] >= start) & (frame["date"] < end) & (frame["enter_long"] == 1)]
        for index in signal_indices:
            row = signal_row(frame, int(index), pair, strategy_name, entry_price_mode)
            if row is not None:
                rows.append(row)
    return pd.DataFrame(rows)


def compute_events(
    strategy: Any,
    strategy_name: str,
    pairs: list[str],
    datadir: Path,
    start: pd.Timestamp,
    end: pd.Timestamp,
    entry_price_mode: str = "next_open",
) -> pd.DataFrame:
    prepared_frames = prepare_pair_frames(strategy, pairs, datadir, start, end)
    return compute_strategy_events(strategy, strategy_name, prepared_frames, start, end, entry_price_mode)


def add_event_clusters(events: pd.DataFrame, horizon: str = "72h") -> pd.DataFrame:
    if events.empty:
        return events
    ts_col = "signal_timestamp" if "signal_timestamp" in events.columns else "timestamp"
    events = events.sort_values(["strategy", "pair", ts_col]).reset_index(drop=True).copy()
    gap = pd.Timedelta(horizon)
    cluster_ids: list[int] = []
    current_cluster = -1
    last_key: tuple[str, str] | None = None
    last_time: pd.Timestamp | None = None
    for row in events.itertuples(index=False):
        key = (str(getattr(row, "strategy")), str(getattr(row, "pair")))
        ts = pd.Timestamp(getattr(row, ts_col))
        if key != last_key or last_time is None or ts - last_time > gap:
            current_cluster += 1
        cluster_ids.append(current_cluster)
        last_key = key
        last_time = ts

    events["cluster_id_72h"] = cluster_ids
    events["cluster_start"] = events.groupby("cluster_id_72h")[ts_col].transform("min")
    events["cluster_size"] = events.groupby("cluster_id_72h")[ts_col].transform("size").astype(int)
    events["is_first_signal_in_cluster"] = ~events.duplicated("cluster_id_72h")
    events["independent_signal_count"] = events.groupby("strategy")["is_first_signal_in_cluster"].transform("sum").astype(int)
    return events


def pct_positive(values: pd.Series) -> float:
    clean = values.dropna()
    if clean.empty:
        return float("nan")
    return float((clean > 0).mean())


def build_summary(events: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame()
    aggregations: dict[str, Any] = {
        "signals": ("pair", "size"),
        "independent_clusters_72h": ("is_first_signal_in_cluster", "sum"),
        "active_pairs": ("pair", "nunique"),
        "median_flush_score": ("flush_score", "median"),
        "median_rebound_score": ("rebound_score", "median"),
        "mfe_72h_mean": ("mfe_72h", "mean"),
        "mfe_72h_median": ("mfe_72h", "median"),
        "mae_72h_mean": ("mae_72h", "mean"),
        "mae_72h_median": ("mae_72h", "median"),
        "null_sample_count_median": ("null_sample_count", "median"),
    }
    for label in FORWARD_CANDLES:
        column = f"forward_{label}"
        aggregations[f"valid_{column}"] = (f"has_forward_{label}", "sum")
        aggregations[f"{column}_mean"] = (column, "mean")
        aggregations[f"{column}_median"] = (column, "median")
        aggregations[f"{column}_win_rate"] = (column, pct_positive)
    for label in ("24h", "72h"):
        aggregations[f"null_forward_{label}_median"] = (f"null_forward_{label}_median", "median")
        aggregations[f"excess_forward_{label}_median"] = (f"excess_forward_{label}", "median")
    summary = events.groupby(group_cols, as_index=False).agg(**aggregations)
    summary["independent_clusters_72h"] = summary["independent_clusters_72h"].astype(int)
    for label in FORWARD_CANDLES:
        summary[f"valid_forward_{label}"] = summary[f"valid_forward_{label}"].astype(int)
    return summary


def table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    return frame.to_markdown(index=False, floatfmt=".4f")


def markdown_report(events: pd.DataFrame, args: argparse.Namespace) -> str:
    strategy_summary = build_summary(events, ["strategy"])
    pair_summary = build_summary(events, ["strategy", "pair"]).sort_values(
        ["strategy", "signals", "pair"], ascending=[True, False, True]
    )
    year_summary = build_summary(events, ["strategy", "year"]).sort_values(["strategy", "year"])
    readout: list[str] = []
    if not strategy_summary.empty:
        for row in strategy_summary.to_dict("records"):
            strategy = str(row["strategy"])
            signals = int(row["signals"])
            clusters = int(row["independent_clusters_72h"])
            forward_24h_median = float(row.get("forward_24h_median", float("nan")))
            forward_72h_median = float(row.get("forward_72h_median", float("nan")))
            excess_24h_median = float(row.get("excess_forward_24h_median", float("nan")))
            excess_72h_median = float(row.get("excess_forward_72h_median", float("nan")))
            sample_note = "below validation scale" if clusters < 50 or signals < 100 else "validation-scale sample"
            if forward_24h_median > 0 and forward_72h_median > 0 and excess_24h_median > 0 and excess_72h_median > 0:
                signal_note = "raw and matched-null excess medians are positive at 24h and 72h"
            elif forward_24h_median > 0 and forward_72h_median > 0:
                signal_note = "raw medians are positive, but matched-null excess is not fully confirmed"
            else:
                signal_note = "raw forward expectancy is not yet durable"
            readout.append(f"- `{strategy}`: {signals} raw signals / {clusters} independent 72h clusters, {sample_note}; {signal_note}.")

    lines = [
        "# Major 11 Flush/Rebound Event Study",
        "",
        "> Raw-signal event study requested after the external audit. This checks forward expectancy after every candidate signal, independent of exits, stoplosses, and portfolio logic.",
        "",
        "## Scope",
        "",
        f"- Start: `{args.start}`",
        f"- End: `{args.end}` exclusive for signal timestamps",
        f"- Pairs file: `{args.pairs_file}`",
        f"- Strategies: `{', '.join(args.strategies)}`",
        f"- Entry price mode: `{args.entry_price_mode}`",
        f"- Cluster horizon: `{args.cluster_horizon}`",
        f"- Matched-null samples per event: `{args.null_samples_per_event}`",
        f"- Matched-null fields: `{args.null_match}`",
        f"- Matched-null exclusion horizon: `{args.null_exclude_horizon}`",
        f"- Matched-null same-timestamp exclusion: `{args.null_exclude_same_timestamp}`",
        f"- Forward horizons: `{', '.join(FORWARD_CANDLES.keys())}`",
        "",
        "## Strategy Summary",
        "",
        table(strategy_summary),
        "",
        "## Research Readout",
        "",
        "\n".join(readout) if readout else "No strategy readout is available.",
        "",
        "## Pair Summary",
        "",
        table(pair_summary.head(40)),
        "",
        "## Year Summary",
        "",
        table(year_summary),
        "",
        "## Interpretation Rules",
        "",
        "- Treat this as signal research, not a tradable strategy result.",
        "- `next_open` is the default entry mode because Freqtrade enters after the signal candle closes.",
        "- Raw signal count and independent 72h cluster count must both reach research scale before any strategy promotion discussion.",
        "- Positive raw forward medians should be discounted unless matched random null excess is also positive.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    datadir = Path(args.datadir)
    strategy_path = Path(args.strategy_path)
    strategy_file = Path(args.strategy_file)
    start = pd.Timestamp(args.start, tz="UTC")
    end = pd.Timestamp(args.end, tz="UTC")
    pairs = load_pairs(Path(args.pairs_file))
    match_fields = parse_null_match(args.null_match)

    frames: list[pd.DataFrame] = []
    for strategy_name in args.strategies:
        strategy = load_strategy(strategy_file, strategy_path, strategy_name)
        prepared_frames = prepare_pair_frames(strategy, pairs, datadir, start, end)
        events = compute_strategy_events(strategy, strategy_name, prepared_frames, start, end, args.entry_price_mode)
        null_pool = build_null_pool(prepared_frames, args.entry_price_mode)
        events = attach_matched_null_controls(
            events,
            null_pool,
            match_fields,
            args.null_samples_per_event,
            args.random_seed,
            args.null_exclude_horizon,
            args.null_exclude_same_timestamp,
        )
        frames.append(events)

    all_events = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    all_events = add_event_clusters(all_events, args.cluster_horizon)
    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    all_events.to_csv(output_csv, index=False)
    output_md.write_text(markdown_report(all_events, args), encoding="utf-8")
    print(f"Signal events: {len(all_events)}")
    print(f"Event study written to {output_md}")


if __name__ == "__main__":
    main()
