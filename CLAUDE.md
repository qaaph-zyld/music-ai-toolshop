@AGENTS.md

## MAirina Tucc (`MAirina_Tucc/`)
- Product rule: MAirina finds and analyzes — it never writes lyric lines.
- **Private git submodule** (`github.com/qaaph-zyld/MAirina_Tucc`) since W2' 2026-10-04 — absorbed the
  `lyrics_popper` craft repo (`lyrics_popper/` inside it) and keeps the old RimerSR code at `legacy/rimersr/`.
  MAirina code still imports `toolshop.syllables` + `toolshop.rhyme_miner` from THIS repo, so it only works
  inside the parent: clone with `git clone --recurse-submodules` (private repo → GitHub auth required).
- Work on MAirina happens in its own repo/branches; the parent only bumps the submodule pointer.
- Ledger: `handoffs/orchestration_ledger_mairina_v2_20260930.md`.
- Linux tests: `PYTHONPATH=.:MAirina_Tucc python -m pytest MAirina_Tucc/tests -q -p no:cacheprovider` (`.` on PYTHONPATH so `toolshop` resolves).
- `lyrics.db` (78 MB corpus) is local-only and gitignored; `tests/test_live_smoke.py` skips without it.

## Submodule children (W2' 2026-10-04)
`mastering_tool`, `suno_prompter`, `open_DAW`, `track_reverse_engineering`, `suno_extractor`,
`track_inventory`, `MAirina_Tucc` — each is its own repo (see `.gitmodules`). **Work lands in the child
repo; the parent only bumps the gitlink pointer.** `suno_extractor` and `track_inventory` also exist as
junctions at `D:\Projects\suno_extractor` / `D:\Projects\track_inventory` for legacy absolute paths.
