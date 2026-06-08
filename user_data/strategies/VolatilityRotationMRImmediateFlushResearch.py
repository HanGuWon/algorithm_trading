from __future__ import annotations

import csv
from datetime import timedelta
from pathlib import Path
from typing import Any

from pandas import DataFrame

from VolatilityRotationMR import VolatilityRotationMRDiagnosticLongOnly


MANIFEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "validation"
    / "analysis"
    / "major_11_immediate_flush_canonical_manifest.csv"
)

DEFAULT_CANDIDATES: list[dict[str, Any]] = [
    {
        "canonical_fixed_candidate_id": "RFC008_original",
        "price_z_threshold": 3.1,
        "rsi_threshold": 26,
        "vol_z_min": 1.5,
        "bb_width_min": 0.04,
        "use_weak_trend": False,
        "use_breakout_block": False,
        "require_close_below_bb": False,
    },
    {
        "canonical_fixed_candidate_id": "RFC001_original",
        "price_z_threshold": 3.1,
        "rsi_threshold": 26,
        "vol_z_min": 1.0,
        "bb_width_min": 0.04,
        "use_weak_trend": False,
        "use_breakout_block": False,
        "require_close_below_bb": False,
    },
    {
        "canonical_fixed_candidate_id": "RFC019_original",
        "price_z_threshold": 3.1,
        "rsi_threshold": 26,
        "vol_z_min": 0.0,
        "bb_width_min": 0.04,
        "use_weak_trend": False,
        "use_breakout_block": False,
        "require_close_below_bb": False,
    },
    {
        "canonical_fixed_candidate_id": "RFC002_original",
        "price_z_threshold": 3.1,
        "rsi_threshold": 18,
        "vol_z_min": 1.0,
        "bb_width_min": 0.04,
        "use_weak_trend": False,
        "use_breakout_block": False,
        "require_close_below_bb": False,
    },
    {
        "canonical_fixed_candidate_id": "RFC025_original",
        "price_z_threshold": 3.1,
        "rsi_threshold": 26,
        "vol_z_min": 0.5,
        "bb_width_min": 0.04,
        "use_weak_trend": False,
        "use_breakout_block": False,
        "require_close_below_bb": False,
    },
    {
        "canonical_fixed_candidate_id": "RFC009_original",
        "price_z_threshold": 3.1,
        "rsi_threshold": 18,
        "vol_z_min": 1.5,
        "bb_width_min": 0.04,
        "use_weak_trend": False,
        "use_breakout_block": False,
        "require_close_below_bb": False,
    },
    {
        "canonical_fixed_candidate_id": "RFC015_original",
        "price_z_threshold": 3.1,
        "rsi_threshold": 18,
        "vol_z_min": 0.0,
        "bb_width_min": 0.04,
        "use_weak_trend": False,
        "use_breakout_block": False,
        "require_close_below_bb": False,
    },
]

EXIT_MODES: dict[str, dict[str, Any]] = {
    "Hold24h": {"exit_mode": "hold_24h", "max_hold_hours": 24},
    "Hold72h": {"exit_mode": "hold_72h", "max_hold_hours": 72},
    "Hold120h": {"exit_mode": "hold_120h", "max_hold_hours": 120},
    "ZscoreRevert72h": {"exit_mode": "zscore_revert_or_72h", "max_hold_hours": 72},
    "RsiRevert72h": {"exit_mode": "rsi_revert_or_72h", "max_hold_hours": 72},
    "BbMidReclaim72h": {"exit_mode": "bb_mid_reclaim_or_72h", "max_hold_hours": 72},
}


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def load_manifest_candidates(path: Path = MANIFEST_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return DEFAULT_CANDIDATES

    candidates: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            candidates.append(
                {
                    "canonical_fixed_candidate_id": row["canonical_fixed_candidate_id"],
                    "price_z_threshold": safe_float(row["price_z_threshold"]),
                    "rsi_threshold": safe_int(row["rsi_threshold"]),
                    "vol_z_min": safe_float(row["vol_z_min"]),
                    "bb_width_min": safe_float(row["bb_width_min"]),
                    "use_weak_trend": as_bool(row["use_weak_trend"]),
                    "use_breakout_block": as_bool(row["use_breakout_block"]),
                    "require_close_below_bb": as_bool(row["require_close_below_bb"]),
                }
            )
    return candidates or DEFAULT_CANDIDATES


class ImmediateFlushResearchBase(VolatilityRotationMRDiagnosticLongOnly):
    """
    Research-only immediate-flush strategy shell.

    Indicator construction is inherited from the existing MR strategy. This class
    changes only the long entry mask and fixed exit family used for portfolio
    backtests of the canonical Major 11 fixed candidates.
    """

    can_short = False
    live_filters_enabled = False
    enable_live_spread_filter = False
    enable_live_orderbook_filter = False
    enable_live_funding_filter = False

    use_custom_stoploss = False
    use_custom_roi = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    stoploss = -0.99
    minimal_roi = {"0": 100.0}

    canonical_fixed_candidate_id = "BASE"
    price_z_threshold_value = 3.1
    rsi_threshold_value = 26
    vol_z_min_value = 1.0
    bb_width_min_value = 0.04
    use_weak_trend_gate = False
    use_breakout_block_gate = False
    require_close_below_bb_gate = False
    exit_mode = "hold_72h"
    max_hold_hours = 72

    @property
    def protections(self) -> list[dict[str, Any]]:
        return []

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        _ = metadata
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        long_condition = self._to_bool(
            (dataframe["volume"] > 0)
            & (dataframe["price_z"] < -float(self.price_z_threshold_value))
            & (dataframe["rsi"] < float(self.rsi_threshold_value))
            & (dataframe["vol_z"] >= float(self.vol_z_min_value))
            & (dataframe["bb_width"] >= float(self.bb_width_min_value))
        )

        if self.use_weak_trend_gate:
            long_condition &= dataframe["weak_trend_regime"].fillna(False).astype(bool)
        if self.use_breakout_block_gate:
            long_condition &= ~dataframe["breakout_block_long"].fillna(False).astype(bool)
        if self.require_close_below_bb_gate:
            long_condition &= dataframe["close"] < dataframe["bb_lower"]

        dataframe.loc[long_condition, "enter_long"] = 1
        dataframe.loc[long_condition, "enter_tag"] = f"immediate_flush_{self.canonical_fixed_candidate_id}"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        _ = metadata
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        if self.exit_mode == "zscore_revert_or_72h":
            exit_condition = dataframe["price_z"] >= 0
        elif self.exit_mode == "rsi_revert_or_72h":
            exit_condition = dataframe["rsi"] >= 50
        elif self.exit_mode == "bb_mid_reclaim_or_72h":
            exit_condition = dataframe["close"] >= dataframe["bb_mid"]
        else:
            exit_condition = False

        if exit_condition is not False:
            exit_condition = self._to_bool(exit_condition)
            dataframe.loc[exit_condition, "exit_long"] = 1
            dataframe.loc[exit_condition, "exit_tag"] = self.exit_mode
        return dataframe

    def custom_exit(
        self,
        pair: str,
        trade,
        current_time,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> str | None:
        _ = (pair, current_rate, current_profit, kwargs)
        if current_time - trade.open_date_utc >= timedelta(hours=int(self.max_hold_hours)):
            return f"time_exit_{int(self.max_hold_hours)}h"
        return None


def strategy_class_name(candidate_id: str, exit_label: str) -> str:
    source_id = candidate_id.split("_", maxsplit=1)[0]
    return f"ImmediateFlushResearch{source_id}{exit_label}"


def build_strategy_class(candidate: dict[str, Any], exit_label: str, exit_spec: dict[str, Any]):
    candidate_id = str(candidate["canonical_fixed_candidate_id"])
    return type(
        strategy_class_name(candidate_id, exit_label),
        (ImmediateFlushResearchBase,),
        {
            "__module__": __name__,
            "canonical_fixed_candidate_id": candidate_id,
            "price_z_threshold_value": safe_float(candidate["price_z_threshold"], 3.1),
            "rsi_threshold_value": safe_int(candidate["rsi_threshold"], 26),
            "vol_z_min_value": safe_float(candidate["vol_z_min"], 1.0),
            "bb_width_min_value": safe_float(candidate["bb_width_min"], 0.04),
            "use_weak_trend_gate": as_bool(candidate["use_weak_trend"]),
            "use_breakout_block_gate": as_bool(candidate["use_breakout_block"]),
            "require_close_below_bb_gate": as_bool(candidate["require_close_below_bb"]),
            "exit_mode": str(exit_spec["exit_mode"]),
            "max_hold_hours": int(exit_spec["max_hold_hours"]),
        },
    )


for _candidate in load_manifest_candidates():
    for _exit_label, _exit_spec in EXIT_MODES.items():
        _class = build_strategy_class(_candidate, _exit_label, _exit_spec)
        globals()[_class.__name__] = _class
