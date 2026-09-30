# MAirina v2 — Wave 1F "Restore corpus annotation" — D0 handoff

Agent: Devin (D0). Task: repopulate `tokens`/`entities` in `lyrics.db` via `toolshop lyrics annotate --resume` after the lyrics-sources rebuild wiped the CLASSLA L3 layer. **No code changed** — operational run only. Pipeline: `toolshop/annotate.py` → `classla.Pipeline('sr', type='nonstandard')` (tokenize/pos/lemma/ner = nonstandard, depparse = standard), CPU only.

## Baseline (captured 2026-09-30 ~21:57, before any writes)

| Metric | Value |
|---|---|
| `lyrics.db` | 67,166,208 bytes, mtime `2026-09-30T20:03:56`, `journal_mode=wal` |
| Sidecars | no `-wal` writer pending (0-byte `-wal`/`-shm` seen at 21:25 were from my read-only baseline conn; `-journal` absent) |
| songs / lines | 1,519 / 71,750 (all `text_raw` non-empty) |
| tokens / entities | **0 / 0** |
| Per-corpus non-empty lines | genius-pro 65,912 · sacred-texts 2,832 · lrclib 1,219 · mudcat-digitrad 893 · ccmixter 758 · gutenberg_pd 116 · hymnary 20 |

Concurrency gate: user/orchestrator confirmed at 21:27 no ingest/rebuild/annotate/scratch job was running (the 20:14 activity was `_scratch_v1test.db`, a copy — not `lyrics.db`).

## Timing probe (--limit 300)

```
time .../python.exe -X utf8 -u -m toolshop.cli lyrics annotate --db .../lyrics.db --resume --limit 300
→ real 1m11.338s   Done: 300 lines, 1856 tokens, 6 entities
```

- CLASSLA model load: 37.6 s cold (measured separately), ~18.5 s warm inside the probe.
- Annotation rate ≈ **0.176 s/line** (52.8 s / 300 after subtracting warm load).
- Extrapolation reported to user before full run: ~3.5 h for the remaining 71,450 lines (bound 4.7 h incl. load). Matches project memory (~2 h / 36,572 lines ≈ 0.197 s/line).

## Full run (--resume, no --limit)

Dedicated background shell → `wave1F/annotate_d0.log` (this directory).

- Start: 22:04:08 (log open), `Lines to annotate: 71450 (skipped 300 already done)` — resume verified working.
- Progress: 142 `Progress: N/71450` lines (500-line cadence), commits per 500 lines.
- End: `Done: 71450 lines, 589314 tokens, 11912 entities`; final `lyrics.db` mtime `2026-10-01T01:15:43`.
- **Total annotation wall ≈ 3 h 11 m** (22:04:25 → 01:15:4x) ≈ **0.160 s/line avg**. Steady ~0.145 s/line through genius-pro; slowed to ~0.3–0.5 s/line on the sacred-texts/gutenberg tail (24 tokens/line vs ~7.4 corpus avg).
- **Zero WARN lines, zero errors, exit code 0.**

## Final state (verified post-run, read-only conn)

| Metric | Value |
|---|---|
| `lyrics.db` | 78,524,416 bytes (+11.36 MB), mtime `2026-10-01T01:15:43` |
| tokens | **591,170** |
| entities | **11,918** |
| annotated lines | **71,750 / 71,750 = 100.0%** |
| sidecars | `-wal`/`-shm`/`-journal` all absent (clean WAL checkpoint on close) |

Coverage per corpus (annotated / non-empty lines — all 100%):

| corpus | lines | annotated | tokens |
|---|---|---|---|
| genius-pro | 65,912 | 65,912 | 501,386 |
| sacred-texts | 2,832 | 2,832 | 68,190 |
| lrclib | 1,219 | 1,219 | 8,259 |
| mudcat-digitrad | 893 | 893 | 6,834 |
| ccmixter | 758 | 758 | 5,198 |
| gutenberg_pd | 116 | 116 | 1,104 |
| hymnary | 20 | 20 | 199 |

Entity breakdown (run's own coverage printout): PER 6,691 · LOC 2,038 · ORG 1,742 · MISC 1,358 · DERIV-PER 89. Script split: latin 583,330 tokens / 70,741 lines; cyrillic 7,840 / 1,009. OOV 0%.

## Spot-check (genius-pro tokens: form, lemma, upos)

```
(87334, 8, 'snimaš', 'snimati', 'VERB', Mood=Ind|Number=Sing|Person=2|Tense=Pres|VerbForm=Fin)
(68224, 2, 'imaš',   'imati',   'VERB', Mood=Ind|Number=Sing|Person=2|Tense=Pres|VerbForm=Fin)
(73163,11, 'lava',   'lav',     'NOUN', Case=Acc|Gender=Masc|Number=Sing)
(66054, 6, 'znaš',   'znati',   'VERB', Mood=Ind|Number=Sing|Person=2|Tense=Pres|VerbForm=Fin)
(74743, 2, 'imas',   'imati',   'VERB', Mood=Ind|Number=Sing|Person=2|Tense=Pres|VerbForm=Fin)
```

Diacritic and stripped forms both lemmatize correctly.

## Files produced by this wave task

- `MAirina_Tucc/ORCHESTRATION/mairina_v2/wave1F/D0_handoff.md` (this file)
- `MAirina_Tucc/ORCHESTRATION/mairina_v2/wave1F/annotate_d0.log` (full run stdout/stderr)

`lyrics.db` was mutated only via the annotate command (tokens/entities INSERTs). No code, tests, configs, or other project files touched. `index_3a770ed6.pre-rebuild-20260930.pkl` untouched. No git mutations performed; `git status` shows only other lanes' pre-existing dirt plus the new untracked `MAirina_Tucc/ORCHESTRATION/mairina_v2/` dir.

## Deviations / notes

- Added `-X utf8 -u` to the given command (UTF-8 console output for Serbian forms + unbuffered stdout for the piped log) — additive flags only.
- `annotate` has no `--corpus` scope — it annotates all corpora; per the rebuild this is intended (F1 gates MAirina reads to `CORPORA = genius-pro`).
- Lines that emit zero tokens are not marked done in `tokens` — a resume would re-attempt them; coverage check shows none occurred (71,750/71,750).

## For F1 / user

Live checks may now run: `tokens`/`entities` are populated for 100% of non-empty lines across all 7 corpora, `lyrics.db` is quiescent (no WAL sidecars, mtime 01:15:43), and the genius-pro ids are the renumbered 1426+ range from the rebuild.
