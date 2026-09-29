# R4 — Standards recon: license metadata conventions for lyric corpora (lyrics-sources megaplan)

You are a **researcher** agent. Web research only — do not grep local files, do not run code, do not make implementation decisions. Every factual claim must carry a URL citation. This is the smallest research wave — one focused question cluster.

## Context

The megaplan will store license metadata per lyric item (`license_tier`, `license_ref`, `release_ok` on song rows; per-item license fields in `_index.json` catalog entries). Before the W0 spec freezes the schema, check how existing open lyric-corpus / music-metadata projects encode licensing per item so we match convention rather than inventing one.

## Key questions

1. **OSS lyric-corpus projects**: how do 2-3 maintained projects that aggregate lyrics from multiple sources record per-item license/source? (e.g. lyric-fetcher libraries with source plugins, lyrics corpus datasets on Hugging Face/GitHub, MusicBrainz-style metadata models.) What field names/shapes recur — SPDX license identifiers, license URLs, provenance chains?
2. **SPDX + CC IDs**: confirm the canonical short identifiers we'd map to (`CC-BY-4.0`, `CC-BY-NC-4.0`, `CC0-1.0`, `public-domain` conventions) and whether CC itself publishes machine-readable license codes per item.
3. **Catalog interchange**: is there an existing JSON Lines / CSV convention for "media item + license + source-url" catalogs we should mirror (e.g. Openverse's catalog — they index CC media at scale; what columns/fields does their catalog carry)?
4. **Attribution-text capture**: for CC-BY items, what attribution fields do projects store (author, title, source URL, license URL) — the minimum set to emit a correct credit line later.

## Deliverable

Write `D:\Projects\.workspace_archive\handoffs\researcher_lyrsrc_standards_<yyyymmdd_hhmm>.md` containing:

- Convention summary with the 2-3 projects examined + their license-field shapes
- Recommended field names for our schema (map to SPDX/CC IDs where they fit)
- Openverse-style catalog fields worth borrowing
- End with this fenced contract:

```yaml
findings:
  projects_examined: "<names>"
  license_field_convention: "<recommended field names + id system>"
  attribution_minimum: "<fields needed for a correct CC-BY credit line>"
  schema_sufficiency: "<our JSON+index shape suffices | needs <change>>"
  sources: <n URLs cited>
```
