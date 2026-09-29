# R1 — CC-licensed lyric-text sources: ccMixter API surface + netlabel angle (lyrics-sources megaplan)

You are a **researcher** agent. Web research only — do not grep local files, do not run code, do not make implementation decisions. Every factual claim must carry a URL citation.

## Context

`Music-AI-Toolshop` has a lyrics corpus lane (`toolshop lyrics`, `Genious_lyrics_extractor/` folder) that today ingests only Genius text — copyrighted, study-only. The megaplan adds a **release-cleared tier**: sources whose lyric text is PD/CC-licensed so the user can actually record and release lines built from them. Your topic is the Creative Commons end of that roster.

ccMixter is the primary candidate: a CC remix community whose vocal stems ("pells") often carry lyric text in their descriptions, with per-item CC licenses. Secondary angle: Free Music Archive / Jamendo / netlabel tracks that publish lyrics under CC.

## Key questions

1. **ccMixter API surface**: document the query API — endpoints, parameters (search by tag/type "acapella"/"pell", user, license), response formats (XML/JSON), pagination, rate limits, whether an API key or attribution link-back is required. Cite the API docs directly.
2. **Lyric-text yield**: do pell pages/descriptions actually contain lyric text? Sample/browse ~50 recent or popular pells (or find documented examples) and estimate what fraction carry usable lyric text vs only a title/tags. Check whether descriptions are HTML with extractable text.
3. **Per-item license fields**: where does the license live in the API response/page — license URL, license name (CC-BY / CC-BY-NC / CC0 / PD), attribution requirements? Can license be resolved per item programmatically?
4. **Bulk/download policy**: does ccMixter permit automated fetching of metadata/text at ~1 req / 1.5 s? robots.txt status for `/api/`, pell pages.
5. **FMA/Jamendo/netlabel angle**: is there a parallel CC-music source where lyrics text is exposed (not just audio)? FMA's current state (it changed hands — what's actually queryable?), Jamendo API lyric fields, archive.org netlabel collections with lyric metadata.
6. **Wikimedia Commons**: does the "Audio files of vocal music" / spoken-word categories carry CC/PD material whose description pages include lyrics or transcriptions? MediaWiki API category traversal is assumed workable — confirm what's actually IN the categories at realistic yield.

## Deliverable

Write `D:\Projects\.workspace_archive\handoffs\researcher_lyrsrc_ccmixter_<yyyymmdd_hhmm>.md` containing:

- ccMixter API reference summary (endpoints, params, formats, limits, key requirements) with URLs
- Lyric-text yield estimate with the sampling method you used
- Per-item license resolution verdict (field name / XPath / JSON key — as concrete as the API allows)
- Policy verdict: `auto-fetch` vs `catalog-only` per source, one line of reasoning each
- FMA/Jamendo/netlabel viability — keep or cut, one line each
- Wikimedia Commons yield verdict
- End with this fenced contract:

```yaml
findings:
  ccmixter_api: "<endpoints/format/auth — one line>"
  lyric_text_yield: "<% of pells with usable lyric text + sample size>"
  license_per_item: "<field/URL path or 'page-only' or 'unresolvable'>"
  ccmixter_policy: "<auto-fetch|catalog-only> — reason"
  fma: "<keep|cut — reason>"
  jamendo: "<keep|cut — reason>"
  wikimedia_commons: "<keep|cut — reason>"
  sources: <n URLs cited>
```
