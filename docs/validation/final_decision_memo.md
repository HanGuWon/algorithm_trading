# Final Decision Memo

## Bottom Line

The broader, historically aligned research pass improved sample density enough to answer the main
question cleanly:

- the zero-trade issue was solved
- the thesis is still not strong enough to justify full long/short optimization

## What Improved

- Candidate universe expanded from a manually curated `25`-pair set to a reproducible `90`-pair
  Binance USDT-M research list.
- Quarterly PTI snapshots from `2022-01-01` through `2025-01-01` now retain up to `50` pairs with a
  top-50 union of `85`.
- The primary matrix now uses non-overlapping `6m` windows, so the `2024-01` burst is no longer
  counted twice.

## What The Data Says

- Baseline de-overlapped matrix: `15` trades, `376.381 USDT`
- Diagnostic de-overlapped matrix: `45` trades, `908.870 USDT`
- Only one window is sample-usable on its own:
  - `2024-01-01 -> 2024-07-01` diagnostic with `27` trades

Side ablation:

- baseline long-only keeps `12 / 15` trades and `339.778 / 376.381 USDT`
- diagnostic long-only keeps `38 / 45` trades and `768.682 / 908.870 USDT`

Event study:

- long signals stay positive through `12`, `24`, and `48` candles
- diagnostic short signals turn negative by `12`, `24`, and `48` candles
- short-side mean-hit probability stays effectively zero

## Decision

### Full long/short optimization

`No-go`

Reason:

- the sample is broader than before, but still not well distributed across windows
- the short side is too sparse and too weak at the raw-signal level
- aggressive hyperopt would overfit a small number of bursts

### Long-only research continuation

`Conditional yes`

Reason:

- the long side is the only part of the thesis with repeated, positive forward behavior
- long-only keeps most of the realized edge while removing the weakest signal family

Scope if research continues:

- keep it research-only
- do not change Binance live safety plumbing
- do not promote to live optimization until a larger, less clustered sample is collected

## Recommendation

Treat `VolatilityRotationMRDiagnosticLongOnly` as the only viable follow-up research candidate.
Do not optimize the full long/short strategy further at this stage.
