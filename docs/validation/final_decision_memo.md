# Final Decision Memo

## Bottom Line

Full long/short remains parked.

`VolatilityRotationMRDiagnosticLongOnly` was the only follow-up candidate advanced beyond the broader PTI validation path.
After the frozen-candidate promotion study, it also ends at `No-go / Park`.

## Decision

### Full long/short

`No-go / Park`

Reason:

- short-side raw signals remain weak
- the broader PTI path already showed that full long/short does not have enough distributed sample
- nothing in the long-only follow-up changes the full-strategy verdict

### Frozen long-only candidate

`No-go / Park`

Candidate:

- `VolatilityRotationMRDiagnosticLongOnly`

Reason:

- the candidate-selection package was positive, but almost all usable evidence still sits inside the `2024-01-01 -> 2024-07-01` burst
- forward promotion holdouts `2024-07-01 -> 2025-01-01` and `2025-01-01 -> 2025-07-01` both produced `0` trades
- the 12m forward view `2024-07-01 -> 2025-07-01` also produced `0` trades
- mild parameter perturbations were locally stable inside the profitable burst, so the issue is not a tiny threshold cliff
- the issue is that the edge does not promote out of sample

## Evidence

### 1. Candidate-selection evidence

- baseline long-only: `12` trades, `339.778 USDT`
- diagnostic long-only: `38` trades, `768.682 USDT`
- only one non-overlapping window reached a usable sample on its own:
  - `2024-01-01 -> 2024-07-01` diagnostic long-only with `27` trades and `733.229 USDT`

Interpretation:

- long-only was the only continuation candidate worth freezing
- that did not mean it was promotable

### 2. Promotion evidence

Frozen-candidate holdouts:

- `2024-07-01 -> 2025-01-01`: `0` trades, `0.000 USDT`, `0.00%` drawdown
- `2025-01-01 -> 2025-07-01`: `0` trades, `0.000 USDT`, `0.00%` drawdown
- `2024-07-01 -> 2025-07-01` 12m forward view: `0` trades, `0.000 USDT`, `0.00%` drawdown

Answer:

- Is the holdout evidence good enough to justify more work?
  - `No`

### 3. Concentration and time-window stress

Pair concentration:

- diagnostic long-only top-1 pair share: `7.7%`
- top-5 pair share: `31.8%`
- remove-top-5 still leaves `524.535 USDT`

Time concentration:

- remove best month `2024-01`: `15` trades, `46.275 USDT`
- remove best 2 months: `13` trades, `-18.521 USDT`
- remove best anchor `2024-01-01 -> 2024-07-01`: `11` trades, `35.453 USDT`
- promotion holdouts only: `0` trades, `0.000 USDT`

Answer:

- Is the candidate only positive because of one dominant burst or window?
  - `Mostly yes`

### 4. Parameter stability

Frozen defaults:

- `vol_z_min = 1.00`
- `price_z_threshold = 1.50`
- `bb_width_min = 0.020`
- `adx_1h_max = 24`
- `slope_cap = 0.0060`

Observed local stability on `2024-01-01 -> 2024-07-01`:

- baseline: `27` trades, `733.229 USDT`
- `vol_z_min` down/up: `28` / `27` trades, `720.114` / `706.940 USDT`
- `adx_1h_max` down/up: `22` / `30` trades, `639.025` / `821.400 USDT`
- the other mild perturbations were effectively unchanged in this burst window

Answer:

- Is the edge stable enough under mild parameter perturbation?
  - `Locally yes inside the profitable burst`
- Does that save the candidate?
  - `No`, because forward promotion still shows zero sample

### 5. Regime context and subclass decision

- baseline long-only signals land entirely in `flush_high` / `oversold_high`
- diagnostic long-only signals also land entirely in `flush_high` / `oversold_high`
- no `VolatilityRotationMRDiagnosticLongOnlyContext` subclass was added

Reason:

- the observed context mostly relabels the same flush / oversold rebound exposure
- there is no forward holdout evidence that a simple extra context gate materially improves robustness or distribution

## Final Answers

- Is `VolatilityRotationMRDiagnosticLongOnly` robust enough to continue as a research candidate?
  - `No`
- Is it only positive because of one dominant burst or window?
  - `Mostly yes`
- Is the edge stable enough under mild parameter perturbation?
  - `Locally yes`, but only inside the dominant burst
- Is the holdout evidence good enough to justify more work?
  - `No`

## Recommendation

Keep the broader PTI validation path published and reproducible.
Keep the long-only package published as diagnostic research history.

Do not reopen full long/short optimization.
Do not promote `VolatilityRotationMRDiagnosticLongOnly` further on current evidence.
Do not change Binance dry-run/live safety settings.

If future work happens at all, it should start only after materially new data or a clearly distinct context design changes the forward distribution story.
