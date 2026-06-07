# Major 11 Flush Fixed Candidate Set

> Research-only fixed-scope follow-up. This does not broaden the threshold search, revive rebound confirmation, or promote any strategy to dry-run/live use.

## Scope

- Recommendations: `docs/validation/analysis/major_11_flush_candidate_simplification_recommendations.csv`
- Selected fixed candidates: `10`
- Start: `2020-01-09`
- End: `2026-06-03` exclusive for signal timestamps
- Entry price mode: `next_open`
- Cluster horizon: `72h`
- Validation split start: `2024-01-01`
- Matched-null samples per event: `100`
- Cost stress bps: `0.0, 10.0, 20.0, 40.0`

## Fixed Candidate Definitions

| fixed_candidate_id         | source_candidate_id   | fixed_action                    | recommended_simplification   |   price_z_threshold |   rsi_threshold |   vol_z_min |   bb_width_min | use_weak_trend   | use_breakout_block   | require_close_below_bb   |
|:---------------------------|:----------------------|:--------------------------------|:-----------------------------|--------------------:|----------------:|------------:|---------------:|:-----------------|:---------------------|:-------------------------|
| RFC020_drop_breakout_block | RFC020                | TEST_SIMPLIFIED_IMMEDIATE_FLUSH | DROP_BREAKOUT_BLOCK          |              3.1000 |              18 |      1.0000 |         0.0400 | False            | False                | False                    |
| RFC026_drop_breakout_block | RFC026                | TEST_SIMPLIFIED_IMMEDIATE_FLUSH | DROP_BREAKOUT_BLOCK          |              3.1000 |              18 |      1.5000 |         0.0400 | False            | False                | False                    |
| RFC031_drop_breakout_block | RFC031                | TEST_SIMPLIFIED_IMMEDIATE_FLUSH | DROP_BREAKOUT_BLOCK          |              3.1000 |              18 |      0.0000 |         0.0400 | False            | False                | False                    |
| RFC008_original            | RFC008                | KEEP_ORIGINAL_IMMEDIATE_FLUSH   | NONE                         |              3.1000 |              26 |      1.5000 |         0.0400 | False            | False                | False                    |
| RFC019_original            | RFC019                | KEEP_ORIGINAL_IMMEDIATE_FLUSH   | NONE                         |              3.1000 |              26 |      0.0000 |         0.0400 | False            | False                | False                    |
| RFC009_original            | RFC009                | KEEP_ORIGINAL_IMMEDIATE_FLUSH   | NONE                         |              3.1000 |              18 |      1.5000 |         0.0400 | False            | False                | False                    |
| RFC001_original            | RFC001                | KEEP_ORIGINAL_IMMEDIATE_FLUSH   | NONE                         |              3.1000 |              26 |      1.0000 |         0.0400 | False            | False                | False                    |
| RFC025_original            | RFC025                | KEEP_ORIGINAL_IMMEDIATE_FLUSH   | NONE                         |              3.1000 |              26 |      0.5000 |         0.0400 | False            | False                | False                    |
| RFC002_original            | RFC002                | KEEP_ORIGINAL_IMMEDIATE_FLUSH   | NONE                         |              3.1000 |              18 |      1.0000 |         0.0400 | False            | False                | False                    |
| RFC015_original            | RFC015                | KEEP_ORIGINAL_IMMEDIATE_FLUSH   | NONE                         |              3.1000 |              18 |      0.0000 |         0.0400 | False            | False                | False                    |

## Diagnostic Decision Counts

| diagnostic_decision      |   candidates |
|:-------------------------|-------------:|
| FIXED_RESEARCH_CANDIDATE |           10 |

## Summary

| fixed_candidate_id         | source_candidate_id   | fixed_action                    |   signals |   independent_clusters_72h |   cluster_excess_72h_median |   cluster_excess_72h_median_ci_low |   validation_excess_72h_median |   validation_excess_72h_median_ci_low |   net_excess_72h_median_20bps |   top_pair_cluster_share |   top_year_cluster_share |   positive_pairs_72h |   positive_years_72h | diagnostic_decision      |
|:---------------------------|:----------------------|:--------------------------------|----------:|---------------------------:|----------------------------:|-----------------------------------:|-------------------------------:|--------------------------------------:|------------------------------:|-------------------------:|-------------------------:|---------------------:|---------------------:|:-------------------------|
| RFC008_original            | RFC008                | KEEP_ORIGINAL_IMMEDIATE_FLUSH   |      1334 |                        871 |                      0.0156 |                             0.0072 |                         0.0196 |                                0.0076 |                        0.0136 |                   0.1148 |                   0.2503 |                   11 |                    6 | FIXED_RESEARCH_CANDIDATE |
| RFC001_original            | RFC001                | KEEP_ORIGINAL_IMMEDIATE_FLUSH   |      1361 |                        881 |                      0.0153 |                             0.0073 |                         0.0193 |                                0.0073 |                        0.0133 |                   0.1146 |                   0.2474 |                   11 |                    6 | FIXED_RESEARCH_CANDIDATE |
| RFC019_original            | RFC019                | KEEP_ORIGINAL_IMMEDIATE_FLUSH   |      1371 |                        884 |                      0.0153 |                             0.0073 |                         0.0193 |                                0.0079 |                        0.0133 |                   0.1154 |                   0.2477 |                   11 |                    6 | FIXED_RESEARCH_CANDIDATE |
| RFC020_drop_breakout_block | RFC020                | TEST_SIMPLIFIED_IMMEDIATE_FLUSH |       844 |                        643 |                      0.0152 |                             0.0073 |                         0.0196 |                                0.0073 |                        0.0132 |                   0.1213 |                   0.2208 |                    9 |                    7 | FIXED_RESEARCH_CANDIDATE |
| RFC025_original            | RFC025                | KEEP_ORIGINAL_IMMEDIATE_FLUSH   |      1369 |                        883 |                      0.0152 |                             0.0072 |                         0.0193 |                                0.0073 |                        0.0132 |                   0.1144 |                   0.2469 |                   11 |                    6 | FIXED_RESEARCH_CANDIDATE |
| RFC002_original            | RFC002                | KEEP_ORIGINAL_IMMEDIATE_FLUSH   |       844 |                        643 |                      0.0152 |                             0.0073 |                         0.0196 |                                0.0073 |                        0.0132 |                   0.1213 |                   0.2208 |                    9 |                    7 | FIXED_RESEARCH_CANDIDATE |
| RFC026_drop_breakout_block | RFC026                | TEST_SIMPLIFIED_IMMEDIATE_FLUSH |       832 |                        636 |                      0.0149 |                             0.0073 |                         0.0194 |                                0.0071 |                        0.0129 |                   0.1226 |                   0.2217 |                    9 |                    7 | FIXED_RESEARCH_CANDIDATE |
| RFC009_original            | RFC009                | KEEP_ORIGINAL_IMMEDIATE_FLUSH   |       832 |                        636 |                      0.0149 |                             0.0078 |                         0.0194 |                                0.0071 |                        0.0129 |                   0.1226 |                   0.2217 |                    9 |                    7 | FIXED_RESEARCH_CANDIDATE |
| RFC031_drop_breakout_block | RFC031                | TEST_SIMPLIFIED_IMMEDIATE_FLUSH |       848 |                        645 |                      0.0145 |                             0.0073 |                         0.0196 |                                0.0073 |                        0.0125 |                   0.1209 |                   0.2202 |                    9 |                    7 | FIXED_RESEARCH_CANDIDATE |
| RFC015_original            | RFC015                | KEEP_ORIGINAL_IMMEDIATE_FLUSH   |       848 |                        645 |                      0.0145 |                             0.0073 |                         0.0196 |                                0.0073 |                        0.0125 |                   0.1209 |                   0.2202 |                    9 |                    7 | FIXED_RESEARCH_CANDIDATE |

## Cost Stress

| fixed_candidate_id         |    0.0 |   10.0 |   20.0 |   40.0 |
|:---------------------------|-------:|-------:|-------:|-------:|
| RFC001_original            | 0.0153 | 0.0143 | 0.0133 | 0.0113 |
| RFC002_original            | 0.0152 | 0.0142 | 0.0132 | 0.0112 |
| RFC008_original            | 0.0156 | 0.0146 | 0.0136 | 0.0116 |
| RFC009_original            | 0.0149 | 0.0139 | 0.0129 | 0.0109 |
| RFC015_original            | 0.0145 | 0.0135 | 0.0125 | 0.0105 |
| RFC019_original            | 0.0153 | 0.0143 | 0.0133 | 0.0113 |
| RFC020_drop_breakout_block | 0.0152 | 0.0142 | 0.0132 | 0.0112 |
| RFC025_original            | 0.0152 | 0.0142 | 0.0132 | 0.0112 |
| RFC026_drop_breakout_block | 0.0149 | 0.0139 | 0.0129 | 0.0109 |
| RFC031_drop_breakout_block | 0.0145 | 0.0135 | 0.0125 | 0.0105 |

## Top-Removal Stress

| fixed_candidate_id         | analysis           | group   |   clusters |   cluster_share |   cluster_excess_72h_median |   cluster_forward_72h_median |   validation_excess_72h_median | removed_groups                                | decision   |
|:---------------------------|:-------------------|:--------|-----------:|----------------:|----------------------------:|-----------------------------:|-------------------------------:|:----------------------------------------------|:-----------|
| RFC001_original            | remove_top_1_month | month   |        850 |          0.9648 |                      0.0166 |                       0.0259 |                         0.0193 | 2020-03                                       | survives   |
| RFC001_original            | remove_top_1_pair  | pair    |        780 |          0.8854 |                      0.0149 |                       0.0243 |                         0.0161 | ADA/USDT:USDT                                 | survives   |
| RFC001_original            | remove_top_3_pairs | pair    |        579 |          0.6572 |                      0.0161 |                       0.0268 |                         0.0161 | ADA/USDT:USDT, LINK/USDT:USDT, XRP/USDT:USDT  | survives   |
| RFC002_original            | remove_top_1_month | month   |        620 |          0.9642 |                      0.0159 |                       0.0243 |                         0.0196 | 2021-11                                       | survives   |
| RFC002_original            | remove_top_1_pair  | pair    |        565 |          0.8787 |                      0.0145 |                       0.0253 |                         0.0203 | XRP/USDT:USDT                                 | survives   |
| RFC002_original            | remove_top_3_pairs | pair    |        424 |          0.6594 |                      0.0113 |                       0.0231 |                         0.0196 | XRP/USDT:USDT, DOGE/USDT:USDT, ADA/USDT:USDT  | survives   |
| RFC008_original            | remove_top_1_month | month   |        841 |          0.9656 |                      0.0168 |                       0.0261 |                         0.0196 | 2020-03                                       | survives   |
| RFC008_original            | remove_top_1_pair  | pair    |        771 |          0.8852 |                      0.0162 |                       0.0260 |                         0.0193 | LINK/USDT:USDT                                | survives   |
| RFC008_original            | remove_top_3_pairs | pair    |        574 |          0.6590 |                      0.0158 |                       0.0267 |                         0.0161 | LINK/USDT:USDT, XRP/USDT:USDT, ADA/USDT:USDT  | survives   |
| RFC009_original            | remove_top_1_month | month   |        613 |          0.9638 |                      0.0156 |                       0.0241 |                         0.0194 | 2021-11                                       | survives   |
| RFC009_original            | remove_top_1_pair  | pair    |        558 |          0.8774 |                      0.0144 |                       0.0247 |                         0.0201 | XRP/USDT:USDT                                 | survives   |
| RFC009_original            | remove_top_3_pairs | pair    |        418 |          0.6572 |                      0.0149 |                       0.0269 |                         0.0242 | XRP/USDT:USDT, DOGE/USDT:USDT, LINK/USDT:USDT | survives   |
| RFC015_original            | remove_top_1_month | month   |        622 |          0.9643 |                      0.0156 |                       0.0240 |                         0.0196 | 2021-11                                       | survives   |
| RFC015_original            | remove_top_1_pair  | pair    |        567 |          0.8791 |                      0.0142 |                       0.0241 |                         0.0203 | XRP/USDT:USDT                                 | survives   |
| RFC015_original            | remove_top_3_pairs | pair    |        426 |          0.6605 |                      0.0110 |                       0.0228 |                         0.0196 | XRP/USDT:USDT, DOGE/USDT:USDT, ADA/USDT:USDT  | survives   |
| RFC019_original            | remove_top_1_month | month   |        853 |          0.9649 |                      0.0165 |                       0.0259 |                         0.0193 | 2020-03                                       | survives   |
| RFC019_original            | remove_top_1_pair  | pair    |        782 |          0.8846 |                      0.0156 |                       0.0256 |                         0.0183 | LINK/USDT:USDT                                | survives   |
| RFC019_original            | remove_top_3_pairs | pair    |        581 |          0.6572 |                      0.0156 |                       0.0267 |                         0.0161 | LINK/USDT:USDT, ADA/USDT:USDT, XRP/USDT:USDT  | survives   |
| RFC020_drop_breakout_block | remove_top_1_month | month   |        620 |          0.9642 |                      0.0159 |                       0.0243 |                         0.0196 | 2021-11                                       | survives   |
| RFC020_drop_breakout_block | remove_top_1_pair  | pair    |        565 |          0.8787 |                      0.0145 |                       0.0253 |                         0.0203 | XRP/USDT:USDT                                 | survives   |
| RFC020_drop_breakout_block | remove_top_3_pairs | pair    |        424 |          0.6594 |                      0.0113 |                       0.0231 |                         0.0196 | XRP/USDT:USDT, DOGE/USDT:USDT, ADA/USDT:USDT  | survives   |
| RFC025_original            | remove_top_1_month | month   |        852 |          0.9649 |                      0.0164 |                       0.0259 |                         0.0193 | 2020-03                                       | survives   |
| RFC025_original            | remove_top_1_pair  | pair    |        782 |          0.8856 |                      0.0144 |                       0.0240 |                         0.0161 | ADA/USDT:USDT                                 | survives   |
| RFC025_original            | remove_top_3_pairs | pair    |        581 |          0.6580 |                      0.0156 |                       0.0267 |                         0.0161 | ADA/USDT:USDT, LINK/USDT:USDT, XRP/USDT:USDT  | survives   |
| RFC026_drop_breakout_block | remove_top_1_month | month   |        613 |          0.9638 |                      0.0156 |                       0.0241 |                         0.0194 | 2021-11                                       | survives   |
| RFC026_drop_breakout_block | remove_top_1_pair  | pair    |        558 |          0.8774 |                      0.0144 |                       0.0247 |                         0.0201 | XRP/USDT:USDT                                 | survives   |
| RFC026_drop_breakout_block | remove_top_3_pairs | pair    |        418 |          0.6572 |                      0.0149 |                       0.0269 |                         0.0242 | XRP/USDT:USDT, DOGE/USDT:USDT, LINK/USDT:USDT | survives   |
| RFC031_drop_breakout_block | remove_top_1_month | month   |        622 |          0.9643 |                      0.0156 |                       0.0240 |                         0.0196 | 2021-11                                       | survives   |
| RFC031_drop_breakout_block | remove_top_1_pair  | pair    |        567 |          0.8791 |                      0.0142 |                       0.0241 |                         0.0203 | XRP/USDT:USDT                                 | survives   |
| RFC031_drop_breakout_block | remove_top_3_pairs | pair    |        426 |          0.6605 |                      0.0110 |                       0.0228 |                         0.0196 | XRP/USDT:USDT, DOGE/USDT:USDT, ADA/USDT:USDT  | survives   |

## Top Pair Concentration

| fixed_candidate_id         | analysis          | group          |   clusters |   cluster_share |   cluster_excess_72h_median |   cluster_forward_72h_median |   validation_excess_72h_median | removed_groups   | decision   |
|:---------------------------|:------------------|:---------------|-----------:|----------------:|----------------------------:|-----------------------------:|-------------------------------:|:-----------------|:-----------|
| RFC020_drop_breakout_block | top_pair_clusters | XRP/USDT:USDT  |         78 |          0.1213 |                      0.0167 |                       0.0197 |                            nan |                  |            |
| RFC020_drop_breakout_block | top_pair_clusters | DOGE/USDT:USDT |         71 |          0.1104 |                      0.0273 |                       0.0292 |                            nan |                  |            |
| RFC020_drop_breakout_block | top_pair_clusters | ADA/USDT:USDT  |         70 |          0.1089 |                      0.0263 |                       0.0326 |                            nan |                  |            |
| RFC020_drop_breakout_block | top_pair_clusters | LINK/USDT:USDT |         70 |          0.1089 |                     -0.0038 |                       0.0086 |                            nan |                  |            |
| RFC020_drop_breakout_block | top_pair_clusters | LTC/USDT:USDT  |         67 |          0.1042 |                      0.0194 |                       0.0267 |                            nan |                  |            |
| RFC020_drop_breakout_block | top_pair_clusters | ETH/USDT:USDT  |         57 |          0.0886 |                      0.0071 |                       0.0217 |                            nan |                  |            |
| RFC020_drop_breakout_block | top_pair_clusters | AVAX/USDT:USDT |         56 |          0.0871 |                     -0.0127 |                       0.0051 |                            nan |                  |            |
| RFC020_drop_breakout_block | top_pair_clusters | SOL/USDT:USDT  |         53 |          0.0824 |                      0.0211 |                       0.0278 |                            nan |                  |            |
| RFC026_drop_breakout_block | top_pair_clusters | XRP/USDT:USDT  |         78 |          0.1226 |                      0.0167 |                       0.0197 |                            nan |                  |            |
| RFC026_drop_breakout_block | top_pair_clusters | DOGE/USDT:USDT |         70 |          0.1101 |                      0.0271 |                       0.0273 |                            nan |                  |            |
| RFC026_drop_breakout_block | top_pair_clusters | LINK/USDT:USDT |         70 |          0.1101 |                     -0.0038 |                       0.0086 |                            nan |                  |            |
| RFC026_drop_breakout_block | top_pair_clusters | ADA/USDT:USDT  |         69 |          0.1085 |                      0.0266 |                       0.0369 |                            nan |                  |            |
| RFC026_drop_breakout_block | top_pair_clusters | LTC/USDT:USDT  |         67 |          0.1053 |                      0.0194 |                       0.0267 |                            nan |                  |            |
| RFC026_drop_breakout_block | top_pair_clusters | ETH/USDT:USDT  |         56 |          0.0881 |                      0.0055 |                       0.0211 |                            nan |                  |            |
| RFC026_drop_breakout_block | top_pair_clusters | AVAX/USDT:USDT |         54 |          0.0849 |                     -0.0127 |                       0.0051 |                            nan |                  |            |
| RFC026_drop_breakout_block | top_pair_clusters | SOL/USDT:USDT  |         52 |          0.0818 |                      0.0221 |                       0.0283 |                            nan |                  |            |
| RFC031_drop_breakout_block | top_pair_clusters | XRP/USDT:USDT  |         78 |          0.1209 |                      0.0167 |                       0.0197 |                            nan |                  |            |
| RFC031_drop_breakout_block | top_pair_clusters | DOGE/USDT:USDT |         71 |          0.1101 |                      0.0273 |                       0.0292 |                            nan |                  |            |
| RFC031_drop_breakout_block | top_pair_clusters | ADA/USDT:USDT  |         70 |          0.1085 |                      0.0263 |                       0.0326 |                            nan |                  |            |
| RFC031_drop_breakout_block | top_pair_clusters | LINK/USDT:USDT |         70 |          0.1085 |                     -0.0038 |                       0.0086 |                            nan |                  |            |
| RFC031_drop_breakout_block | top_pair_clusters | LTC/USDT:USDT  |         67 |          0.1039 |                      0.0194 |                       0.0267 |                            nan |                  |            |
| RFC031_drop_breakout_block | top_pair_clusters | ETH/USDT:USDT  |         57 |          0.0884 |                      0.0071 |                       0.0217 |                            nan |                  |            |
| RFC031_drop_breakout_block | top_pair_clusters | AVAX/USDT:USDT |         56 |          0.0868 |                     -0.0127 |                       0.0051 |                            nan |                  |            |
| RFC031_drop_breakout_block | top_pair_clusters | SOL/USDT:USDT  |         54 |          0.0837 |                      0.0204 |                       0.0277 |                            nan |                  |            |
| RFC008_original            | top_pair_clusters | LINK/USDT:USDT |        100 |          0.1148 |                      0.0065 |                       0.0223 |                            nan |                  |            |
| RFC008_original            | top_pair_clusters | XRP/USDT:USDT  |         99 |          0.1137 |                      0.0113 |                       0.0155 |                            nan |                  |            |
| RFC008_original            | top_pair_clusters | ADA/USDT:USDT  |         98 |          0.1125 |                      0.0254 |                       0.0342 |                            nan |                  |            |
| RFC008_original            | top_pair_clusters | LTC/USDT:USDT  |         95 |          0.1091 |                      0.0194 |                       0.0267 |                            nan |                  |            |
| RFC008_original            | top_pair_clusters | DOGE/USDT:USDT |         92 |          0.1056 |                      0.0271 |                       0.0273 |                            nan |                  |            |
| RFC008_original            | top_pair_clusters | SOL/USDT:USDT  |         84 |          0.0964 |                      0.0204 |                       0.0314 |                            nan |                  |            |
| RFC008_original            | top_pair_clusters | AVAX/USDT:USDT |         84 |          0.0964 |                      0.0039 |                       0.0173 |                            nan |                  |            |
| RFC008_original            | top_pair_clusters | ETH/USDT:USDT  |         67 |          0.0769 |                      0.0028 |                       0.0147 |                            nan |                  |            |
| RFC019_original            | top_pair_clusters | LINK/USDT:USDT |        102 |          0.1154 |                      0.0076 |                       0.0229 |                            nan |                  |            |
| RFC019_original            | top_pair_clusters | ADA/USDT:USDT  |        101 |          0.1143 |                      0.0228 |                       0.0284 |                            nan |                  |            |
| RFC019_original            | top_pair_clusters | XRP/USDT:USDT  |        100 |          0.1131 |                      0.0102 |                       0.0153 |                            nan |                  |            |
| RFC019_original            | top_pair_clusters | LTC/USDT:USDT  |         95 |          0.1075 |                      0.0194 |                       0.0267 |                            nan |                  |            |
| RFC019_original            | top_pair_clusters | DOGE/USDT:USDT |         93 |          0.1052 |                      0.0273 |                       0.0292 |                            nan |                  |            |
| RFC019_original            | top_pair_clusters | AVAX/USDT:USDT |         87 |          0.0984 |                      0.0082 |                       0.0144 |                            nan |                  |            |
| RFC019_original            | top_pair_clusters | SOL/USDT:USDT  |         85 |          0.0962 |                      0.0197 |                       0.0289 |                            nan |                  |            |
| RFC019_original            | top_pair_clusters | ETH/USDT:USDT  |         67 |          0.0758 |                      0.0028 |                       0.0147 |                            nan |                  |            |

## Interpretation

- `FIXED_RESEARCH_CANDIDATE` means the fixed definition passes sample, CI, validation, concentration, and 20 bps cost diagnostics for this event-study layer only.
- `RESEARCH_ADVANCE_*_WATCH` means the candidate remains research-only but needs explicit attention before any backtest-class or strict-gate work.
- `REJECT_*` means this fixed follow-up should not advance without new evidence.
- Costs are applied as round-trip bps against event-study 72h forward and matched-null excess returns; they are not a replacement for a Freqtrade backtest.
