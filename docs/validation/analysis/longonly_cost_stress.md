# Long-Only Cost Stress

> Research-only cost sensitivity. Baseline uses the exported Freqtrade trade fees. Stress cases increase per-side fee and then add modest per-side slippage.

| strategy_variant     | scenario                |   trade_count |   profit_usdt |   avg_profit_per_trade_usdt | positive_after_stress   | target_fee_per_side   |   slippage_per_side |
|:---------------------|:------------------------|--------------:|--------------:|----------------------------:|:------------------------|:----------------------|--------------------:|
| baseline_long_only   | baseline_exported_fees  |            12 |       339.778 |                      28.315 | yes                     | exported              |              0      |
| baseline_long_only   | moderately_worse_fee    |            12 |       335.234 |                      27.936 | yes                     | 0.0007                |              0      |
| baseline_long_only   | worse_fee_plus_slippage |            12 |       323.874 |                      26.99  | yes                     | 0.0007                |              0.0005 |
| diagnostic_long_only | baseline_exported_fees  |            38 |       768.682 |                      20.228 | yes                     | exported              |              0      |
| diagnostic_long_only | moderately_worse_fee    |            38 |       753.633 |                      19.832 | yes                     | 0.0007                |              0      |
| diagnostic_long_only | worse_fee_plus_slippage |            38 |       716.009 |                      18.842 | yes                     | 0.0007                |              0.0005 |

Assumptions:

- `baseline_exported_fees`: exported backtest fees (`fee_open`, `fee_close`).
- `moderately_worse_fee`: raises both sides to `7 bps` if the exported fee is lower.
- `worse_fee_plus_slippage`: same fee stress plus `5 bps` slippage per side.
