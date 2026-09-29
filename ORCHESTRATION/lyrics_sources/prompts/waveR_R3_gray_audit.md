# R3 — Gray-source access audit + free lyrics APIs (lyrics-sources megaplan)

You are a **researcher** agent. Web research only — do not grep local files, do not run code, do not make implementation decisions. Every factual claim must carry a URL citation.

## Context

The megaplan's hard license gate needs an access audit of the *gray* tier: sources whose content is not cleared for release. The question per source is not "is it legal to use the lyrics" (it is not — that's settled) but **"what may our tooling even fetch?"** — catalog metadata vs nothing vs (for user-consented, per-uploader-licensed content) possibly text.

Sources in scope: **Looperman** (11k+ user-uploaded acapellas, per-uploader royalty-free terms), **Voclr.it** and **Acapellas4u** (free acapella rips of commercial songs — account/credit gated), plus the *legitimate free lyrics APIs* for a possible `study-only` tier: **LRCLIB** (lrclib.net — open synced-lyrics DB/API) and **Musixmatch free tier**.

## Key questions

1. **Looperman**: ToS on automated access/scraping; what the acapella listing + track pages expose without login (metadata: title, BPM, key, genre, uploader; do descriptions carry lyric text?); robots.txt status. Verdict: `auto` / `manual-metadata-only` / `catalog-only`.
2. **Voclr.it + Acapellas4u**: auth/credit gates, robots.txt, ToS — expected verdict `catalog-only` (registry rows, no fetch); confirm or correct.
3. **LRCLIB**: API endpoints (`/api/search`, `/api/get`, `/api/get-cached`), auth needs (none?), response fields (plainLyrics vs syncedLyrics — the synced timestamps are a bonus for the repo's whisperX alignment lane), licensing of the *service/data*, rate limits. The lyric content itself is still © — this is a `study-only` tier candidate at best; confirm the API reality.
4. **Musixmatch free tier**: what the free API actually returns (reportedly 30% of lyrics), key requirements, whether worth a `study-only` adapter or catalog-only.
5. **Paid vocal-pack sites as registry rows** (Tech House Market, Loopmasters, Vocalfy, Studiotronnic, Weapon Sounds, Splice): confirm each has public pack-listing pages suitable for a metadata catalog entry (name/price/license-type) — no scraping of downloads needed, just that a registry row pointing at the pack is meaningful.

## Deliverable

Write `D:\Projects\.workspace_archive\handoffs\researcher_lyrsrc_grayaudit_<yyyymmdd_hhmm>.md` containing:

- Per-source verdict with evidence (robots lines, ToS clauses, auth gate descriptions — cite each)
- LRCLIB/Musixmatch API reference summary (endpoints, fields, limits) if kept
- Which metadata is safely fetchable per gray source (title/BPM/key/genre listings vs nothing)
- End with this fenced contract:

```yaml
findings:
  looperman: "<auto|manual-metadata-only|catalog-only> — reason"
  voclr: "<catalog-only expected — confirm>"
  acapellas4u: "<catalog-only expected — confirm>"
  lrclib: "<keep|cut — API surface + licensing of service>"
  musixmatch: "<keep|cut — free-tier reality>"
  paid_packs_registry: "<confirm public listing pages exist — per site one word>"
  sources: <n URLs cited>
```
