# F — hymnary fetch executor handoff (run B6, "bounded retry")

**Date:** 2026-11-27 (session clock ~02:5x)
**Lane:** `lyrics-p2` @ worktree `D:/Projects/Music-AI-Toolshop-wt-lyrics-p2`
**Role:** fetch executor — no code edits made, no new fetch path improvised.
**Verdict: `deferred-with-evidence`** — the `/text/` fetch lane is still
Bunny-challenged: 23/25 probe items returned `HTTPError: 403` (92%). The lane
is intermittently leaky, not dead — 2/25 fetched clean — but bulk fetch is
blocked this session. SPEC §9 / GATE-0 outcome; pending + failed entries all
remain `--resume`-retryable.

## Step 1 — catalog verification

`D:/Projects/Music-AI-Toolshop/data/toolshop/lyrics/hymnary/_catalog.json`
(the post-quarantine catalog; the rejected bad-query one is parked in
`_quarantine_bad_query/_catalog.json` — 10 rows, `lane: html-fallback`).

- **527 entries** — matches the expected catalog.
- Pre-probe statuses: **`pending: 522` (expected)**, `failed: 4`, `fetched: 1`.
  All 4 pre-existing `failed` rows carry the pilot's verbatim error
  `HTTPError: 403 Client Error: Forbidden for url: https://hymnary.org/text/…`.
- Spot-checks (3 pending rows) — hymnalID year suffix → `min_instance_year`:

| foreign_identifier | hymnal_ids | instance_years | min ≤1930 |
|---|---|---|---|
| `afflictions_though_they_seem_severe` | SH1835 | [1835] | ✓ (1835) |
| `ah_who_are_these_from_far` | HE1900 | [1900] | ✓ (1900) |
| `alas_and_did_my_savior_bleed` | GTSS1886, OSSN1908 | [1886, 1908] | ✓ (1886) |

All catalog rows observed carry `meta.lane: csv-export` with resolved
instance-year lists.

## Step 2 — probe (verbatim)

Command (env passed via exec `env` param — inline `VAR=val` prefix is
sandbox-denied here):

```
TOOLSHOP_DATA_DIR=D:/Projects/Music-AI-Toolshop/data/toolshop \
D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe \
  Genious_lyrics_extractor/fetch_lyrics_source.py --source hymnary --resume --limit 25
```

Output (full, verbatim — benign `RequestsDependencyWarning`/`FutureWarning`
urllib3 lines elided from the head):

```
[hymnary] 25 entries to process (resume=True, corpus=D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\hymnary)
  [1/25] FAIL: ? — Anticipation — 403 Client Error: Forbidden for url: https://hymnary.org/text/a_few_more_days_on_earth_to_spend
  [2/25] FAIL: Philip Phillips, Jr. — Jesus, Savior, Thy dying blood — 403 Client Error: Forbidden for url: https://hymnary.org/text/a_guilty_sinner_once_was_i_till_god
  [3/25] FAIL: Elisha A. Hoffman; Elisha Albright Hoffman — When you have time — 403 Client Error: Forbidden for url: https://hymnary.org/text/a_home_in_heaven_you_hope_to_gain
  [4/25] FAIL: John Chandler — Children's praise — 403 Client Error: Forbidden for url: https://hymnary.org/text/above_the_clear_blue_sky_in_heavens
  [5/25] FAIL: ? — Afflictions, though they seem severe — 403 Client Error: Forbidden for url: https://hymnary.org/text/afflictions_though_they_seem_severe
  [6/25] FAIL: N. Perry — The friends of Jesus — 403 Client Error: Forbidden for url: https://hymnary.org/text/ah_who_are_these_from_far
  [7/25] FAIL: ? — Alas! and Did my Savior Bleed — 403 Client Error: Forbidden for url: https://hymnary.org/text/alas_and_did_my_savior_bleed
  [8/25] FAIL: Mary D. James — All for Jesus — 403 Client Error: Forbidden for url: https://hymnary.org/text/all_for_jesus_all_for_jesus_all_my_being
  [9/25] FAIL: Nicolaus Decius — All Glory Be to Thee, Most High — 403 Client Error: Forbidden for url: https://hymnary.org/text/all_glory_be_to_thee_most_high_to_thee
  [10/25] FAIL: S. Minerva Boyce — Ring, ye bells, ring — 403 Client Error: Forbidden for url: https://hymnary.org/text/all_hail_the_glorious_christmas_morn
  [11/25] OK (pre-1931): ? — Crown Him Lord of All
  [12/25] FAIL: Mrs. Laura E. Newell — The Gospel Message — 403 Client Error: Forbidden for url: https://hymnary.org/text/all_the_world_should_hear_the_message
  [13/25] FAIL: P. P. B. — Almost Persuaded — 403 Client Error: Forbidden for url: https://hymnary.org/text/almost_persuaded_now_to_believe_almost_p
  [14/25] FAIL: Isaac Watts, 1674-1748 — Am I a soldier of the cross — 403 Client Error: Forbidden for url: https://hymnary.org/text/am_i_a_soldier_of_the_cross
  [15/25] OK (pre-1931): John Newton — Amazing Grace
  [16/25] FAIL: W. Hunter, D.D. — Let Me Die at My Post — 403 Client Error: Forbidden for url: https://hymnary.org/text/an_old_soldier_i_stand
  [17/25] FAIL: ? — And am I born to die? — 403 Client Error: Forbidden for url: https://hymnary.org/text/and_am_i_born_to_die
  [18/25] FAIL: Francis Pott — Angel Voices, Ever Singing — 403 Client Error: Forbidden for url: https://hymnary.org/text/angel_voices_ever_singing
  [19/25] FAIL: Jessie H. Brown — Anywhere With Jesus — 403 Client Error: Forbidden for url: https://hymnary.org/text/anywhere_with_jesus_i_can_safely_pounds
  [20/25] FAIL: Mrs. W. J. Kennedy — Waiting for His Coming — 403 Client Error: Forbidden for url: https://hymnary.org/text/are_you_waiting_for_the_coming_kennedy
  [21/25] FAIL: H. L. — The Beautiful Gates of Gold — 403 Client Error: Forbidden for url: https://hymnary.org/text/are_you_walking_the_path_that_is_leading
  [22/25] FAIL: Charles Wesley, 1707-1788 — Arise, my soul, arise, shake off — 403 Client Error: Forbidden for url: https://hymnary.org/text/arise_my_soul_arise_shake_off_thy_guilty
  [23/25] FAIL: ? — As on the cross the Saviour hung — 403 Client Error: Forbidden for url: https://hymnary.org/text/as_on_the_cross_the_savior_hung_and_wept
  [24/25] FAIL: Fanny J. Crosby — As the Bird Flies Home — 403 Client Error: Forbidden for url: https://hymnary.org/text/as_the_bird_flies_home_to_its_parent_nes
  [25/25] FAIL: Alice Jean Cleator — Every Step of the Way — 403 Client Error: Forbidden for url: https://hymnary.org/text/as_you_journey_along_oer_the_highway_of_
[hymnary] index: 3 unique songs, 0 intra-corpus dupes
[hymnary] done: {'fetched': 2, 'failed': 23, 'dropped': 0, 'skipped': 0} (catalog counts: {'failed': 23, 'fetched': 3, 'pending': 501})
```

**Exit code: 0** (per-item failures are catalog marks, not process failures).

Verbatim failure error (every failure, identical class):

```
HTTPError: 403 Client Error: Forbidden for url: https://hymnary.org/text/<id>
```

The 4 items that failed in the pilot (`a_few_more_days_on_earth_to_spend`,
`a_guilty_sinner_once_was_i_till_god`, `a_home_in_heaven_you_hope_to_gain`,
`above_the_clear_blue_sky_in_heavens`) **re-403'd** — the Bunny
"Establishing a secure connection" challenge on `/text/` pages persists, same
signature the pilot (I7) recorded. 2 pages leaked through
(`all_hail_the_power_of_jesus_name_let`, `amazing_grace_how_sweet_the_sound`),
consistent with the adapter docstring's "some /text/ pages … while others
serve 200".

## Why deferred, not resumed

The task fork: *"if fetches succeed → resume unbounded / if 403s persist →
deferred-with-evidence."* Both are literally true — the block is leaky — but
the evidence supports deferred:

1. **403 is the dominant response** (23/25 = 92%, incl. all 4 pilot retries
   re-failing). The pilot's blocker persists; nothing lifted.
2. **Cost model is ~7× the task estimate.** The brief budgets "522 rows @1.5s
   ≈ 13 min", but the adapter enforces `MIN_INTERVAL_S = 5.0` (robots.txt
   `Crawl-delay: 5`) plus a 5 s retry sleep inside `fetch_lyrics` on each 403 —
   a full pass is ~522 × ~10–11 s ≈ **90+ min of requests to a host actively
   challenging us**. Grinding a live bot-challenge risks escalating the block
   (soft challenge → hard IP block), shrinking the leaky window for future
   retries. Per GATE-0's audit posture, the polite move is to back off and let
   a later wave's `--resume` harvest when Bunny's posture changes — `failed`
   and `pending` entries are all retryable; nothing is forfeited.
3. **SPEC §9 binding:** CSV-primary + existing-HTML-fallback — both catalog
   lanes already produced the catalog; what remains dead-ish is per-text page
   fetch, and "never build a new scraper" forecloses improvisation. Deferral
   is the sanctioned outcome.

## Correctness gate (pre-1931) — verified on all 3 `fetched` items

| item | meta.pd_year | rep_text_year | gate |
|---|---|---|---|
| Abide With Me | 1929 | 2013 | `modified_note` records rep text from Lift Up Your Hearts 2013; PD basis = 1929 instance |
| Crown Him Lord of All | 1900 | 1987 | `modified_note` records Psalter Hymnal (Gray) 1987; PD basis = 1900 instance |
| Amazing Grace | 1835 | 2013 | `modified_note` records Ancient & Modern 2013; PD basis = 1835 instance |

**No post-1930 item reached `fetched`** — the ≤1930 instance-year gate held on
every emitted song. Post-probe catalog counts:
`{'pending': 501, 'failed': 23, 'fetched': 3}`.

## Disk state (main-repo data dir, gitignored — never committed)

- `pre-1931/`: 3 `.json` + 3 `.txt` (abide_with_me, crown_him, amazing_grace).
- `_index.json`: 3 unique songs, `_dedup_log.json`: 0 dupes.
- `_quarantine_bad_query/`: untouched this run (10 rows, html-fallback lane).

## Timing

Probe: ~25 items in ~3.5–4 min (~9 s/item — 5 s limiter + 5 s in-adapter retry
sleep on 403s + request latency). Full-pass extrapolation: ~90+ min.

## Git evidence (worktree, pre-commit)

```
$ git -C "D:/Projects/Music-AI-Toolshop-wt-lyrics-p2" status --short
(clean — nothing but this handoff added; corpus artifacts live in the
 gitignored main-repo data dir)

$ git -C "D:/Projects/Music-AI-Toolshop-wt-lyrics-p2" log --oneline -3
fb4ce99 lyrics-p2: B3-rerun gutenberg_pd fetch handoff — 1,107 fetched, 0 failed; all 10 works emit post-G-fix
442ee51 lyrics-p2 G-fix: split the six zero-row Gutenberg works (child vols II-V, songs-of-the-west, bundle-of-ballads)
1a4619a docs(lyrics-p2): wave P2-B run B4 ccmixter fetch handoff (547 fetched, 36.3% yield)
```

## Risks / notes for downstream waves

1. **hymnary DID produce a (tiny) corpus this wave** — 3 songs, all PD-gated
   with auditable `meta.pd_instance` + `modified_note`. Whether that crosses
   I9's "if B6 produced" ingest bar is the orchestrator's call; the files are
   valid song-JSON v2.
2. **Resume is free later:** `fetch_lyrics_source.py --source hymnary
   --resume` retries all 524 un-fetched entries (501 pending + 23 failed).
   Recommend re-probing in a different session/IP/time-window first — the
   challenge rate may differ.
3. **No adapter defect found.** The 403 is upstream (Bunny bot-rules);
   pipeline, writer, index, and the 1931 gate all verified working. The
   catalog CSV lane remains the proven-good path — it built 527 rows and the
   per-text `in:instances` CSV fallback inside `fetch_lyrics` may still work
   where the HTML page is challenged (untested at volume this run).
4. If a future wave needs the corpus urgently, spacing beyond 5 s or a fresh
   egress IP are the sanctioned levers — **not** a new scraper (GATE-0).
