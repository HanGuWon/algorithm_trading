# External Review Response

Source chat: https://chatgpt.com/g/g-p-69a9f92954288191a063fd1eea40b983-gasanghwapye-teureiding/c/6a23ed68-fe48-83aa-9134-275a3978e5f4
Captured: 2026-06-06 Asia/Seoul

---

Independent Audit Review (Document-Based)

Scope limitation: I cannot inspect the actual repository source files (VolatilityRotationMR.py, VolatilityRotationMRCandidates.py, adapter code, or runner code). Therefore:

Document-Based Findings = supported by the information you provided.

Source-Code Findings Requiring Verification = plausible high-risk areas that must be checked in the actual code before conclusions are finalized.

Executive Conclusion

Recommendation: REDESIGN (not promote, not retire).

The project has successfully solved the infrastructure problem (data acquisition and long-window backtesting), but has not demonstrated a statistically credible trading edge.

The current evidence supports continued research into the underlying mean-reversion hypothesis, but does not support continued iteration on the current strategy architecture without simplification and diagnostic analysis.

1. Critical Findings (Ordered by Severity)
Critical Finding #1
Strategy edge is not statistically demonstrated
Evidence

Best result:

Strategy	Trades	Profit
FlushReboundLongOnly	19	+1.60%
DelayedConfirmLongOnly	10	-0.21%

Across approximately:

6+ years

11 major futures pairs

multiple market regimes

the strategy only produced:

19 trades

total return ≈ +1.6%

That is far below what would normally be considered validation-quality evidence.

Why this matters

With only 19 observations:

expectancy estimates are unstable

Sharpe-like metrics are unreliable

a few outliers can dominate results

regime robustness cannot be assessed

The most likely interpretation is:

The strategy is filtering so aggressively that it has become an event detector rather than a trading system.

Critical Finding #2
Signal density is too low to validate the thesis

This is actually a larger issue than profitability.

The strategy currently cannot answer:

Does the setup work?

Does the setup fail?

Which assets work?

Which regimes work?

because there are too few observations.

A strategy producing:

10 trades

19 trades

over six years on 11 major futures pairs is effectively untestable.

The primary bottleneck is not optimization.

The primary bottleneck is information.

Critical Finding #3
Positive result may be entirely explained by a few exceptional events

The reported result strongly suggests:

a handful of flush events generated most profits

most time periods generated nothing

Without:

yearly breakdown

trade distribution

per-pair attribution

you do not know whether:

19 trades contributed evenly

or

2 trades generated all profits

If the latter is true, the strategy is probably not deployable.

Critical Finding #4
Current architecture appears over-constrained

The naming suggests something like:

Volatility
→ Rotation
→ Mean Reversion
→ Flush
→ Rebound
→ Confirmation

Every additional filter:

increases precision

decreases sample size

The observed trade count strongly suggests excessive filtering.

A common quant failure mode is:

"Stacking good ideas until no trades remain."

Current evidence is consistent with that failure mode.

Critical Finding #5
Funding and mark-price effects are not yet the main problem

For this strategy specifically:

Funding-rate omission is not the largest issue.

Reason:

Total trades = 19.

The statistical uncertainty from the tiny sample is vastly larger than funding adjustments.

However:

Before paper trading or production deployment:

funding should be incorporated

realistic fees should be incorporated

slippage should be incorporated

Currently these are second-order issues.

The first-order issue is lack of evidence.

2. High-Risk Source-Code Areas Requiring Verification

These cannot be confirmed without source inspection.

Risk A: Informative timeframe lookahead

You mentioned:

5m execution timeframe

1h informative timeframe

This is generally acceptable.

However, the implementation matters enormously.

Safe pattern:

use Freqtrade informative pair mechanisms

use merge_informative_pair()

only consume closed higher-timeframe values

Freqtrade explicitly documents merge_informative_pair() as the safe merge mechanism intended to avoid lookahead bias. 
Freqtrade
+1

Verify:

Python
실행됨
merge_informative_pair(...)

is used correctly.

Risk B: HTF candle leakage

A subtle but common failure:

Using the current unfinished 1h candle.

Example:

At 13:35

using:

Python
실행됨
close_1h
high_1h
low_1h
range_1h

from the currently forming hour.

This can create hidden lookahead contamination in backtests. Similar concerns have been discussed by Freqtrade users when higher-timeframe values are merged and used before candle completion. 
GitHub
+1

Verify whether any HTF-derived features should be:

Python
실행됨
.shift(1)

after merging.

Risk C: Full-dataframe leakage

Search for:

Python
실행됨
dataframe.max()
dataframe.min()
dataframe.mean()

without rolling windows.

Also inspect for:

Python
실행됨
iloc[-1]

inside indicator generation.

Freqtrade's lookahead documentation specifically warns that backtesting computes the entire dataframe at once, making future-data leakage easy to introduce. 
Freqtrade
+1

Risk D: Rotation ranking leakage

If "Rotation" means:

selecting top volatility assets

selecting strongest mean-reversion candidates

then verify rankings are computed only from information available at that timestamp.

Common mistake:

Python
실행됨
groupby().transform(...)

using future rows.

Risk E: Candidate universe survivorship bias

Current universe:

BTC

ETH

SOL

AVAX

etc.

This is effectively a modern winners list.

The test is not survivorship-free.

This does not invalidate research.

But it means:

Results represent current major winners, not the average futures asset.

Important distinction.

3. Backtest Methodology Assessment
Ten-year request handling

Assessment:

Honest and acceptable.

Requested:

2016–2026

Actual:

2020–2026

because Binance USDT-M data did not exist earlier.

This is not a methodological flaw.

It should simply be documented exactly as you already did.

5m execution + 1h informative

Assessment:

Reasonable design choice.

For a mean-reversion strategy:

5m = execution

1h = context/regime

is entirely defensible.

No issue here.

The implementation is the issue.

Not the design.

Funding-rate omission

Assessment:

Acceptable for current research stage.

Not acceptable for deployment stage.

Priority:

Edge validation

Costs

Funding

4. Promote, Park, or Redesign?
Recommendation: REDESIGN

Not Promote.

Not Retire.

Not Park.

Why?

Because:

infrastructure works

hypothesis is still plausible

current implementation is information-starved

You have enough evidence to reject the current architecture.

You do not yet have enough evidence to reject the underlying thesis.

5. Strongest Reason For Recommendation

The strongest reason is:

The strategy generated only 19 trades across more than six years and 11 major futures markets.

Everything else is secondary.

Until signal count increases substantially:

no confidence intervals

no robustness analysis

no parameter stability analysis

no meaningful out-of-sample assessment

are possible.

6. Prioritized Next-Action Plan
Priority 1
Run Freqtrade lookahead analysis

Mandatory.

Run:

Bash
freqtrade lookahead-analysis \
  --strategy VolatilityRotationMRFlushReboundLongOnly

and all candidate variants.

Do this before any additional optimization. 
Freqtrade
+1

Priority 2
Produce event-study dataset

For every signal:

Export:

timestamp

pair

volatility score

flush magnitude

rebound magnitude

forward returns

for:

+1h

+4h

+12h

+24h

+72h

This is likely the single most informative analysis you can run.

Priority 3
Per-pair attribution

Generate:

Trades
PnL
Win rate
Expectancy
Profit factor

for every asset.

Determine:

edge everywhere

edge only in BTC

edge only in SOL

etc.

Priority 4
Yearly regime decomposition

Split:

2020

2021

2022

2023

2024

2025

2026

Measure performance independently.

You need regime evidence.

Priority 5
Threshold sensitivity

Move all major thresholds:

±10%

±20%

±30%

around current values.

Goal:

Determine whether performance is stable.

If performance collapses immediately:

likely overfit.

Priority 6
Cost stress testing

Run:

current fee

2× fee

3× fee

slippage model

If edge disappears instantly:

reject.

7. Specific Code/Validation Additions
Add Validation Script #1
Signal Event Study

Create:

scripts/event_study_flush_rebound.py

Output:

csv
timestamp
pair
signal_strength
future_1h
future_4h
future_12h
future_24h
future_72h

This should become a permanent validation artifact.

Add Validation Script #2
Parameter Surface Scan

Create:

scripts/parameter_surface_scan.py

Grid-search only:

flush threshold

rebound threshold

Output heatmaps.

Avoid broad hyperopt.

Add Validation Script #3
Trade Concentration Analysis

Measure:

Top 1 trade contribution
Top 3 trade contribution
Top 5 trade contribution

to total profits.

This directly tests whether the edge depends on rare outliers.

Add Validation Script #4
Baseline Comparison Harness

Compare against:

Baseline A

RSI(2) mean reversion

Baseline B

Bollinger Band reversion

Baseline C

Volatility breakout

If your complex strategy cannot outperform simple baselines, complexity is not justified.

Add Validation Script #5
Survivorship Check

Create historical universes by year.

Example:

2020 universe
2021 universe
2022 universe
...

instead of only today's major assets.

Final Assessment

Infrastructure Status: Successful.

Data Pipeline Status: Successful.

Research Status: Active.

Strategy Status: Not validated.

Deployment Readiness: No.

Recommendation: Redesign around a simpler, more measurable mean-reversion core and use event-study diagnostics to determine whether the underlying flush-rebound phenomenon actually contains a durable edge before investing further effort in optimization.
