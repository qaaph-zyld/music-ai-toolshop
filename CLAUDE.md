@AGENTS.md

## MAirina Tucc (`MAirina_Tucc/`)
- Product rule: MAirina finds and analyzes — it never writes lyric lines.
- Ledger: `handoffs/orchestration_ledger_mairina_v2_20260930.md`.
- Linux tests: `PYTHONPATH=MAirina_Tucc python -m pytest MAirina_Tucc/tests -q -p no:cacheprovider`.
- `lyrics.db` (78 MB corpus) is local-only and gitignored; `tests/test_live_smoke.py` skips without it.
