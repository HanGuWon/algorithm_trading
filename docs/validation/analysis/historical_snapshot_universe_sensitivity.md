# Historical Snapshot Universe Sensitivity

- Candidate pairs file: `user_data/pairs/binance_usdt_futures_research_candidates.json`
- Anchors: `2022-01-01` to `2025-01-01` quarterly
- top_n sweep: `20, 35, 50`
- Coverage filter: `95%` lookback and post-window
- Union size at top_n=50: `85` pairs

## Selected Pair Counts by Anchor

| anchor     |   20 |   35 |   50 |
|:-----------|-----:|-----:|-----:|
| 2022-01-01 |   20 |   35 |   44 |
| 2022-04-01 |   20 |   35 |   45 |
| 2022-07-01 |   20 |   35 |   46 |
| 2022-10-01 |   20 |   35 |   49 |
| 2023-01-01 |   20 |   35 |   50 |
| 2023-04-01 |   20 |   35 |   50 |
| 2023-07-01 |   20 |   35 |   50 |
| 2023-10-01 |   20 |   35 |   50 |
| 2024-01-01 |   20 |   35 |   50 |
| 2024-04-01 |   20 |   35 |   50 |
| 2024-07-01 |   20 |   35 |   50 |
| 2024-10-01 |   20 |   35 |   50 |
| 2025-01-01 |   20 |   35 |   50 |

## Summary Table

| anchor     |   top_n |   candidate_files |   eligible_pairs |   selected_pairs | first_pair    | last_pair       |
|:-----------|--------:|------------------:|-----------------:|-----------------:|:--------------|:----------------|
| 2022-01-01 |      20 |                90 |               44 |               20 | BTC/USDT:USDT | ALGO/USDT:USDT  |
| 2022-01-01 |      35 |                90 |               44 |               35 | BTC/USDT:USDT | XMR/USDT:USDT   |
| 2022-01-01 |      50 |                90 |               44 |               44 | BTC/USDT:USDT | CTSI/USDT:USDT  |
| 2022-04-01 |      20 |                90 |               45 |               20 | BTC/USDT:USDT | ATOM/USDT:USDT  |
| 2022-04-01 |      35 |                90 |               45 |               35 | BTC/USDT:USDT | XLM/USDT:USDT   |
| 2022-04-01 |      50 |                90 |               45 |               45 | BTC/USDT:USDT | ZEN/USDT:USDT   |
| 2022-07-01 |      20 |                90 |               46 |               20 | BTC/USDT:USDT | TRX/USDT:USDT   |
| 2022-07-01 |      35 |                90 |               46 |               35 | BTC/USDT:USDT | XLM/USDT:USDT   |
| 2022-07-01 |      50 |                90 |               46 |               46 | BTC/USDT:USDT | ZEN/USDT:USDT   |
| 2022-10-01 |      20 |                90 |               49 |               20 | BTC/USDT:USDT | FIL/USDT:USDT   |
| 2022-10-01 |      35 |                90 |               49 |               35 | BTC/USDT:USDT | NEO/USDT:USDT   |
| 2022-10-01 |      50 |                90 |               49 |               49 | BTC/USDT:USDT | CTSI/USDT:USDT  |
| 2023-01-01 |      20 |                90 |               51 |               20 | BTC/USDT:USDT | AVAX/USDT:USDT  |
| 2023-01-01 |      35 |                90 |               51 |               35 | BTC/USDT:USDT | DASH/USDT:USDT  |
| 2023-01-01 |      50 |                90 |               51 |               50 | BTC/USDT:USDT | ICX/USDT:USDT   |
| 2023-04-01 |      20 |                90 |               55 |               20 | BTC/USDT:USDT | GALA/USDT:USDT  |
| 2023-04-01 |      35 |                90 |               55 |               35 | BTC/USDT:USDT | FET/USDT:USDT   |
| 2023-04-01 |      50 |                90 |               55 |               50 | BTC/USDT:USDT | QTUM/USDT:USDT  |
| 2023-07-01 |      20 |                90 |               58 |               20 | BTC/USDT:USDT | INJ/USDT:USDT   |
| 2023-07-01 |      35 |                90 |               58 |               35 | BTC/USDT:USDT | ATOM/USDT:USDT  |
| 2023-07-01 |      50 |                90 |               58 |               50 | BTC/USDT:USDT | DASH/USDT:USDT  |
| 2023-10-01 |      20 |                90 |               60 |               20 | BTC/USDT:USDT | GALA/USDT:USDT  |
| 2023-10-01 |      35 |                90 |               60 |               35 | BTC/USDT:USDT | MASK/USDT:USDT  |
| 2023-10-01 |      50 |                90 |               60 |               50 | BTC/USDT:USDT | BLUR/USDT:USDT  |
| 2024-01-01 |      20 |                90 |               68 |               20 | BTC/USDT:USDT | LTC/USDT:USDT   |
| 2024-01-01 |      35 |                90 |               68 |               35 | BTC/USDT:USDT | CAKE/USDT:USDT  |
| 2024-01-01 |      50 |                90 |               68 |               50 | BTC/USDT:USDT | MAGIC/USDT:USDT |
| 2024-04-01 |      20 |                90 |               74 |               20 | BTC/USDT:USDT | NEAR/USDT:USDT  |
| 2024-04-01 |      35 |                90 |               74 |               35 | BTC/USDT:USDT | TIA/USDT:USDT   |
| 2024-04-01 |      50 |                90 |               74 |               50 | BTC/USDT:USDT | BLUR/USDT:USDT  |
| 2024-07-01 |      20 |                90 |               80 |               20 | BTC/USDT:USDT | ADA/USDT:USDT   |
| 2024-07-01 |      35 |                90 |               80 |               35 | BTC/USDT:USDT | TIA/USDT:USDT   |
| 2024-07-01 |      50 |                90 |               80 |               50 | BTC/USDT:USDT | APE/USDT:USDT   |
| 2024-10-01 |      20 |                90 |               83 |               20 | BTC/USDT:USDT | AVAX/USDT:USDT  |
| 2024-10-01 |      35 |                90 |               83 |               35 | BTC/USDT:USDT | ALT/USDT:USDT   |
| 2024-10-01 |      50 |                90 |               83 |               50 | BTC/USDT:USDT | TRX/USDT:USDT   |
| 2025-01-01 |      20 |                90 |               89 |               20 | BTC/USDT:USDT | THE/USDT:USDT   |
| 2025-01-01 |      35 |                90 |               89 |               35 | BTC/USDT:USDT | NEAR/USDT:USDT  |
| 2025-01-01 |      50 |                90 |               89 |               50 | BTC/USDT:USDT | TON/USDT:USDT   |

## Notes

Higher top_n values broaden the retained universe only when the historical coverage filter passes.
The union file is intended for 5m research downloads and de-overlapped alpha validation.
