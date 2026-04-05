from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from longonly_research_utils import LONGONLY_VARIANTS, run_matrix_backtests


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
    parser = argparse.ArgumentParser(description="Run the dedicated de-overlapped long-only validation matrix.")
    parser.add_argument("--anchors", nargs="+", default=DEFAULT_ANCHORS)
    parser.add_argument("--window-months", type=int, default=6)
    parser.add_argument("--snapshot-dir", default="user_data/pairs")
    parser.add_argument("--snapshot-top-n", type=int, default=50)
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--base-config", default="user_data/configs/volatility_rotation_mr_base.json")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--logs-dir", default="docs/validation/logs/longonly_matrix")
    parser.add_argument("--backtest-dir", default="user_data/backtest_results/longonly_matrix")
    parser.add_argument(
        "--db-url",
        default="sqlite:///user_data/tradesv3_volatility_rotation_mr_longonly_matrix.sqlite",
    )
    parser.add_argument("--usable-trade-threshold", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = run_matrix_backtests(
        anchors=args.anchors,
        window_months=args.window_months,
        snapshot_dir=Path(args.snapshot_dir),
        snapshot_top_n=args.snapshot_top_n,
        strategy_path=Path(args.strategy_path),
        base_config=Path(args.base_config),
        logs_dir=Path(args.logs_dir),
        backtest_dir=Path(args.backtest_dir),
        db_url=args.db_url,
    )
    frame["usable_sample"] = frame["raw_trade_count"].map(lambda count: "yes" if int(count) >= args.usable_trade_threshold else "no")

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_csv, index=False)

    totals_rows: list[dict[str, object]] = []
    for variant in LONGONLY_VARIANTS:
        subset = frame[frame["strategy_variant"] == variant.label].copy()
        totals_rows.append(
            {
                "strategy_variant": variant.label,
                "raw_trade_count": int(subset["raw_trade_count"].sum()),
                "unique_trade_count": int(subset["unique_trade_count"].sum()),
                "profit_pct": round(float(subset["profit_pct"].sum()), 2),
                "profit_usdt": round(float(subset["profit_usdt"].sum()), 3),
                "max_drawdown_pct": round(float(subset["drawdown_pct"].max()), 2),
                "usable_windows": int((subset["usable_sample"] == "yes").sum()),
            }
        )
    totals = pd.DataFrame(totals_rows)

    lines = [
        "# Long-Only Alpha Validation Matrix",
        "",
        "> Research-only artifact. These long-only profiles are for robustness diagnosis only and are not live deployment candidates.",
        "",
        f"- Anchors: `{', '.join(args.anchors)}`",
        f"- Window design: non-overlapping forward `{args.window_months}m` windows",
        f"- Snapshot top_n: `{args.snapshot_top_n}`",
        f"- Usable-sample threshold: `{args.usable_trade_threshold}` trades per window",
        "",
        "## Matrix",
        "",
        frame[
            [
                "anchor",
                "window_label",
                "strategy_variant",
                "pair_count",
                "raw_trade_count",
                "unique_trade_count",
                "profit_pct",
                "profit_usdt",
                "drawdown_pct",
                "usable_sample",
                "monthly_distribution",
                "pair_contribution",
            ]
        ].to_markdown(index=False),
        "",
        "## Totals",
        "",
        totals.to_markdown(index=False),
        "",
        "## Decision Framing",
        "",
        "Use this matrix to judge whether the long-only subclasses are robust enough to justify more research.",
        "A single profitable burst is not enough if the edge collapses under concentration, regime, or cost stress.",
        "",
    ]
    Path(args.output_md).write_text("\n".join(lines), encoding="utf-8")
    print(frame.to_string(index=False))
    print("")
    print(totals.to_string(index=False))


if __name__ == "__main__":
    main()
