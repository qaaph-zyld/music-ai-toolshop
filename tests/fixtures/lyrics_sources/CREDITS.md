# Fixture provenance — tests/fixtures/lyrics_sources/

Per SPEC §7: committed fixtures come only from cleared sources, or are
synthetic structure with no sourced lyric text. Every file here is synthetic
(authored for the test suite) — no content was scraped from any source.

| File | Provenance | License |
|---|---|---|
| `registry_test.json` | Synthetic mini-registry, authored for tests (no lyric content) | CC0-1.0 |
| `robots_sample.txt` | Synthetic robots.txt, authored for tests | CC0-1.0 |
| `sample_pd_song.json` | Synthetic song-JSON v2; lyric text composed ad hoc for the test suite (NOT a sourced folk lyric — see `meta.fixture`) | CC0-1.0 |

Rule for future fixtures: real HTML/JSON samples may be committed **only**
from `release_ok=yes` tiers (`pd`, `cc0`, `cc-by` with attribution here);
gray-source fixtures must be synthetic structure with no lyric text
(megaplan F5; looperman lyric text is ToS-banned outright, R3 §1).
