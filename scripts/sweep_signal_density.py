from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class SweepProfile:
    name: str
    rank: int
    vol_z_min: float
    price_z_threshold: float
    bb_width_min: float
    adx_1h_max: int
    slope_cap: float


@dataclass
class SweepResult:
    profile: str
    rank: int
    vol_z_min: float
    price_z_threshold: float
    bb_width_min: float
    adx_1h_max: int
    slope_cap: float
    active_pair_rows: int
    weak_trend_rows: int
    long_signals: int
    short_signals: int
    total_signals: int


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


DEFAULT_PROFILES = [
    SweepProfile("baseline", 0, 2.00, 1.80, 0.040, 20, 0.0040),
    SweepProfile("vol_relaxed", 1, 1.50, 1.80, 0.040, 20, 0.0040),
    SweepProfile("price_relaxed", 1, 2.00, 1.50, 0.040, 20, 0.0040),
    SweepProfile("bb_relaxed", 1, 2.00, 1.80, 0.020, 20, 0.0040),
    SweepProfile("regime_relaxed", 1, 2.00, 1.80, 0.040, 24, 0.0060),
    SweepProfile("combined_mild", 2, 1.50, 1.65, 0.030, 22, 0.0050),
    SweepProfile("diagnostic", 3, 1.00, 1.50, 0.020, 24, 0.0060),
    SweepProfile("diagnostic_plus", 4, 0.75, 1.35, 0.015, 26, 0.0080),
    SweepProfile("exploratory_plus", 5, 0.50, 1.20, 0.010, 28, 0.0100),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sweep signal density for the PTI 2024 research universe.")
    parser.add_argument("--snapshot-json", required=True)
    parser.add_argument("--strategy-file", default="user_data/strategies/VolatilityRotationMR.py")
    parser.add_argument("--strategy-class", default="VolatilityRotationMR")
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--timerange", required=True, help="YYYYMMDD-YYYYMMDD")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--target-signals", type=int, default=20)
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


def build_prepared_frames(
    strategy: Any,
    pairs: list[str],
    datadir: Path,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict[str, pd.DataFrame]:
    timeframe_minutes = strategy._timeframe_to_minutes(strategy.timeframe)
    preload_start = start - pd.Timedelta(minutes=int(strategy.startup_candle_count) * timeframe_minutes)

    pair_frames: dict[tuple[str, str], pd.DataFrame] = {}
    for pair in pairs:
        pair_frames[(pair, strategy.timeframe)] = load_ohlcv(datadir, pair, strategy.timeframe)
        pair_frames[(pair, strategy.informative_timeframe)] = load_ohlcv(datadir, pair, strategy.informative_timeframe)

    strategy.dp = LocalDataProvider(pair_frames=pair_frames, whitelist=pairs)

    prepared: dict[str, pd.DataFrame] = {}
    for pair in pairs:
        raw_5m = pair_frames[(pair, strategy.timeframe)]
        raw_1h = pair_frames[(pair, strategy.informative_timeframe)]
        pair_frames[(pair, strategy.informative_timeframe)] = raw_1h[(raw_1h["date"] >= preload_start) & (raw_1h["date"] <= end)].copy()
        dataframe = raw_5m[(raw_5m["date"] >= preload_start) & (raw_5m["date"] <= end)].copy()
        dataframe = strategy.populate_indicators(dataframe.copy(), {"pair": pair})
        dataframe = dataframe[(dataframe["date"] >= start) & (dataframe["date"] <= end)].copy()
        dataframe["month"] = dataframe["date"].dt.strftime("%Y-%m")
        prepared[pair] = dataframe.reset_index(drop=True)
    return prepared


def evaluate_profile(
    profile: SweepProfile,
    prepared_frames: dict[str, pd.DataFrame],
    strategy: Any,
) -> tuple[SweepResult, pd.DataFrame, pd.DataFrame]:
    pair_rows: list[dict[str, Any]] = []
    monthly_rows: list[dict[str, Any]] = []

    natr_min = float(strategy.natr_min.value)
    rsi_long_threshold = float(strategy.rsi_long_threshold.value)
    rsi_short_threshold = float(strategy.rsi_short_threshold.value)

    active_total = 0
    weak_total = 0
    long_total = 0
    short_total = 0

    for pair, dataframe in prepared_frames.items():
        volume_gate = dataframe["volume"] > 0
        active_gate = volume_gate & (dataframe["vol_z"] > profile.vol_z_min) & (dataframe["natr"] > natr_min) & (dataframe["bb_width"] > profile.bb_width_min)
        weak_gate = active_gate & (dataframe["adx_1h"] < profile.adx_1h_max) & (dataframe["ema50_slope_1h"].abs() < profile.slope_cap)

        strong_trend_threshold = float(profile.adx_1h_max) + 5.0
        breakout_block_long = (
            (dataframe["adx_1h"] > strong_trend_threshold)
            & (dataframe["ema50_1h"] < dataframe["ema200_1h"])
            & (dataframe["ema50_slope_1h"] < -profile.slope_cap)
            & (dataframe["close_1h"] < dataframe["bb_lower_1h"])
        )
        breakout_block_short = (
            (dataframe["adx_1h"] > strong_trend_threshold)
            & (dataframe["ema50_1h"] > dataframe["ema200_1h"])
            & (dataframe["ema50_slope_1h"] > profile.slope_cap)
            & (dataframe["close_1h"] > dataframe["bb_upper_1h"])
        )

        long_signals = (
            weak_gate
            & ~breakout_block_long.fillna(False)
            & (dataframe["close"] < dataframe["bb_lower"])
            & (dataframe["rsi"] < rsi_long_threshold)
            & (dataframe["price_z"] < -profile.price_z_threshold)
            & dataframe["bullish_reversal"].fillna(False)
        )
        short_signals = (
            weak_gate
            & ~breakout_block_short.fillna(False)
            & (dataframe["close"] > dataframe["bb_upper"])
            & (dataframe["rsi"] > rsi_short_threshold)
            & (dataframe["price_z"] > profile.price_z_threshold)
            & dataframe["bearish_reversal"].fillna(False)
        )

        pair_long = int(long_signals.sum())
        pair_short = int(short_signals.sum())
        pair_active = int(active_gate.sum())
        pair_weak = int(weak_gate.sum())
        active_total += pair_active
        weak_total += pair_weak
        long_total += pair_long
        short_total += pair_short

        pair_rows.append(
            {
                "profile": profile.name,
                "pair": pair,
                "long_signals": pair_long,
                "short_signals": pair_short,
                "total_signals": pair_long + pair_short,
                "active_pair_rows": pair_active,
                "weak_trend_rows": pair_weak,
            }
        )

        monthly = pd.DataFrame(
            {
                "month": dataframe["month"],
                "long_signals": long_signals.astype(int),
                "short_signals": short_signals.astype(int),
            }
        ).groupby("month", as_index=False).sum()
        monthly["profile"] = profile.name
        monthly["pair"] = pair
        monthly_rows.extend(monthly.to_dict("records"))

    result = SweepResult(
        profile=profile.name,
        rank=profile.rank,
        vol_z_min=profile.vol_z_min,
        price_z_threshold=profile.price_z_threshold,
        bb_width_min=profile.bb_width_min,
        adx_1h_max=profile.adx_1h_max,
        slope_cap=profile.slope_cap,
        active_pair_rows=active_total,
        weak_trend_rows=weak_total,
        long_signals=long_total,
        short_signals=short_total,
        total_signals=long_total + short_total,
    )
    return result, pd.DataFrame(pair_rows), pd.DataFrame(monthly_rows)


def profile_table(results: list[SweepResult]) -> pd.DataFrame:
    return pd.DataFrame([result.__dict__ for result in results]).sort_values(["rank", "total_signals"], ascending=[True, False]).reset_index(drop=True)


def summarize_pair_contribution(pair_frame: pd.DataFrame, profile_name: str) -> pd.DataFrame:
    subset = pair_frame[pair_frame["profile"] == profile_name].copy()
    subset = subset[subset["total_signals"] > 0].sort_values(["total_signals", "long_signals", "short_signals"], ascending=False)
    return subset[["pair", "long_signals", "short_signals", "total_signals"]].reset_index(drop=True)


def summarize_monthly_distribution(monthly_frame: pd.DataFrame, profile_name: str) -> pd.DataFrame:
    subset = monthly_frame[monthly_frame["profile"] == profile_name].copy()
    if subset.empty:
        return pd.DataFrame(columns=["month", "long_signals", "short_signals", "total_signals"])
    grouped = subset.groupby("month", as_index=False)[["long_signals", "short_signals"]].sum()
    grouped["total_signals"] = grouped["long_signals"] + grouped["short_signals"]
    return grouped[grouped["total_signals"] > 0].reset_index(drop=True)


def choose_recommendation(summary: pd.DataFrame, target_signals: int) -> tuple[str | None, str]:
    eligible = summary[summary["total_signals"] >= target_signals].sort_values(["rank", "total_signals"], ascending=[True, False])
    if not eligible.empty:
        row = eligible.iloc[0]
        return str(row["profile"]), (
            f"`{row['profile']}` is the minimum tested relaxation that reaches the target sample size "
            f"with `{int(row['total_signals'])}` total entry signals."
        )

    best = summary.sort_values("total_signals", ascending=False).iloc[0]
    return None, (
        f"No tested profile reached the target sample size of `{target_signals}` signals. "
        f"The densest tested profile was `{best['profile']}` with `{int(best['total_signals'])}` signals."
    )


def write_markdown(
    path: Path,
    timerange: str,
    snapshot_json: str,
    summary: pd.DataFrame,
    pair_frame: pd.DataFrame,
    monthly_frame: pd.DataFrame,
    target_signals: int,
) -> None:
    recommended_profile, recommendation_text = choose_recommendation(summary, target_signals)
    highlight_profiles = ["baseline", "diagnostic"]
    if recommended_profile and recommended_profile not in highlight_profiles:
        highlight_profiles.append(recommended_profile)
    if "diagnostic_plus" not in highlight_profiles and "diagnostic_plus" in set(summary["profile"]):
        highlight_profiles.append("diagnostic_plus")
    if "exploratory_plus" not in highlight_profiles and "exploratory_plus" in set(summary["profile"]):
        highlight_profiles.append("exploratory_plus")

    lines = [
        "# PTI 2024 Signal Density Sweep",
        "",
        f"- Timerange: `{timerange}`",
        f"- Snapshot: `{snapshot_json}`",
        f"- Target signal count for usable sample: `{target_signals}`",
        "",
        "## Profile Summary",
        "",
        summary.to_markdown(index=False),
        "",
        "## Recommendation",
        "",
        recommendation_text,
        "",
    ]

    for profile_name in highlight_profiles:
        profile_rows = summary[summary["profile"] == profile_name]
        if profile_rows.empty:
            continue
        lines.extend(
            [
                f"## Profile: `{profile_name}`",
                "",
                profile_rows.to_markdown(index=False),
                "",
            ]
        )

        pair_contribution = summarize_pair_contribution(pair_frame, profile_name)
        if pair_contribution.empty:
            lines.extend(["No entry signals were generated for this profile.", ""])
        else:
            lines.extend(
                [
                    "### Pair Contribution",
                    "",
                    pair_contribution.to_markdown(index=False),
                    "",
                ]
            )

        monthly_distribution = summarize_monthly_distribution(monthly_frame, profile_name)
        if monthly_distribution.empty:
            lines.extend(["### Monthly Distribution", "", "No monthly distribution is available because no signals passed.", ""])
        else:
            lines.extend(
                [
                    "### Monthly Distribution",
                    "",
                    monthly_distribution.to_markdown(index=False),
                    "",
                ]
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    snapshot_path = Path(args.snapshot_json)
    datadir = Path(args.datadir)
    strategy = load_strategy(Path(args.strategy_file), args.strategy_class)
    start, end = parse_timerange(args.timerange)
    pairs = load_snapshot_pairs(snapshot_path)

    prepared = build_prepared_frames(strategy, pairs, datadir, start, end)

    results: list[SweepResult] = []
    pair_frames: list[pd.DataFrame] = []
    monthly_frames: list[pd.DataFrame] = []
    for profile in DEFAULT_PROFILES:
        result, pair_frame, monthly_frame = evaluate_profile(profile, prepared, strategy)
        results.append(result)
        pair_frames.append(pair_frame)
        monthly_frames.append(monthly_frame)

    summary = profile_table(results)
    pair_contribution = pd.concat(pair_frames, ignore_index=True)
    monthly_distribution = pd.concat(monthly_frames, ignore_index=True)

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_csv, index=False)

    write_markdown(
        path=Path(args.output_md),
        timerange=args.timerange,
        snapshot_json=args.snapshot_json,
        summary=summary,
        pair_frame=pair_contribution,
        monthly_frame=monthly_distribution,
        target_signals=args.target_signals,
    )

    print(summary.to_string(index=False))
    recommended_profile, recommendation_text = choose_recommendation(summary, args.target_signals)
    print()
    print(recommendation_text)
    if recommended_profile:
        print(f"Recommended profile: {recommended_profile}")


if __name__ == "__main__":
    main()
