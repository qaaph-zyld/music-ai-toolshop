# Wave 1F2 Handoff — WAL guard relaxation + name_drop/code_switch dedupe

**Status: DONE.** Both fixes landed, full suite green incl. the 2 live smoke tests
(they previously failed exit 2 on the stale 0-byte `lyrics.db-wal`), both `mt`
live runs verified, lyrics.db untouched, `data\` restored.

## Diff summary (file:line)

- `mairina/corpus.py:62-86` — `build_guarded`: refuse only when
  `lyrics.db-journal` exists or `lyrics.db-wal` exists **with size > 0**
  (`wal.exists() and wal.stat().st_size > 0`, lines 76-80). A 0-byte `-wal`
  (and any `-shm`) is a reader artifact, not a writer signal. mtime+size
  before/after stability check and the single retry unchanged; docstring and
  error text updated (`-journal present` / `-wal non-empty`, still matching
  "being written").
- `mairina/devices.py:279-284` — `analyze_line`: `_name_drops` computed first;
  `named = {t for d in drops for t in d["span"].split()}` collects every token
  covered by a drop (single spans and phrase constituents); `code_switch`
  skips `named`. name_drop wins; `Gucci na meni, BMW ispred kuce` no longer
  yields `code_switch(gucci)`.
- `tests/test_keys_corpus.py:214-249` —
  `test_build_guarded_refuses_wal_and_retries_on_change` reworked: (a) 0-byte
  `-wal` + `-shm` → builds fine; (b) non-empty `-wal` → `DbUnavailable`
  "being written"; (c) `-journal` → `DbUnavailable`. Retry-on-change
  assertions unchanged. Sidecars created only under `tmp_path`.
- `tests/test_devices.py:128-133` — new `test_name_drop_wins_over_code_switch`:
  gazetteer `{gucci, bmw}` vs `Gucci na meni, BMW ispred kuce` →
  `name_drop` ⊇ {gucci, bmw}, `code_switch` ∩ `name_drop` = ∅.

## Verification

- `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe -X utf8 -m pytest
  D:\Projects\Music-AI-Toolshop\MAirina_Tucc\tests -q -p no:cacheprovider`
  → **147 passed, 1 warning in 42.65s** (0 skipped; both live smoke tests ran
  against the real lyrics.db: `test_live_anchors_aabb_gives_four`,
  `test_live_rhyme_imas_has_snimas_in_top_10`).
- `mt rhyme imaš --lane drill` → exit 0; `snimaš` at **#5** (top 10 ✓):
  klimaš 5.79, cimaš 5.71, otimaš 5.71, uzimaš 5.71, **snimaš 5.57**,
  znaš 3.52, baš 3.51, moraš 3.39, nemaš 3.39, trebaš 3.33.
- `mt anchors --scheme AABB --lane drill` → exit 0; 4 anchors:
  `[A] glavi`, `[A] napravi`, `[B] spavanja`, `[B] sećanja`.

## lyrics.db invariant (opened read-only via immutable URI only)

| | size | mtime (epoch) |
|---|---|---|
| before | 78,524,416 | 1790810143 (2026-10-01 01:15:43) |
| after  | 78,524,416 | 1790810143 — **equal** ✓ |

Sidecars also unchanged: `-wal` 0 B @ 01:18, `-shm` 32,768 B @ 01:18
(pre-existing reader artifacts, never touched).

## `MAirina_Tucc\data\` before → after

```
before:  .gitignore  index_3a770ed6.pkl (Sep29)  index_3a770ed6.pre-rebuild-20260930.pkl  targets_3a770ed6.pkl (230,905)
run:     index_3a770ed6.pkl rebuilt in place (Oct1 01:38, stale vs db mtime Oct1 01:15 — expected);
         targets_3a770ed6.pkl rebuilt in place (1,369,104); mairina.db created (36,864) by votes.connect
after:   .gitignore  index_3a770ed6.pkl  index_3a770ed6.pre-rebuild-20260930.pkl  targets_3a770ed6.pkl
         — mairina.db deleted; no NEW index_*/targets_* files (same tag); no sidecars;
         index_3a770ed6.pre-rebuild-20260930.pkl untouched ✓
```

## git status --short (MAirina_Tucc) — tree NOT clean, declared

```
 M MAirina_Tucc/README.md            M mairina/cli.py        M mairina/rank.py
 M mairina/__init__.py               M mairina/flow.py       M mairina/used.py
 M mairina/corpus.py  (this wave)    M mairina/keys.py
 M tests/conftest.py                 M tests/test_cli_flow_used.py
 M tests/test_keys_corpus.py (this)  M tests/test_live_smoke.py
 M tests/test_rank_anchors_multis.py
?? ORCHESTRATION/mairina_v2/  ?? lexicons/  ?? mairina/devices.py (this wave)
?? mairina/phonetics.py  ?? mairina/rules.py  ?? mairina/targets.py
?? tests/test_devices.py (this)  ?? tests/test_phonetics.py  ?? tests/test_rules.py
?? tests/test_targets.py  ?? tests/test_xray.py
```

Most dirt predates this wave (wave 1F landed uncommitted devices/rules/targets/
phonetics + their tests). My changes: `corpus.py`, `devices.py`,
`test_keys_corpus.py`, `test_devices.py`, this handoff. **No commits made** —
wave constraints forbade `git add/commit`; declared per AGENTS "clean tree or
declared". `toolshop closeout` not run (requires commits).

## Notes for the next wave

- `mt` is usable again with a stale 0-byte `-wal` (the 01:18 reader leftover).
  A live writer still blocks via non-empty `-wal` / `-journal`, and a mid-build
  mutation still trips the mtime+size retry — both covered by tests.
- First `mt` run after a lyrics.db mtime bump rebuilds `index_3a770ed6.pkl`
  in place (~40 s CPU). Not a new file; do not delete.
- name_drop now suppresses code_switch per covered token, including phrase
  constituents (`span.split()`) — e.g. `corp` inside a matched `acme corp`.
