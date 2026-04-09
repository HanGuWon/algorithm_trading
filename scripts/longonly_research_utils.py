from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


FORWARD_HORIZONS = [1, 3, 6, 12, 24, 48]
TIMEFRAME_MINUTES = {"5m": 5, "1h": 60}


@dataclass(frozen=True)
class StrategyVariant:
    label: str
    strategy: str
    config_path: str


LONGONLY_VARIANTS = [
    StrategyVariant(
        label="baseline_long_only",
        strategy="VolatilityRotationMRLongOnly",
        config_path="user_data/configs/volatility_rotation_mr_backtest_top50_longonly.json",
    ),
    StrategyVariant(
        label="diagnostic_long_only",
        strategy="VolatilityRotationMRDiagnosticLongOnly",
        config_path="user_data/configs/volatility_rotation_mr_backtest_top50_diagnostic_longonly.json",
    ),
]


class LocalDataProvider:
    def __init__(self, pair_frames: dict[tuple[str, str], pd.DataFrame], whitelist: list[str]) -> None:
        self._pair_frames = pair_frames
        self._whitelist = whitelist
        self.runmode = type("RunModeStub", (), {"value": "backtest"})()

    def current_whitelist(self) -> list[str]:
        return list(self._whitelist)

    def get_pair_dataframe(self, pair: str, timeframe: str) -> pd.DataFrame:
        frame = self._pair_frames.get((pair, timeframe))
        if frame is None:
            raise KeyError(f"Missing dataframe for {(pair, timeframe)}")
        return frame.copy()


def load_strategy(strategy_file: Path, class_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"longonly_strategy_module_{class_name}", strategy_file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import strategy file {strategy_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    strategy_class = getattr(module, class_name)
    return strategy_class(config={})


def snapshot_path(snapshot_dir: Path, anchor: str, top_n: int) -> Path:
    if top_n == 20:
        return snapshot_dir / f"binance_usdt_futures_snapshot_{anchor}.json"
    return snapshot_dir / f"binance_usdt_futures_snapshot_{anchor}_top{top_n}.json"


def load_snapshot_pairs(snapshot_json: Path) -> list[str]:
    payload = json.loads(snapshot_json.read_text(encoding="utf-8"))
    return list(payload["exchange"]["pair_whitelist"])


def pair_to_file_stem(pair: str) -> str:
    base, rest = pair.split("/", maxsplit=1)
    quote, settle = rest.split(":", maxsplit=1)
    return f"{base}_{quote}_{settle}"


def load_ohlcv(datadir: Path, pair: str, timeframe: str) -> pd.DataFrame:
    stem = pair_to_file_stem(pair)
    path = datadir / "futures" / f"{stem}-{timeframe}-futures.feather"
    frame = pd.read_feather(path)
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    return frame.sort_values("date").reset_index(drop=True)


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def make_timerange(anchor: pd.Timestamp, months: int) -> tuple[str, pd.Timestamp, pd.Timestamp]:
    end = anchor + pd.DateOffset(months=months)
    return f"{anchor.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}", anchor, end


def write_temp_config(temp_dir: Path, base_config: Path, snapshot: Path, variant: StrategyVariant, db_url: str) -> Path:
    payload = {
        "$schema": "https://schema.freqtrade.io/schema.json",
        "add_config_files": [str(base_config.resolve()), str(snapshot.resolve())],
        "strategy": variant.strategy,
        "dry_run": True,
        "db_url": db_url,
        "exchange": {"key": "", "secret": "", "password": ""},
        "pairlists": [{"method": "StaticPairList"}],
    }
    path = temp_dir / f"{snapshot.stem}_{variant.label}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def run_backtest(
    python_executable: Path,
    config_path: Path,
    strategy_path: Path,
    timerange: str,
    logs_dir: Path,
    backtest_dir: Path,
    anchor_label: str,
    variant: StrategyVariant,
) -> Path:
    ensure_directory(logs_dir)
    ensure_directory(backtest_dir)
    log_path = logs_dir / f"{anchor_label}_{variant.label}.log"
    command = [
        str(python_executable),
        "-m",
        "freqtrade",
        "backtesting",
        "--config",
        str(config_path),
        "--strategy",
        variant.strategy,
        "--strategy-path",
        str(strategy_path),
        "--timeframe",
        "5m",
        "--timerange",
        timerange,
        "--enable-protections",
        "--export",
        "signals",
        "--backtest-directory",
        str(backtest_dir),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    log_path.write_text(
        (completed.stdout or "") + ("\n" if completed.stdout else "") + (completed.stderr or ""),
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Backtest failed for {anchor_label} {variant.label}. See {log_path}")
    last_result = json.loads((backtest_dir / ".last_result.json").read_text(encoding="utf-8"))
    return backtest_dir / last_result["latest_backtest"]


def parse_backtest_zip(zip_path: Path, strategy_name: str) -> tuple[dict[str, Any], pd.DataFrame]:
    with zipfile.ZipFile(zip_path) as archive:
        json_name = next(name for name in archive.namelist() if name.endswith(".json") and not name.endswith("_config.json"))
        payload = json.loads(archive.read(json_name).decode("utf-8"))
    strategy_data = payload["strategy"][strategy_name]
    trades = pd.DataFrame(strategy_data.get("trades", []))
    if not trades.empty:
        trades["open_date"] = pd.to_datetime(trades["open_date"], utc=True)
        trades["close_date"] = pd.to_datetime(trades["close_date"], utc=True)
        trades["trade_signature"] = (
            trades["pair"].astype(str)
            + "|"
            + trades["open_date"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            + "|"
            + trades["is_short"].astype(str)
        )
        trades["month"] = trades["open_date"].dt.strftime("%Y-%m")
    return strategy_data, trades


def monthly_distribution(trades: pd.DataFrame) -> str:
    if trades.empty:
        return ""
    grouped = trades.groupby("month").size().sort_index()
    return ", ".join(f"{month}:{count}" for month, count in grouped.items())


def pair_contribution(trades: pd.DataFrame, top_n: int = 8) -> str:
    if trades.empty:
        return ""
    grouped = trades.groupby("pair")["profit_abs"].sum().sort_values(ascending=False).head(top_n)
    return ", ".join(f"{pair}:{value:.3f}" for pair, value in grouped.items())


def max_drawdown_from_profit(trades: pd.DataFrame) -> float:
    if trades.empty:
        return 0.0
    equity = trades.sort_values("open_date")["profit_abs"].cumsum()
    running_max = equity.cummax()
    drawdown = equity - running_max
    return float(abs(drawdown.min()))


def classify_resilience(profit_after: float, trade_count_after: int, base_profit: float, base_trades: int) -> str:
    if trade_count_after <= 0 or profit_after <= 0:
        return "collapses"
    profit_share = profit_after / base_profit if base_profit > 0 else 0.0
    trade_share = trade_count_after / base_trades if base_trades > 0 else 0.0
    if profit_share < 0.5 or trade_share < 0.6:
        return "weakens materially"
    return "survives"


def pct_share(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def compute_hhi(values: pd.Series) -> float:
    positive = values[values > 0]
    total = positive.sum()
    if total <= 0:
        return 0.0
    shares = positive / total
    return float((shares**2).sum())


def build_pair_frames(
    strategy: Any,
    pairs: list[str],
    datadir: Path,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[dict[tuple[str, str], pd.DataFrame], pd.Timestamp]:
    timeframe_minutes = strategy._timeframe_to_minutes(strategy.timeframe)
    preload_start = start - pd.Timedelta(minutes=int(strategy.startup_candle_count) * timeframe_minutes)

    pair_frames: dict[tuple[str, str], pd.DataFrame] = {}
    for pair in pairs:
        pair_frames[(pair, strategy.timeframe)] = load_ohlcv(datadir, pair, strategy.timeframe)
        pair_frames[(pair, strategy.informative_timeframe)] = load_ohlcv(datadir, pair, strategy.informative_timeframe)
    return pair_frames, preload_start


def compute_long_signal_events(
    strategy: Any,
    pairs: list[str],
    datadir: Path,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    pair_frames, preload_start = build_pair_frames(strategy, pairs, datadir, start, end)
    strategy.dp = LocalDataProvider(pair_frames=pair_frames, whitelist=pairs)
    rows: list[dict[str, object]] = []

    for pair in pairs:
        raw_5m = pair_frames[(pair, strategy.timeframe)]
        raw_1h = pair_frames[(pair, strategy.informative_timeframe)]
        pair_frames[(pair, strategy.informative_timeframe)] = raw_1h[(raw_1h["date"] >= preload_start) & (raw_1h["date"] <= end)].copy()
        frame = raw_5m[(raw_5m["date"] >= preload_start) & (raw_5m["date"] <= end)].copy()
        frame = strategy.populate_indicators(frame.copy(), {"pair": pair})
        frame = strategy.populate_entry_trend(frame.copy(), {"pair": pair})
        frame = frame.reset_index(drop=True)

        signal_indices = frame.index[(frame["date"] >= start) & (frame["date"] <= end) & (frame["enter_long"] == 1)]
        for idx in signal_indices:
            entry_price = float(frame.at[idx, "close"])
            future = frame.iloc[idx + 1 : idx + 49].copy()
            if future.empty or entry_price <= 0:
                continue

            row: dict[str, object] = {
                "pair": pair,
                "signal_date": frame.at[idx, "date"],
                "trade_open_date": frame.at[idx, "date"] + pd.Timedelta(minutes=TIMEFRAME_MINUTES[strategy.timeframe]),
                "month": frame.at[idx, "date"].strftime("%Y-%m"),
                "entry_price": entry_price,
                "bb_mid": float(frame.at[idx, "bb_mid"]),
                "price_z": float(frame.at[idx, "price_z"]),
                "rsi": float(frame.at[idx, "rsi"]),
                "vol_z": float(frame.at[idx, "vol_z"]),
                "natr": float(frame.at[idx, "natr"]),
                "bb_width": float(frame.at[idx, "bb_width"]),
                "adx_1h": float(frame.at[idx, "adx_1h"]),
                "ema50_slope_1h": float(frame.at[idx, "ema50_slope_1h"]),
            }

            for horizon in FORWARD_HORIZONS:
                if idx + horizon >= len(frame):
                    row[f"ret_{horizon}"] = np.nan
                    row[f"mean_hit_{horizon}"] = np.nan
                    continue
                forward_close = float(frame.at[idx + horizon, "close"])
                row[f"ret_{horizon}"] = (forward_close / entry_price) - 1.0
                row[f"mean_hit_{horizon}"] = bool((frame.iloc[idx + 1 : idx + 1 + horizon]["high"] >= row["bb_mid"]).any())

            row["mfe_48"] = float(((future["high"] / entry_price) - 1.0).max())
            row["mae_48"] = float(((future["low"] / entry_price) - 1.0).min())
            rows.append(row)

    return pd.DataFrame(rows)


def collect_long_setup_rows(
    strategy: Any,
    pairs: list[str],
    datadir: Path,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    pair_frames, preload_start = build_pair_frames(strategy, pairs, datadir, start, end)
    strategy.dp = LocalDataProvider(pair_frames=pair_frames, whitelist=pairs)
    rows: list[dict[str, object]] = []

    for pair in pairs:
        raw_5m = pair_frames[(pair, strategy.timeframe)]
        raw_1h = pair_frames[(pair, strategy.informative_timeframe)]
        pair_frames[(pair, strategy.informative_timeframe)] = raw_1h[(raw_1h["date"] >= preload_start) & (raw_1h["date"] <= end)].copy()
        frame = raw_5m[(raw_5m["date"] >= preload_start) & (raw_5m["date"] <= end)].copy()
        frame = strategy.populate_indicators(frame.copy(), {"pair": pair})
        frame = strategy.populate_entry_trend(frame.copy(), {"pair": pair})
        frame = frame.reset_index(drop=True)

        analysis_mask = (frame["date"] >= start) & (frame["date"] <= end)
        for idx in frame.index[analysis_mask]:
            entry_price = float(frame.at[idx, "close"])
            if entry_price <= 0:
                continue
            future = frame.iloc[idx + 1 : idx + 49].copy()
            if future.empty:
                continue

            gates = {
                "volume": bool(frame.at[idx, "volume"] > 0),
                "active_pair": bool(frame.at[idx, "active_pair"]),
                "weak_trend_regime": bool(frame.at[idx, "weak_trend_regime"]),
                "no_breakout": not bool(frame.at[idx, "breakout_block_long"]),
                "bb_breach": bool(frame.at[idx, "close"] < frame.at[idx, "bb_lower"]),
                "rsi": bool(frame.at[idx, "rsi"] < float(strategy.rsi_long_threshold.value)),
                "price_z": bool(frame.at[idx, "price_z"] < -float(strategy.price_z_threshold.value)),
                "bullish_reversal": bool(frame.at[idx, "bullish_reversal"]),
            }
            structural_pass = (
                gates["volume"]
                and gates["active_pair"]
                and gates["weak_trend_regime"]
                and gates["no_breakout"]
                and gates["bb_breach"]
            )
            if not structural_pass:
                continue

            first_failed_gate = next(
                (name for name in ("rsi", "price_z", "bullish_reversal") if not gates[name]),
                "signal",
            )
            row = {
                "pair": pair,
                "date": frame.at[idx, "date"],
                "month": frame.at[idx, "date"].strftime("%Y-%m"),
                "row_type": "signal" if first_failed_gate == "signal" else "near_miss",
                "first_failed_gate": first_failed_gate,
                "active_pair": gates["active_pair"],
                "weak_trend_regime": gates["weak_trend_regime"],
                "no_breakout": gates["no_breakout"],
                "bb_breach": gates["bb_breach"],
                "rsi_gate": gates["rsi"],
                "price_z_gate": gates["price_z"],
                "bullish_reversal_gate": gates["bullish_reversal"],
                "enter_long": int(frame.at[idx, "enter_long"]),
                "vol_z": float(frame.at[idx, "vol_z"]),
                "natr": float(frame.at[idx, "natr"]),
                "bb_width": float(frame.at[idx, "bb_width"]),
                "adx_1h": float(frame.at[idx, "adx_1h"]),
                "ema50_slope_1h": float(frame.at[idx, "ema50_slope_1h"]),
                "rsi": float(frame.at[idx, "rsi"]),
                "price_z": float(frame.at[idx, "price_z"]),
                "ret_12": float((frame.at[idx + 12, "close"] / entry_price) - 1.0) if idx + 12 < len(frame) else np.nan,
                "ret_24": float((frame.at[idx + 24, "close"] / entry_price) - 1.0) if idx + 24 < len(frame) else np.nan,
                "ret_48": float((frame.at[idx + 48, "close"] / entry_price) - 1.0) if idx + 48 < len(frame) else np.nan,
                "mfe_48": float(((future["high"] / entry_price) - 1.0).max()),
                "mae_48": float(((future["low"] / entry_price) - 1.0).min()),
                "mean_hit_24": bool((frame.iloc[idx + 1 : idx + 25]["high"] >= frame.at[idx, "bb_mid"]).any()) if idx + 24 < len(frame) else np.nan,
                "mean_hit_48": bool((frame.iloc[idx + 1 : idx + 49]["high"] >= frame.at[idx, "bb_mid"]).any()) if idx + 48 < len(frame) else np.nan,
            }
            rows.append(row)

    return pd.DataFrame(rows)


def match_realized_trades_to_signals(trades: pd.DataFrame, signal_events: pd.DataFrame) -> pd.DataFrame:
    if trades.empty or signal_events.empty:
        return pd.DataFrame()
    signals = signal_events.copy()
    signals["trade_open_date"] = pd.to_datetime(signals["trade_open_date"], utc=True)
    merged = trades.merge(
        signals,
        how="left",
        left_on=["pair", "open_date"],
        right_on=["pair", "trade_open_date"],
        suffixes=("_trade", "_signal"),
    )
    return merged


def read_matrix_results(matrix_csv: Path, backtest_dir: Path) -> pd.DataFrame:
    frame = pd.read_csv(matrix_csv)
    frame["zip_path"] = frame["results_zip"].map(lambda name: str((backtest_dir / name).resolve()))
    return frame


def run_matrix_backtests(
    anchors: list[str],
    window_months: int,
    snapshot_dir: Path,
    snapshot_top_n: int,
    strategy_path: Path,
    base_config: Path,
    logs_dir: Path,
    backtest_dir: Path,
    db_url: str,
) -> pd.DataFrame:
    python_executable = Path(sys.executable)
    rows: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="longonly_matrix_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        for anchor_text in anchors:
            anchor = pd.Timestamp(anchor_text, tz="UTC")
            snapshot = snapshot_path(snapshot_dir, anchor_text, snapshot_top_n)
            if not snapshot.exists():
                raise FileNotFoundError(f"Missing snapshot: {snapshot}")
            pair_count = len(load_snapshot_pairs(snapshot))
            timerange, start, end = make_timerange(anchor, window_months)

            for variant in LONGONLY_VARIANTS:
                config_path = write_temp_config(temp_dir, base_config, snapshot, variant, db_url=db_url)
                zip_path = run_backtest(
                    python_executable=python_executable,
                    config_path=config_path,
                    strategy_path=strategy_path,
                    timerange=timerange,
                    logs_dir=logs_dir,
                    backtest_dir=backtest_dir,
                    anchor_label=anchor_text,
                    variant=variant,
                )
                strategy_data, trades = parse_backtest_zip(zip_path, variant.strategy)
                unique_trades = int(trades["trade_signature"].nunique()) if not trades.empty else 0
                rows.append(
                    {
                        "anchor": anchor_text,
                        "window_label": f"{window_months}m",
                        "strategy_variant": variant.label,
                        "strategy": variant.strategy,
                        "snapshot": snapshot.name,
                        "pair_count": pair_count,
                        "timerange": timerange,
                        "analysis_start": start.strftime("%Y-%m-%d"),
                        "analysis_end": end.strftime("%Y-%m-%d"),
                        "raw_trade_count": int(strategy_data.get("total_trades", 0)),
                        "unique_trade_count": unique_trades,
                        "profit_pct": round(float(strategy_data.get("profit_total", 0.0)) * 100.0, 2),
                        "profit_usdt": round(float(strategy_data.get("profit_total_abs", 0.0)), 3),
                        "drawdown_pct": round(float(strategy_data.get("max_drawdown_account", 0.0)) * 100.0, 2),
                        "monthly_distribution": monthly_distribution(trades),
                        "pair_contribution": pair_contribution(trades),
                        "usable_sample": "yes" if int(strategy_data.get("total_trades", 0)) >= 20 else "no",
                        "results_zip": zip_path.name,
                    }
                )

    return pd.DataFrame(rows).sort_values(["anchor", "strategy_variant"]).reset_index(drop=True)
