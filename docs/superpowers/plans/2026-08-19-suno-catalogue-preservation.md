# Suno Catalogue Preservation — fetch the CDN-only tracks to local disk

**Date:** 2026-08-19 · **Author:** orchestrator · **Size:** 1 session + one long background run
**Decision:** D10, authorised by the user 2026-08-19
**Why now:** Assessment F1b. **3,426 Suno tracks exist on this machine only as
`https://cdn1.suno.ai/<id>.mp3` links.** Only **37 mp3s (211 MB)** are actually downloaded. No backup
can protect a file that was never fetched, so this is a *preservation* task and it runs ahead of —
not instead of — the backup coverage fix in P0 Task 1b.

**Verified before writing this plan (2026-08-19):**
- A live `HEAD` against a real record returned **`200`, `Content-Type: audio/mp3`,
  `Content-Length: 3,928,374`**. The CDN links resolve, are public, and need no authentication.
- At ~3.9 MB/track, the full catalogue is **≈13.4 GB**. D: has ~148 GB free — comfortable.
- Prior art to model on: `D:\Projects\suno_extractor\suno_downloader.py` (636 lines —
  ThreadPoolExecutor, retry/backoff, mutagen ID3 tagging, the same CDN host list). It expects that
  project's own extractor dicts, so this plan writes a focused fetcher against the toolshop metadata
  schema rather than bending it.

---

## Source of truth

`data/toolshop/suno/*_metadata.json` — 3,426 records. Each supplies:

| Field | Use |
|---|---|
| `id` | Filename and primary key. Stable, unique, ASCII — no unicode/collision problems |
| `audio_url` | What to fetch |
| `title`, `display_name`, `created_at`, `model_name`, `metadata` (tags + lyrics) | ID3 tags |
| `image_url` | Cover art — **out of scope for this pass**, note it and move on |

---

## Destination and naming

```
data/toolshop/suno/audio/<id>.mp3
```

Sits beside the metadata it belongs to, inside the already-gitignored `data/` tree, on D:. Honours
the data-boundary rule without any new configuration.

**Name by `id`, not title.** Titles contain spaces, unicode, and duplicates
(`uveKk_nasedneci - Hardcore_Pop x Helenea_Dacijevska`); ids are already the join key to the
metadata. Human-readable naming belongs in the ID3 tags, not the filename.

**The 37 legacy mp3s in `suno_extractor\suno_downloads` stay where they are.** They are title-named,
so matching them to ids reliably is not worth the effort against a 211 MB overlap. Back them up as-is
(P0 Task 1b) and let this pass re-fetch by id. Note the overlap; do not build a fuzzy matcher.

---

## Tasks

### Task 1 — Write `scripts/suno_fetch_catalogue.py`

Requirements, each of which exists because of a specific failure mode:

1. **Resume by default.** Skip any `<id>.mp3` already present whose size matches the CDN
   `Content-Length`. A partial or size-mismatched file is re-fetched, not trusted. The run must be
   safely interruptible — 3,389 files over a slow HDD will get interrupted.
2. **Integrity per file.** Compare bytes written against `Content-Length`; discard and retry on
   mismatch. Record `sha256` for every completed file.
3. **Manifest** at `data/toolshop/suno/audio/_download_manifest.json`: `id`, `url`, `bytes`,
   `sha256`, `http_status`, `attempts`, `fetched_at`, `status`. This is what proves the run, and what
   the backup verifies against later.
4. **Polite concurrency.** Max **4 workers**, small inter-request delay, exponential backoff on
   429/5xx, capped retries (3). Do not tune for speed — this is someone else's CDN.
5. **Failure list, not a crash.** A dead link records `status: "failed"` with the code and continues.
   The run's value is the 99% that succeed.
6. **ID3 tags via mutagen** from the metadata (title, artist `display_name`, date `created_at`,
   comment `model_name`, lyrics from `metadata`). If mutagen is unavailable, still save the audio —
   **tagging must never be able to lose a download.**
7. **`--limit N` and `--dry-run`** so the pass can be proven small before it runs large.

### Task 2 — Prove it on a small batch

`--limit 20`. Confirm: 20 files land, sizes match `Content-Length`, manifest entries are complete,
ID3 tags readable, and a second run with the same flag downloads **nothing** (resume works).

**Exit evidence:** the manifest excerpt, a re-run showing 20 skips, and one file's tags dumped.

### Task 3 — Full run

Background, unattended. Expect ~13.4 GB and a long tail on a 2010 HDD.

**Exit evidence:** total fetched / skipped / failed, bytes on disk, wall time, and the failure list
with HTTP codes.

### Task 4 — Reconcile

1. Compare manifest ids against the 3,426 metadata ids. **Every id must be accounted for** as
   fetched, skipped, or failed — no silent gaps.
2. Report any dead links explicitly. A link that 404s today is a track that is *already* lost, and
   the user should know which ones rather than discovering it later.
3. Record disk delta and the new free space on D:.

### Task 5 — Fold into the backup

The new `audio/` tree must be covered by `toolshop/backup.py` (P0 Task 1b). **Decide deliberately
whether the mp3s belong in the Tier-1 backup at all:** 13.4 GB of re-fetchable-while-links-live audio
has a very different value density from 3,426 metadata records.

**Recommendation:** metadata and manifest are Tier-1 (small, irreplaceable). Audio is Tier-2 —
covered, but flagged so a Tier-1 restore stays fast. **[USER DECISION]** if it changes the answer.

### Task 6 — Close-out

CHANGELOG entry, STATUS update (retire the D10 exposure line, replace with the fetched count),
`toolshop closeout` exit 0, push.

---

## Out of scope

- Cover art (`image_url`) — noted, not fetched
- Matching or deduplicating the 37 legacy title-named mp3s
- Ingesting the audio into the catalogue, stems, or analysis pipelines
- Anything touching `ai_modules/` (D6 still deferred)

## Risks

| Risk | Handling |
|---|---|
| Links expire mid-run | Resume + manifest means a re-run picks up exactly what is missing. Fetch soon. |
| CDN rate-limits or blocks | 4 workers, backoff, capped retries. If sustained 429s appear, **stop and report** — do not escalate concurrency or rotate anything. |
| Interrupted run leaves partial files | Size check against `Content-Length` on resume treats partials as missing. |
| 13.4 GB lands on the same disk as everything else | True and unavoidable tonight. It is preservation against link-rot, **not** DR. G5 still owes a second physical disk. |
