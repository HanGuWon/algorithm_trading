# Major 11 Flush Candidate Simplification Recommendations

Research-only decision summary derived from the frozen baseline candidate summary and fixed flush/rebound component diagnostics.

## Scope

- Candidate summary: `docs/validation/analysis/major_11_flush_baseline_candidate_summary.csv`
- Component diagnostics: `docs/validation/analysis/major_11_flush_rebound_component_diagnostics.csv`
- Default scope: candidates with `SURVIVES_BASELINES_STRONG` or `SURVIVES_BASELINES_WEAK` only.
- This report does not create or promote a live strategy.

## Recommendation Counts

| recommended_next_step           |   candidates |
|:--------------------------------|-------------:|
| KEEP_ORIGINAL_IMMEDIATE_FLUSH   |            7 |
| REJECT_COMPONENT_FAILURE        |            4 |
| TEST_SIMPLIFIED_IMMEDIATE_FLUSH |            3 |

## Simplification Counts

| recommended_simplification   |   candidates |
|:-----------------------------|-------------:|
| NONE                         |           11 |
| DROP_BREAKOUT_BLOCK          |            3 |

## Ranked Recommendations

| candidate_id   | candidate_baseline_decision   | recommended_next_step           | recommended_simplification   |   baseline_beater_ci_count |   immediate_clusters_72h |   immediate_cluster_excess_72h_median |   immediate_cluster_excess_72h_median_ci_low |   immediate_validation_excess_72h_median | no_breakout_block_decision   | price_z_rsi_only_decision   | rebound_1c_confirmation_decision   | rebound_3c_confirmation_decision   |
|:---------------|:------------------------------|:--------------------------------|:-----------------------------|---------------------------:|-------------------------:|--------------------------------------:|---------------------------------------------:|-----------------------------------------:|:-----------------------------|:----------------------------|:-----------------------------------|:-----------------------------------|
| RFC020         | SURVIVES_BASELINES_STRONG     | TEST_SIMPLIFIED_IMMEDIATE_FLUSH | DROP_BREAKOUT_BLOCK          |                          6 |                      637 |                                0.0135 |                                       0.0083 |                                   0.0157 | SIMPLIFY_FILTERS             | DROP_COMPONENT              | INSUFFICIENT_COMPONENT_SAMPLE      | DROP_COMPONENT                     |
| RFC026         | SURVIVES_BASELINES_STRONG     | TEST_SIMPLIFIED_IMMEDIATE_FLUSH | DROP_BREAKOUT_BLOCK          |                          6 |                      631 |                                0.0135 |                                       0.0081 |                                   0.0149 | SIMPLIFY_FILTERS             | DROP_COMPONENT              | INSUFFICIENT_COMPONENT_SAMPLE      | DROP_COMPONENT                     |
| RFC031         | SURVIVES_BASELINES_STRONG     | TEST_SIMPLIFIED_IMMEDIATE_FLUSH | DROP_BREAKOUT_BLOCK          |                          6 |                      639 |                                0.0133 |                                       0.0081 |                                   0.0157 | SIMPLIFY_FILTERS             | DROP_COMPONENT              | INSUFFICIENT_COMPONENT_SAMPLE      | DROP_COMPONENT                     |
| RFC008         | SURVIVES_BASELINES_STRONG     | KEEP_ORIGINAL_IMMEDIATE_FLUSH   | NONE                         |                          6 |                      871 |                                0.0143 |                                       0.0099 |                                   0.0172 | KEEP_IMMEDIATE_FLUSH         | DROP_COMPONENT              | DROP_COMPONENT                     | DROP_COMPONENT                     |
| RFC019         | SURVIVES_BASELINES_STRONG     | KEEP_ORIGINAL_IMMEDIATE_FLUSH   | NONE                         |                          6 |                      884 |                                0.0135 |                                       0.0089 |                                   0.0165 | KEEP_IMMEDIATE_FLUSH         | DROP_COMPONENT              | DROP_COMPONENT                     | DROP_COMPONENT                     |
| RFC009         | SURVIVES_BASELINES_STRONG     | KEEP_ORIGINAL_IMMEDIATE_FLUSH   | NONE                         |                          6 |                      636 |                                0.0143 |                                       0.0088 |                                   0.0164 | KEEP_IMMEDIATE_FLUSH         | DROP_COMPONENT              | INSUFFICIENT_COMPONENT_SAMPLE      | DROP_COMPONENT                     |
| RFC001         | SURVIVES_BASELINES_STRONG     | KEEP_ORIGINAL_IMMEDIATE_FLUSH   | NONE                         |                          6 |                      881 |                                0.0135 |                                       0.0086 |                                   0.0165 | KEEP_IMMEDIATE_FLUSH         | DROP_COMPONENT              | DROP_COMPONENT                     | DROP_COMPONENT                     |
| RFC025         | SURVIVES_BASELINES_STRONG     | KEEP_ORIGINAL_IMMEDIATE_FLUSH   | NONE                         |                          6 |                      883 |                                0.0135 |                                       0.0086 |                                   0.0165 | KEEP_IMMEDIATE_FLUSH         | DROP_COMPONENT              | DROP_COMPONENT                     | DROP_COMPONENT                     |
| RFC002         | SURVIVES_BASELINES_STRONG     | KEEP_ORIGINAL_IMMEDIATE_FLUSH   | NONE                         |                          6 |                      643 |                                0.0143 |                                       0.0086 |                                   0.0165 | KEEP_IMMEDIATE_FLUSH         | DROP_COMPONENT              | INSUFFICIENT_COMPONENT_SAMPLE      | DROP_COMPONENT                     |
| RFC015         | SURVIVES_BASELINES_STRONG     | KEEP_ORIGINAL_IMMEDIATE_FLUSH   | NONE                         |                          6 |                      645 |                                0.0135 |                                       0.0086 |                                   0.0165 | KEEP_IMMEDIATE_FLUSH         | DROP_COMPONENT              | INSUFFICIENT_COMPONENT_SAMPLE      | DROP_COMPONENT                     |
| RFC010         | SURVIVES_BASELINES_WEAK       | REJECT_COMPONENT_FAILURE        | NONE                         |                          0 |                     1731 |                                0.0028 |                                      -0.0010 |                                   0.0080 | DROP_COMPONENT               | DROP_COMPONENT              | DROP_COMPONENT                     | DROP_COMPONENT                     |
| RFC004         | SURVIVES_BASELINES_WEAK       | REJECT_COMPONENT_FAILURE        | NONE                         |                          0 |                     1719 |                                0.0030 |                                      -0.0014 |                                   0.0077 | DROP_COMPONENT               | DROP_COMPONENT              | DROP_COMPONENT                     | DROP_COMPONENT                     |
| RFC032         | SURVIVES_BASELINES_WEAK       | REJECT_COMPONENT_FAILURE        | NONE                         |                          0 |                      955 |                                0.0021 |                                      -0.0018 |                                   0.0017 | DROP_COMPONENT               | DROP_COMPONENT              | DROP_COMPONENT                     | DROP_COMPONENT                     |
| RFC028         | SURVIVES_BASELINES_WEAK       | REJECT_COMPONENT_FAILURE        | NONE                         |                          0 |                      955 |                                0.0021 |                                      -0.0020 |                                   0.0017 | DROP_COMPONENT               | DROP_COMPONENT              | DROP_COMPONENT                     | DROP_COMPONENT                     |

## Interpretation

- `TEST_SIMPLIFIED_IMMEDIATE_FLUSH` means a fixed filter ablation preserved the immediate-flush edge and should be considered for the next diagnostic-only candidate definition.
- `KEEP_ORIGINAL_IMMEDIATE_FLUSH` means the immediate flush survived, while tested simplifications or rebound confirmations did not add enough value.
- `RETEST_REBOUND_CONFIRMATION` is reserved for candidates where a rebound-confirmation variant survived the component gate.
- `DO_NOT_ADVANCE_BASELINE_GATE` keeps non-survivors out of the next research step.
