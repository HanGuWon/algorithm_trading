from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

import build_historical_pair_snapshot as snapshot_builder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build quarterly PTI snapshots with top_n sensitivity and union summaries."
    )
    parser.add_argument("--datadir", default="user_data/data/binance")
    parser.add_argument("--pairs-file", required=True)
    parser.add_argument("--anchor-start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--anchor-end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--top-n", nargs="+", type=int, default=[20, 35, 50])
    parser.add_argument("--quote-currency", default="USDT")
    parser.add_argument("--settle-currency", default="USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--lookback", default="7d")
    parser.add_argument("--post-window", default="30d")
    parser.add_argument("--min-coverage-ratio", type=float, default=0.95)
    parser.add_argument("--snapshot-dir", default="user_data/pairs")
    parser.add_argument("--report-dir", default="docs/validation/analysis")
    parser.add_argument("--summary-md", default="docs/validation/analysis/historical_snapshot_universe_sensitivity.md")
    parser.add_argument("--summary-csv", default="docs/validation/analysis/historical_snapshot_universe_sensitivity.csv")
    parser.add_argument("--union-top-n", type=int, default=50)
    parser.add_argument("--union-output", default="user_data/pairs/binance_usdt_futures_snapshot_union_top50_2022-2025.json")
    return parser.parse_args()


def load_pair_filter(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return set(payload)
    if isinstance(payload, dict):
        whitelist = payload.get("exchange", {}).get("pair_whitelist")
        if isinstance(whitelist, list):
            return set(str(pair) for pair in whitelist)
    raise ValueError(f"Unsupported pairs file format: {path}")


def anchor_dates(start: str, end: str) -> list[pd.Timestamp]:
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")
    return list(pd.date_range(start=start_ts, end=end_ts, freq="QS"))


def write_snapshot(path: Path, pairs: list[str]) -> None:
    payload = {
        "$schema": "https://schema.freqtrade.io/schema.json",
        "exchange": {"pair_whitelist": pairs},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    datadir = Path(args.datadir)
    futures_dir = datadir / "futures"
    pair_filter = load_pair_filter(Path(args.pairs_file))
    timeframe_delta = snapshot_builder.timeframe_to_timedelta(args.timeframe)
    lookback = pd.Timedelta(args.lookback)
    post_window = pd.Timedelta(args.post_window)

    all_paths: list[tuple[str, Path]] = []
    for path in sorted(futures_dir.glob(f"*_{args.quote_currency}_{args.settle_currency}-{args.timeframe}-futures.feather")):
        pair = snapshot_builder.parse_pair_from_filename(path, args.quote_currency, args.settle_currency, args.timeframe)
        if pair is None or pair not in pair_filter:
            continue
        all_paths.append((pair, path))

    if not all_paths:
        raise SystemExit(f"No candidate candle files found under {futures_dir} for {args.pairs_file}")

    anchors = anchor_dates(args.anchor_start, args.anchor_end)
    summary_rows: list[dict[str, object]] = []
    union_pairs: set[str] = set()

    for anchor in anchors:
        results = [
            snapshot_builder.evaluate_pair(
                path=path,
                pair=pair,
                reference_date=anchor,
                lookback=lookback,
                post_window=post_window,
                timeframe_delta=timeframe_delta,
                min_coverage_ratio=args.min_coverage_ratio,
            )
            for pair, path in all_paths
        ]
        frame = snapshot_builder.to_dataframe(results)
        eligible = frame.loc[frame["selected"]].copy()

        base_name = anchor.strftime("%Y-%m-%d")
        report_csv = Path(args.report_dir) / f"historical_snapshot_{base_name}.csv"
        report_md = Path(args.report_dir) / f"historical_snapshot_{base_name}.md"
        report_csv.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(report_csv, index=False)
        snapshot_builder.write_markdown(
            report_md,
            reference_date=anchor,
            lookback=lookback,
            post_window=post_window,
            top_n=max(args.top_n),
            eligible_frame=eligible,
            all_frame=frame,
        )

        for top_n in args.top_n:
            selected_pairs = eligible["pair"].tolist()[:top_n]
            if top_n == 20:
                output_name = f"binance_usdt_futures_snapshot_{base_name}.json"
            else:
                output_name = f"binance_usdt_futures_snapshot_{base_name}_top{top_n}.json"
            output_json = Path(args.snapshot_dir) / output_name
            write_snapshot(output_json, selected_pairs)

            if top_n == args.union_top_n:
                union_pairs.update(selected_pairs)

            summary_rows.append(
                {
                    "anchor": base_name,
                    "top_n": top_n,
                    "candidate_files": len(all_paths),
                    "eligible_pairs": len(eligible),
                    "selected_pairs": len(selected_pairs),
                    "first_pair": selected_pairs[0] if selected_pairs else "",
                    "last_pair": selected_pairs[-1] if selected_pairs else "",
                }
            )

    summary_frame = pd.DataFrame(summary_rows).sort_values(["anchor", "top_n"]).reset_index(drop=True)
    summary_csv = Path(args.summary_csv)
    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_frame.to_csv(summary_csv, index=False)

    union_output = Path(args.union_output)
    union_list = sorted(union_pairs)
    union_output.parent.mkdir(parents=True, exist_ok=True)
    union_output.write_text(json.dumps(union_list, ensure_ascii=True, indent=2), encoding="utf-8")

    pivot = summary_frame.pivot(index="anchor", columns="top_n", values="selected_pairs").fillna(0).astype(int)
    lines = [
        "# Historical Snapshot Universe Sensitivity",
        "",
        f"- Candidate pairs file: `{args.pairs_file}`",
        f"- Anchors: `{args.anchor_start}` to `{args.anchor_end}` quarterly",
        f"- top_n sweep: `{', '.join(str(value) for value in args.top_n)}`",
        f"- Coverage filter: `{args.min_coverage_ratio:.0%}` lookback and post-window",
        f"- Union size at top_n={args.union_top_n}: `{len(union_list)}` pairs",
        "",
        "## Selected Pair Counts by Anchor",
        "",
        pivot.to_markdown(),
        "",
        "## Summary Table",
        "",
        summary_frame.to_markdown(index=False),
        "",
        "## Notes",
        "",
        "Higher top_n values broaden the retained universe only when the historical coverage filter passes.",
        "The union file is intended for 5m research downloads and de-overlapped alpha validation.",
        "",
    ]
    Path(args.summary_md).write_text("\n".join(lines), encoding="utf-8")

    print(f"Processed {len(anchors)} anchors from {args.anchor_start} to {args.anchor_end}.")
    print(f"Union top-{args.union_top_n} pair count: {len(union_list)}")
    print(f"Summary markdown saved to {args.summary_md}")
    print(f"Union pairs JSON saved to {args.union_output}")


if __name__ == "__main__":
    main()
