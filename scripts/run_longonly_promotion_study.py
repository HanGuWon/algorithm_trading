from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from longonly_research_utils import (
    StrategyVariant,
    ensure_directory,
    make_timerange,
    monthly_distribution,
    pair_contribution,
    parse_backtest_zip,
    run_backtest,
    snapshot_path,
    write_temp_config,
)


FROZEN_VARIANT = StrategyVariant(
    label="frozen_diagnostic_long_only",
    strategy="VolatilityRotationMRDiagnosticLongOnly",
    config_path="user_data/configs/volatility_rotation_mr_backtest_top50_diagnostic_longonly.json",
)

SELECTION_CUTOFF_ANCHOR = "2024-07-01"
FROZEN_DEFAULTS = {
    "vol_z_min": 1.00,
    "price_z_threshold": 1.50,
    "bb_width_min": 0.020,
    "adx_1h_max": 24,
    "slope_cap": 0.0060,
}


@dataclass(frozen=True)
class PromotionWindow:
    label: str
    anchor: str
    months: int
    evidence_role: str
    notes: str


DEFAULT_WINDOWS = [
    PromotionWindow(
        label="holdout_2024h2",
        anchor="2024-07-01",
        months=6,
        evidence_role="promotion_holdout",
        notes="First forward non-overlapping holdout after the 2024-01 burst.",
    ),
    PromotionWindow(
        label="holdout_2025h1",
        anchor="2025-01-01",
        months=6,
        evidence_role="promotion_holdout",
        notes="Second forward non-overlapping holdout.",
    ),
    PromotionWindow(
        label="holdout_forward_12m",
        anchor="2024-07-01",
        months=12,
        evidence_role="promotion_holdout_12m",
        notes="Aggregate forward view across the two 6m holdouts. Overlaps the 6m rows and is used only as a stress summary.",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the frozen long-only promotion study on forward holdout windows.")
    parser.add_argument("--selection-matrix-csv", default="docs/validation/alpha_validation_matrix_longonly.csv")
    parser.add_argument("--selection-backtest-dir", default="user_data/backtest_results/longonly_matrix")
    parser.add_argument("--snapshot-dir", default="user_data/pairs")
    parser.add_argument("--snapshot-top-n", type=int, default=50)
    parser.add_argument("--strategy-path", default="user_data/strategies")
    parser.add_argument("--base-config", default="user_data/configs/volatility_rotation_mr_base.json")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--logs-dir", default="docs/validation/logs/longonly_promotion")
    parser.add_argument("--backtest-dir", default="user_data/backtest_results/longonly_promotion")
    parser.add_argument(
        "--db-url",
        default="sqlite:///user_data/tradesv3_volatility_rotation_mr_longonly_promotion.sqlite",
    )
    return parser.parse_args()


def summarize_row(
    *,
    label: str,
    evidence_role: str,
    anchor: str,
    months: int,
    timerange: str,
    pair_count: int,
    strategy_data: dict[str, object],
    trades: pd.DataFrame,
    notes: str,
    results_zip: str,
) -> dict[str, object]:
    unique_trade_count = int(trades["trade_signature"].nunique()) if not trades.empty else 0
    return {
        "study_label": label,
        "evidence_role": evidence_role,
        "anchor": anchor,
        "window_months": months,
        "timerange": timerange,
        "pair_count": pair_count,
        "raw_trade_count": int(strategy_data.get("total_trades", 0)),
        "unique_trade_count": unique_trade_count,
        "profit_pct": round(float(strategy_data.get("profit_total", 0.0)) * 100.0, 2),
        "profit_usdt": round(float(strategy_data.get("profit_total_abs", 0.0)), 3),
        "max_drawdown_pct": round(float(strategy_data.get("max_drawdown_account", 0.0)) * 100.0, 2),
        "monthly_distribution": monthly_distribution(trades),
        "pair_contribution": pair_contribution(trades),
        "sample_large_enough": "yes" if int(strategy_data.get("total_trades", 0)) >= 20 else "no",
        "notes": notes,
        "results_zip": results_zip,
    }


def load_selection_reference_rows(matrix_csv: Path, selection_backtest_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    matrix = pd.read_csv(matrix_csv)
    selection_rows = matrix[
        (matrix["strategy_variant"] == "diagnostic_long_only")
        & (matrix["anchor"] < SELECTION_CUTOFF_ANCHOR)
    ].copy()
    trade_frames: list[pd.DataFrame] = []
    for row in selection_rows.itertuples(index=False):
        zip_path = selection_backtest_dir / row.results_zip
        _, trades = parse_backtest_zip(zip_path, FROZEN_VARIANT.strategy)
        if not trades.empty:
            trades["anchor"] = row.anchor
            trade_frames.append(trades)
    selection_trades = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()
    return selection_rows, selection_trades


def build_selection_summary(selection_rows: pd.DataFrame, selection_trades: pd.DataFrame) -> dict[str, object]:
    strategy_data = {
        "total_trades": int(selection_rows["raw_trade_count"].sum()),
        "profit_total": float(selection_rows["profit_pct"].sum()) / 100.0,
        "profit_total_abs": float(selection_rows["profit_usdt"].sum()),
        "max_drawdown_account": float(selection_rows["drawdown_pct"].max()) / 100.0 if not selection_rows.empty else 0.0,
    }
    return summarize_row(
        label="selection_reference",
        evidence_role="candidate_selection_reference",
        anchor="2022-01-01..2024-01-01",
        months=6,
        timerange="20220101-20240701 (selection windows only)",
        pair_count=int(selection_rows["pair_count"].max()) if not selection_rows.empty else 0,
        strategy_data=strategy_data,
        trades=selection_trades,
        notes="Known evidence used to justify the frozen candidate. Holdout windows begin at 2024-07-01 and are excluded from this selection summary.",
        results_zip="selection_reference_from_longonly_matrix",
    )


def render_defaults_table() -> str:
    defaults = pd.DataFrame([{"parameter": name, "frozen_value": value} for name, value in FROZEN_DEFAULTS.items()])
    return defaults.to_markdown(index=False)


def main() -> None:
    args = parse_args()
    selection_matrix_csv = Path(args.selection_matrix_csv)
    selection_backtest_dir = Path(args.selection_backtest_dir)
    snapshot_dir = Path(args.snapshot_dir)
    strategy_path = Path(args.strategy_path)
    base_config = Path(args.base_config)
    logs_dir = Path(args.logs_dir)
    backtest_dir = Path(args.backtest_dir)
    ensure_directory(logs_dir)
    ensure_directory(backtest_dir)

    selection_rows, selection_trades = load_selection_reference_rows(selection_matrix_csv, selection_backtest_dir)
    results: list[dict[str, object]] = [build_selection_summary(selection_rows, selection_trades)]

    with tempfile.TemporaryDirectory(prefix="longonly_promotion_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        for window in DEFAULT_WINDOWS:
            snapshot = snapshot_path(snapshot_dir, window.anchor, args.snapshot_top_n)
            snapshot_payload = json.loads(snapshot.read_text(encoding="utf-8"))
            pair_count = len(snapshot_payload["exchange"]["pair_whitelist"])
            timerange, _, _ = make_timerange(pd.Timestamp(window.anchor, tz="UTC"), window.months)
            config_path = write_temp_config(
                temp_dir=temp_dir,
                base_config=base_config,
                snapshot=snapshot,
                variant=FROZEN_VARIANT,
                db_url=args.db_url,
            )
            zip_path = run_backtest(
                python_executable=Path(sys.executable),
                config_path=config_path,
                strategy_path=strategy_path,
                timerange=timerange,
                logs_dir=logs_dir,
                backtest_dir=backtest_dir,
                anchor_label=f"{window.anchor}_{window.months}m",
                variant=FROZEN_VARIANT,
            )
            strategy_data, trades = parse_backtest_zip(zip_path, FROZEN_VARIANT.strategy)
            results.append(
                summarize_row(
                    label=window.label,
                    evidence_role=window.evidence_role,
                    anchor=window.anchor,
                    months=window.months,
                    timerange=timerange,
                    pair_count=pair_count,
                    strategy_data=strategy_data,
                    trades=trades,
                    notes=window.notes,
                    results_zip=zip_path.name,
                )
            )

    frame = pd.DataFrame(results)
    output_csv = Path(args.output_csv)
    ensure_directory(output_csv.parent)
    frame.to_csv(output_csv, index=False)

    holdouts = frame[frame["evidence_role"].str.startswith("promotion_holdout")].copy()
    holdout_trade_total = int(holdouts["raw_trade_count"].sum())
    holdout_profit_total = float(holdouts["profit_usdt"].sum())
    holdout_decision = (
        "No. Forward holdouts do not supply enough sample to justify continued research."
        if holdout_trade_total < 20 or holdout_profit_total <= 0
        else "Yes. Forward holdouts are large enough to justify continued research."
    )

    lines = [
        "# Long-Only Promotion Study",
        "",
        "> Frozen-candidate study only. No new hyperopt, no threshold retuning in the conclusion path, and no strategy redesign.",
        "",
        "## Frozen Candidate",
        "",
        "- Strategy: `VolatilityRotationMRDiagnosticLongOnly`",
        "- Snapshot design: point-in-time top-50 universes on the broadened PTI research set",
        "- Selection evidence ends at `2024-01-01 -> 2024-07-01`.",
        "- Promotion evidence starts at `2024-07-01 -> 2025-01-01`.",
        "",
        render_defaults_table(),
        "",
        "## Candidate-Selection Reference",
        "",
        frame[frame["evidence_role"] == "candidate_selection_reference"][
            [
                "study_label",
                "anchor",
                "timerange",
                "raw_trade_count",
                "unique_trade_count",
                "profit_pct",
                "profit_usdt",
                "max_drawdown_pct",
                "monthly_distribution",
                "pair_contribution",
            ]
        ].to_markdown(index=False),
        "",
        "## Promotion Holdouts",
        "",
        holdouts[
            [
                "study_label",
                "anchor",
                "window_months",
                "timerange",
                "raw_trade_count",
                "unique_trade_count",
                "profit_pct",
                "profit_usdt",
                "max_drawdown_pct",
                "sample_large_enough",
                "monthly_distribution",
                "pair_contribution",
            ]
        ].to_markdown(index=False),
        "",
        "## Decision",
        "",
        f"- Combined holdout raw trades: `{holdout_trade_total}`",
        f"- Combined holdout profit: `{holdout_profit_total:.3f} USDT`",
        f"- Holdout evidence large enough to justify continued research? `{holdout_decision}`",
        "",
        "## Reproduction",
        "",
        "```powershell",
        "& .\\.venv-freqtrade\\Scripts\\python.exe scripts\\run_longonly_promotion_study.py `",
        f"  --selection-matrix-csv {selection_matrix_csv.as_posix()} `",
        f"  --selection-backtest-dir {selection_backtest_dir.as_posix()} `",
        f"  --output-md {Path(args.output_md).as_posix()} `",
        f"  --output-csv {output_csv.as_posix()} `",
        f"  --logs-dir {logs_dir.as_posix()} `",
        f"  --backtest-dir {backtest_dir.as_posix()}",
        "```",
        "",
    ]
    Path(args.output_md).write_text("\n".join(lines), encoding="utf-8")
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
