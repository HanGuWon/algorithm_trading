from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


PAIR_PATTERN = re.compile(
    r"^(?P<base>.+)_(?P<quote>[A-Z0-9]+)_(?P<settle>[A-Z0-9]+)-(?P<timeframe>[^-]+)-futures\.feather$"
)


@dataclass
class CoverageResult:
    pair: str
    file_name: str
    lookback_bars: int
    expected_lookback_bars: int
    lookback_coverage: float
    post_bars: int
    expected_post_bars: int
    post_coverage: float
    first_candle: pd.Timestamp | None
    last_candle: pd.Timestamp | None
    approx_quote_volume: float
    selected: bool
    exclusion_reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a point-in-time Freqtrade static pair snapshot from historical candles.")
    parser.add_argument(
        "--datadir",
        default="user_data/data/binance",
        help="Freqtrade exchange data directory. Example: user_data/data/binance",
    )
    parser.add_argument(
        "--reference-date",
        required=True,
        help="Reference timestamp in ISO format. Example: 2024-01-01 or 2024-01-01T00:00:00+00:00",
    )
    parser.add_argument("--quote-currency", default="USDT")
    parser.add_argument("--settle-currency", default="USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument(
        "--lookback",
        default="7d",
        help="Ranking lookback window. Supports pandas Timedelta strings such as 7d, 72h.",
    )
    parser.add_argument(
        "--post-window",
        default="30d",
        help="Forward coverage window after the reference date. Supports pandas Timedelta strings.",
    )
    parser.add_argument(
        "--min-coverage-ratio",
        type=float,
        default=0.95,
        help="Minimum required coverage ratio in both the lookback and post window.",
    )
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument(
        "--output-json",
        required=True,
        help="Path to the output Freqtrade StaticPairList JSON snapshot.",
    )
    parser.add_argument(
        "--output-csv",
        required=True,
        help="Path to the output CSV coverage report.",
    )
    parser.add_argument(
        "--output-md",
        required=True,
        help="Path to the output Markdown coverage report.",
    )
    return parser.parse_args()


def timeframe_to_timedelta(timeframe: str) -> pd.Timedelta:
    if timeframe.endswith("m"):
        return pd.Timedelta(minutes=int(timeframe[:-1]))
    if timeframe.endswith("h"):
        return pd.Timedelta(hours=int(timeframe[:-1]))
    if timeframe.endswith("d"):
        return pd.Timedelta(days=int(timeframe[:-1]))
    raise ValueError(f"Unsupported timeframe: {timeframe}")


def parse_reference_date(value: str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def parse_pair_from_filename(path: Path, quote_currency: str, settle_currency: str, timeframe: str) -> str | None:
    match = PAIR_PATTERN.match(path.name)
    if not match:
        return None
    if match.group("quote") != quote_currency or match.group("settle") != settle_currency:
        return None
    if match.group("timeframe") != timeframe:
        return None
    base = match.group("base")
    return f"{base}/{quote_currency}:{settle_currency}"


def expected_bars(window: pd.Timedelta, timeframe_delta: pd.Timedelta) -> int:
    bars = window / timeframe_delta
    return int(math.floor(bars + 1e-9))


def evaluate_pair(
    path: Path,
    pair: str,
    reference_date: pd.Timestamp,
    lookback: pd.Timedelta,
    post_window: pd.Timedelta,
    timeframe_delta: pd.Timedelta,
    min_coverage_ratio: float,
) -> CoverageResult:
    df = pd.read_feather(path, columns=["date", "high", "low", "close", "volume"])
    if df.empty:
        return CoverageResult(
            pair=pair,
            file_name=path.name,
            lookback_bars=0,
            expected_lookback_bars=expected_bars(lookback, timeframe_delta),
            lookback_coverage=0.0,
            post_bars=0,
            expected_post_bars=expected_bars(post_window, timeframe_delta),
            post_coverage=0.0,
            first_candle=None,
            last_candle=None,
            approx_quote_volume=0.0,
            selected=False,
            exclusion_reason="empty file",
        )

    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.sort_values("date").reset_index(drop=True)

    lookback_start = reference_date - lookback
    lookback_end = reference_date
    post_end = reference_date + post_window

    lookback_df = df[(df["date"] >= lookback_start) & (df["date"] < lookback_end)]
    post_df = df[(df["date"] >= reference_date) & (df["date"] < post_end)]

    expected_lookback = expected_bars(lookback, timeframe_delta)
    expected_post = expected_bars(post_window, timeframe_delta)
    lookback_coverage = len(lookback_df) / expected_lookback if expected_lookback else 0.0
    post_coverage = len(post_df) / expected_post if expected_post else 0.0

    typical_price = (lookback_df["high"] + lookback_df["low"] + lookback_df["close"]) / 3.0
    approx_quote_volume = float((typical_price * lookback_df["volume"]).sum())

    selected = True
    exclusion_reason = ""
    if lookback_coverage < min_coverage_ratio:
        selected = False
        exclusion_reason = f"lookback coverage {lookback_coverage:.1%} below {min_coverage_ratio:.0%}"
    elif post_coverage < min_coverage_ratio:
        selected = False
        exclusion_reason = f"post coverage {post_coverage:.1%} below {min_coverage_ratio:.0%}"

    return CoverageResult(
        pair=pair,
        file_name=path.name,
        lookback_bars=len(lookback_df),
        expected_lookback_bars=expected_lookback,
        lookback_coverage=lookback_coverage,
        post_bars=len(post_df),
        expected_post_bars=expected_post,
        post_coverage=post_coverage,
        first_candle=df["date"].iloc[0],
        last_candle=df["date"].iloc[-1],
        approx_quote_volume=approx_quote_volume,
        selected=selected,
        exclusion_reason=exclusion_reason,
    )


def to_dataframe(results: list[CoverageResult]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for result in results:
        rows.append(
            {
                "pair": result.pair,
                "file_name": result.file_name,
                "lookback_bars": result.lookback_bars,
                "expected_lookback_bars": result.expected_lookback_bars,
                "lookback_coverage": round(result.lookback_coverage, 6),
                "post_bars": result.post_bars,
                "expected_post_bars": result.expected_post_bars,
                "post_coverage": round(result.post_coverage, 6),
                "first_candle": "" if result.first_candle is None else result.first_candle.isoformat(),
                "last_candle": "" if result.last_candle is None else result.last_candle.isoformat(),
                "approx_quote_volume": result.approx_quote_volume,
                "selected": result.selected,
                "exclusion_reason": result.exclusion_reason,
            }
        )
    frame = pd.DataFrame(rows)
    return frame.sort_values(
        by=["selected", "approx_quote_volume", "lookback_coverage", "post_coverage"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)


def write_snapshot(path: Path, pairs: list[str]) -> None:
    payload = {
        "$schema": "https://schema.freqtrade.io/schema.json",
        "exchange": {
            "pair_whitelist": pairs,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_markdown(
    path: Path,
    reference_date: pd.Timestamp,
    lookback: pd.Timedelta,
    post_window: pd.Timedelta,
    top_n: int,
    eligible_frame: pd.DataFrame,
    all_frame: pd.DataFrame,
) -> None:
    selected_pairs = eligible_frame["pair"].tolist()[:top_n]
    top_frame = eligible_frame.head(top_n)[
        ["pair", "approx_quote_volume", "lookback_bars", "post_bars", "lookback_coverage", "post_coverage"]
    ].copy()
    if not top_frame.empty:
        top_frame["approx_quote_volume"] = top_frame["approx_quote_volume"].map(lambda value: f"{value:,.0f}")
        top_frame["lookback_coverage"] = top_frame["lookback_coverage"].map(lambda value: f"{value:.1%}")
        top_frame["post_coverage"] = top_frame["post_coverage"].map(lambda value: f"{value:.1%}")

    excluded_frame = all_frame.loc[~all_frame["selected"], ["pair", "exclusion_reason"]].copy()

    lines = [
        f"# Historical Pair Snapshot Report",
        "",
        f"- Reference date: `{reference_date.isoformat()}`",
        f"- Lookback window: `{lookback}`",
        f"- Post window: `{post_window}`",
        f"- Requested top_n: `{top_n}`",
        f"- Eligible pairs: `{len(eligible_frame)}`",
        f"- Selected pairs: `{len(selected_pairs)}`",
        "",
        "## Selected Pairs",
        "",
        *([top_frame.to_markdown(index=False)] if not top_frame.empty else ["No eligible pairs."]),
        "",
        "## Excluded Pairs",
        "",
        *([excluded_frame.to_markdown(index=False)] if not excluded_frame.empty else ["No exclusions."]),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    datadir = Path(args.datadir)
    futures_dir = datadir / "futures"
    reference_date = parse_reference_date(args.reference_date)
    lookback = pd.Timedelta(args.lookback)
    post_window = pd.Timedelta(args.post_window)
    timeframe_delta = timeframe_to_timedelta(args.timeframe)

    results: list[CoverageResult] = []
    for path in sorted(futures_dir.glob(f"*_{args.quote_currency}_{args.settle_currency}-{args.timeframe}-futures.feather")):
        pair = parse_pair_from_filename(path, args.quote_currency, args.settle_currency, args.timeframe)
        if pair is None:
            continue
        results.append(
            evaluate_pair(
                path=path,
                pair=pair,
                reference_date=reference_date,
                lookback=lookback,
                post_window=post_window,
                timeframe_delta=timeframe_delta,
                min_coverage_ratio=args.min_coverage_ratio,
            )
        )

    if not results:
        raise SystemExit(f"No matching futures candle files found under {futures_dir}")

    frame = to_dataframe(results)
    eligible_frame = frame.loc[frame["selected"]].copy()
    selected_pairs = eligible_frame["pair"].tolist()[: args.top_n]

    output_json = Path(args.output_json)
    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)

    write_snapshot(output_json, selected_pairs)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_csv, index=False)
    write_markdown(output_md, reference_date, lookback, post_window, args.top_n, eligible_frame, frame)

    print(f"Selected {len(selected_pairs)} pairs for {reference_date.date()}:")
    for pair in selected_pairs:
        print(pair)
    print(f"Snapshot saved to {output_json}")
    print(f"Coverage CSV saved to {output_csv}")
    print(f"Coverage report saved to {output_md}")


if __name__ == "__main__":
    main()
