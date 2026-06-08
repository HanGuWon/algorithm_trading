# Major 11 Immediate Flush Canonical Manifest

> Research-only manifest for the next Freqtrade backtest layer. This is not a dry-run or live-trading approval.

## Scope

- Source: `docs/validation/analysis/major_11_flush_fixed_candidate_set.csv`
- Canonical signal sets: `7`
- Canonical rows with aliases: `3`
- Active optional gates: `{'use_weak_trend': 0, 'use_breakout_block': 0, 'require_close_below_bb': 0}`

## Canonical Entries

| canonical_fixed_candidate_id | alias_fixed_candidate_ids | source_candidate_ids | price_z_threshold | rsi_threshold | vol_z_min | bb_width_min | signals | independent_clusters_72h | active_pairs | active_years | cluster_excess_72h_median | validation_excess_72h_median | net_excess_72h_median_20bps | diagnostic_decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RFC008_original | RFC008_original | RFC008 | 3.1000 | 26 | 1.5000 | 0.0400 | 1334 | 871 | 11 | 7 | 0.0156 | 0.0196 | 0.0136 | FIXED_RESEARCH_CANDIDATE |
| RFC001_original | RFC001_original | RFC001 | 3.1000 | 26 | 1.0000 | 0.0400 | 1361 | 881 | 11 | 7 | 0.0153 | 0.0193 | 0.0133 | FIXED_RESEARCH_CANDIDATE |
| RFC019_original | RFC019_original | RFC019 | 3.1000 | 26 | 0.0000 | 0.0400 | 1371 | 884 | 11 | 7 | 0.0153 | 0.0193 | 0.0133 | FIXED_RESEARCH_CANDIDATE |
| RFC002_original | RFC002_original,RFC020_drop_breakout_block | RFC002,RFC020 | 3.1000 | 18 | 1.0000 | 0.0400 | 844 | 643 | 11 | 7 | 0.0152 | 0.0196 | 0.0132 | FIXED_RESEARCH_CANDIDATE |
| RFC025_original | RFC025_original | RFC025 | 3.1000 | 26 | 0.5000 | 0.0400 | 1369 | 883 | 11 | 7 | 0.0152 | 0.0193 | 0.0132 | FIXED_RESEARCH_CANDIDATE |
| RFC009_original | RFC009_original,RFC026_drop_breakout_block | RFC009,RFC026 | 3.1000 | 18 | 1.5000 | 0.0400 | 832 | 636 | 11 | 7 | 0.0149 | 0.0194 | 0.0129 | FIXED_RESEARCH_CANDIDATE |
| RFC015_original | RFC015_original,RFC031_drop_breakout_block | RFC015,RFC031 | 3.1000 | 18 | 0.0000 | 0.0400 | 848 | 645 | 11 | 7 | 0.0145 | 0.0196 | 0.0125 | FIXED_RESEARCH_CANDIDATE |

## Interpretation

- Duplicate fixed-candidate labels are represented as aliases on one canonical row.
- The current canonical set is an immediate extreme-flush research set; optional trend, breakout, and lower-band gates should remain disabled unless this manifest changes.
- A downstream portfolio backtest should iterate these canonical rows, not every row in the fixed-candidate CSV.
