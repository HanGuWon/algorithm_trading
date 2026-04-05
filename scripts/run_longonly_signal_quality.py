from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from longonly_research_utils import (
    LONGONLY_VARIANTS,
    collect_long_setup_rows,
    load_snapshot_pairs,
    load_strategy,
    parse_backtest_zip,
    snapshot_path,
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

INDICATOR_COLUMNS = ["vol_z", "natr", "bb_width", "adx_1h", "ema50_slope_1h", "rsi", "price_z"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the long-only signal-quality report from existing long-side artifacts.")
    parser.add_argument("--anchors", nargs="+", default=DEFAULT_ANCHORS)
    parser.add_argument("--window-months", type=int, default=6)
    parser.add_argument("--snapshot-dir", default="user_data/pairs")
    parser.add_argument("--snapshot-top-n", type=int, default=50)
    parser.add_argument("--strategy-file", default="user_data/strategies/VolatilityRotationMR.py")
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--matrix-csv", required=True)
    parser.add_argument("--backtest-dir", default="user_data/backtest_results/longonly_matrix")
    parser.add_argument("--event-study-csv", default="docs/validation/analysis/signal_event_study.csv")
    parser.add_argument("--indicator-csv", default="docs/validation/analysis/signal_indicator_diagnostics.csv")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", default="")
    return parser.parse_args()


def load_realized_trades(matrix_csv: Path, backtest_dir: Path, strategy_variant: str, strategy_name: str) -> pd.DataFrame:
    matrix = pd.read_csv(matrix_csv)
    subset = matrix[matrix["strategy_variant"] == strategy_variant]
    frames: list[pd.DataFrame] = []
    for row in subset.itertuples(index=False):
        _, trades = parse_backtest_zip(backtest_dir / row.results_zip, strategy_name)
        if not trades.empty:
            trades["anchor"] = row.anchor
            frames.append(trades)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def summarize_forward(frame: pd.DataFrame, label: str) -> dict[str, object]:
    if frame.empty:
        return {
            "bucket": label,
            "count": 0,
            "ret_12": 0.0,
            "ret_24": 0.0,
            "ret_48": 0.0,
            "mfe_48": 0.0,
            "mae_48": 0.0,
            "mean_hit_24": 0.0,
            "mean_hit_48": 0.0,
        }
    return {
        "bucket": label,
        "count": int(len(frame)),
        "ret_12": round(float(frame["ret_12"].mean()), 4),
        "ret_24": round(float(frame["ret_24"].mean()), 4),
        "ret_48": round(float(frame["ret_48"].mean()), 4),
        "mfe_48": round(float(frame["mfe_48"].mean()), 4),
        "mae_48": round(float(frame["mae_48"].mean()), 4),
        "mean_hit_24": round(float(frame["mean_hit_24"].mean()), 3),
        "mean_hit_48": round(float(frame["mean_hit_48"].mean()), 3),
    }


def indicator_summary(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame([{"bucket": label, **{column: 0.0 for column in INDICATOR_COLUMNS}}])
    row = {column: round(float(frame[column].mean()), 4) for column in INDICATOR_COLUMNS}
    row["bucket"] = label
    return pd.DataFrame([row])


def main() -> None:
    args = parse_args()
    strategy_file = Path(args.strategy_file)
    datadir = Path(args.datadir)
    snapshot_dir = Path(args.snapshot_dir)
    matrix_csv = Path(args.matrix_csv)
    backtest_dir = Path(args.backtest_dir)
    event_study = pd.read_csv(args.event_study_csv, parse_dates=["date"])
    indicator_rows = pd.read_csv(args.indicator_csv, parse_dates=["date"])

    csv_frames: list[pd.DataFrame] = []
    sections: list[str] = [
        "# Long-Only Signal Quality",
        "",
        "> Research-only report. Raw long-signal event-study and indicator rows are inherited from the existing baseline/diagnostic artifacts because the long-only subclasses only disable short entries.",
        "",
    ]

    for variant in LONGONLY_VARIANTS:
        base_variant = "diagnostic" if "diagnostic" in variant.label else "baseline"
        strategy = load_strategy(strategy_file, variant.strategy)

        raw_signals = event_study[(event_study["strategy_variant"] == base_variant) & (event_study["side"] == "long")].copy()
        raw_signals["trade_open_date"] = raw_signals["date"] + pd.Timedelta(minutes=5)
        realized_trades = load_realized_trades(matrix_csv, backtest_dir, variant.label, variant.strategy)
        realized = realized_trades.merge(
            raw_signals,
            how="left",
            left_on=["pair", "open_date"],
            right_on=["pair", "trade_open_date"],
            suffixes=("_trade", "_signal"),
        )

        near_miss_frames: list[pd.DataFrame] = []
        for anchor_text in args.anchors:
            start = pd.Timestamp(anchor_text, tz="UTC")
            end = start + pd.DateOffset(months=args.window_months)
            pairs = load_snapshot_pairs(snapshot_path(snapshot_dir, anchor_text, args.snapshot_top_n))
            rows = collect_long_setup_rows(strategy, pairs, datadir, start, end)
            if not rows.empty:
                rows["anchor"] = anchor_text
                near_miss_frames.append(rows[rows["row_type"] == "near_miss"].copy())
        near_miss = pd.concat(near_miss_frames, ignore_index=True) if near_miss_frames else pd.DataFrame()
        good_near_miss = near_miss[(near_miss["ret_24"] > 0) | (near_miss["mean_hit_24"] == True)].copy()

        indicator_subset = indicator_rows[(indicator_rows["strategy_variant"] == base_variant) & (indicator_rows["side"] == "long")].copy()
        signal_indicator_rows = indicator_subset[indicator_subset["row_type"] == "signal"].copy()
        near_miss_indicator_rows = indicator_subset[indicator_subset["row_type"] == "near_miss"].copy()

        quality_summary = pd.DataFrame(
            [
                summarize_forward(raw_signals, "raw_signal"),
                summarize_forward(realized, "realized_trade"),
                summarize_forward(near_miss, "near_miss"),
                summarize_forward(good_near_miss, "good_near_miss"),
            ]
        )
        opportunity_summary = pd.DataFrame(
            [
                {
                    "strategy_variant": variant.label,
                    "raw_signal_count": int(len(raw_signals)),
                    "realized_trade_count": int(len(realized)),
                    "near_miss_count": int(len(near_miss)),
                    "good_near_miss_count": int(len(good_near_miss)),
                    "realized_profit_usdt": round(float(realized["profit_abs"].sum()) if not realized.empty else 0.0, 3),
                    "realized_win_rate": round(float((realized["profit_abs"] > 0).mean()) if not realized.empty else 0.0, 3),
                }
            ]
        )
        blocker_summary = (
            good_near_miss.groupby("first_failed_gate", as_index=False)
            .agg(rows=("first_failed_gate", "size"), ret_24=("ret_24", "mean"), mean_hit_24=("mean_hit_24", "mean"))
            .sort_values(["rows", "first_failed_gate"], ascending=[False, True])
            if not good_near_miss.empty
            else pd.DataFrame(columns=["first_failed_gate", "rows", "ret_24", "mean_hit_24"])
        )
        realized_indicator_rows = realized.copy()
        if not realized_indicator_rows.empty and "vol_z" not in realized_indicator_rows.columns and "vol_z_signal" in realized_indicator_rows.columns:
            realized_indicator_rows = realized_indicator_rows.rename(
                columns={
                    "vol_z_signal": "vol_z",
                    "natr_signal": "natr",
                    "bb_width_signal": "bb_width",
                    "adx_1h_signal": "adx_1h",
                    "ema50_slope_1h_signal": "ema50_slope_1h",
                    "rsi_signal": "rsi",
                    "price_z_signal": "price_z",
                }
            )
        indicators = pd.concat(
            [
                indicator_summary(signal_indicator_rows, "raw_signal"),
                indicator_summary(realized_indicator_rows, "realized_trade"),
                indicator_summary(near_miss_indicator_rows, "near_miss"),
                indicator_summary(good_near_miss, "good_near_miss"),
            ],
            ignore_index=True,
        )

        sections.extend(
            [
                f"## {variant.label}",
                "",
                opportunity_summary.to_markdown(index=False),
                "",
                "### Forward Quality",
                "",
                quality_summary.to_markdown(index=False),
                "",
                "### Indicator Distributions",
                "",
                indicators.to_markdown(index=False),
                "",
                "### Good Near-Miss Gate Blockers",
                "",
                blocker_summary.to_markdown(index=False) if not blocker_summary.empty else "No good near-miss rows were found.",
                "",
            ]
        )

        for name, frame in (
            ("opportunity_summary", opportunity_summary),
            ("quality_summary", quality_summary),
            ("indicator_summary", indicators),
            ("blocker_summary", blocker_summary),
        ):
            if frame.empty:
                continue
            exported = frame.copy()
            if "strategy_variant" not in exported.columns:
                exported.insert(0, "strategy_variant", variant.label)
            if "analysis" not in exported.columns:
                exported.insert(1, "analysis", name)
            csv_frames.append(exported)

    sections.extend(
        [
            "## Interpretation Rule",
            "",
            "The raw long event-study rows come from the existing baseline/diagnostic artifacts because long-only does not alter long-entry logic.",
            "Good near-miss rows identify structurally valid oversold setups that missed entry mainly because one of the last long gates failed.",
            "Read pair and regime concentration together with the separate concentration and regime artifacts before deciding whether to continue research.",
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
