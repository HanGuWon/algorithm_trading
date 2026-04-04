from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


FORWARD_HORIZONS = [1, 3, 6, 12, 24, 48]


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
            raise KeyError(f"Missing dataframe for {(pair, timeframe)}")
        return frame.copy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a raw-signal forward-return event study on PTI snapshots.")
    parser.add_argument("--anchors", nargs="+", required=True)
    parser.add_argument("--window-months", type=int, default=6)
    parser.add_argument("--snapshot-dir", default="user_data/pairs")
    parser.add_argument("--snapshot-top-n", type=int, default=50)
    parser.add_argument("--strategy-file", default="user_data/strategies/VolatilityRotationMR.py")
    parser.add_argument("--strategy-classes", nargs="+", default=["VolatilityRotationMR", "VolatilityRotationMRDiagnostic"])
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", required=True)
    return parser.parse_args()


def load_strategy(strategy_file: Path, class_name: str) -> Any:
    spec = importlib.util.spec_from_file_location("local_strategy_module_event_study", strategy_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import strategy file {strategy_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    strategy_class = getattr(module, class_name)
    return strategy_class(config={})


def snapshot_path(snapshot_dir: Path, anchor: str, top_n: int) -> Path:
    if top_n == 20:
        return snapshot_dir / f"binance_usdt_futures_snapshot_{anchor}.json"
    return snapshot_dir / f"binance_usdt_futures_snapshot_{anchor}_top{top_n}.json"


def load_snapshot_pairs(snapshot_json: Path) -> list[str]:
    payload = json.loads(snapshot_json.read_text(encoding="utf-8"))
    return list(payload["exchange"]["pair_whitelist"])


def pair_to_file_stem(pair: str) -> str:
    base, rest = pair.split("/", maxsplit=1)
    quote, settle = rest.split(":", maxsplit=1)
    return f"{base}_{quote}_{settle}"


def load_ohlcv(datadir: Path, pair: str, timeframe: str) -> pd.DataFrame:
    stem = pair_to_file_stem(pair)
    path = datadir / "futures" / f"{stem}-{timeframe}-futures.feather"
    frame = pd.read_feather(path)
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    return frame.sort_values("date").reset_index(drop=True)


def mean_hit_probability(frame: pd.DataFrame, index: int, side: str, horizon: int) -> bool:
    start_close = float(frame.at[index, "close"])
    target = float(frame.at[index, "bb_mid"])
    future = frame.iloc[index + 1 : index + 1 + horizon]
    if future.empty:
        return False
    if side == "long":
        return bool((future["high"] >= target).any()) if target >= start_close else bool((future["low"] <= target).any())
    return bool((future["low"] <= target).any()) if target <= start_close else bool((future["high"] >= target).any())


def compute_signal_events(strategy: Any, pairs: list[str], datadir: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    timeframe_minutes = strategy._timeframe_to_minutes(strategy.timeframe)
    preload_start = start - pd.Timedelta(minutes=int(strategy.startup_candle_count) * timeframe_minutes)

    pair_frames: dict[tuple[str, str], pd.DataFrame] = {}
    for pair in pairs:
        pair_frames[(pair, strategy.timeframe)] = load_ohlcv(datadir, pair, strategy.timeframe)
        pair_frames[(pair, strategy.informative_timeframe)] = load_ohlcv(datadir, pair, strategy.informative_timeframe)

    strategy.dp = LocalDataProvider(pair_frames=pair_frames, whitelist=pairs)

    rows: list[dict[str, object]] = []
    for pair in pairs:
        raw_5m = pair_frames[(pair, strategy.timeframe)]
        raw_1h = pair_frames[(pair, strategy.informative_timeframe)]
        pair_frames[(pair, strategy.informative_timeframe)] = raw_1h[(raw_1h["date"] >= preload_start) & (raw_1h["date"] <= end)].copy()
        frame = raw_5m[(raw_5m["date"] >= preload_start) & (raw_5m["date"] <= end)].copy()
        frame = strategy.populate_indicators(frame.copy(), {"pair": pair})
        frame = strategy.populate_entry_trend(frame.copy(), {"pair": pair})
        frame = frame.reset_index(drop=True)

        for side, column in (("long", "enter_long"), ("short", "enter_short")):
            signal_indices = frame.index[(frame["date"] >= start) & (frame["date"] <= end) & (frame[column] == 1)]
            direction = 1.0 if side == "long" else -1.0
            for idx in signal_indices:
                entry_price = float(frame.at[idx, "close"])
                future = frame.iloc[idx + 1 : idx + 49].copy()
                if future.empty or entry_price <= 0:
                    continue

                row: dict[str, object] = {
                    "pair": pair,
                    "date": frame.at[idx, "date"],
                    "month": frame.at[idx, "date"].strftime("%Y-%m"),
                    "side": side,
                    "entry_price": entry_price,
                    "bb_mid": float(frame.at[idx, "bb_mid"]),
                    "price_z": float(frame.at[idx, "price_z"]),
                    "rsi": float(frame.at[idx, "rsi"]),
                }

                for horizon in FORWARD_HORIZONS:
                    if idx + horizon >= len(frame):
                        row[f"ret_{horizon}"] = np.nan
                        row[f"mean_hit_{horizon}"] = np.nan
                        continue
                    forward_close = float(frame.at[idx + horizon, "close"])
                    row[f"ret_{horizon}"] = ((forward_close / entry_price) - 1.0) * direction
                    row[f"mean_hit_{horizon}"] = mean_hit_probability(frame, idx, side, horizon)

                if side == "long":
                    row["mfe_48"] = float(((future["high"] / entry_price) - 1.0).max())
                    row["mae_48"] = float(((future["low"] / entry_price) - 1.0).min())
                else:
                    row["mfe_48"] = float(((entry_price / future["low"]) - 1.0).max())
                    row["mae_48"] = float(((entry_price / future["high"]) - 1.0).min())
                rows.append(row)

    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    datadir = Path(args.datadir)
    snapshot_dir = Path(args.snapshot_dir)
    strategy_file = Path(args.strategy_file)
    event_frames: list[pd.DataFrame] = []

    for anchor_text in args.anchors:
        anchor = pd.Timestamp(anchor_text, tz="UTC")
        end = anchor + pd.DateOffset(months=args.window_months)
        snapshot = snapshot_path(snapshot_dir, anchor_text, args.snapshot_top_n)
        pairs = load_snapshot_pairs(snapshot)

        for strategy_class in args.strategy_classes:
            strategy = load_strategy(strategy_file, strategy_class)
            frame = compute_signal_events(strategy, pairs, datadir, anchor, end)
            if frame.empty:
                continue
            frame["anchor"] = anchor_text
            frame["strategy_class"] = strategy_class
            frame["strategy_variant"] = "diagnostic" if "Diagnostic" in strategy_class else "baseline"
            event_frames.append(frame)

    all_events = pd.concat(event_frames, ignore_index=True) if event_frames else pd.DataFrame()
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    all_events.to_csv(output_csv, index=False)

    summary = (
        all_events.groupby(["strategy_variant", "side"], as_index=False)[
            ["ret_1", "ret_3", "ret_6", "ret_12", "ret_24", "ret_48", "mfe_48", "mae_48"]
        ]
        .mean()
        if not all_events.empty
        else pd.DataFrame()
    )
    anchor_summary = (
        all_events.groupby(["anchor", "strategy_variant", "side"], as_index=False)
        .agg(
            signals=("pair", "size"),
            mean_hit_12=("mean_hit_12", "mean"),
            mean_hit_24=("mean_hit_24", "mean"),
            mean_hit_48=("mean_hit_48", "mean"),
            avg_ret_12=("ret_12", "mean"),
            avg_ret_24=("ret_24", "mean"),
            avg_ret_48=("ret_48", "mean"),
        )
        if not all_events.empty
        else pd.DataFrame()
    )
    monthly = (
        all_events.groupby(["month", "strategy_variant", "side"], as_index=False)
        .agg(signals=("pair", "size"), avg_ret_24=("ret_24", "mean"), mean_hit_24=("mean_hit_24", "mean"))
        if not all_events.empty
        else pd.DataFrame()
    )
    pair_summary = (
        all_events.groupby(["pair", "strategy_variant", "side"], as_index=False)
        .agg(signals=("pair", "size"), avg_ret_24=("ret_24", "mean"), mean_hit_24=("mean_hit_24", "mean"))
        .sort_values(["signals", "pair"], ascending=[False, True])
        .head(30)
        if not all_events.empty
        else pd.DataFrame()
    )

    lines = [
        "# Signal Event Study",
        "",
        f"- Anchors: `{', '.join(args.anchors)}`",
        f"- Window design: forward `{args.window_months}m` windows on top-{args.snapshot_top_n} PTI snapshots",
        f"- Forward horizons (candles): `{', '.join(str(value) for value in FORWARD_HORIZONS)}`",
        "",
        "## Mean Forward Returns by Variant and Side",
        "",
        summary.to_markdown(index=False) if not summary.empty else "No signal events were generated.",
        "",
        "## Anchor-Level Summary",
        "",
        anchor_summary.to_markdown(index=False) if not anchor_summary.empty else "No anchor-level summary is available.",
        "",
        "## Monthly Summary",
        "",
        monthly.to_markdown(index=False) if not monthly.empty else "No monthly summary is available.",
        "",
        "## Pair Summary",
        "",
        pair_summary.to_markdown(index=False) if not pair_summary.empty else "No pair summary is available.",
        "",
    ]
    Path(args.output_md).write_text("\n".join(lines), encoding="utf-8")
    print(f"Signal events: {len(all_events)}")
    print(f"Markdown report saved to {args.output_md}")
    print(f"CSV report saved to {args.output_csv}")


if __name__ == "__main__":
    main()
