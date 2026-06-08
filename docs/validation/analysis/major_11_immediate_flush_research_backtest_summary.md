# Major 11 Immediate Flush Research Backtest

> Research-only Freqtrade portfolio backtest layer. Passing rows are not dry-run or live-trading approvals.

## Scope

- Manifest: `docs/validation/analysis/major_11_immediate_flush_canonical_manifest.csv`
- Config: `user_data/configs/volatility_rotation_mr_backtest_major_11.json`
- Timerange: `20200109-20260603`
- Export mode: `trades`
- Fee scenarios: `base`
- Plan only: `True`
- Runs: `42`
- Manifest rows: `7`
- Exit modes: `6`
- Strategy classes: `42`
- Artifact mode: `plan_only`
- Is backtest result: `False`
- Manifest SHA256: `5bbe6d9824c23d37bf19afb32acaeb4ccb77c3c40a68e1a321b4b388b11d347b`
- Strategy file SHA256: `7aefbe0abb124037556afc35b4a89f4590e6bbfbde5c02150b5de2e821fa5d8c`
- Config SHA256: `754a7276bf52e6904cbb07fd217662273306b6d5074b970b6eb991c04804ea48`
- Git commit: `d94d2927ba1a5349bcd420ebb6b47515740a1f6d`
- Git worktree dirty at run time: `True`
- Freqtrade version: `unavailable: C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe: No module named freqtrade`
- Discovery status: `not_run_plan_only`

## Artifacts

- Metadata: `docs/validation/analysis/major_11_immediate_flush_research_backtest_metadata.json`
- Trades: `docs/validation/analysis/major_11_immediate_flush_research_backtest_trades.csv`
- Pair breakdown: `docs/validation/analysis/major_11_immediate_flush_research_backtest_pair_breakdown.csv`
- Year breakdown: `docs/validation/analysis/major_11_immediate_flush_research_backtest_year_breakdown.csv`
- Month breakdown: `docs/validation/analysis/major_11_immediate_flush_research_backtest_month_breakdown.csv`
- Exit reason breakdown: `docs/validation/analysis/major_11_immediate_flush_research_backtest_exit_reason_breakdown.csv`
- Strategy discovery: `docs/validation/analysis/major_11_immediate_flush_strategy_discovery.txt`

## Decision Counts

```csv
decision,runs
NOT_RUN_PLAN_ONLY,42
```

## Plan-Only Guard

`--plan-only` was used. Summary rows are execution plans, and trades/breakdown CSVs are explicit placeholder artifacts, not backtest results.

## Summary

```csv
strategy_class,canonical_fixed_candidate_id,exit_mode,cost_scenario,artifact_mode,is_backtest_result,status,decision
ImmediateFlushResearchRFC008Hold24h,RFC008_original,hold_24h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC008Hold72h,RFC008_original,hold_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC008Hold120h,RFC008_original,hold_120h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC008ZscoreRevert72h,RFC008_original,zscore_revert_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC008RsiRevert72h,RFC008_original,rsi_revert_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC008BbMidReclaim72h,RFC008_original,bb_mid_reclaim_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC001Hold24h,RFC001_original,hold_24h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC001Hold72h,RFC001_original,hold_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC001Hold120h,RFC001_original,hold_120h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC001ZscoreRevert72h,RFC001_original,zscore_revert_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC001RsiRevert72h,RFC001_original,rsi_revert_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC001BbMidReclaim72h,RFC001_original,bb_mid_reclaim_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC019Hold24h,RFC019_original,hold_24h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC019Hold72h,RFC019_original,hold_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC019Hold120h,RFC019_original,hold_120h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC019ZscoreRevert72h,RFC019_original,zscore_revert_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC019RsiRevert72h,RFC019_original,rsi_revert_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC019BbMidReclaim72h,RFC019_original,bb_mid_reclaim_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC002Hold24h,RFC002_original,hold_24h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC002Hold72h,RFC002_original,hold_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC002Hold120h,RFC002_original,hold_120h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC002ZscoreRevert72h,RFC002_original,zscore_revert_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC002RsiRevert72h,RFC002_original,rsi_revert_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC002BbMidReclaim72h,RFC002_original,bb_mid_reclaim_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC025Hold24h,RFC025_original,hold_24h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC025Hold72h,RFC025_original,hold_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC025Hold120h,RFC025_original,hold_120h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC025ZscoreRevert72h,RFC025_original,zscore_revert_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC025RsiRevert72h,RFC025_original,rsi_revert_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC025BbMidReclaim72h,RFC025_original,bb_mid_reclaim_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC009Hold24h,RFC009_original,hold_24h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC009Hold72h,RFC009_original,hold_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC009Hold120h,RFC009_original,hold_120h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC009ZscoreRevert72h,RFC009_original,zscore_revert_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC009RsiRevert72h,RFC009_original,rsi_revert_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC009BbMidReclaim72h,RFC009_original,bb_mid_reclaim_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC015Hold24h,RFC015_original,hold_24h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC015Hold72h,RFC015_original,hold_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC015Hold120h,RFC015_original,hold_120h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC015ZscoreRevert72h,RFC015_original,zscore_revert_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC015RsiRevert72h,RFC015_original,rsi_revert_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
ImmediateFlushResearchRFC015BbMidReclaim72h,RFC015_original,bb_mid_reclaim_or_72h,base,plan_only,False,planned,NOT_RUN_PLAN_ONLY
```

## Decision Gates

- trades >= `200`
- validation_trades >= `50`
- active_pairs >= `8`
- active_years >= `5`
- validation_profit_usdt > `0`
- validation_profit_pct_of_starting_balance > `0`
- profit_after_top_5_trade_removal > `0`
- profit_after_fee_2x > `0`
- profit_after_20bps_cost_proxy > `0`
- top_pair_profit_share <= `0.35`
- top_year_profit_share <= `0.4`
- max_drawdown_pct <= `15.0`
