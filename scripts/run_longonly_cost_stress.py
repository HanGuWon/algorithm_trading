from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from longonly_research_utils import LONGONLY_VARIANTS, parse_backtest_zip


SCENARIOS = [
    {"scenario": "baseline_exported_fees", "target_fee": None, "slippage_per_side": 0.0},
    {"scenario": "moderately_worse_fee", "target_fee": 0.0007, "slippage_per_side": 0.0},
    {"scenario": "worse_fee_plus_slippage", "target_fee": 0.0007, "slippage_per_side": 0.0005},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply fee/slippage stress to long-only backtest trades.")
    parser.add_argument("--matrix-csv", required=True)
    parser.add_argument("--backtest-dir", default="user_data/backtest_results/longonly_matrix")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", default="")
    return parser.parse_args()


def load_variant_trades(matrix_csv: Path, backtest_dir: Path, strategy_variant: str, strategy_name: str) -> pd.DataFrame:
    matrix = pd.read_csv(matrix_csv)
    subset = matrix[matrix["strategy_variant"] == strategy_variant]
    frames: list[pd.DataFrame] = []
    for row in subset.itertuples(index=False):
        _, trades = parse_backtest_zip(backtest_dir / row.results_zip, strategy_name)
        if not trades.empty:
            trades["anchor"] = row.anchor
            frames.append(trades)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def stressed_profit(frame: pd.DataFrame, target_fee: float | None, slippage_per_side: float) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=float)
    extra_open_fee = 0.0 if target_fee is None else (target_fee - frame["fee_open"].astype(float)).clip(lower=0.0)
    extra_close_fee = 0.0 if target_fee is None else (target_fee - frame["fee_close"].astype(float)).clip(lower=0.0)
    open_cost = frame["open_rate"].astype(float) * frame["amount"].astype(float)
    close_cost = frame["close_rate"].astype(float) * frame["amount"].astype(float)
    extra_cost = (open_cost * extra_open_fee) + (close_cost * extra_close_fee)
    extra_cost += (open_cost + close_cost) * float(slippage_per_side)
    return frame["profit_abs"].astype(float) - extra_cost


def main() -> None:
    args = parse_args()
    matrix_csv = Path(args.matrix_csv)
    backtest_dir = Path(args.backtest_dir)

    rows: list[dict[str, object]] = []
    for variant in LONGONLY_VARIANTS:
        trades = load_variant_trades(matrix_csv, backtest_dir, variant.label, variant.strategy)
        for scenario in SCENARIOS:
            adjusted = stressed_profit(trades, scenario["target_fee"], scenario["slippage_per_side"])
            rows.append(
                {
                    "strategy_variant": variant.label,
                    "scenario": scenario["scenario"],
                    "trade_count": int(len(trades)),
                    "profit_usdt": round(float(adjusted.sum()), 3) if not adjusted.empty else 0.0,
                    "avg_profit_per_trade_usdt": round(float(adjusted.mean()), 3) if not adjusted.empty else 0.0,
                    "positive_after_stress": "yes" if (not adjusted.empty and float(adjusted.sum()) > 0) else "no",
                    "target_fee_per_side": scenario["target_fee"] if scenario["target_fee"] is not None else "exported",
                    "slippage_per_side": scenario["slippage_per_side"],
                }
            )

    frame = pd.DataFrame(rows)
    output_md = Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Long-Only Cost Stress",
        "",
        "> Research-only cost sensitivity. Baseline uses the exported Freqtrade trade fees. Stress cases increase per-side fee and then add modest per-side slippage.",
        "",
        frame.to_markdown(index=False),
        "",
        "Assumptions:",
        "",
        "- `baseline_exported_fees`: exported backtest fees (`fee_open`, `fee_close`).",
        "- `moderately_worse_fee`: raises both sides to `7 bps` if the exported fee is lower.",
        "- `worse_fee_plus_slippage`: same fee stress plus `5 bps` slippage per side.",
        "",
    ]
    output_md.write_text("\n".join(lines), encoding="utf-8")

    if args.output_csv:
        output_csv = Path(args.output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output_csv, index=False)

    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
