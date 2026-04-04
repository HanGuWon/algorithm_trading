from __future__ import annotations

import argparse
import json
from pathlib import Path

import ccxt
import pandas as pd


EXPLICIT_EXCLUSIONS = {
    "AAPL",
    "AMZN",
    "BTCDOM",
    "COIN",
    "DEFI",
    "EWJ",
    "EWY",
    "GOOGL",
    "HOOD",
    "INTC",
    "MSTR",
    "NATGAS",
    "NVDA",
    "PAXG",
    "PAYP",
    "PLTR",
    "QQQ",
    "SPY",
    "TSLA",
    "TSM",
    "USDC",
    "XAG",
    "XAU",
    "XAUT",
    "XPD",
    "XPT",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a reproducible Binance USDT-M research candidate universe."
    )
    parser.add_argument("--exchange", default="binance")
    parser.add_argument("--quote", default="USDT")
    parser.add_argument("--settle", default="USDT")
    parser.add_argument("--target-size", type=int, default=90)
    parser.add_argument(
        "--max-onboard-date",
        default="2025-01-01",
        help="Exclude pairs listed after this UTC date because they cannot contribute to anchors before it.",
    )
    parser.add_argument(
        "--output-json",
        default="user_data/pairs/binance_usdt_futures_research_candidates.json",
    )
    parser.add_argument(
        "--output-csv",
        default="docs/validation/analysis/research_candidate_universe.csv",
    )
    parser.add_argument(
        "--output-md",
        default="docs/validation/analysis/research_candidate_universe.md",
    )
    return parser.parse_args()


def is_ascii(value: str) -> bool:
    try:
        value.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def build_rows(exchange_name: str, quote: str, settle: str) -> list[dict[str, object]]:
    exchange_class = getattr(ccxt, exchange_name)
    exchange = exchange_class({"options": {"defaultType": "swap"}})
    markets = exchange.load_markets()
    tickers = exchange.fetch_tickers()

    rows: list[dict[str, object]] = []
    for symbol, market in markets.items():
        if market.get("quote") != quote:
            continue
        if market.get("settle") != settle:
            continue
        if not market.get("swap") or not market.get("linear"):
            continue

        base = str(market.get("base") or "")
        ticker = tickers.get(symbol, {})
        info = market.get("info") or {}
        onboard_raw = info.get("onboardDate") or 0
        onboard_date = pd.to_datetime(int(onboard_raw), unit="ms", utc=True) if onboard_raw else pd.NaT

        rows.append(
            {
                "pair": symbol,
                "base": base,
                "active": bool(market.get("active", False)),
                "quote_volume": float(ticker.get("quoteVolume") or 0.0),
                "base_volume": float(ticker.get("baseVolume") or 0.0),
                "onboard_date": onboard_date,
                "onboard_date_raw": int(onboard_raw) if onboard_raw else 0,
            }
        )
    return rows


def apply_filters(frame: pd.DataFrame, target_size: int, max_onboard_date: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    working = frame.copy()
    working["exclude_reason"] = ""

    working.loc[~working["active"], "exclude_reason"] = "inactive on exchange"
    working.loc[(working["exclude_reason"] == "") & (~working["base"].map(is_ascii)), "exclude_reason"] = "non-ascii base"
    working.loc[
        (working["exclude_reason"] == "") & (working["base"].isin(EXPLICIT_EXCLUSIONS)),
        "exclude_reason",
    ] = "explicit non-crypto proxy / index / commodity exclusion"
    working.loc[
        (working["exclude_reason"] == "") & (working["onboard_date"].isna() | (working["onboard_date"] > max_onboard_date)),
        "exclude_reason",
    ] = f"listed after {max_onboard_date.date()}"
    working.loc[(working["exclude_reason"] == "") & (working["quote_volume"] <= 0), "exclude_reason"] = "zero current quote volume"

    eligible = (
        working.loc[working["exclude_reason"] == ""]
        .sort_values(["quote_volume", "onboard_date_raw", "pair"], ascending=[False, True, True])
        .head(target_size)
        .copy()
    )
    eligible["selected"] = True

    excluded = working.loc[working["exclude_reason"] != ""].copy()
    excluded["selected"] = False

    return eligible.reset_index(drop=True), excluded.reset_index(drop=True)


def write_markdown(
    path: Path,
    exchange_name: str,
    quote: str,
    settle: str,
    target_size: int,
    max_onboard_date: pd.Timestamp,
    eligible: pd.DataFrame,
    excluded: pd.DataFrame,
) -> None:
    selected_pairs = eligible["pair"].tolist()
    reason_counts = (
        excluded.groupby("exclude_reason", as_index=False)
        .size()
        .sort_values("size", ascending=False)
        .reset_index(drop=True)
    )

    selected_table = eligible[["pair", "quote_volume", "onboard_date"]].copy()
    if not selected_table.empty:
        selected_table["quote_volume"] = selected_table["quote_volume"].map(lambda value: f"{value:,.0f}")
        selected_table["onboard_date"] = pd.to_datetime(selected_table["onboard_date"], utc=True).dt.strftime("%Y-%m-%d")

    excluded_table = excluded[["pair", "exclude_reason", "quote_volume", "onboard_date"]].copy()
    if not excluded_table.empty:
        excluded_table = excluded_table.head(30)
        excluded_table["quote_volume"] = excluded_table["quote_volume"].map(lambda value: f"{value:,.0f}")
        excluded_table["onboard_date"] = pd.to_datetime(excluded_table["onboard_date"], utc=True).dt.strftime("%Y-%m-%d")

    lines = [
        "# Research Candidate Universe",
        "",
        f"- Exchange: `{exchange_name}` futures",
        f"- Quote / settle: `{quote}/{settle}`",
        f"- Target candidate size: `{target_size}`",
        f"- Max onboard date: `{max_onboard_date.date()}`",
        f"- Eligible candidates retained: `{len(selected_pairs)}`",
        f"- Explicit exclusions: `{', '.join(sorted(EXPLICIT_EXCLUSIONS))}`",
        "",
        "## Rationale",
        "",
        "The candidate universe is derived from current Binance USDT-M swap metadata plus current quote-volume ranking,",
        "but it explicitly excludes stock/index/commodity proxy markets and non-ASCII novelty contracts that are",
        "structurally unsuitable for this crypto mean-reversion thesis. Historical PTI snapshots then re-rank this",
        "candidate set using point-in-time candle-based quote-volume approximations and coverage checks.",
        "",
        "## Selected Candidates",
        "",
        selected_table.to_markdown(index=False) if not selected_table.empty else "No candidates were retained.",
        "",
        "## Exclusion Summary",
        "",
        reason_counts.to_markdown(index=False) if not reason_counts.empty else "No exclusions were applied.",
        "",
        "## Example Excluded Markets",
        "",
        excluded_table.to_markdown(index=False) if not excluded_table.empty else "No example exclusions.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    max_onboard_date = pd.Timestamp(args.max_onboard_date, tz="UTC")

    rows = build_rows(args.exchange, args.quote, args.settle)
    frame = pd.DataFrame(rows).sort_values(["pair"]).reset_index(drop=True)
    eligible, excluded = apply_filters(frame, args.target_size, max_onboard_date)

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(eligible["pair"].tolist(), ensure_ascii=True, indent=2), encoding="utf-8")

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    combined = pd.concat([eligible, excluded], ignore_index=True)
    combined["onboard_date"] = combined["onboard_date"].astype("string")
    combined.to_csv(output_csv, index=False)

    write_markdown(
        path=Path(args.output_md),
        exchange_name=args.exchange,
        quote=args.quote,
        settle=args.settle,
        target_size=args.target_size,
        max_onboard_date=max_onboard_date,
        eligible=eligible,
        excluded=excluded,
    )

    print(f"Selected {len(eligible)} research candidates.")
    print(f"Pairs JSON saved to {output_json}")
    print(f"Coverage CSV saved to {output_csv}")
    print(f"Summary markdown saved to {args.output_md}")


if __name__ == "__main__":
    main()
