# Final Decision Memo

## Bottom Line

Full long/short remains parked.

`VolatilityRotationMRDiagnosticLongOnly` earns a `Conditional go` for narrowly scoped follow-up research, not for broad optimization and not for live promotion.

## Decision

### Full long/short

`No-go`

Reason:

- short-side raw signals remain weak
- sample remains too clustered for full optimization
- the broader research path is already good enough to show that the short side is not the continuation candidate

### Long-only diagnostic continuation

`Conditional go`

Allowed scope:

- research-only
- no Binance live or dry-run architecture changes
- no aggressive hyperopt
- focus on robustness diagnosis or simple context-aware filtering only if it stays thesis-consistent

## Evidence

### 1. Long-only matrix

- baseline long-only: `12` trades, `339.778 USDT`
- diagnostic long-only: `38` trades, `768.682 USDT`
- only one non-overlapping window reaches the repo's usable sample threshold:
  - `2024-01-01 -> 2024-07-01` diagnostic long-only with `27` trades and `733.229 USDT`

Interpretation:

- long-only is better than full long/short as a continuation candidate
- the edge is still not broad across time

### 2. Concentration risk

Pair concentration:

- diagnostic long-only top-1 pair share: `7.7%`
- top-3 pair share: `21.8%`
- top-5 pair share: `31.8%`
- remove-top-5 still leaves `524.535 USDT`

Window and month concentration:

- leave-one-anchor-out on `2024-01-01` drops diagnostic long-only to `35.453 USDT` on `11` trades
- leave-one-month-out on `2024-01` drops diagnostic long-only to `46.275 USDT` on `15` trades

Answer:

- Does long-only survive concentration tests?
  - `Yes` on pair concentration
  - `No` on time and regime concentration

### 3. Regime context

- baseline long-only signals land entirely in `flush_high` / `oversold_high`
- diagnostic long-only signals also land entirely in `flush_high` / `oversold_high`
- diagnostic long-only is strongest in `btc_neutral` and `btc_downtrend`
- the lone `btc_uptrend` trade lost money

Answer:

- Is the edge broad enough across windows and contexts?
  - `No`
- What environment does it belong to?
  - mostly a flush / oversold rebound regime

### 4. Signal quality

- baseline raw long signals: `12`
- diagnostic raw long signals: `38`
- baseline good near-misses: `30`
- diagnostic good near-misses: `83`
- dominant blocker on good near-misses: `bullish_reversal`

Interpretation:

- the candidate is not purely opportunity-starved
- there are many structurally valid long setups that miss entry because the last confirmation gate is strict
- that does not fix the broader time/regime concentration problem by itself

### 5. Cost stress

- diagnostic long-only baseline: `768.682 USDT`
- moderately worse fee: `753.633 USDT`
- worse fee plus slippage: `716.009 USDT`

Answer:

- Does long-only remain positive after cost stress?
  - `Yes`

## Final Answers

- Does long-only survive concentration tests?
  - `Partially`. It survives pair concentration but fails the stricter time/regime concentration test.
- Does long-only remain positive after cost stress?
  - `Yes`.
- Is the edge broad enough across windows and contexts?
  - `No`.
- Is continued research justified?
  - `Yes, conditionally`.

## Recommendation

Continue only with limited long-only diagnostic research around `VolatilityRotationMRDiagnosticLongOnly`.

Do not reopen full long/short optimization.
Do not treat the current long-only evidence as broad enough for live candidacy.
If the next pass cannot reduce the visible dependence on the `2024-01` flush-rebound cluster, park long-only as well.
