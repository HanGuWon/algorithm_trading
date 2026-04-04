from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

import pandas as pd


INDICATOR_COLUMNS = [
    "vol_z",
    "natr",
    "bb_width",
    "adx_1h",
    "ema50_slope_1h",
    "rsi",
    "price_z",
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
            raise KeyError(f"Missing dataframe for {(pair, timeframe)}")
        return frame.copy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize indicator values on signal candles and near-miss rows.")
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
    spec = importlib.util.spec_from_file_location("local_strategy_module_indicator_diag", strategy_file)
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


def collect_rows(strategy: Any, pairs: list[str], datadir: Path, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
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
        frame = frame[(frame["date"] >= start) & (frame["date"] <= end)].copy()

        volume_gate = frame["volume"] > 0
        long_signal = frame["enter_long"] == 1
        short_signal = frame["enter_short"] == 1
        near_long = volume_gate & frame["active_pair"].fillna(False) & frame["weak_trend_regime"].fillna(False) & ~frame["breakout_block_long"].fillna(False) & (frame["close"] < frame["bb_lower"]) & (frame["rsi"] < float(strategy.rsi_long_threshold.value)) & (frame["price_z"] < -float(strategy.price_z_threshold.value))
        near_short = volume_gate & frame["active_pair"].fillna(False) & frame["weak_trend_regime"].fillna(False) & ~frame["breakout_block_short"].fillna(False) & (frame["close"] > frame["bb_upper"]) & (frame["rsi"] > float(strategy.rsi_short_threshold.value)) & (frame["price_z"] > float(strategy.price_z_threshold.value))

        for side, mask, label in (
            ("long", long_signal, "signal"),
            ("short", short_signal, "signal"),
            ("long", near_long & ~long_signal, "near_miss"),
            ("short", near_short & ~short_signal, "near_miss"),
        ):
            subset = frame.loc[mask, ["date", *INDICATOR_COLUMNS]].copy()
            if subset.empty:
                continue
            subset["pair"] = pair
            subset["side"] = side
            subset["row_type"] = label
            rows.extend(subset.to_dict("records"))

    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    datadir = Path(args.datadir)
    snapshot_dir = Path(args.snapshot_dir)
    strategy_file = Path(args.strategy_file)
    frames: list[pd.DataFrame] = []

    for anchor_text in args.anchors:
        anchor = pd.Timestamp(anchor_text, tz="UTC")
        end = anchor + pd.DateOffset(months=args.window_months)
        snapshot = snapshot_path(snapshot_dir, anchor_text, args.snapshot_top_n)
        pairs = load_snapshot_pairs(snapshot)

        for strategy_class in args.strategy_classes:
            strategy = load_strategy(strategy_file, strategy_class)
            frame = collect_rows(strategy, pairs, datadir, anchor, end)
            if frame.empty:
                continue
            frame["anchor"] = anchor_text
            frame["strategy_variant"] = "diagnostic" if "Diagnostic" in strategy_class else "baseline"
            frames.append(frame)

    all_rows = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    all_rows.to_csv(output_csv, index=False)

    summary = (
        all_rows.groupby(["strategy_variant", "row_type", "side"], as_index=False)[INDICATOR_COLUMNS]
        .mean()
        if not all_rows.empty
        else pd.DataFrame()
    )
    pair_summary = (
        all_rows.groupby(["pair", "strategy_variant", "row_type", "side"], as_index=False)
        .size()
        .sort_values(["size", "pair"], ascending=[False, True])
        .head(30)
        if not all_rows.empty
        else pd.DataFrame()
    )

    lines = [
        "# Signal Indicator Diagnostics",
        "",
        f"- Anchors: `{', '.join(args.anchors)}`",
        f"- Window design: forward `{args.window_months}m` windows on top-{args.snapshot_top_n} PTI snapshots",
        f"- Indicator set: `{', '.join(INDICATOR_COLUMNS)}`",
        "",
        "## Mean Indicator Values",
        "",
        summary.to_markdown(index=False) if not summary.empty else "No signal or near-miss rows were found.",
        "",
        "## Pair Contribution",
        "",
        pair_summary.to_markdown(index=False) if not pair_summary.empty else "No pair contribution summary is available.",
        "",
    ]
    Path(args.output_md).write_text("\n".join(lines), encoding="utf-8")
    print(f"Diagnostic rows: {len(all_rows)}")
    print(f"Markdown report saved to {args.output_md}")
    print(f"CSV report saved to {args.output_csv}")


if __name__ == "__main__":
    main()
