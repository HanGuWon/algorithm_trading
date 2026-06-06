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
    parser.add_argument("--output-md", default="docs/validation/analysis/major_11_flush_rebound_event_study.md")
    parser.add_argument("--output-csv", default="docs/validation/analysis/major_11_flush_rebound_event_study.csv")
    return parser.parse_args()


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


def compute_forward_row(frame: pd.DataFrame, index: int, entry_price: float) -> dict[str, float]:
    row: dict[str, float] = {}
    for label, candles in FORWARD_CANDLES.items():
        target = index + candles
        if target >= len(frame):
            row[f"forward_{label}"] = float("nan")
        else:
            row[f"forward_{label}"] = (float(frame.at[target, "close"]) / entry_price) - 1.0

    max_candles = max(FORWARD_CANDLES.values())
    future = frame.iloc[index + 1 : index + 1 + max_candles]
    if future.empty:
        row["mfe_72h"] = float("nan")
        row["mae_72h"] = float("nan")
    else:
        row["mfe_72h"] = (float(future["high"].max()) / entry_price) - 1.0
        row["mae_72h"] = (float(future["low"].min()) / entry_price) - 1.0
    return row


def signal_row(frame: pd.DataFrame, index: int, pair: str, strategy_name: str) -> dict[str, Any]:
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
        "timestamp": frame.at[index, "date"],
        "year": frame.at[index, "date"].strftime("%Y"),
        "month": frame.at[index, "date"].strftime("%Y-%m"),
        "entry_price": close,
        "flush_score": flush_score,
        "lower_band_extension": lower_band_extension,
        "rebound_score": rebound_score,
        "candle_rebound": candle_rebound,
        "previous_close_rebound": previous_close_rebound,
        "rsi": rsi,
        "price_z": price_z,
        "vol_z": safe_float(frame.at[index, "vol_z"]),
        "natr": safe_float(frame.at[index, "natr"]),
        "bb_width": safe_float(frame.at[index, "bb_width"]),
        "bb_mid_distance": ((bb_mid / close) - 1.0) if close > 0 and not np.isnan(bb_mid) else float("nan"),
        "adx_1h": safe_float(frame.at[index, "adx_1h"]),
        "ema50_slope_1h": safe_float(frame.at[index, "ema50_slope_1h"]),
        "active_pair": bool(frame.at[index, "active_pair"]),
        "weak_trend_regime": bool(frame.at[index, "weak_trend_regime"]),
        "enter_tag": str(frame.at[index, "enter_tag"]),
    }
    row.update(compute_forward_row(frame, index, close))
    return row


def compute_events(strategy: Any, strategy_name: str, pairs: list[str], datadir: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    timeframe_minutes = strategy._timeframe_to_minutes(strategy.timeframe)
    preload_start = start - pd.Timedelta(minutes=int(strategy.startup_candle_count) * timeframe_minutes)

    pair_frames: dict[tuple[str, str], pd.DataFrame] = {}
    for pair in pairs:
        pair_frames[(pair, strategy.timeframe)] = load_ohlcv(datadir, pair, strategy.timeframe)
        pair_frames[(pair, strategy.informative_timeframe)] = load_ohlcv(datadir, pair, strategy.informative_timeframe)

    strategy.dp = LocalDataProvider(pair_frames=pair_frames, whitelist=pairs)

    rows: list[dict[str, Any]] = []
    for pair in pairs:
        raw_5m = pair_frames[(pair, strategy.timeframe)]
        raw_1h = pair_frames[(pair, strategy.informative_timeframe)]
        pair_frames[(pair, strategy.informative_timeframe)] = raw_1h[
            (raw_1h["date"] >= preload_start) & (raw_1h["date"] < end)
        ].copy()
        frame = raw_5m[(raw_5m["date"] >= preload_start) & (raw_5m["date"] < end)].copy()
        frame = strategy.populate_indicators(frame, {"pair": pair})
        frame = strategy.populate_entry_trend(frame, {"pair": pair}).reset_index(drop=True)
        signal_indices = frame.index[(frame["date"] >= start) & (frame["date"] < end) & (frame["enter_long"] == 1)]
        rows.extend(signal_row(frame, int(index), pair, strategy_name) for index in signal_indices)
    return pd.DataFrame(rows)


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
        "active_pairs": ("pair", "nunique"),
        "median_flush_score": ("flush_score", "median"),
        "median_rebound_score": ("rebound_score", "median"),
        "mfe_72h_mean": ("mfe_72h", "mean"),
        "mae_72h_mean": ("mae_72h", "mean"),
    }
    for label in FORWARD_CANDLES:
        column = f"forward_{label}"
        aggregations[f"{column}_mean"] = (column, "mean")
        aggregations[f"{column}_median"] = (column, "median")
        aggregations[f"{column}_win_rate"] = (column, pct_positive)
    return events.groupby(group_cols, as_index=False).agg(**aggregations)


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
            forward_24h_median = float(row.get("forward_24h_median", float("nan")))
            forward_72h_median = float(row.get("forward_72h_median", float("nan")))
            sample_note = "below validation scale" if signals < 150 else "validation-scale sample"
            if forward_24h_median > 0 and forward_72h_median > 0:
                signal_note = "raw forward expectancy is positive at 24h and 72h medians"
            elif forward_24h_median > 0:
                signal_note = "raw forward expectancy is positive at 24h but not durable through 72h"
            else:
                signal_note = "raw forward expectancy is not positive at 24h median"
            readout.append(f"- `{strategy}`: {signals} signals, {sample_note}; {signal_note}.")

    lines = [
        "# Major 11 Flush/Rebound Event Study",
        "",
        "> Raw-signal event study requested after the external audit. This checks forward expectancy after every candidate signal, independent of exits, stoplosses, and portfolio logic.",
        "",
        "## Scope",
        "",
        f"- Start: `{args.start}`",
        f"- End: `{args.end}` exclusive",
        f"- Pairs file: `{args.pairs_file}`",
        f"- Strategies: `{', '.join(args.strategies)}`",
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
        "- If median 24h and 72h forward returns are near zero or negative, the raw flush signal is not yet showing durable forward expectancy.",
        "- If the signal count remains below validation scale, redesign should focus on simpler signal definitions before optimization.",
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

    frames: list[pd.DataFrame] = []
    for strategy_name in args.strategies:
        strategy = load_strategy(strategy_file, strategy_path, strategy_name)
        events = compute_events(strategy, strategy_name, pairs, datadir, start, end)
        frames.append(events)

    all_events = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
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
