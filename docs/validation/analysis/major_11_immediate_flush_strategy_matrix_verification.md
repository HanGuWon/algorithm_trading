# Major 11 Immediate Flush Strategy Matrix Verification

> Loader/discovery readiness checks for the generated immediate-flush research strategy classes.

## Scope

- Manifest: `docs/validation/analysis/major_11_immediate_flush_canonical_manifest.csv`
- Strategy file: `user_data/strategies/VolatilityRotationMRImmediateFlushResearch.py`
- Strategy path: `user_data/strategies`
- Expected classes: `42`

## Status Counts

```csv
status,checks
pass,7
unavailable,2
```

## Checks

```csv
check,status,detail,imported_class_count,missing_imported_class_count,command
manifest_row_count,pass,manifest_rows=7; expected=7,,,
expected_class_count,pass,expected_classes=42,,,
unique_strategy_class_names,pass,unique_classes=42; total_classes=42,,,
representative_exit_mode_classes_present,pass,All representative exit-mode smoke classes are present.,,,
entry_mask_coverage_classes_present,pass,All entry-mask coverage classes are present.,,,
manifest_fallback_guard,pass,Manifest fallback is disabled by default and missing/empty manifest paths raise explicit errors.,,,
stake_leverage_callbacks_fixed,pass,Research strategy fixes leverage to 1.0 and returns proposed_stake.,,,
strategy_module_import,unavailable,Strategy import dependency is unavailable: No module named 'talib',0.0,42.0,
freqtrade_list_strategies,unavailable,Freqtrade is not installed in this Python environment.,,,C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m freqtrade list-strategies --strategy-path user_data/strategies --recursive-strategy-search
```
