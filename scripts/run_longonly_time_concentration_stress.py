from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from longonly_research_utils import max_drawdown_from_profit, parse_backtest_zip


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an explicit time/window concentration stress on the frozen long-only candidate.")
    parser.add_argument("--selection-matrix-csv", default="docs/validation/alpha_validation_matrix_longonly.csv")
    parser.add_argument("--selection-backtest-dir", default="user_data/backtest_results/longonly_matrix")
    parser.add_argument("--promotion-csv", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", default="")
    return parser.parse_args()


def classify(profit_usdt: float, trade_count: int) -> str:
    if trade_count <= 0 or profit_usdt <= 0:
        return "collapses"
    if trade_count < 10 or profit_usdt < 100:
        return "weakens materially"
    return "survives"


def load_selection_trades(matrix_csv: Path, backtest_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    matrix = pd.read_csv(matrix_csv)
    rows = matrix[
        (matrix["strategy_variant"] == "diagnostic_long_only")
        & (matrix["anchor"] < "2024-07-01")
    ].copy()
    frames: list[pd.DataFrame] = []
    for row in rows.itertuples(index=False):
        zip_path = backtest_dir / row.results_zip
        _, trades = parse_backtest_zip(zip_path, "VolatilityRotationMRDiagnosticLongOnly")
        if not trades.empty:
            trades["anchor"] = row.anchor
            frames.append(trades)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return rows, combined


def load_promotion_holdout_rows(promotion_csv: Path) -> pd.DataFrame:
    frame = pd.read_csv(promotion_csv)
    return frame[frame["evidence_role"] == "promotion_holdout"].copy()


def scenario_row(label: str, trades: pd.DataFrame) -> dict[str, object]:
    profit = float(trades["profit_abs"].sum()) if not trades.empty else 0.0
    trade_count = int(len(trades))
    return {
        "scenario": label,
        "raw_trade_count": trade_count,
        "profit_usdt": round(profit, 3),
        "max_drawdown_usdt": round(max_drawdown_from_profit(trades), 3),
        "status": classify(profit, trade_count),
    }


def main() -> None:
    args = parse_args()
    selection_rows, selection_trades = load_selection_trades(Path(args.selection_matrix_csv), Path(args.selection_backtest_dir))
    promotion_rows = load_promotion_holdout_rows(Path(args.promotion_csv))

    month_profit = (
        selection_trades.groupby("month", as_index=False)
        .agg(raw_trade_count=("month", "size"), profit_usdt=("profit_abs", "sum"))
        .sort_values("profit_usdt", ascending=False)
    ) if not selection_trades.empty else pd.DataFrame(columns=["month", "raw_trade_count", "profit_usdt"])
    anchor_profit = (
        selection_trades.groupby("anchor", as_index=False)
        .agg(raw_trade_count=("anchor", "size"), profit_usdt=("profit_abs", "sum"))
        .sort_values("profit_usdt", ascending=False)
    ) if not selection_trades.empty else pd.DataFrame(columns=["anchor", "raw_trade_count", "profit_usdt"])

    top_months = month_profit["month"].head(2).tolist()
    best_anchor = anchor_profit["anchor"].iloc[0] if not anchor_profit.empty else ""

    scenarios = [
        scenario_row("selection_reference", selection_trades),
        scenario_row("remove_best_month", selection_trades[~selection_trades["month"].isin(top_months[:1])].copy()),
        scenario_row("remove_best_two_months", selection_trades[~selection_trades["month"].isin(top_months)].copy()),
        scenario_row("remove_best_anchor_window", selection_trades[selection_trades["anchor"] != best_anchor].copy()),
        {
            "scenario": "promotion_holdouts_only",
            "raw_trade_count": int(promotion_rows["raw_trade_count"].sum()),
            "profit_usdt": round(float(promotion_rows["profit_usdt"].sum()), 3),
            "max_drawdown_usdt": 0.0,
            "status": classify(float(promotion_rows["profit_usdt"].sum()), int(promotion_rows["raw_trade_count"].sum())),
        },
    ]
    scenario_frame = pd.DataFrame(scenarios)

    comparison_rows = pd.DataFrame(
        [
            {
                "bucket": "selection_like_windows",
                "windows": len(selection_rows),
                "raw_trade_count": int(selection_rows["raw_trade_count"].sum()),
                "profit_usdt": round(float(selection_rows["profit_usdt"].sum()), 3),
                "max_drawdown_pct": round(float(selection_rows["drawdown_pct"].max()), 2) if not selection_rows.empty else 0.0,
            },
            {
                "bucket": "forward_holdout_windows",
                "windows": int(len(promotion_rows)),
                "raw_trade_count": int(promotion_rows["raw_trade_count"].sum()),
                "profit_usdt": round(float(promotion_rows["profit_usdt"].sum()), 3),
                "max_drawdown_pct": round(float(promotion_rows["max_drawdown_pct"].max()), 2) if not promotion_rows.empty else 0.0,
            },
        ]
    )

    lines = [
        "# Long-Only Time Concentration Stress",
        "",
        "> Explicit time-cluster stress on the frozen diagnostic long-only candidate.",
        "",
        "## Stress Scenarios",
        "",
        scenario_frame.to_markdown(index=False),
        "",
        "## Selection-Like vs Holdout Windows",
        "",
        comparison_rows.to_markdown(index=False),
        "",
        "## Dominant Windows",
        "",
        month_profit.head(6).to_markdown(index=False) if not month_profit.empty else "No monthly data available.",
        "",
        anchor_profit.to_markdown(index=False) if not anchor_profit.empty else "No anchor data available.",
        "",
        "## Interpretation",
        "",
        "This stress isolates whether the published long-only edge survives removal of the dominant burst and whether anything remains in forward holdouts.",
        "",
        "## Reproduction",
        "",
        "```powershell",
        "& .\\.venv-freqtrade\\Scripts\\python.exe scripts\\run_longonly_time_concentration_stress.py `",
        f"  --selection-matrix-csv {Path(args.selection_matrix_csv).as_posix()} `",
        f"  --selection-backtest-dir {Path(args.selection_backtest_dir).as_posix()} `",
        f"  --promotion-csv {Path(args.promotion_csv).as_posix()} `",
        f"  --output-md {Path(args.output_md).as_posix()}",
        "```",
        "",
    ]
    Path(args.output_md).write_text("\n".join(lines), encoding="utf-8")

    if args.output_csv:
        Path(args.output_csv).parent.mkdir(parents=True, exist_ok=True)
        pd.concat(
            [
                scenario_frame.assign(analysis="stress_scenarios"),
                comparison_rows.assign(analysis="selection_vs_holdout"),
                month_profit.assign(analysis="month_profit"),
                anchor_profit.assign(analysis="anchor_profit"),
            ],
            ignore_index=True,
            sort=False,
        ).to_csv(args.output_csv, index=False)

    print(scenario_frame.to_string(index=False))
    print("")
    print(comparison_rows.to_string(index=False))


if __name__ == "__main__":
    main()
