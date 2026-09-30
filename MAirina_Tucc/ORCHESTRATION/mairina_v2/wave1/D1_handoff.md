# MAirina v2 — Wave 1 "Craft engine" — D1 handoff

Implementer: Devin (D1). Scope: `MAirina_Tucc/` only. Plan: `D:\Projects\.workspace_archive\plans\mairina-v2-craft-4d7a19.md`.
Product rule preserved: the tool finds and analyzes; it never writes or completes lines.

## Files created

| File | Lines | Purpose |
|---|---|---|
| `mairina/phonetics.py` | 132 | Serbian Latin → phoneme units (`lj`/`nj`/`dž`, syllabic `r`), consonant classes (plosive/sibilant/liquid/nasal/other), voicing pairs, `CLITICS`, `consonant_stream`, `dominant_class` |
| `mairina/devices.py` | 300 | `analyze_line`/`analyze_verse`; tags `{kind, span, confidence, advisory:true}`: alliteration (4-word window, phoneme=high/class=low), consonance density + gauge, internal & multisyllabic rhyme via `toolshop.rhyme_miner`, simile (kao/ko/k'o/ka'o/poput with the `ko`="who" guards), epizeuxis, code-switch (`english_tokens.txt`), name-drop (gazetteer: `entities` ORG/PER/LOC + `songs.primary_artist`/`target_artist`, lowercased, lru-cached), anaphora, epistrophe, anadiplosis, hook-repeat, rhyme letters per line |
| `mairina/rules.py` | 126 | Soft hints only, stable `rule_id`s: `dialect_mix`, `cliche`, `calque`, `abstract_stack`, `self_rhyme`. No lazy-rhyme/suffix rule (per plan). `SHORT_LABELS` for display |
| `mairina/targets.py` | 92 | p25/median/p75 of `lines.syllable_count` per lane × section (`strofa`, `refren`, `prerefren`, `postrefren`, `hook`, `bridge`); pickle cache + in-process memo; `cache_dir` injectable so tests never write the real `data/` |
| `tests/test_phonetics.py` | 68 | units/digraphs, syllabic r, classes, voicing symmetry, clitics, onset, stream |
| `tests/test_devices.py` | 129 | advisory shape, simile & `ko` disambiguation (incl. VERB check via index), alliteration strong/weak, density gauge, maximal internal-rhyme filter, multis + rhyme letters, anaphora (content-word & 2-word), epistrophe/epizeuxis/anadiplosis/hook-repeat, code-switch, name-drop, gazetteer load, the task verse |
| `tests/test_rules.py` | 64 | lexicon load, cliche/calque hits (word-boundary), abstract-stack needs ≥2 + no concrete, verse-level dialect mix, self-rhyme (adjacent only, hook repeats excluded) |
| `tests/test_targets.py` | 67 | quartiles on a purpose-built mini DB, `fmt_range`, cache lands in injected dir, missing-DB raises `DbUnavailable` |
| `tests/test_xray.py` | 79 | xray row shape/tags (simile, rhyme letters, multis), degraded mode without lyrics.db, missing/blank file paths, `rhyme --line/--target` shows `gap`, rank-level gap/dom-class features, anchors rows show `syl` range |
| `data/lexicons/english_tokens.txt` | 172 | `ENGLISH_TOKENS` copied from `lyrics_popper/scripts/qc.py` (~lines 46-68) |
| `data/lexicons/PROVENANCE.md` | 19 | names `D:\Projects\lyrics_popper\data\lexicons\` as source |
| `data/lexicons/{calques,cliches,abstract_nouns,concrete_nouns,dialect_pairs}.{txt,csv}` | 65/130/106/160/95 | byte-identical copies (verified with `cmp`); originals untouched |

## Files changed

| File | Δ | What changed |
|---|---|---|
| `mairina/__init__.py` (23) | +1/-1 | `RANKER_VERSION = "v2"` |
| `mairina/rank.py` (143) | +~15 | `Ctx` gains `line`, `target_syl`; `features_for` adds `gap` (candidate syllables vs `target − line syllables`, `W_GAP=1.0`) and `dom-class` (candidate shares the line's dominant consonant class, `W_CLASS=0.5`); both render in `explain`/`why` |
| `mairina/cli.py` (279) | +~60 | `xray` subcommand (`--lane`, `--section`), `rhyme --line/--target`, `anchors --section`; `_cmd_xray` prints `n | syl X (p25–p75) | rhyme L | cons ▮▮▯ | allit ✓ | ≈tag(span) | hints: label?`; degraded mode (stderr Note, exit 0) when lyrics.db is absent; still never prompts |
| `tests/conftest.py` (123) | +~8 | `entities` table + fixture rows (Timbuktu/LOC, Acme Corp/ORG, Panamera/MISC) so `load_gazetteer` works on the fixture corpus |
| `README.md` (69) | +~10 | `xray` row, `rhyme --line/--target`, `anchors --section`, craft-engine section, lexicon provenance note |

## Verification

### 1. Test suite

```
"D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe" -X utf8 -m pytest "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\tests" -q
→ 124 passed, 1 warning in 84.80s (0:01:24)
```

(v1 baseline was 87; +37 new. The one warning is a pre-existing `requests`/`urllib3` version notice, unrelated.)

### 2. `mt xray` on the required verse (`--lane drill --section strofa`)

```
X-ray 6 lines  lane=drill section=strofa (advisory only — you write)
1 | syl 8 (10–15) | rhyme A | cons ▮▮▯ | ≈simile(ko)
2 | syl 7 (10–15) | rhyme - | cons ▮▮▯
3 | syl 9 (10–15) | rhyme A | cons ▮▮▯ | allit ✓ | ≈internal_rhyme(aa) | ≈name_drop(niko)
4 | syl 10 (10–15) | rhyme - | cons ▮▮▮ | allit ✓ | ≈internal_rhyme(ea)
5 | syl 9 (10–15) | rhyme B | cons ▮▯▯ | allit ✓ | ≈internal_rhyme(ia) | ≈name_drop(mala) | ≈multisyllabic_rhyme(eia)
6 | syl 9 (10–15) | rhyme B | cons ▮▮▯ | allit ✓ | ≈internal_rhyme(aeia) | ≈multisyllabic_rhyme(eia)
```

Gate expectations met: line 1 `simile(ko)`; lines 1 & 3 rhyme `A` (lava/spava); lines 5–6 share `multisyllabic_rhyme(eia)` (imaš/snimaš); `Panameri` is corpus-MISC so untagged (spec-allowed), no rule hint fires; nothing blocks. Advisory notes: `niko` and `mala` match real gazetteer entities (corpus has a PER "Niko" and entity "Mala") — reported, not suppressed; this is honest gazetteer behavior, not a rule problem. No `dialect_mix` fired: `ludilo,ludilo` is an identical pair and is correctly ignored.

### 3. `mt rhyme imaš --lane drill --line "Mala, mogla si da me" --target 9`

```
Rhymes for 'imaš'  lane=drill fresh=0.5 arm=learned ranker=v2 list=#1
  1. klimaš             7.29  perfect-2 +6.00 | freq(5) +0.36 | fresh -0.57 | gap +1.00 | dom-class +0.50
  2. cimaš              6.71  perfect-2 +6.00 | freq(3) +0.28 | fresh -0.57 | gap +1.00
  3. snimaš             6.57  perfect-2 +6.00 | freq(1) +0.14 | fresh -0.57 | gap +1.00
  4. otimaš             6.21  perfect-2 +6.00 | freq(3) +0.28 | fresh -0.57 | gap +0.50
  5. uzimaš             6.21  perfect-2 +6.00 | freq(3) +0.28 | fresh -0.57 | gap +0.50
  6. moraš              4.89  perfect-1 +3.00 | freq(85) +0.89 | fresh -0.50 | gap +1.00 | dom-class +0.50
  7. kalaš              4.77  perfect-1 +3.00 | freq(25) +0.65 | fresh -0.38 | gap +1.00 | dom-class +0.50
  8. igraš              4.72  perfect-1 +3.00 | freq(14) +0.54 | fresh -0.32 | gap +1.00 | dom-class +0.50
  9. karaš              4.70  perfect-1 +3.00 | freq(24) +0.64 | fresh -0.45 | gap +1.00 | dom-class +0.50
 10. lutaš              4.60  perfect-1 +3.00 | freq(4) +0.32 | fresh -0.22 | gap +1.00 | dom-class +0.50
 11. muljaš             4.60  perfect-1 +3.00 | freq(2) +0.22 | fresh -0.12 | gap +1.00 | dom-class +0.50
 12. valjaš             4.60  perfect-1 +3.00 | freq(2) +0.22 | fresh -0.12 | gap +1.00 | dom-class +0.50
 13. varaš              4.58  perfect-1 +3.00 | freq(13) +0.53 | fresh -0.45 | gap +1.00 | dom-class +0.50
 14. teraš              4.57  perfect-1 +3.00 | freq(5) +0.36 | fresh -0.29 | gap +1.00 | dom-class +0.50
 15. rolaš              4.56  perfect-1 +3.00 | freq(1) +0.14 | fresh -0.08 | gap +1.00 | dom-class +0.50
 16. furaš              4.52  perfect-1 +3.00 | freq(2) +0.22 | fresh -0.20 | gap +1.00 | dom-class +0.50
 17. guraš              4.52  perfect-1 +3.00 | freq(2) +0.22 | fresh -0.20 | gap +1.00 | dom-class +0.50
 18. lupaš              4.48  perfect-1 +3.00 | freq(1) +0.14 | fresh -0.16 | gap +1.00 | dom-class +0.50
 19. diraš              4.46  perfect-1 +3.00 | freq(6) +0.39 | fresh -0.43 | gap +1.00 | dom-class +0.50
 20. balaš              4.39  perfect-1 +3.00 | freq(3) +0.28 | fresh -0.38 | gap +1.00 | dom-class +0.50
```

`gap` and `dom-class` appear in the `why` breakdown (line has 7 syl, target 9 → gap 2; 2-syllable candidates get `gap +1.00`).

### 4. `mt anchors --scheme AABB --lane drill`

```
Anchors AABB (rhyme)  lane=drill fresh=0.5 arm=learned ranker=v2 list=#2
Write each line so that it ends on its anchor. The tool never writes lines.
  1. [A] sluti            VERB  class -uti  freq 5  syl 10–15
  2. [A] muti             VERB  class -uti  freq 11  syl 10–15
  3. [B] roka             NOUN  class -oka  freq 12  syl 10–15
  4. [B] koka             NOUN  class -oka  freq 336  syl 10–15
```

Every row carries the drill `strofa` target range `10–15`.

### 5. lyrics.db mtime & git status

- `lyrics.db` LastWriteTime before: `2026-08-09 00:47:25.786102200 +0200`
- `lyrics.db` LastWriteTime after all runs: `2026-08-09 00:47:25.786102200 +0200` — unchanged. Opened only via `corpus.open_ro` (`file:...?mode=ro&immutable=1`, `uri=True`), also covered by `test_lyrics_db_never_modified`.
- `git status --short` (mine only; other dirty paths are pre-existing, other sessions' work: `ORCHESTRATION/ogcm_flip`, `lyrics_research`, `mastering_tool`, `suno_prompter`, `handoffs/`):

```
 M MAirina_Tucc/README.md
 M MAirina_Tucc/mairina/__init__.py
 M MAirina_Tucc/mairina/cli.py
 M MAirina_Tucc/mairina/rank.py
 M MAirina_Tucc/tests/conftest.py
?? MAirina_Tucc/mairina/devices.py
?? MAirina_Tucc/mairina/phonetics.py
?? MAirina_Tucc/mairina/rules.py
?? MAirina_Tucc/mairina/targets.py
?? MAirina_Tucc/tests/test_devices.py
?? MAirina_Tucc/tests/test_phonetics.py
?? MAirina_Tucc/tests/test_rules.py
?? MAirina_Tucc/tests/test_targets.py
?? MAirina_Tucc/tests/test_xray.py
?? MAirina_Tucc/ORCHESTRATION/mairina_v2/   (this file)
```

Cleanup done: temp verse deleted; `data/mairina.db` created by the rhyme/anchors runs deleted; two stale `targets_*.pkl` files (from an earlier in-development run before `cache_dir` was injectable) deleted. Remaining `data/` files: `index_*.pkl`, `targets_3a770ed6.pkl` (live-DB cache), `lexicons/`.

## Deviations from plan

1. **`data/lexicons/` is inside the repo-wide `data/` gitignore rule** (root `.gitignore:47`). Git cannot re-include files under an excluded directory, and the root `.gitignore` is outside my allowed scope — **the orchestrator should commit the lexicons with `git add -f MAirina_Tucc/data/lexicons`** (or add a root-level exception). The code reads them from disk at runtime and works either way.
2. **`xray` degraded mode**: when `lyrics.db` is missing, `xray` prints a `Note:` to stderr and still analyzes (exit 0) rather than exiting 2 — xray is useful offline; other commands keep exit 2.
3. **`anchors` shows one target per row** (the `--section` range, default `strofa`) rather than per-scheme-line syllable budgets — matches "a target range per row".
4. **Internal-rhyme dedupe**: `find_internal_rhymes` returns every repeated skeleton (nested echoes like `ia` inside `aeia`); `devices` keeps only maximal-length matches per line so the meter stays readable.
5. **`dialect_pairs.csv` identical-value rows** (`ludilo,ludilo`, 2 rows) are skipped — a form identical in both dialects cannot mark mixing (found via the gate verse false-positive).
6. **`self_rhyme` hint reports the second line** (`i+2`), not the first of the pair.
7. **`_AUX_CLITICS` + infinitive-suffix fallback** (`-ti`/`-ći`) for the `ko`=who check when no index is available (e.g. degraded mode); with an index, real `upos` is used.

## Not done / known limits

- `name_drop` matches whole tokens/known phrases; inflected forms of multi-word entities ("Panameri" vs "Panamera") only match when the single-token stem is itself in the gazetteer. Corpus-MISC entities are intentionally out of the gazetteer per the spec (ORG/PER/LOC only).
- `dominant_class` ties resolve alphabetically (deterministic); the `dom-class` term is small (+0.5) by design.
- No lazy-rhyme/suffix-rhyme rule, and none of the excluded devices (metaphor, wordplay, double meaning, chiasmus, hyperbole, polyptoton, stress prediction) — all deliberate.
- Waves 2–4 untouched.
