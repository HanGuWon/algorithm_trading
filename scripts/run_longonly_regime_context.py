from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import talib.abstract as ta

from longonly_research_utils import (
    LONGONLY_VARIANTS,
    build_pair_frames,
    compute_long_signal_events,
    load_ohlcv,
    load_snapshot_pairs,
    load_strategy,
    match_realized_trades_to_signals,
    max_drawdown_from_profit,
    parse_backtest_zip,
    snapshot_path,
    LocalDataProvider,
)


DEFAULT_ANCHORS = [
    "2022-01-01",
    "2022-07-01",
    "2023-01-01",
    "2023-07-01",
    "2024-01-01",
    "2024-07-01",
    "2025-01-01",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify long-only signals and trades by market regime/context.")
    parser.add_argument("--anchors", nargs="+", default=DEFAULT_ANCHORS)
    parser.add_argument("--window-months", type=int, default=6)
    parser.add_argument("--snapshot-dir", default="user_data/pairs")
    parser.add_argument("--snapshot-top-n", type=int, default=50)
    parser.add_argument("--strategy-file", default="user_data/strategies/VolatilityRotationMR.py")
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--matrix-csv", required=True)
    parser.add_argument("--backtest-dir", default="user_data/backtest_results/longonly_matrix")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", default="")
    return parser.parse_args()


def bucket_three(series: pd.Series, prefix: str) -> pd.Series:
    clean = series.astype(float)
    if clean.nunique(dropna=True) < 3:
        median = clean.median()
        return clean.map(lambda value: f"{prefix}_high" if value > median else f"{prefix}_low")
    buckets = pd.qcut(clean.rank(method="first"), q=3, labels=[f"{prefix}_low", f"{prefix}_mid", f"{prefix}_high"])
    return buckets.astype(str)


def compute_context_frame(
    strategy,
    pairs: list[str],
    datadir: Path,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    pair_frames, preload_start = build_pair_frames(strategy, pairs, datadir, start, end)
    strategy.dp = LocalDataProvider(pair_frames=pair_frames, whitelist=pairs)
    breadth_rows: list[pd.DataFrame] = []

    for pair in pairs:
        raw_5m = pair_frames[(pair, strategy.timeframe)]
        raw_1h = pair_frames[(pair, strategy.informative_timeframe)]
        pair_frames[(pair, strategy.informative_timeframe)] = raw_1h[(raw_1h["date"] >= preload_start) & (raw_1h["date"] <= end)].copy()
        frame = raw_5m[(raw_5m["date"] >= preload_start) & (raw_5m["date"] <= end)].copy()
        frame = strategy.populate_indicators(frame.copy(), {"pair": pair})
        frame = strategy.populate_entry_trend(frame.copy(), {"pair": pair})
        frame = frame[(frame["date"] >= start) & (frame["date"] <= end)].copy()

        breadth_rows.append(
            pd.DataFrame(
                {
                    "date": frame["date"],
                    "flush_flag": (frame["close"] < frame["bb_lower"]) & (frame["price_z"] < -float(strategy.price_z_threshold.value)),
                    "oversold_flag": (
                        (frame["rsi"] < float(strategy.rsi_long_threshold.value))
                        | (frame["price_z"] < -float(strategy.price_z_threshold.value))
                        | (frame["close"] < frame["bb_lower"])
                    ),
                    "active_flag": frame["active_pair"].fillna(False),
                    "universe_count": 1,
                }
            )
        )

    breadth = pd.concat(breadth_rows, ignore_index=True)
    context = (
        breadth.groupby("date", as_index=False)
        .agg(
            flush_breadth=("flush_flag", "mean"),
            oversold_breadth=("oversold_flag", "mean"),
            active_breadth=("active_flag", "mean"),
            universe_count=("universe_count", "sum"),
        )
        .sort_values("date")
    )

    btc_5m = load_ohlcv(datadir, "BTC/USDT:USDT", "5m")
    btc_1h = load_ohlcv(datadir, "BTC/USDT:USDT", "1h")
    btc_5m = btc_5m[(btc_5m["date"] >= start - pd.Timedelta(days=10)) & (btc_5m["date"] <= end)].copy()
    btc_1h = btc_1h[(btc_1h["date"] >= start - pd.Timedelta(days=20)) & (btc_1h["date"] <= end)].copy()

    btc_1h["ema50"] = ta.EMA(btc_1h, timeperiod=50)
    btc_1h["ema200"] = ta.EMA(btc_1h, timeperiod=200)
    btc_1h["ema50_slope"] = btc_1h["ema50"].pct_change()
    btc_1h["btc_trend_regime"] = np.select(
        [
            (btc_1h["ema50"] > btc_1h["ema200"]) & (btc_1h["ema50_slope"] > 0),
            (btc_1h["ema50"] < btc_1h["ema200"]) & (btc_1h["ema50_slope"] < 0),
        ],
        ["btc_uptrend", "btc_downtrend"],
        default="btc_neutral",
    )

    btc_5m["log_ret"] = np.log(btc_5m["close"]).diff()
    btc_5m["btc_realized_vol"] = btc_5m["log_ret"].rolling(288, min_periods=72).std(ddof=0) * np.sqrt(288)
    merged = pd.merge_asof(
        context.sort_values("date"),
        btc_1h[["date", "btc_trend_regime"]].sort_values("date"),
        on="date",
        direction="backward",
    )
    merged = pd.merge_asof(
        merged.sort_values("date"),
        btc_5m[["date", "btc_realized_vol"]].sort_values("date"),
        on="date",
        direction="backward",
    )
    merged["btc_realized_vol_bucket"] = bucket_three(merged["btc_realized_vol"].ffill().fillna(0.0), "btc_vol")
    merged["flush_breadth_bucket"] = bucket_three(merged["flush_breadth"], "flush")
    merged["oversold_breadth_bucket"] = bucket_three(merged["oversold_breadth"], "oversold")
    merged["active_breadth_bucket"] = bucket_three(merged["active_breadth"], "active")
    return merged


def load_variant_trades(matrix_csv: Path, backtest_dir: Path, strategy_variant: str, strategy_name: str) -> dict[str, pd.DataFrame]:
    matrix = pd.read_csv(matrix_csv)
    subset = matrix[matrix["strategy_variant"] == strategy_variant]
    trade_map: dict[str, pd.DataFrame] = {}
    for row in subset.itertuples(index=False):
        _, trades = parse_backtest_zip(backtest_dir / row.results_zip, strategy_name)
        trade_map[row.anchor] = trades
    return trade_map


def summarize_feature(signals: pd.DataFrame, trades: pd.DataFrame, bucket_column: str) -> pd.DataFrame:
    signal_summary = (
        signals.groupby(["strategy_variant", bucket_column], as_index=False)
        .agg(
            signal_count=("pair", "size"),
            signal_ret_12=("ret_12", "mean"),
            signal_ret_24=("ret_24", "mean"),
            signal_ret_48=("ret_48", "mean"),
            signal_mean_hit_24=("mean_hit_24", "mean"),
            signal_mean_hit_48=("mean_hit_48", "mean"),
        )
        .rename(columns={bucket_column: "bucket"})
    )
    if trades.empty:
        signal_summary["trade_count"] = 0
        signal_summary["win_rate"] = 0.0
        signal_summary["profit_usdt"] = 0.0
        signal_summary["drawdown_abs_usdt"] = 0.0
        return signal_summary

    trade_rows: list[dict[str, object]] = []
    for (variant, bucket), frame in trades.groupby(["strategy_variant", bucket_column]):
        trade_rows.append(
            {
                "strategy_variant": variant,
                "bucket": bucket,
                "trade_count": int(len(frame)),
                "win_rate": round(float((frame["profit_abs"] > 0).mean()), 3),
                "profit_usdt": round(float(frame["profit_abs"].sum()), 3),
                "drawdown_abs_usdt": round(max_drawdown_from_profit(frame), 3),
                "trade_ret_12": round(float(frame["ret_12"].mean()), 4),
                "trade_ret_24": round(float(frame["ret_24"].mean()), 4),
                "trade_ret_48": round(float(frame["ret_48"].mean()), 4),
            }
        )
    trade_summary = pd.DataFrame(trade_rows)
    return signal_summary.merge(trade_summary, how="left", on=["strategy_variant", "bucket"]).fillna(0.0)


def main() -> None:
    args = parse_args()
    datadir = Path(args.datadir)
    strategy_file = Path(args.strategy_file)
    snapshot_dir = Path(args.snapshot_dir)
    matrix_csv = Path(args.matrix_csv)
    backtest_dir = Path(args.backtest_dir)

    csv_frames: list[pd.DataFrame] = []
    sections: list[str] = [
        "# Long-Only Regime Context",
        "",
        "> Research-only context study over the existing long-only subclasses. The goal is to identify whether the edge is broad or concentrated in flush-rebound environments.",
        "",
    ]

    for variant in LONGONLY_VARIANTS:
        strategy = load_strategy(strategy_file, variant.strategy)
        trade_map = load_variant_trades(matrix_csv, backtest_dir, variant.label, variant.strategy)
        signal_frames: list[pd.DataFrame] = []
        trade_frames: list[pd.DataFrame] = []

        for anchor_text in args.anchors:
            start = pd.Timestamp(anchor_text, tz="UTC")
            end = start + pd.DateOffset(months=args.window_months)
            pairs = load_snapshot_pairs(snapshot_path(snapshot_dir, anchor_text, args.snapshot_top_n))
            context = compute_context_frame(strategy, pairs, datadir, start, end)
            raw_signals = compute_long_signal_events(strategy, pairs, datadir, start, end)
            if raw_signals.empty:
                continue
            signals = raw_signals.copy()
            signals["anchor"] = anchor_text
            signals["strategy_variant"] = variant.label
            signals = signals.merge(context, how="left", left_on="signal_date", right_on="date").drop(columns=["date"])
            signal_frames.append(signals)

            trades = trade_map.get(anchor_text, pd.DataFrame()).copy()
            if trades.empty:
                continue
            trades["anchor"] = anchor_text
            matched = match_realized_trades_to_signals(trades, raw_signals)
            matched["strategy_variant"] = variant.label
            matched = matched.merge(context, how="left", left_on="open_date", right_on="date").drop(columns=["date"])
            trade_frames.append(matched)

        variant_signals = pd.concat(signal_frames, ignore_index=True) if signal_frames else pd.DataFrame()
        variant_trades = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()
        if variant_signals.empty:
            continue

        sections.extend(
            [
                f"## {variant.label}",
                "",
                f"- signal count: `{len(variant_signals)}`",
                f"- realized trade count: `{len(variant_trades)}`",
                f"- realized profit: `{variant_trades['profit_abs'].sum():.3f} USDT`" if not variant_trades.empty else "- realized profit: `0.000 USDT`",
                "",
            ]
        )

        for feature in [
            "btc_trend_regime",
            "btc_realized_vol_bucket",
            "flush_breadth_bucket",
            "oversold_breadth_bucket",
            "active_breadth_bucket",
        ]:
            summary = summarize_feature(variant_signals, variant_trades, feature)
            summary.insert(1, "feature", feature)
            csv_frames.append(summary)
            sections.extend(
                [
                    f"### {feature}",
                    "",
                    summary.to_markdown(index=False),
                    "",
                ]
            )

        flush_trade_profit = (
            variant_trades.groupby("flush_breadth_bucket")["profit_abs"].sum().sort_values(ascending=False)
            if not variant_trades.empty
            else pd.Series(dtype=float)
        )
        oversold_trade_profit = (
            variant_trades.groupby("oversold_breadth_bucket")["profit_abs"].sum().sort_values(ascending=False)
            if not variant_trades.empty
            else pd.Series(dtype=float)
        )
        sections.extend(
            [
                "### Interpretation",
                "",
                f"- Highest-profit flush bucket: `{flush_trade_profit.index[0]}` with `{flush_trade_profit.iloc[0]:.3f} USDT`." if not flush_trade_profit.empty else "- No flush-bucket trade profit recorded.",
                f"- Highest-profit oversold bucket: `{oversold_trade_profit.index[0]}` with `{oversold_trade_profit.iloc[0]:.3f} USDT`." if not oversold_trade_profit.empty else "- No oversold-bucket trade profit recorded.",
                "",
            ]
        )

    output_md = Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(sections), encoding="utf-8")

    if args.output_csv:
        output_csv = Path(args.output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        pd.concat(csv_frames, ignore_index=True, sort=False).to_csv(output_csv, index=False)

    print(f"Wrote {args.output_md}")


if __name__ == "__main__":
    main()
