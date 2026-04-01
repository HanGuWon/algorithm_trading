from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class FunnelResult:
    pair: str
    rows: int
    volume_rows: int
    active_pair_rows: int
    weak_trend_long_rows: int
    weak_trend_short_rows: int
    no_breakout_long_rows: int
    no_breakout_short_rows: int
    bb_breach_long_rows: int
    bb_breach_short_rows: int
    rsi_long_rows: int
    rsi_short_rows: int
    price_z_long_rows: int
    price_z_short_rows: int
    reversal_long_rows: int
    reversal_short_rows: int
    enter_long_rows: int
    enter_short_rows: int


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
    parser = argparse.ArgumentParser(description="Diagnose the VolatilityRotationMR entry funnel on a fixed historical universe.")
    parser.add_argument("--snapshot-json", required=True)
    parser.add_argument("--strategy-file", default="user_data/strategies/VolatilityRotationMR.py")
    parser.add_argument("--strategy-class", default="VolatilityRotationMR")
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--timerange", required=True, help="YYYYMMDD-YYYYMMDD")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", required=True)
    return parser.parse_args()


def parse_timerange(value: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    start_raw, end_raw = value.split("-", maxsplit=1)
    start = pd.Timestamp(start_raw, tz="UTC")
    end = pd.Timestamp(end_raw, tz="UTC")
    return start, end


def load_strategy(strategy_file: Path, class_name: str) -> Any:
    spec = importlib.util.spec_from_file_location("local_strategy_module", strategy_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import strategy file {strategy_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    strategy_class = getattr(module, class_name)
    return strategy_class(config={})


def load_snapshot_pairs(snapshot_path: Path) -> list[str]:
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
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


def build_result_frame(results: list[FunnelResult]) -> pd.DataFrame:
    return pd.DataFrame([result.__dict__ for result in results])


def pct(value: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return f"{(value / total):.1%}"


def write_markdown(path: Path, timerange: str, aggregate: pd.Series, frame: pd.DataFrame) -> None:
    total_rows = int(aggregate["rows"]) if not frame.empty else 0
    summary_rows = [
        {
            "gate": "volume > 0",
            "long_count": int(aggregate["volume_rows"]),
            "long_pass_rate": pct(int(aggregate["volume_rows"]), total_rows),
            "short_count": int(aggregate["volume_rows"]),
            "short_pass_rate": pct(int(aggregate["volume_rows"]), total_rows),
        },
        {
            "gate": "active_pair",
            "long_count": int(aggregate["active_pair_rows"]),
            "long_pass_rate": pct(int(aggregate["active_pair_rows"]), total_rows),
            "short_count": int(aggregate["active_pair_rows"]),
            "short_pass_rate": pct(int(aggregate["active_pair_rows"]), total_rows),
        },
        {
            "gate": "weak_trend_regime",
            "long_count": int(aggregate["weak_trend_long_rows"]),
            "long_pass_rate": pct(int(aggregate["weak_trend_long_rows"]), total_rows),
            "short_count": int(aggregate["weak_trend_short_rows"]),
            "short_pass_rate": pct(int(aggregate["weak_trend_short_rows"]), total_rows),
        },
        {
            "gate": "not breakout_block",
            "long_count": int(aggregate["no_breakout_long_rows"]),
            "long_pass_rate": pct(int(aggregate["no_breakout_long_rows"]), total_rows),
            "short_count": int(aggregate["no_breakout_short_rows"]),
            "short_pass_rate": pct(int(aggregate["no_breakout_short_rows"]), total_rows),
        },
        {
            "gate": "BB breach",
            "long_count": int(aggregate["bb_breach_long_rows"]),
            "long_pass_rate": pct(int(aggregate["bb_breach_long_rows"]), total_rows),
            "short_count": int(aggregate["bb_breach_short_rows"]),
            "short_pass_rate": pct(int(aggregate["bb_breach_short_rows"]), total_rows),
        },
        {
            "gate": "RSI threshold",
            "long_count": int(aggregate["rsi_long_rows"]),
            "long_pass_rate": pct(int(aggregate["rsi_long_rows"]), total_rows),
            "short_count": int(aggregate["rsi_short_rows"]),
            "short_pass_rate": pct(int(aggregate["rsi_short_rows"]), total_rows),
        },
        {
            "gate": "price_z threshold",
            "long_count": int(aggregate["price_z_long_rows"]),
            "long_pass_rate": pct(int(aggregate["price_z_long_rows"]), total_rows),
            "short_count": int(aggregate["price_z_short_rows"]),
            "short_pass_rate": pct(int(aggregate["price_z_short_rows"]), total_rows),
        },
        {
            "gate": "reversal confirmation",
            "long_count": int(aggregate["reversal_long_rows"]),
            "long_pass_rate": pct(int(aggregate["reversal_long_rows"]), total_rows),
            "short_count": int(aggregate["reversal_short_rows"]),
            "short_pass_rate": pct(int(aggregate["reversal_short_rows"]), total_rows),
        },
        {
            "gate": "final enter",
            "long_count": int(aggregate["enter_long_rows"]),
            "long_pass_rate": pct(int(aggregate["enter_long_rows"]), total_rows),
            "short_count": int(aggregate["enter_short_rows"]),
            "short_pass_rate": pct(int(aggregate["enter_short_rows"]), total_rows),
        },
    ]

    pair_table = frame[
        [
            "pair",
            "rows",
            "enter_long_rows",
            "enter_short_rows",
            "active_pair_rows",
            "bb_breach_long_rows",
            "bb_breach_short_rows",
            "reversal_long_rows",
            "reversal_short_rows",
        ]
    ].copy()

    lines = [
        "# Signal Funnel Report",
        "",
        f"- Timerange: `{timerange}`",
        f"- Total analyzed rows: `{total_rows}`",
        f"- Aggregate long entries: `{int(aggregate['enter_long_rows'])}`",
        f"- Aggregate short entries: `{int(aggregate['enter_short_rows'])}`",
        "",
        "## Aggregate Funnel",
        "",
        pd.DataFrame(summary_rows).to_markdown(index=False),
        "",
        "## Per-Pair Summary",
        "",
        pair_table.to_markdown(index=False),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    snapshot_path = Path(args.snapshot_json)
    datadir = Path(args.datadir)
    output_md = Path(args.output_md)
    output_csv = Path(args.output_csv)
    timerange = args.timerange
    start, end = parse_timerange(timerange)

    strategy = load_strategy(Path(args.strategy_file), args.strategy_class)
    pairs = load_snapshot_pairs(snapshot_path)

    startup_delta = pd.Timedelta(minutes=int(strategy.startup_candle_count) * 5)
    preload_start = start - startup_delta

    pair_frames: dict[tuple[str, str], pd.DataFrame] = {}
    for pair in pairs:
        five_minute = load_ohlcv(datadir, pair, strategy.timeframe)
        one_hour = load_ohlcv(datadir, pair, strategy.informative_timeframe)
        pair_frames[(pair, strategy.timeframe)] = five_minute
        pair_frames[(pair, strategy.informative_timeframe)] = one_hour

    strategy.dp = LocalDataProvider(pair_frames=pair_frames, whitelist=pairs)

    results: list[FunnelResult] = []
    for pair in pairs:
        raw_5m = pair_frames[(pair, strategy.timeframe)]
        raw_1h = pair_frames[(pair, strategy.informative_timeframe)]
        dataframe = raw_5m[(raw_5m["date"] >= preload_start) & (raw_5m["date"] <= end)].copy()
        pair_frames[(pair, strategy.informative_timeframe)] = raw_1h[(raw_1h["date"] >= preload_start) & (raw_1h["date"] <= end)].copy()
        dataframe = strategy.populate_indicators(dataframe.copy(), {"pair": pair})
        dataframe = strategy.populate_entry_trend(dataframe.copy(), {"pair": pair})
        dataframe = dataframe[(dataframe["date"] >= start) & (dataframe["date"] <= end)].copy()

        volume_gate = dataframe["volume"] > 0
        active_gate = volume_gate & dataframe["active_pair"].fillna(False)
        weak_long = active_gate & dataframe["weak_trend_regime"].fillna(False)
        weak_short = active_gate & dataframe["weak_trend_regime"].fillna(False)
        no_breakout_long = weak_long & ~dataframe["breakout_block_long"].fillna(False)
        no_breakout_short = weak_short & ~dataframe["breakout_block_short"].fillna(False)
        bb_breach_long = no_breakout_long & (dataframe["close"] < dataframe["bb_lower"])
        bb_breach_short = no_breakout_short & (dataframe["close"] > dataframe["bb_upper"])
        rsi_long = bb_breach_long & (dataframe["rsi"] < float(strategy.rsi_long_threshold.value))
        rsi_short = bb_breach_short & (dataframe["rsi"] > float(strategy.rsi_short_threshold.value))
        price_z_long = rsi_long & (dataframe["price_z"] < -float(strategy.price_z_threshold.value))
        price_z_short = rsi_short & (dataframe["price_z"] > float(strategy.price_z_threshold.value))
        reversal_long = price_z_long & dataframe["bullish_reversal"].fillna(False)
        reversal_short = price_z_short & dataframe["bearish_reversal"].fillna(False)

        results.append(
            FunnelResult(
                pair=pair,
                rows=len(dataframe),
                volume_rows=int(volume_gate.sum()),
                active_pair_rows=int(active_gate.sum()),
                weak_trend_long_rows=int(weak_long.sum()),
                weak_trend_short_rows=int(weak_short.sum()),
                no_breakout_long_rows=int(no_breakout_long.sum()),
                no_breakout_short_rows=int(no_breakout_short.sum()),
                bb_breach_long_rows=int(bb_breach_long.sum()),
                bb_breach_short_rows=int(bb_breach_short.sum()),
                rsi_long_rows=int(rsi_long.sum()),
                rsi_short_rows=int(rsi_short.sum()),
                price_z_long_rows=int(price_z_long.sum()),
                price_z_short_rows=int(price_z_short.sum()),
                reversal_long_rows=int(reversal_long.sum()),
                reversal_short_rows=int(reversal_short.sum()),
                enter_long_rows=int((dataframe["enter_long"] == 1).sum()),
                enter_short_rows=int((dataframe["enter_short"] == 1).sum()),
            )
        )

    frame = build_result_frame(results)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_csv, index=False)
    aggregate = frame.sum(numeric_only=True)
    write_markdown(output_md, timerange, aggregate, frame)

    print(f"Pairs analyzed: {len(pairs)}")
    print(f"Aggregate long entries: {int(aggregate['enter_long_rows'])}")
    print(f"Aggregate short entries: {int(aggregate['enter_short_rows'])}")
    print(f"CSV report saved to {output_csv}")
    print(f"Markdown report saved to {output_md}")


if __name__ == "__main__":
    main()
