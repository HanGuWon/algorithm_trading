from __future__ import annotations

import argparse
import importlib.util
import json
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd


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
    parser = argparse.ArgumentParser(description="Report monthly clustering for PTI signals and trades.")
    parser.add_argument("--snapshot-json", required=True)
    parser.add_argument("--strategy-file", default="user_data/strategies/VolatilityRotationMR.py")
    parser.add_argument("--strategy-class", default="VolatilityRotationMR")
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--timerange", required=True, help="YYYYMMDD-YYYYMMDD")
    parser.add_argument("--backtest-zip")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", required=True)
    return parser.parse_args()


def parse_timerange(value: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    start_raw, end_raw = value.split("-", maxsplit=1)
    return pd.Timestamp(start_raw, tz="UTC"), pd.Timestamp(end_raw, tz="UTC")


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


def build_signal_frames(
    strategy: Any,
    pairs: list[str],
    datadir: Path,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    timeframe_minutes = strategy._timeframe_to_minutes(strategy.timeframe)
    preload_start = start - pd.Timedelta(minutes=int(strategy.startup_candle_count) * timeframe_minutes)

    pair_frames: dict[tuple[str, str], pd.DataFrame] = {}
    for pair in pairs:
        pair_frames[(pair, strategy.timeframe)] = load_ohlcv(datadir, pair, strategy.timeframe)
        pair_frames[(pair, strategy.informative_timeframe)] = load_ohlcv(datadir, pair, strategy.informative_timeframe)

    strategy.dp = LocalDataProvider(pair_frames=pair_frames, whitelist=pairs)

    frames: list[pd.DataFrame] = []
    for pair in pairs:
        raw_5m = pair_frames[(pair, strategy.timeframe)]
        raw_1h = pair_frames[(pair, strategy.informative_timeframe)]
        pair_frames[(pair, strategy.informative_timeframe)] = raw_1h[(raw_1h["date"] >= preload_start) & (raw_1h["date"] <= end)].copy()
        dataframe = raw_5m[(raw_5m["date"] >= preload_start) & (raw_5m["date"] <= end)].copy()
        dataframe = strategy.populate_indicators(dataframe.copy(), {"pair": pair})
        dataframe = strategy.populate_entry_trend(dataframe.copy(), {"pair": pair})
        dataframe = dataframe[(dataframe["date"] >= start) & (dataframe["date"] <= end)].copy()
        dataframe["pair"] = pair
        dataframe["month"] = dataframe["date"].dt.strftime("%Y-%m")
        frames.append(dataframe[["pair", "month", "enter_long", "enter_short"]])
    return pd.concat(frames, ignore_index=True)


def load_trades(backtest_zip: Path, strategy_class: str) -> pd.DataFrame:
    with zipfile.ZipFile(backtest_zip) as archive:
        json_name = next(
            name
            for name in archive.namelist()
            if name.endswith(".json") and not name.endswith("_config.json")
        )
        payload = json.loads(archive.read(json_name).decode("utf-8"))

    strategy_results = payload["strategy"][strategy_class]
    trades = pd.DataFrame(strategy_results.get("trades", []))
    if trades.empty:
        return trades

    trades["open_date"] = pd.to_datetime(trades["open_date"], utc=True)
    trades["month"] = trades["open_date"].dt.strftime("%Y-%m")
    trades["side"] = trades["is_short"].map({True: "short", False: "long"})
    return trades


def monthly_signal_summary(signal_frame: pd.DataFrame) -> pd.DataFrame:
    monthly = signal_frame.groupby("month", as_index=False)[["enter_long", "enter_short"]].sum()
    monthly = monthly.rename(columns={"enter_long": "long_signals", "enter_short": "short_signals"})
    monthly["total_signals"] = monthly["long_signals"] + monthly["short_signals"]
    return monthly[monthly["total_signals"] > 0].reset_index(drop=True)


def pair_month_signal_summary(signal_frame: pd.DataFrame) -> pd.DataFrame:
    pair_month = signal_frame.groupby(["month", "pair"], as_index=False)[["enter_long", "enter_short"]].sum()
    pair_month = pair_month.rename(columns={"enter_long": "long_signals", "enter_short": "short_signals"})
    pair_month["total_signals"] = pair_month["long_signals"] + pair_month["short_signals"]
    pair_month = pair_month[pair_month["total_signals"] > 0]
    return pair_month.sort_values(["month", "total_signals", "pair"], ascending=[True, False, True]).reset_index(drop=True)


def monthly_trade_summary(trade_frame: pd.DataFrame) -> pd.DataFrame:
    if trade_frame.empty:
        return pd.DataFrame(columns=["month", "long_trades", "short_trades", "total_trades", "profit_abs"])
    monthly = (
        trade_frame.assign(long_trade=(trade_frame["side"] == "long").astype(int), short_trade=(trade_frame["side"] == "short").astype(int))
        .groupby("month", as_index=False)[["long_trade", "short_trade", "profit_abs"]]
        .sum()
        .rename(columns={"long_trade": "long_trades", "short_trade": "short_trades"})
    )
    monthly["total_trades"] = monthly["long_trades"] + monthly["short_trades"]
    return monthly[monthly["total_trades"] > 0].reset_index(drop=True)


def pair_month_trade_summary(trade_frame: pd.DataFrame) -> pd.DataFrame:
    if trade_frame.empty:
        return pd.DataFrame(columns=["month", "pair", "long_trades", "short_trades", "total_trades", "profit_abs"])
    pair_month = (
        trade_frame.assign(long_trade=(trade_frame["side"] == "long").astype(int), short_trade=(trade_frame["side"] == "short").astype(int))
        .groupby(["month", "pair"], as_index=False)[["long_trade", "short_trade", "profit_abs"]]
        .sum()
        .rename(columns={"long_trade": "long_trades", "short_trade": "short_trades"})
    )
    pair_month["total_trades"] = pair_month["long_trades"] + pair_month["short_trades"]
    return pair_month[pair_month["total_trades"] > 0].sort_values(["month", "total_trades", "pair"], ascending=[True, False, True]).reset_index(drop=True)


def write_markdown(
    path: Path,
    snapshot_json: str,
    strategy_class: str,
    timerange: str,
    monthly_signals: pd.DataFrame,
    pair_month_signals: pd.DataFrame,
    monthly_trades: pd.DataFrame,
    pair_month_trades: pd.DataFrame,
) -> None:
    lines = [
        "# Monthly Signal Clustering",
        "",
        f"- Snapshot: `{snapshot_json}`",
        f"- Strategy class: `{strategy_class}`",
        f"- Timerange: `{timerange}`",
        "",
        "## Monthly Signal Counts",
        "",
        monthly_signals.to_markdown(index=False) if not monthly_signals.empty else "No entry signals were generated.",
        "",
        "## Pair-by-Month Signal Contribution",
        "",
        pair_month_signals.to_markdown(index=False) if not pair_month_signals.empty else "No pair-by-month signal contribution is available.",
        "",
        "## Monthly Trade Counts",
        "",
        monthly_trades.to_markdown(index=False) if not monthly_trades.empty else "No backtest trades were available for monthly clustering.",
        "",
        "## Pair-by-Month Trade Contribution",
        "",
        pair_month_trades.to_markdown(index=False) if not pair_month_trades.empty else "No pair-by-month trade contribution is available.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    snapshot_path = Path(args.snapshot_json)
    strategy = load_strategy(Path(args.strategy_file), args.strategy_class)
    pairs = load_snapshot_pairs(snapshot_path)
    start, end = parse_timerange(args.timerange)

    signal_frame = build_signal_frames(strategy, pairs, Path(args.datadir), start, end)
    monthly_signals = monthly_signal_summary(signal_frame)
    pair_month_signals = pair_month_signal_summary(signal_frame)

    if args.backtest_zip:
        trades = load_trades(Path(args.backtest_zip), args.strategy_class)
    else:
        trades = pd.DataFrame()

    monthly_trades = monthly_trade_summary(trades)
    pair_month_trades = pair_month_trade_summary(trades)

    combined_rows: list[dict[str, object]] = []
    if not monthly_signals.empty:
        combined_rows.extend(monthly_signals.assign(section="monthly_signals", pair="").to_dict("records"))
    if not pair_month_signals.empty:
        combined_rows.extend(pair_month_signals.assign(section="pair_month_signals", profit_abs=pd.NA).to_dict("records"))
    if not monthly_trades.empty:
        combined_rows.extend(monthly_trades.assign(section="monthly_trades", pair="").to_dict("records"))
    if not pair_month_trades.empty:
        combined_rows.extend(pair_month_trades.assign(section="pair_month_trades").to_dict("records"))

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    if combined_rows:
        pd.DataFrame(combined_rows).to_csv(output_csv, index=False)
    else:
        pd.DataFrame(columns=["section"]).to_csv(output_csv, index=False)

    write_markdown(
        path=Path(args.output_md),
        snapshot_json=args.snapshot_json,
        strategy_class=args.strategy_class,
        timerange=args.timerange,
        monthly_signals=monthly_signals,
        pair_month_signals=pair_month_signals,
        monthly_trades=monthly_trades,
        pair_month_trades=pair_month_trades,
    )

    print(f"Signal months: {len(monthly_signals)}")
    print(f"Trade months: {len(monthly_trades)}")
    print(f"Markdown report saved to {args.output_md}")
    print(f"CSV report saved to {args.output_csv}")


if __name__ == "__main__":
    main()
