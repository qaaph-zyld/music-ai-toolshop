# R2 — Public-domain lyric-text sources: Wikisource (sr+en), Gutenberg, PDInfo, folk archives (lyrics-sources megaplan)

You are a **researcher** agent. Web research only — do not grep local files, do not run code, do not make implementation decisions. Every factual claim must carry a URL citation.

## Context

`Music-AI-Toolshop` lyrics corpus lane wants a **release-cleared tier** — public-domain lyric text the user can legally record and release. The single most interesting candidate for this project is **sr.wikisource**: Vuk Karadžić's folk-poem collections and related PD Serbian folk material are public domain, phonetically spelled, and would feed the existing Serbian rhyme engine (`lyrics.db` rimer) with zero copyright exposure. English pre-1930 songbooks (Wikisource, Project Gutenberg, hymnal archives) are the second arm.

## Key questions

1. **sr.wikisource traversal**: what categories/pages hold PD Serbian folk poems/songs (Karadžić's "Srpske narodne pjesme" and successors)? Via MediaWiki API (`sr.wikisource.org/w/api.php`) — which category tree gives bulk access, roughly how many items, what does a page's text look like (clean stanzas vs editorial scaffolding)? Cite API/category URLs.
2. **en.wikisource PD songbooks**: categories holding pre-1930 song lyrics (e.g. folk-song collections, hymnals) — expected yield, text cleanliness.
3. **MediaWiki API etiquette**: rate limits, `maxlag`, User-Agent policy, whether scraping page-parse output is within API norms at ~1 req/1.5 s. Cite the API etiquette/robots docs.
4. **Project Gutenberg**: which song/poem collections carry lyric text usable as lines (not sheet-music scans)? Plain-text e-books vs HTML; the `gutenberg.org` robot/terms position for text download (it's PD content — confirm mirrors/cache policy).
5. **PDInfo structure**: is pdinfo.com's PD song list usable as a *title index* (titles aren't copyrightable) to drive Wikisource/Gutenberg lookups? Page structure, list sizes.
6. **Folk-lyric archives**: mudcat.org Digital Tradition, hymnary.org, contemplator, similar — PD folk lyric text, fetchability, licensing of the site layer vs the content.

## Deliverable

Write `D:\Projects\.workspace_archive\handoffs\researcher_lyrsrc_pdtext_<yyyymmdd_hhmm>.md` containing:

- Per-source: access method (API endpoint / page scrape), traversal recipe (category names or query), expected yield, text cleanliness, licensing basis (why PD), robots/terms status
- sr corpus spotlight: concrete category/page list for Karadžić material + realistic item count
- Ranked keep/cut recommendation per source
- End with this fenced contract:

```yaml
findings:
  sr_wikisource: "<keep|cut> — traversal method + yield estimate"
  en_wikisource: "<keep|cut — reason>"
  gutenberg: "<keep|cut — usable collections>"
  pdinfo: "<keep|cut — role: title index vs text source>"
  folk_archives: "<keep|cut each — one line>"
  api_etiquette: "<rate limit / UA / maxlag requirements>"
  sources: <n URLs cited>
```
