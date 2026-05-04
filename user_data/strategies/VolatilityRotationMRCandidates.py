from __future__ import annotations

from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter

from VolatilityRotationMR import VolatilityRotationMRDiagnosticLongOnly


class VolatilityRotationMRFlushReboundLongOnly(VolatilityRotationMRDiagnosticLongOnly):
    """
    Research-only long candidate built from the profitable good-near-miss cohort.
    It keeps the severe oversold flush, active-pair, and weak-trend gates, but does
    not require the same candle to close as a bullish reversal.
    """

    live_filters_enabled = True
    enable_live_spread_filter = True
    enable_live_orderbook_filter = True
    enable_live_funding_filter = True

    rsi_long_threshold = IntParameter(8, 28, default=18, space="buy", optimize=True)
    price_z_threshold = DecimalParameter(2.00, 4.00, default=2.80, decimals=2, space="buy", optimize=True)
    vol_z_min = DecimalParameter(0.50, 3.00, default=1.00, decimals=2, space="buy", optimize=True)
    bb_width_min = DecimalParameter(0.005, 0.100, default=0.020, decimals=3, space="buy", optimize=True)
    adx_1h_max = IntParameter(16, 32, default=24, space="buy", optimize=True)
    slope_cap = DecimalParameter(0.0010, 0.0200, default=0.0060, decimals=4, space="buy", optimize=True)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        _ = metadata
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
        )

        dataframe.loc[long_condition, "enter_long"] = 1
        dataframe.loc[long_condition, "enter_tag"] = "flush_rebound_long"
        return dataframe


class VolatilityRotationMRDelayedConfirmLongOnly(VolatilityRotationMRDiagnosticLongOnly):
    """
    Research-only long candidate that enters after a previous-candle oversold flush
    and a next-candle reclaim confirmation.
    """

    live_filters_enabled = True
    enable_live_spread_filter = True
    enable_live_orderbook_filter = True
    enable_live_funding_filter = True

    rsi_long_threshold = IntParameter(10, 32, default=20, space="buy", optimize=True)
    price_z_threshold = DecimalParameter(1.80, 3.80, default=2.50, decimals=2, space="buy", optimize=True)
    vol_z_min = DecimalParameter(0.50, 3.00, default=1.00, decimals=2, space="buy", optimize=True)
    bb_width_min = DecimalParameter(0.005, 0.100, default=0.020, decimals=3, space="buy", optimize=True)
    adx_1h_max = IntParameter(16, 32, default=24, space="buy", optimize=True)
    slope_cap = DecimalParameter(0.0010, 0.0200, default=0.0060, decimals=4, space="buy", optimize=True)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        _ = metadata
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        previous_flush = self._to_bool(
            (dataframe["volume"].shift(1) > 0)
            & dataframe["active_pair"].shift(1).fillna(False).astype(bool)
            & dataframe["weak_trend_regime"].shift(1).fillna(False).astype(bool)
            & ~dataframe["breakout_block_long"].shift(1).fillna(False).astype(bool)
            & (dataframe["close"].shift(1) < dataframe["bb_lower"].shift(1))
            & (dataframe["rsi"].shift(1) < float(self.rsi_long_threshold.value))
            & (dataframe["price_z"].shift(1) < -float(self.price_z_threshold.value))
        )
        reclaim_confirmation = self._to_bool(
            (dataframe["volume"] > 0)
            & (dataframe["close"] > dataframe["open"])
            & (dataframe["close"] > dataframe["close"].shift(1))
            & (dataframe["close"] > dataframe["bb_lower"])
            & (dataframe["close"] < dataframe["bb_mid"])
            & (dataframe["rsi"] > dataframe["rsi"].shift(1))
            & (dataframe["price_z"] > dataframe["price_z"].shift(1))
        )

        long_condition = self._to_bool(previous_flush & reclaim_confirmation)
        dataframe.loc[long_condition, "enter_long"] = 1
        dataframe.loc[long_condition, "enter_tag"] = "delayed_confirm_long"
        return dataframe
