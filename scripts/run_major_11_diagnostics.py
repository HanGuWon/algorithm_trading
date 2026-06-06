from __future__ import annotations

import argparse
import json
import math
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_SUMMARY_CSV = "docs/validation/analysis/major_11_backtest_summary.csv"
DEFAULT_OUTPUT_CSV = "docs/validation/analysis/major_11_concentration_diagnostics.csv"
DEFAULT_OUTPUT_MD = "docs/validation/analysis/major_11_concentration_diagnostics.md"
DEFAULT_BACKTEST_ROOT = "user_data/backtest_results/major_11"
DEFAULT_DATADIR = "user_data/data/binance"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose concentration, calendar, pair, and baseline fragility for the major-11 backtests."
    )
    parser.add_argument("--summary-csv", default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--backtest-root", default=DEFAULT_BACKTEST_ROOT)
    parser.add_argument("--datadir", default=DEFAULT_DATADIR)
    parser.add_argument("--output-csv", default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--output-md", default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--min-validation-trades", type=int, default=150)
    parser.add_argument("--max-top3-trade-share", type=float, default=0.50)
    parser.add_argument("--max-month-profit-share", type=float, default=0.35)
    parser.add_argument("--max-pair-profit-share", type=float, default=0.25)
    return parser.parse_args()


def pct_share(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def clean_float(value: Any, digits: int = 4) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isinf(numeric) or math.isnan(numeric):
        return numeric
    return round(numeric, digits)


def table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    try:
        return frame.to_markdown(index=False)
    except ImportError:
        return "```csv\n" + frame.to_csv(index=False).replace("\r\n", "\n").strip() + "\n```"


def pair_to_file_stem(pair: str) -> str:
    base, rest = pair.split("/", maxsplit=1)
    quote, settle = rest.split(":", maxsplit=1)
    return f"{base}_{quote}_{settle}"


def locate_zip(backtest_root: Path, row: pd.Series) -> Path:
    raw_name = str(row.get("results_zip", ""))
    if not raw_name:
        raise FileNotFoundError("Summary row does not include results_zip.")
    candidate = Path(raw_name)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    strategy_path = backtest_root / str(row["strategy"]) / raw_name
    if strategy_path.exists():
        return strategy_path
    root_path = backtest_root / raw_name
    if root_path.exists():
        return root_path
    raise FileNotFoundError(f"Could not locate backtest zip: {raw_name}")


def read_result(zip_path: Path, strategy: str) -> tuple[dict[str, Any], pd.DataFrame]:
    with zipfile.ZipFile(zip_path) as archive:
        json_name = next(
            name for name in archive.namelist() if name.endswith(".json") and not name.endswith("_config.json")
        )
        payload = json.loads(archive.read(json_name).decode("utf-8"))
    data = payload["strategy"][strategy]
    trades = pd.DataFrame(data.get("trades", []))
    if not trades.empty:
        trades["open_date"] = pd.to_datetime(trades["open_date"], utc=True)
        trades["close_date"] = pd.to_datetime(trades["close_date"], utc=True)
        trades["month"] = trades["open_date"].dt.strftime("%Y-%m")
        trades["year"] = trades["open_date"].dt.strftime("%Y")
        trades["profit_abs"] = trades["profit_abs"].astype(float)
        trades["profit_ratio"] = trades["profit_ratio"].astype(float)
    return data, trades


def profit_factor(trades: pd.DataFrame) -> float:
    if trades.empty:
        return 0.0
    gross_profit = float(trades.loc[trades["profit_abs"] > 0, "profit_abs"].sum())
    gross_loss = abs(float(trades.loc[trades["profit_abs"] < 0, "profit_abs"].sum()))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def max_group_share(trades: pd.DataFrame, column: str, total_profit: float) -> float:
    if trades.empty or total_profit <= 0:
        return 0.0
    grouped = trades.groupby(column)["profit_abs"].sum()
    return pct_share(max(float(grouped.max()), 0.0), total_profit) if not grouped.empty else 0.0


def top_trade_share(trades: pd.DataFrame, count: int, total_profit: float) -> float:
    if trades.empty or total_profit <= 0:
        return 0.0
    top_profit = float(
        trades.loc[trades["profit_abs"] > 0, "profit_abs"].sort_values(ascending=False).head(count).sum()
    )
    return pct_share(top_profit, total_profit)


def classify(summary: dict[str, Any], args: argparse.Namespace) -> tuple[str, str]:
    failed: list[str] = []
    if int(summary["trades"]) < args.min_validation_trades:
        failed.append("sample_size")
    if float(summary["profit_usdt"]) <= 0:
        failed.append("net_profit")
    if float(summary["top3_trade_profit_share"]) > args.max_top3_trade_share:
        failed.append("top_trade_concentration")
    if float(summary["top_month_profit_share"]) > args.max_month_profit_share:
        failed.append("month_concentration")
    if float(summary["top_pair_profit_share"]) > args.max_pair_profit_share:
        failed.append("pair_concentration")

    if "net_profit" in failed:
        decision = "PARK"
    elif failed:
        decision = "REDESIGN_RESEARCH_ONLY"
    else:
        decision = "CONTINUE_VALIDATION"
    return decision, ", ".join(failed)


def summarize_strategy(data: dict[str, Any], trades: pd.DataFrame, strategy: str, args: argparse.Namespace) -> dict[str, Any]:
    total_profit = float(trades["profit_abs"].sum()) if not trades.empty else 0.0
    days = float(data.get("backtest_days", 0.0) or 0.0)
    summary = {
        "strategy": strategy,
        "analysis": "strategy_summary",
        "trades": int(len(trades)),
        "profit_usdt": clean_float(total_profit, 3),
        "profit_pct": clean_float(float(data.get("profit_total", 0.0)) * 100.0, 4),
        "win_rate": clean_float(float((trades["profit_abs"] > 0).mean()) if not trades.empty else 0.0, 4),
        "profit_factor": clean_float(profit_factor(trades), 4),
        "trades_per_year": clean_float((len(trades) / days) * 365.0 if days > 0 else 0.0, 3),
        "active_months": int(trades["month"].nunique()) if not trades.empty else 0,
        "active_years": int(trades["year"].nunique()) if not trades.empty else 0,
        "top1_trade_profit_share": clean_float(top_trade_share(trades, 1, total_profit), 4),
        "top3_trade_profit_share": clean_float(top_trade_share(trades, 3, total_profit), 4),
        "top5_trade_profit_share": clean_float(top_trade_share(trades, 5, total_profit), 4),
        "top_month_profit_share": clean_float(max_group_share(trades, "month", total_profit), 4),
        "top_pair_profit_share": clean_float(max_group_share(trades, "pair", total_profit), 4),
        "backtest_start": data.get("backtest_start", ""),
        "backtest_end": data.get("backtest_end", ""),
    }
    decision, failed = classify(summary, args)
    summary["decision"] = decision
    summary["failed_checks"] = failed
    return summary


def contribution_table(trades: pd.DataFrame, group_cols: list[str], analysis: str, strategy: str) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    total_profit = float(trades["profit_abs"].sum())
    grouped = (
        trades.groupby(group_cols, as_index=False)
        .agg(
            trades=("profit_abs", "size"),
            wins=("profit_abs", lambda values: int((values > 0).sum())),
            profit_usdt=("profit_abs", "sum"),
            avg_profit_usdt=("profit_abs", "mean"),
            avg_profit_pct=("profit_ratio", lambda values: float(values.mean()) * 100.0),
        )
        .sort_values(["profit_usdt", "trades"], ascending=[False, False])
    )
    grouped.insert(0, "strategy", strategy)
    grouped.insert(1, "analysis", analysis)
    grouped["win_rate"] = grouped["wins"] / grouped["trades"]
    grouped["net_profit_share"] = grouped["profit_usdt"].map(
        lambda value: pct_share(max(float(value), 0.0), total_profit) if total_profit > 0 else 0.0
    )
    for column in ("profit_usdt", "avg_profit_usdt", "avg_profit_pct", "win_rate", "net_profit_share"):
        grouped[column] = grouped[column].map(lambda value: clean_float(value, 4))
    return grouped


def top_trade_removal(trades: pd.DataFrame, strategy: str) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    ranked = trades.sort_values("profit_abs", ascending=False).reset_index(drop=True)
    rows: list[dict[str, Any]] = []
    for count in (1, 3, 5):
        removed = ranked.head(count)
        remaining = ranked.drop(index=removed.index)
        rows.append(
            {
                "strategy": strategy,
                "analysis": "top_trade_removal",
                "removed_top_trades": count,
                "remaining_trades": int(len(remaining)),
                "removed_profit_usdt": clean_float(removed["profit_abs"].sum(), 3),
                "remaining_profit_usdt": clean_float(remaining["profit_abs"].sum(), 3),
                "removed_pairs": ", ".join(removed["pair"].astype(str).tolist()),
                "removed_months": ", ".join(removed["month"].astype(str).tolist()),
            }
        )
    return pd.DataFrame(rows)


def buy_hold_rows(datadir: Path, pairs: list[str], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for pair in pairs:
        path = datadir / "futures" / f"{pair_to_file_stem(pair)}-5m-futures.feather"
        if not path.exists():
            rows.append({"pair": pair, "status": "missing_data"})
            continue
        frame = pd.read_feather(path, columns=["date", "close"])
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        subset = frame[(frame["date"] >= start) & (frame["date"] <= end)].sort_values("date")
        if subset.empty:
            rows.append({"pair": pair, "status": "no_data_in_window"})
            continue
        start_close = float(subset.iloc[0]["close"])
        end_close = float(subset.iloc[-1]["close"])
        if start_close <= 0:
            rows.append({"pair": pair, "status": "bad_start_price"})
            continue
        rows.append(
            {
                "pair": pair,
                "status": "ok",
                "start": subset.iloc[0]["date"].isoformat(),
                "end": subset.iloc[-1]["date"].isoformat(),
                "buy_hold_return_pct": clean_float(((end_close / start_close) - 1.0) * 100.0, 3),
            }
        )
    return pd.DataFrame(rows)


def buy_hold_summary(datadir: Path, data: dict[str, Any], strategy: str) -> pd.DataFrame:
    pairs = list(data.get("pairlist", []))
    if not pairs:
        return pd.DataFrame()
    start = pd.to_datetime(data["backtest_start"], utc=True)
    end = pd.to_datetime(data["backtest_end"], utc=True)
    returns = buy_hold_rows(datadir, pairs, start, end)
    ok = returns[returns["status"] == "ok"].copy()
    if ok.empty:
        return pd.DataFrame([{"strategy": strategy, "analysis": "buy_hold_baseline", "pairs": len(pairs), "usable_pairs": 0}])
    return pd.DataFrame(
        [
            {
                "strategy": strategy,
                "analysis": "buy_hold_baseline",
                "pairs": len(pairs),
                "usable_pairs": int(len(ok)),
                "mean_buy_hold_return_pct": clean_float(ok["buy_hold_return_pct"].mean(), 3),
                "median_buy_hold_return_pct": clean_float(ok["buy_hold_return_pct"].median(), 3),
                "best_pair": str(ok.sort_values("buy_hold_return_pct", ascending=False).iloc[0]["pair"]),
                "best_pair_return_pct": clean_float(ok["buy_hold_return_pct"].max(), 3),
                "worst_pair": str(ok.sort_values("buy_hold_return_pct", ascending=True).iloc[0]["pair"]),
                "worst_pair_return_pct": clean_float(ok["buy_hold_return_pct"].min(), 3),
            }
        ]
    )


def build_report(args: argparse.Namespace) -> tuple[pd.DataFrame, str]:
    summary_frame = pd.read_csv(args.summary_csv)
    backtest_root = Path(args.backtest_root)
    datadir = Path(args.datadir)

    csv_frames: list[pd.DataFrame] = []
    strategy_summaries: list[dict[str, Any]] = []
    strategy_sections: list[str] = []

    for _, summary_row in summary_frame.iterrows():
        strategy = str(summary_row["strategy"])
        data, trades = read_result(locate_zip(backtest_root, summary_row), strategy)
        summary = summarize_strategy(data, trades, strategy, args)
        strategy_summaries.append(summary)

        summary_table = pd.DataFrame([summary])
        pair_stats = contribution_table(trades, ["pair"], "pair_contribution", strategy)
        year_stats = contribution_table(trades, ["year"], "year_contribution", strategy)
        month_stats = contribution_table(trades, ["month"], "month_contribution", strategy)
        removals = top_trade_removal(trades, strategy)
        buy_hold = buy_hold_summary(datadir, data, strategy)
        csv_frames.extend([summary_table, pair_stats, year_stats, month_stats, removals, buy_hold])

        strategy_sections.extend(
            [
                f"## {strategy}",
                "",
                "### Summary",
                "",
                table(summary_table),
                "",
                "### Top Trade Removal",
                "",
                table(removals),
                "",
                "### Pair Contribution",
                "",
                table(pair_stats.head(12)),
                "",
                "### Year Contribution",
                "",
                table(year_stats),
                "",
                "### Largest Month Contributions",
                "",
                table(month_stats.head(12)),
                "",
                "### Buy-And-Hold Baseline Context",
                "",
                table(buy_hold),
                "",
            ]
        )

    decision_frame = pd.DataFrame(strategy_summaries)
    report = [
        "# Major 11 Concentration Diagnostics",
        "",
        "> Research-only audit report. These diagnostics test whether the small backtest result is broad and repeatable enough to justify further strategy work.",
        "",
        "## Decision Rules",
        "",
        f"- Minimum validation trades: `{args.min_validation_trades}`",
        f"- Maximum top-3 trade net-profit share: `{args.max_top3_trade_share:.2f}`",
        f"- Maximum top-month net-profit share: `{args.max_month_profit_share:.2f}`",
        f"- Maximum top-pair net-profit share: `{args.max_pair_profit_share:.2f}`",
        "",
        "## Strategy-Level Decision Summary",
        "",
        table(decision_frame),
        "",
    ]
    return pd.concat([frame for frame in csv_frames if not frame.empty], ignore_index=True, sort=False), "\n".join(
        report + strategy_sections
    )


def main() -> None:
    args = parse_args()
    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    combined, markdown = build_report(args)
    combined.to_csv(output_csv, index=False)
    output_md.write_text(markdown, encoding="utf-8")

    summaries = combined[combined["analysis"] == "strategy_summary"].copy()
    print(table(summaries[["strategy", "trades", "profit_usdt", "decision", "failed_checks"]]))
    print(f"Diagnostics written to {output_md}")


if __name__ == "__main__":
    main()
