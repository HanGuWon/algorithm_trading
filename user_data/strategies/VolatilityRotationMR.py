from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any

import numpy as np
import talib.abstract as ta
from pandas import DataFrame, Series

import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.persistence import Trade
from freqtrade.strategy import (
    CategoricalParameter,
    DecimalParameter,
    IStrategy,
    IntParameter,
    merge_informative_pair,
    stoploss_from_absolute,
)

logger = logging.getLogger(__name__)


class VolatilityRotationMR(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    informative_timeframe = "1h"
    can_short = True

    process_only_new_candles = True
    startup_candle_count = 2400

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    use_custom_stoploss = True
    use_custom_roi = True
    position_adjustment_enable = False

    stoploss = -0.20
    minimal_roi = {"0": 0.10}

    bb_window = 20
    bb_std = 2.0
    indicator_window = 20
    vwap_enabled = True

    live_filters_enabled = False
    enable_live_spread_filter = False
    enable_live_orderbook_filter = False
    enable_live_funding_filter = False
    live_max_spread_ratio = 0.0028
    live_min_orderbook_imbalance = 0.05
    live_max_abs_funding_rate = 0.0005
    stake_risk_fraction = 0.005
    min_order_buffer = 1.05
    binance_min_notional = 5.0

    rsi_long_threshold = IntParameter(20, 40, default=30, space="buy", optimize=True)
    rsi_short_threshold = IntParameter(60, 85, default=70, space="buy", optimize=True)
    price_z_threshold = DecimalParameter(1.20, 3.00, default=1.80, decimals=2, space="buy", optimize=True)
    vol_z_min = DecimalParameter(0.50, 4.00, default=2.00, decimals=2, space="buy", optimize=True)
    natr_min = DecimalParameter(0.005, 0.050, default=0.025, decimals=3, space="buy", optimize=True)
    bb_width_min = DecimalParameter(0.010, 0.200, default=0.040, decimals=3, space="buy", optimize=True)
    adx_1h_max = IntParameter(12, 30, default=20, space="buy", optimize=True)
    slope_cap = DecimalParameter(0.0005, 0.0200, default=0.0040, decimals=4, space="buy", optimize=True)

    exit_rsi_long = IntParameter(45, 70, default=52, space="sell", optimize=True)
    exit_rsi_short = IntParameter(30, 55, default=48, space="sell", optimize=True)
    exit_z_long = DecimalParameter(0.00, 1.00, default=0.20, decimals=2, space="sell", optimize=True)
    exit_z_short = DecimalParameter(-1.00, 0.00, default=-0.20, decimals=2, space="sell", optimize=True)
    atr_stop_mult = DecimalParameter(1.00, 2.50, default=1.70, decimals=2, space="sell", optimize=True)
    atr_roi_mult = DecimalParameter(0.50, 3.00, default=1.20, decimals=2, space="sell", optimize=True)
    time_stop_candles = IntParameter(6, 72, default=24, space="sell", optimize=True)
    leverage_tier = CategoricalParameter([1.0, 2.0, 3.0], default=2.0, space="buy", optimize=True)

    @property
    def protections(self) -> list[dict[str, Any]]:
        return [
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 3,
                "stop_duration_candles": 8,
                "required_profit": 0.0,
                "only_per_pair": False,
                "only_per_side": True,
            },
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 48,
                "trade_limit": 2,
                "stop_duration_candles": 12,
                "required_profit": 0.0,
                "only_per_pair": True,
                "only_per_side": True,
            },
        ]

    def informative_pairs(self) -> list[tuple[str, str]]:
        if not self.dp:
            return []
        return [(pair, self.informative_timeframe) for pair in self.dp.current_whitelist()]

    @staticmethod
    def _rolling_zscore(series: Series, window: int) -> Series:
        mean = series.rolling(window=window, min_periods=window).mean()
        std = series.rolling(window=window, min_periods=window).std(ddof=0).replace(0.0, np.nan)
        return (series - mean) / std

    @staticmethod
    def _bollinger(series: Series, window: int, stds: float) -> tuple[Series, Series, Series]:
        mid = series.rolling(window=window, min_periods=window).mean()
        std = series.rolling(window=window, min_periods=window).std(ddof=0)
        upper = mid + stds * std
        lower = mid - stds * std
        return mid, upper, lower

    @staticmethod
    def _safe_div(numerator: Series, denominator: Series) -> Series:
        return numerator / denominator.replace(0.0, np.nan)

    @staticmethod
    def _to_bool(condition: Series) -> Series:
        return condition.fillna(False).astype(bool)

    @staticmethod
    def _coerce_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _session_vwap(self, dataframe: DataFrame) -> Series:
        typical_price = qtpylib.typical_price(dataframe)
        session = dataframe["date"].dt.floor("1D")
        cumulative_tpv = (typical_price * dataframe["volume"]).groupby(session).cumsum()
        cumulative_volume = dataframe["volume"].groupby(session).cumsum().replace(0.0, np.nan)
        return cumulative_tpv / cumulative_volume

    @staticmethod
    def _timeframe_to_minutes(timeframe: str) -> int:
        if timeframe.endswith("m"):
            return int(timeframe[:-1])
        if timeframe.endswith("h"):
            return int(timeframe[:-1]) * 60
        if timeframe.endswith("d"):
            return int(timeframe[:-1]) * 60 * 24
        raise ValueError(f"Unsupported timeframe for minute conversion: {timeframe}")

    def _extract_amount_step(self, market: dict[str, Any]) -> float:
        info = market.get("info") or {}
        filters = info.get("filters") or []
        if isinstance(filters, list):
            for filter_item in filters:
                if not isinstance(filter_item, dict):
                    continue
                if filter_item.get("filterType") in {"LOT_SIZE", "MARKET_LOT_SIZE"}:
                    step_size = self._coerce_float(filter_item.get("stepSize"))
                    if step_size > 0:
                        return step_size

        precision = (market.get("precision") or {}).get("amount")
        if isinstance(precision, int) and precision >= 0:
            return 10 ** (-precision)
        if isinstance(precision, float) and precision > 0:
            return precision
        return 0.0

    def _log_missing_market_metadata(self, pair: str) -> None:
        missing_pairs = getattr(self, "_missing_market_metadata_pairs", set())
        if pair in missing_pairs:
            return
        missing_pairs.add(pair)
        setattr(self, "_missing_market_metadata_pairs", missing_pairs)
        logger.warning(
            "Falling back to conservative Binance futures order guard for %s because market metadata is unavailable.",
            pair,
        )

    @staticmethod
    def _normalize_amount_to_step(amount: float, step: float) -> float:
        normalized_amount = max(amount, 0.0)
        if step <= 0:
            return normalized_amount
        steps = math.floor((normalized_amount / step) + 1e-12)
        return max(0.0, steps * step)

    def _get_market_limits(self, pair: str) -> dict[str, float | bool]:
        if not self.dp or not hasattr(self.dp, "market"):
            return {
                "metadata_available": False,
                "min_qty": 0.0,
                "min_notional": 0.0,
                "contract_size": 1.0,
                "qty_step": 0.0,
            }

        try:
            market = self.dp.market(pair)
        except Exception:
            return {
                "metadata_available": False,
                "min_qty": 0.0,
                "min_notional": 0.0,
                "contract_size": 1.0,
                "qty_step": 0.0,
            }

        if not market:
            return {
                "metadata_available": False,
                "min_qty": 0.0,
                "min_notional": 0.0,
                "contract_size": 1.0,
                "qty_step": 0.0,
            }

        limits = market.get("limits") or {}
        amount_limits = limits.get("amount") or {}
        cost_limits = limits.get("cost") or {}
        return {
            "metadata_available": True,
            "min_qty": self._coerce_float(amount_limits.get("min")),
            "min_notional": self._coerce_float(cost_limits.get("min")),
            "contract_size": max(
                self._coerce_float(market.get("contractSize") or market.get("contract_size"), 1.0),
                1.0,
            ),
            "qty_step": self._extract_amount_step(market),
        }

    def _evaluate_order_size(self, pair: str, amount: float, rate: float) -> dict[str, float | bool]:
        limits = self._get_market_limits(pair)
        if not bool(limits["metadata_available"]):
            self._log_missing_market_metadata(pair)

        rate = max(rate, 0.0)
        contract_size = float(limits["contract_size"])
        qty_step = float(limits["qty_step"])
        effective_amount = self._normalize_amount_to_step(amount, qty_step)
        effective_amount = effective_amount if effective_amount > 0 else max(amount, 0.0)
        min_qty = max(float(limits["min_qty"]), qty_step)
        min_notional = max(float(self.binance_min_notional), float(limits["min_notional"]))
        effective_notional = effective_amount * rate * contract_size

        is_valid = effective_amount > 0
        if min_qty > 0 and effective_amount < min_qty:
            is_valid = False
        if min_notional > 0 and effective_notional < min_notional:
            is_valid = False

        return {
            "is_valid": is_valid,
            "normalized_amount": effective_amount,
            "min_qty": min_qty,
            "min_notional": min_notional,
            "effective_notional": effective_notional,
            "contract_size": contract_size,
        }

    def _apply_min_order_guard(
        self,
        pair: str,
        stake: float,
        current_rate: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
    ) -> float:
        limits = self._get_market_limits(pair)
        if not bool(limits["metadata_available"]):
            self._log_missing_market_metadata(pair)

        effective_leverage = max(leverage, 1.0)
        contract_size = float(limits["contract_size"])
        min_qty = max(float(limits["min_qty"]), float(limits["qty_step"]))
        min_notional = max(float(self.binance_min_notional), float(limits["min_notional"]))
        required_notional = min_notional
        if current_rate > 0 and min_qty > 0:
            required_notional = max(required_notional, min_qty * current_rate * contract_size)

        required_min_stake = float(min_stake) if min_stake is not None else 0.0
        required_min_stake = max(
            required_min_stake,
            (required_notional / effective_leverage) * float(self.min_order_buffer),
        )

        clipped_stake = min(max_stake, max(0.0, stake))
        if current_rate > 0 and contract_size > 0:
            candidate_amount = (clipped_stake * effective_leverage) / (current_rate * contract_size)
            evaluation = self._evaluate_order_size(pair, candidate_amount, current_rate)
            if bool(evaluation["is_valid"]):
                return clipped_stake

        if required_min_stake > max_stake:
            logger.warning(
                "Rejected %s order because required minimum collateral %.4f exceeds max stake %.4f.",
                pair,
                required_min_stake,
                max_stake,
            )
            return 0.0

        return required_min_stake

    def _populate_informative_indicators(self, dataframe: DataFrame) -> DataFrame:
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        bb_mid, bb_upper, bb_lower = self._bollinger(dataframe["close"], self.bb_window, self.bb_std)
        dataframe["bb_mid"] = bb_mid
        dataframe["bb_upper"] = bb_upper
        dataframe["bb_lower"] = bb_lower
        dataframe["ema50_slope"] = self._safe_div(dataframe["ema50"].diff(), dataframe["ema50"].shift(1))
        return dataframe

    def _ensure_informative_columns(self, dataframe: DataFrame) -> DataFrame:
        informative_columns = [
            "open_1h",
            "high_1h",
            "low_1h",
            "close_1h",
            "volume_1h",
            "ema50_1h",
            "ema200_1h",
            "adx_1h",
            "bb_mid_1h",
            "bb_upper_1h",
            "bb_lower_1h",
            "ema50_slope_1h",
        ]
        for column in informative_columns:
            if column not in dataframe.columns:
                dataframe[column] = np.nan
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["natr"] = self._safe_div(dataframe["atr"], dataframe["close"])
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)

        bb_mid, bb_upper, bb_lower = self._bollinger(dataframe["close"], self.bb_window, self.bb_std)
        dataframe["bb_mid"] = bb_mid
        dataframe["bb_upper"] = bb_upper
        dataframe["bb_lower"] = bb_lower
        dataframe["bb_width"] = self._safe_div(bb_upper - bb_lower, bb_mid)

        dataframe["price_z"] = self._rolling_zscore(dataframe["close"], self.indicator_window)
        dataframe["vol_z"] = self._rolling_zscore(dataframe["volume"], self.indicator_window)
        dataframe["vwap"] = self._session_vwap(dataframe) if self.vwap_enabled else np.nan

        informative = None
        if self.dp:
            informative = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=self.informative_timeframe)
        if informative is not None and not informative.empty:
            informative = self._populate_informative_indicators(informative.copy())
            dataframe = merge_informative_pair(
                dataframe,
                informative,
                self.timeframe,
                self.informative_timeframe,
                ffill=True,
            )
        dataframe = self._ensure_informative_columns(dataframe)

        dataframe["active_pair"] = self._to_bool(
            (dataframe["vol_z"] > float(self.vol_z_min.value))
            & (dataframe["natr"] > float(self.natr_min.value))
            & (dataframe["bb_width"] > float(self.bb_width_min.value))
        )

        dataframe["weak_trend_regime"] = self._to_bool(
            (dataframe["adx_1h"] < float(self.adx_1h_max.value))
            & (dataframe["ema50_slope_1h"].abs() < float(self.slope_cap.value))
        )

        strong_trend_threshold = float(self.adx_1h_max.value) + 5.0
        slope_cap = float(self.slope_cap.value)

        dataframe["breakout_block_long"] = self._to_bool(
            (dataframe["adx_1h"] > strong_trend_threshold)
            & (dataframe["ema50_1h"] < dataframe["ema200_1h"])
            & (dataframe["ema50_slope_1h"] < -slope_cap)
            & (dataframe["close_1h"] < dataframe["bb_lower_1h"])
        )

        dataframe["breakout_block_short"] = self._to_bool(
            (dataframe["adx_1h"] > strong_trend_threshold)
            & (dataframe["ema50_1h"] > dataframe["ema200_1h"])
            & (dataframe["ema50_slope_1h"] > slope_cap)
            & (dataframe["close_1h"] > dataframe["bb_upper_1h"])
        )

        dataframe["bullish_reversal"] = self._to_bool(
            (dataframe["close"] > dataframe["open"])
            & (dataframe["close"] > dataframe["close"].shift(1))
        )
        dataframe["bearish_reversal"] = self._to_bool(
            (dataframe["close"] < dataframe["open"])
            & (dataframe["close"] < dataframe["close"].shift(1))
        )

        dataframe["trend_expand_against_long"] = self._to_bool(
            (dataframe["adx_1h"] > strong_trend_threshold)
            & (dataframe["ema50_slope_1h"] < -slope_cap)
        )
        dataframe["trend_expand_against_short"] = self._to_bool(
            (dataframe["adx_1h"] > strong_trend_threshold)
            & (dataframe["ema50_slope_1h"] > slope_cap)
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        long_condition = self._to_bool(
            (dataframe["volume"] > 0)
            & dataframe["active_pair"]
            & dataframe["weak_trend_regime"]
            & ~dataframe["breakout_block_long"]
            & (dataframe["close"] < dataframe["bb_lower"])
            & (dataframe["rsi"] < float(self.rsi_long_threshold.value))
            & (dataframe["price_z"] < -float(self.price_z_threshold.value))
            & dataframe["bullish_reversal"]
        )

        short_condition = self._to_bool(
            (dataframe["volume"] > 0)
            & dataframe["active_pair"]
            & dataframe["weak_trend_regime"]
            & ~dataframe["breakout_block_short"]
            & (dataframe["close"] > dataframe["bb_upper"])
            & (dataframe["rsi"] > float(self.rsi_short_threshold.value))
            & (dataframe["price_z"] > float(self.price_z_threshold.value))
            & dataframe["bearish_reversal"]
        )

        dataframe.loc[long_condition, "enter_long"] = 1
        dataframe.loc[long_condition, "enter_tag"] = "mr_long_extreme"

        dataframe.loc[short_condition, "enter_short"] = 1
        dataframe.loc[short_condition, "enter_tag"] = "mr_short_extreme"

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = ""

        long_mean_hit = self._to_bool(
            (dataframe["close"] >= dataframe["bb_mid"])
            | (dataframe["close"] >= dataframe["ema20"])
            | (dataframe["close"] >= dataframe["vwap"])
            | (dataframe["price_z"] > float(self.exit_z_long.value))
            | (dataframe["rsi"] > float(self.exit_rsi_long.value))
        )
        short_mean_hit = self._to_bool(
            (dataframe["close"] <= dataframe["bb_mid"])
            | (dataframe["close"] <= dataframe["ema20"])
            | (dataframe["close"] <= dataframe["vwap"])
            | (dataframe["price_z"] < float(self.exit_z_short.value))
            | (dataframe["rsi"] < float(self.exit_rsi_short.value))
        )

        long_vol_decay = self._to_bool(~dataframe["active_pair"])
        short_vol_decay = self._to_bool(~dataframe["active_pair"])
        long_trend_expand = self._to_bool(dataframe["trend_expand_against_long"])
        short_trend_expand = self._to_bool(dataframe["trend_expand_against_short"])

        long_exit = self._to_bool(long_mean_hit | long_vol_decay | long_trend_expand)
        short_exit = self._to_bool(short_mean_hit | short_vol_decay | short_trend_expand)

        dataframe.loc[long_exit, "exit_long"] = 1
        dataframe.loc[short_exit, "exit_short"] = 1

        dataframe["long_exit_reason"] = np.select(
            [long_mean_hit, long_trend_expand, long_vol_decay],
            ["mean_hit", "trend_expand", "vol_decay"],
            default="",
        )
        dataframe["short_exit_reason"] = np.select(
            [short_mean_hit, short_trend_expand, short_vol_decay],
            ["mean_hit", "trend_expand", "vol_decay"],
            default="",
        )

        dataframe.loc[long_exit, "exit_tag"] = dataframe.loc[long_exit, "long_exit_reason"]
        dataframe.loc[short_exit, "exit_tag"] = dataframe.loc[short_exit, "short_exit_reason"]
        return dataframe

    def _get_last_candle(self, pair: str) -> Series | None:
        if not self.dp:
            return None
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return None
        return dataframe.iloc[-1]

    def _runmode_allows_live_filters(self) -> bool:
        if not self.dp:
            return False
        runmode = getattr(getattr(self.dp, "runmode", None), "value", None)
        return self.live_filters_enabled and runmode in {"live", "dry_run"}

    def _fetch_live_spread_ratio(self, pair: str) -> float | None:
        if not self.dp:
            return None
        try:
            orderbook = self.dp.orderbook(pair, 5)
        except Exception:
            return None
        if not orderbook:
            return None
        bids = orderbook.get("bids") or []
        asks = orderbook.get("asks") or []
        if not bids or not asks:
            return None
        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        if best_bid <= 0 or best_ask <= 0:
            return None
        mid = (best_bid + best_ask) / 2.0
        return (best_ask - best_bid) / mid if mid > 0 else None

    def _fetch_orderbook_imbalance(self, pair: str) -> float | None:
        if not self.dp:
            return None
        try:
            orderbook = self.dp.orderbook(pair, 5)
        except Exception:
            return None
        if not orderbook:
            return None
        bids = orderbook.get("bids") or []
        asks = orderbook.get("asks") or []
        bid_qty = sum(float(level[1]) for level in bids[:5])
        ask_qty = sum(float(level[1]) for level in asks[:5])
        total = bid_qty + ask_qty
        if total <= 0:
            return None
        return (bid_qty - ask_qty) / total

    def _fetch_live_funding_rate(self, pair: str) -> float | None:
        if not self.dp:
            return None
        try:
            funding = self.dp.funding_rate(pair)
        except Exception:
            return None
        if funding is None:
            return None
        if isinstance(funding, (int, float)):
            return float(funding)
        if isinstance(funding, dict):
            for key in ("fundingRate", "funding_rate", "rate", "value"):
                if key in funding and funding[key] is not None:
                    return float(funding[key])
        return None

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> bool:
        _ = (order_type, amount, rate, time_in_force, current_time, entry_tag)
        if self._runmode_allows_live_filters():
            if self.enable_live_spread_filter:
                spread_ratio = self._fetch_live_spread_ratio(pair)
                if spread_ratio is not None and spread_ratio > self.live_max_spread_ratio:
                    return False

            if self.enable_live_orderbook_filter:
                imbalance = self._fetch_orderbook_imbalance(pair)
                if imbalance is not None:
                    if side == "long" and imbalance < self.live_min_orderbook_imbalance:
                        return False
                    if side == "short" and imbalance > -self.live_min_orderbook_imbalance:
                        return False

            if self.enable_live_funding_filter:
                funding_rate = self._fetch_live_funding_rate(pair)
                if funding_rate is not None and abs(funding_rate) > self.live_max_abs_funding_rate:
                    return False

        if self.dp:
            runmode = getattr(getattr(self.dp, "runmode", None), "value", None)
            if runmode in {"live", "dry_run"}:
                order_check = self._evaluate_order_size(pair, amount, rate)
                if not bool(order_check["is_valid"]):
                    logger.warning(
                        "Rejected %s %s entry because order size is below Binance futures limits "
                        "(amount=%.8f normalized=%.8f min_qty=%.8f notional=%.8f min_notional=%.8f).",
                        pair,
                        side,
                        amount,
                        float(order_check["normalized_amount"]),
                        float(order_check["min_qty"]),
                        float(order_check["effective_notional"]),
                        float(order_check["min_notional"]),
                    )
                    return False

        return True

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        _ = (current_time, current_rate, proposed_leverage, entry_tag, side)
        desired = float(self.leverage_tier.value)
        last_candle = self._get_last_candle(pair)
        spread_ratio = self._fetch_live_spread_ratio(pair) if self._runmode_allows_live_filters() else None

        if last_candle is not None:
            if float(last_candle.get("natr", 0.0) or 0.0) > float(self.natr_min.value) * 1.5:
                desired = 1.0
            if float(last_candle.get("bb_width", 0.0) or 0.0) > float(self.bb_width_min.value) * 2.0:
                desired = 1.0

        if spread_ratio is not None and spread_ratio > self.live_max_spread_ratio:
            desired = 1.0

        return max(1.0, min(float(max_leverage), desired))

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        _ = (current_time, current_rate, entry_tag, side)
        last_candle = self._get_last_candle(pair)
        if last_candle is None:
            return self._apply_min_order_guard(pair, proposed_stake, current_rate, min_stake, max_stake, leverage)

        atr = float(last_candle.get("atr", 0.0) or 0.0)
        close = float(last_candle.get("close", current_rate) or current_rate)
        if atr <= 0 or close <= 0:
            return self._apply_min_order_guard(pair, proposed_stake, current_rate, min_stake, max_stake, leverage)

        stop_ratio = max((atr * float(self.atr_stop_mult.value)) / close, 0.001)
        try:
            total_stake = float(self.wallets.get_total_stake_amount())  # type: ignore[union-attr]
        except Exception:
            total_stake = proposed_stake * 6.0

        risk_budget = total_stake * self.stake_risk_fraction
        denominator = max(stop_ratio * max(leverage, 1.0), 0.001)
        stake = risk_budget / denominator
        return self._apply_min_order_guard(pair, stake, current_rate, min_stake, max_stake, leverage)

    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> float | None:
        _ = (current_time, current_profit, after_fill)
        last_candle = self._get_last_candle(pair)
        if last_candle is None:
            return None

        atr = float(last_candle.get("atr", 0.0) or 0.0)
        if atr <= 0:
            return None

        direction = 1 if trade.is_short else -1
        stop_price = current_rate + direction * atr * float(self.atr_stop_mult.value)
        return stoploss_from_absolute(
            stop_price,
            current_rate=current_rate,
            is_short=trade.is_short,
            leverage=trade.leverage or 1.0,
        )

    def custom_roi(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        trade_duration: int,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float | None:
        _ = (trade, current_time, trade_duration, entry_tag, side)
        last_candle = self._get_last_candle(pair)
        if last_candle is None:
            return None

        atr = float(last_candle.get("atr", 0.0) or 0.0)
        close = float(last_candle.get("close", 0.0) or 0.0)
        if atr <= 0 or close <= 0:
            return None

        atr_ratio = atr / close
        roi = atr_ratio * float(self.atr_roi_mult.value)
        return float(np.clip(roi, 0.008, 0.035))

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> str | None:
        _ = (pair, current_rate, current_profit)
        candle_minutes = self._timeframe_to_minutes(self.timeframe)
        elapsed_minutes = max(int((current_time - trade.open_date_utc).total_seconds() // 60), 0)
        if elapsed_minutes >= int(self.time_stop_candles.value) * candle_minutes:
            return "time_stop"
        return None


class VolatilityRotationMRDiagnostic(VolatilityRotationMR):
    """
    Analysis-only profile to diagnose signal density on historically aligned universes.
    This keeps the same strategy structure and trade lifecycle while relaxing only a few
    gating thresholds that were explicitly approved for diagnostic use.
    """

    vol_z_min = DecimalParameter(0.50, 3.00, default=1.00, decimals=2, space="buy", optimize=True)
    price_z_threshold = DecimalParameter(1.00, 2.50, default=1.50, decimals=2, space="buy", optimize=True)
    bb_width_min = DecimalParameter(0.005, 0.100, default=0.020, decimals=3, space="buy", optimize=True)
    adx_1h_max = IntParameter(16, 32, default=24, space="buy", optimize=True)
    slope_cap = DecimalParameter(0.0010, 0.0200, default=0.0060, decimals=4, space="buy", optimize=True)


class VolatilityRotationMRLongOnly(VolatilityRotationMR):
    """
    Research-only long-only ablation to quantify whether short-side activity adds signal quality.
    """

    can_short = False

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        dataframe["enter_short"] = 0
        return dataframe


class VolatilityRotationMRDiagnosticLongOnly(VolatilityRotationMRDiagnostic):
    """
    Research-only long-only version of the relaxed diagnostic profile.
    """

    can_short = False

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        dataframe["enter_short"] = 0
        return dataframe
