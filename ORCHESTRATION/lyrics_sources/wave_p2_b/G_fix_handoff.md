# G-fix — gutenberg_pd splitter repair handoff (wave p2_b)

Fix for B3's finding: *"6 of 10 works yielded ZERO catalog rows — splitter
gap, not a fetch failure."* All changes are inside
`Genious_lyrics_extractor/sources/gutenberg_pd.py`; `split_songs` stays pure
(text in → list out, no network). No fetch was rerun — a later executor
recatalogs. Validation below reads only the cached `_src/pg<n>.txt` files
under `TOOLSHOP_DATA_DIR=D:/Projects/Music-AI-Toolshop/data/toolshop`.

## Result — per work (previously-0 → now-N splits)

| ebook | work key | kind | B3 rows | now |
|------:|----------|------|--------:|----:|
| 44969 | child-vol1 | child | 125 | 228 |
| 47692 | child-vol2 | child | 0 | **294** |
| 62474 | child-vol3 | child | 0 | **170** |
| 63116 | child-vol4 | child | 0 | **296** |
| 71104 | child-vol5 | child | 0 | **93** |
| 56625 | songs-of-the-west | sotw | 0 | **123** |
| 27129 | elizabethan | caps | 19 | 19 |
| 47607 | yorkshire | caps | 85 | 81 |
| 7535 | old-ballads | caps | 43 | 40 |
| 2831 | bundle-of-ballads | caps | 0 | **29** |

All six previously-silent works contain genuine separable lyric content —
none is prose/no-songs. Every emitted split now carries ≥1 stanza of real
verse (0 empty, 0 `<4`-line for the six; three residual apparatus fragments
in pre-existing works self-filter via the existing `too-short` fetch guard).

## Root causes found + fixes

### child vols II–V (47692, 62474, 63116, 71104) — several layered gaps

1. **First-ballad ceiling.** The ballad-number guard required
   `num <= last_ballad_no + 40` with `last_ballad_no` starting at 0, so the
   volume-openers 54 / 114 / 189 / 266 were all rejected → 0 ballads → 0
   songs. Now the *first* ballad may be any Child number ≤305; later ones
   still need `last + 40` (the CAPS-title lookahead is the real guard).
2. **Unlettered single-text ballads** (HOBIE NOBLE, JAMIE TELFER, CAPTAIN
   WARD): no variant letter is printed. A bare stanza `1` after the `* * *`
   commentary rule (`_DIVIDER` sentinel — kept in the line stream only for
   this splitter) opens the text; where no rule is printed, a 40-line
   lookahead (`_unlettered_opens`) rejects quoted stanzas inside the
   commentary (a quote is always followed soon by the real `A`/`=A.=`/`#A.#`
   head or another heading).
3. **Decorated variant marks `=A.=` / `#A.#`** (vols III–V) open a variant
   only when a bare stanza `1` follows (`_mark_is_variant`) — the same
   marks also head notes sections listing variant readings (`5^1.`…, never
   bare), which now stay out of stanza blocks.
4. **`APPENDIX` / `ADDITIONS AND CORRECTIONS` supplements.** These were in
   `END_HEADS`, so the first appendix ended the volume. They now open a
   supplement mode: CAPS headings there are pieces in their own right
   (Child prints full extra versions — SIR COLIN, the two GILES COLLINS
   texts…), bibliographic citation heads (`II, 28.`, `VOL. II.`, `P. 174.`,
   initials like `G. L. K.`) are rejected by `_supplement_head_ok`, and
   `SECOND FYTTE`/`PART …` division heads continue the current piece. The
   next numbered ballad leaves supplement mode.
5. **Stanza-number orphaning (shared with sotw).** See below.

### songs-of-the-west (56625) — TOC end-head + orphaned stanza numbers

1. `_cut_at_end_head` fired on the CONTENTS row `NOTES ON THE SONGS.`
   (~line 470), truncating the region before `No. 1` (~line 2010) → 0
   songs. All three splitters now only let END_HEADS cut **after the song
   region has begun** (a TOC row for the same heading cannot cut early);
   the real `NOTES ON THE SONGS` back-matter section still terminates the
   region after the last song.
2. The file is treble-spaced: `1` + 3 blanks + verse squeezes to
   `'1', '', verse`, so the bare stanza number flushed as its own block and
   the verse was skipped as apparatus — every one of the 123 songs came
   out *empty* (caught during validation, not by the earlier split-count
   diagnostic). A lone stanza number in `cur` now survives the blank and
   joins its verse block (same rule in `_split_child`).

### bundle-of-ballads (2831) — TOC end-head + heading-shape gaps

1. Same early-cut bug: the CONTENTS row `GLOSSARY` truncated the region
   before the first ballad.
2. New work flags on `WORKS[2831]` (no other work touched):
   `flush_left_heads` (only column-0 CAPS lines are headings — indented
   all-caps refrain lines like `UNWORTHY BARBARA ALLEN.` stay verse) and
   `caps_paren` (`_CAPS_PAREN_RE` accepts a lowercase parenthetical
   qualifier so `CHEVY CHASE (the later version.)` opens a song and keeps
   `(The Later Version)` in the title).

### class fix: PART/FYTTE division heads (affects 3 caps works)

`SECOND FYTTE.`, `PART THE SECOND.`, `THE SECOND PART`, `PART I`… divide
one long ballad; cataloguing them produced anonymous fragments (visible in
B3's dedup log: `Part The First` colliding on slug). Inside an open song
they now continue the parent (`_SUPP_PART_RE`, same semantics as the child
supplement rule); an *indented* `  FIRST PART.` (pg2831 AULD ROBIN GRAY)
is likewise kept out of the verse.

- yorkshire 85→81: 4 part-fragments merged, no title lost.
- old-ballads 43→40: 5 part-fragments merged **and 2 ballads recovered** —
  `The Heir Of Linne` + `The Blind Beggar'S Daughter Of Bednall Green`
  previously opened a song whose head was immediately followed by
  `PART THE FIRST`, leaving an empty (dropped) song while the verse went
  to the part-titles.
- bundle-of-ballads 42→29 after the merge (13 fytte/part fragments folded
  into their ballads — ADAM BELL, THE NUT-BROWN MAID, AULD ROBIN GRAY…).
- child-vol1 125→228: the reworked splitter now emits lettered variants,
  unlettered texts, and supplement pieces the vol-I path also contains
  (B3 had 25 `too-short` drops inside vol I's commentary-heavy tail; the
  supplement/unlettered/variant-mark coverage accounts for the increase).

## Commands + output (counts only — no corpus text quoted)

Validation driver: `split_songs` over each cached `_src/pg<n>.txt` +
`_stanzas` content-length audit per song (same predicates `fetch_lyrics`
uses: `printed_numbers` for sotw/child, `<4` content lines = too-short).

```
$ TOOLSHOP_DATA_DIR=... python -c "<per-work split + stanza audit>"
44969       child-vol1:  228 songs, 0 empty, 1 <4-line
47692       child-vol2:  294 songs, 0 empty, 0 <4-line
62474       child-vol3:  170 songs, 0 empty, 0 <4-line
63116       child-vol4:  296 songs, 0 empty, 0 <4-line
71104       child-vol5:   93 songs, 0 empty, 0 <4-line
56625 songs-of-the-west:  123 songs, 0 empty, 0 <4-line
27129      elizabethan:   19 songs, 0 empty, 1 <4-line
47607        yorkshire:   81 songs, 0 empty, 1 <4-line
7535      old-ballads:   40 songs, 0 empty, 0 <4-line
2831 bundle-of-ballads:   29 songs, 0 empty, 0 <4-line
```
**Exit code: 0**

`fetch_lyrics` smoke over the seeded cache (CatalogEntry → real song body):

```
pg47692:0 The Cherry-Tree Carol [A]   lines= 59 secs=12
pg62474:5 Johnie Cock [F]             lines=124 secs=25
pg63116:0 Hobie Noble                 lines=175 secs=35   (unlettered text)
pg71104:2 The Heir Of Linne [A]       lines=159 secs=32
pg56625:0 By Chance It Was            lines= 44 secs=5
pg56625:60 The Simple Ploughboy       lines= 41 secs=6
pg56625:122 The Evening Prayer        lines= 27 secs=4
pg2831:2 Chevy Chase (The Later Version) lines=319 secs=64
pg2831:28 Auld Robin Gray             lines=131 secs=27   (FIRST PART. head
                                          kept out of verse after fix)
pg7535:9 The Heir Of Linne            lines=268 secs=54   (recovered ballad)
```
**Exit code: 0** — all heads verified as real verse lines; `#`-citation and
page-number apparatus absent from bodies.

Residual `<4`-line splits (self-filtering via `pg<n>:<i>:too-short`):
`pg44969:227 'Young Beichan [N]'` (footnote tail), `pg27129:2 'Song-Books'`
(2-line motto), `pg47607:0 'And A Glossary'` (heading debris). None is a
lost ballad.

## Tests

`tests/test_lyrics_sources_gutenberg.py` — +12 synthetic tests (no real
corpus text committed):

- `TestChildVolsCoverage`: first-ballad >40, `* * *`-gated unlettered text,
  no-rule unlettered text, quoted-stanza rejection, `=A.=`/`=C.=` guarded
  marks, APPENDIX pieces → next ballad, ADDITIONS-AND-CORRECTIONS versions
  + citation-head rejection.
- `TestSotwCoverage`: TOC `NOTES ON THE SONGS.` row does not truncate;
  real section head still ends the region.
- `TestCapsFlagsCoverage`: TOC `GLOSSARY` row vs real `GLOSSARY.`, paren-
  qualifier heading, indented CAPS refrain stays verse, PART/FYTTE heads
  continue the parent (flush-left and indented forms).

```
$ D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe -m pytest \
    tests/test_lyrics_sources_gutenberg.py -x -q
............................
28 passed, 2 warnings in 3.28s
```
**Exit code: 0**

## Files changed

- `Genious_lyrics_extractor/sources/gutenberg_pd.py` — splitters +
  `WORKS[2831]` flags only (fetch/catalog/license paths untouched).
- `tests/test_lyrics_sources_gutenberg.py` — new test classes above.
- `ORCHESTRATION/lyrics_sources/wave_p2_b/G_fix_handoff.md` — this file.

## Risks / notes for the recatalog executor

- Catalog-row counts for yorkshire (85→81) and old-ballads (43→40) drop:
  anonymous `Part*` rows are gone and their verse moved under the parent
  title — fewer rows, more complete songs.
- child-vol1 rows rise 125→228 for the coverage reasons above; expect the
  `too-short` drop count to stay similar (the 25 B3 drops were all in vol
  I) but the fetched count to rise well above 100.
- `split_songs` remains deterministic; `iter_catalog` emits exactly one row
  per split — the table above is what the recatalog will produce.
