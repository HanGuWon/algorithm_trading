from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from longonly_research_utils import (
    LONGONLY_VARIANTS,
    classify_resilience,
    compute_hhi,
    max_drawdown_from_profit,
    parse_backtest_zip,
    pct_share,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quantify concentration risk for the long-only matrix results.")
    parser.add_argument("--matrix-csv", required=True)
    parser.add_argument("--backtest-dir", default="user_data/backtest_results/longonly_matrix")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", default="")
    return parser.parse_args()


def load_variant_trades(matrix_csv: Path, backtest_dir: Path, strategy_variant: str, strategy_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    matrix = pd.read_csv(matrix_csv)
    subset = matrix[matrix["strategy_variant"] == strategy_variant].copy()
    frames: list[pd.DataFrame] = []
    for row in subset.itertuples(index=False):
        zip_path = backtest_dir / row.results_zip
        _, trades = parse_backtest_zip(zip_path, strategy_name)
        if not trades.empty:
            trades["anchor"] = row.anchor
            frames.append(trades)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return subset, combined


def summarize_counterfactual(
    label: str,
    trades: pd.DataFrame,
    base_profit: float,
    base_trades: int,
    base_drawdown: float,
) -> dict[str, object]:
    profit = float(trades["profit_abs"].sum()) if not trades.empty else 0.0
    trade_count = int(len(trades))
    drawdown = max_drawdown_from_profit(trades)
    return {
        "scenario": label,
        "trades": trade_count,
        "profit_usdt": round(profit, 3),
        "profit_share": round(pct_share(profit, base_profit), 3),
        "trade_share": round(pct_share(trade_count, base_trades), 3),
        "drawdown_abs_usdt": round(drawdown, 3),
        "drawdown_share": round(pct_share(drawdown, base_drawdown), 3) if base_drawdown > 0 else 0.0,
        "status": classify_resilience(profit, trade_count, base_profit, base_trades),
    }


def contribution_table(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["pair", "trades", "profit_usdt", "profit_share"])
    grouped = (
        trades.groupby("pair", as_index=False)
        .agg(trades=("pair", "size"), profit_usdt=("profit_abs", "sum"))
        .sort_values(["profit_usdt", "trades", "pair"], ascending=[False, False, True])
    )
    total_profit = float(grouped["profit_usdt"].sum())
    grouped["profit_share"] = grouped["profit_usdt"].map(lambda value: round(pct_share(float(value), total_profit), 3))
    return grouped


def monthly_table(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["month", "trades", "profit_usdt", "profit_share"])
    grouped = (
        trades.groupby("month", as_index=False)
        .agg(trades=("month", "size"), profit_usdt=("profit_abs", "sum"))
        .sort_values("month")
    )
    total_profit = float(grouped["profit_usdt"].sum())
    grouped["profit_share"] = grouped["profit_usdt"].map(lambda value: round(pct_share(float(value), total_profit), 3))
    return grouped


def build_variant_analysis(matrix_csv: Path, backtest_dir: Path, variant_label: str, strategy_name: str) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    matrix_rows, trades = load_variant_trades(matrix_csv, backtest_dir, variant_label, strategy_name)
    base_profit = float(trades["profit_abs"].sum()) if not trades.empty else 0.0
    base_trades = int(len(trades))
    base_drawdown = max_drawdown_from_profit(trades)
    pair_stats = contribution_table(trades)
    month_stats = monthly_table(trades)

    base_summary = {
        "strategy_variant": variant_label,
        "raw_trade_count": base_trades,
        "window_raw_trade_count": int(matrix_rows["raw_trade_count"].sum()),
        "profit_usdt": round(base_profit, 3),
        "drawdown_abs_usdt": round(base_drawdown, 3),
        "top1_pair_share": round(float(pair_stats["profit_share"].iloc[0]), 3) if not pair_stats.empty else 0.0,
        "top3_pair_share": round(float(pair_stats.head(3)["profit_share"].sum()), 3) if not pair_stats.empty else 0.0,
        "top5_pair_share": round(float(pair_stats.head(5)["profit_share"].sum()), 3) if not pair_stats.empty else 0.0,
        "pair_profit_hhi": round(compute_hhi(pair_stats["profit_usdt"]) if not pair_stats.empty else 0.0, 3),
        "pair_trade_hhi": round(compute_hhi(pair_stats["trades"]) if not pair_stats.empty else 0.0, 3),
    }

    leave_one_pair_out_rows: list[dict[str, object]] = []
    for pair in pair_stats["pair"].tolist():
        leave_one_pair_out_rows.append(
            summarize_counterfactual(
                label=pair,
                trades=trades[trades["pair"] != pair].copy(),
                base_profit=base_profit,
                base_trades=base_trades,
                base_drawdown=base_drawdown,
            )
        )
    leave_one_pair_out = pd.DataFrame(leave_one_pair_out_rows)
    if not leave_one_pair_out.empty:
        leave_one_pair_out = leave_one_pair_out.sort_values(["profit_usdt", "scenario"], ascending=[True, True])

    top_removal_rows: list[dict[str, object]] = []
    ranked_pairs = pair_stats["pair"].tolist()
    for count in (1, 3, 5):
        removed_pairs = ranked_pairs[:count]
        remaining = trades[~trades["pair"].isin(removed_pairs)].copy()
        row = summarize_counterfactual(
            label=f"remove_top_{count}",
            trades=remaining,
            base_profit=base_profit,
            base_trades=base_trades,
            base_drawdown=base_drawdown,
        )
        row["removed_pairs"] = ", ".join(removed_pairs)
        top_removal_rows.append(row)
    top_removals = pd.DataFrame(top_removal_rows)

    leave_one_anchor_out_rows: list[dict[str, object]] = []
    for anchor in sorted(trades["anchor"].unique()) if not trades.empty else []:
        leave_one_anchor_out_rows.append(
            summarize_counterfactual(
                label=anchor,
                trades=trades[trades["anchor"] != anchor].copy(),
                base_profit=base_profit,
                base_trades=base_trades,
                base_drawdown=base_drawdown,
            )
        )
    leave_one_anchor_out = pd.DataFrame(leave_one_anchor_out_rows)
    if not leave_one_anchor_out.empty:
        leave_one_anchor_out = leave_one_anchor_out.sort_values(["profit_usdt", "scenario"], ascending=[True, True])

    leave_one_month_out_rows: list[dict[str, object]] = []
    for month in sorted(trades["month"].unique()) if not trades.empty else []:
        leave_one_month_out_rows.append(
            summarize_counterfactual(
                label=month,
                trades=trades[trades["month"] != month].copy(),
                base_profit=base_profit,
                base_trades=base_trades,
                base_drawdown=base_drawdown,
            )
        )
    leave_one_month_out = pd.DataFrame(leave_one_month_out_rows)
    if not leave_one_month_out.empty:
        leave_one_month_out = leave_one_month_out.sort_values(["profit_usdt", "scenario"], ascending=[True, True])

    return base_summary, pair_stats, month_stats, leave_one_pair_out, top_removals, leave_one_anchor_out, leave_one_month_out


def main() -> None:
    args = parse_args()
    matrix_csv = Path(args.matrix_csv)
    backtest_dir = Path(args.backtest_dir)

    summaries: list[dict[str, object]] = []
    csv_frames: list[pd.DataFrame] = []
    sections: list[str] = [
        "# Long-Only Concentration Risk",
        "",
        "> Research-only attribution study. Pair and window removals are contribution counterfactuals, not a redesigned strategy.",
        "",
    ]

    for variant in LONGONLY_VARIANTS:
        base_summary, pair_stats, month_stats, leave_one_pair_out, top_removals, leave_one_anchor_out, leave_one_month_out = build_variant_analysis(
            matrix_csv=matrix_csv,
            backtest_dir=backtest_dir,
            variant_label=variant.label,
            strategy_name=variant.strategy,
        )
        summaries.append(base_summary)

        sections.extend(
            [
                f"## {variant.label}",
                "",
                pd.DataFrame([base_summary]).to_markdown(index=False),
                "",
                "### Pair Contribution",
                "",
                pair_stats.head(12).to_markdown(index=False) if not pair_stats.empty else "No trades.",
                "",
                "### Remove Top Contributors",
                "",
                top_removals.to_markdown(index=False) if not top_removals.empty else "No top-removal analysis available.",
                "",
                "### Leave-One-Pair-Out",
                "",
                leave_one_pair_out.head(15).to_markdown(index=False) if not leave_one_pair_out.empty else "No pair leave-out analysis available.",
                "",
                "### Leave-One-Anchor-Out",
                "",
                leave_one_anchor_out.to_markdown(index=False) if not leave_one_anchor_out.empty else "No anchor leave-out analysis available.",
                "",
                "### Leave-One-Month-Out",
                "",
                leave_one_month_out.to_markdown(index=False) if not leave_one_month_out.empty else "No month leave-out analysis available.",
                "",
                "### Monthly Contribution",
                "",
                month_stats.to_markdown(index=False) if not month_stats.empty else "No monthly contribution data available.",
                "",
            ]
        )

        for name, frame in (
            ("pair_contribution", pair_stats),
            ("month_contribution", month_stats),
            ("leave_one_pair_out", leave_one_pair_out),
            ("top_removals", top_removals),
            ("leave_one_anchor_out", leave_one_anchor_out),
            ("leave_one_month_out", leave_one_month_out),
        ):
            if frame.empty:
                continue
            exported = frame.copy()
            exported.insert(0, "strategy_variant", variant.label)
            exported.insert(1, "analysis", name)
            csv_frames.append(exported)

    summary_frame = pd.DataFrame(summaries)
    sections.extend(
        [
            "## Cross-Variant Summary",
            "",
            summary_frame.to_markdown(index=False),
            "",
            "## Decision Rule",
            "",
            "`survives` means the remaining edge stays positive and retains most of its sample.",
            "`weakens materially` means the edge remains positive but loses enough profit or sample to become fragile.",
            "`collapses` means the remaining edge turns non-positive or nearly disappears.",
            "",
        ]
    )

    output_md = Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(sections), encoding="utf-8")

    if args.output_csv:
        output_csv = Path(args.output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        pd.concat(csv_frames + [summary_frame.assign(analysis="summary")], ignore_index=True, sort=False).to_csv(output_csv, index=False)

    print(summary_frame.to_string(index=False))


if __name__ == "__main__":
    main()
