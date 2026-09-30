# Fixture provenance — tests/fixtures/lyrics_sources/

Per SPEC §7: committed fixtures come only from cleared sources, or are
synthetic structure with no sourced lyric text. Every file here is synthetic
(authored for the test suite) — no content was scraped from any source.

| File | Provenance | License |
|---|---|---|
| `registry_test.json` | Synthetic mini-registry, authored for tests (no lyric content) | CC0-1.0 |
| `robots_sample.txt` | Synthetic robots.txt, authored for tests | CC0-1.0 |
| `sample_pd_song.json` | Synthetic song-JSON v2; lyric text composed ad hoc for the test suite (NOT a sourced folk lyric — see `meta.fixture`) | CC0-1.0 |
| `ccmixter_query_page.json` | ccMixter Query API `f=json&dataview=default` page — **5 real upload rows** (upload_ids 47456, 33699, 41323, 31321, 22762; `files[]` arrays trimmed to 1 entry) + 5 synthetic metadata-only rows (upload_ids 900001–900005, `meta_fixture: true`, self-authored descriptions). Real rows are CC-BY-3.0 / CC0-1.0 uploads — lyric text cleared for release with attribution. TASL: "Homesick" by kizzylotus — https://ccmixter.org/files/kizzylotus/47456 — CC-BY-3.0; "The Right Voice" + "The Haunted Hotel" by SackJo22 — https://ccmixter.org/files/SackJo22/33699 + /41323 — CC-BY-3.0; "A blasted life" by Fireproof_Babies — https://ccmixter.org/files/Fireproof_Babies/31321 — CC0-1.0; "Breves dies hominis by Makemi" by remaxim — https://ccmixter.org/files/remaxim/22762 — CC0-1.0 | CC-BY-3.0 / CC0-1.0 / CC0 (synthetic rows) |
| `pdinfo_list_sample.html` | Synthetic HTML mimicking pdinfo.com `pd-song-list` markup (fabricated titles; V/C blocks contain invented placeholder text purely to prove the parser drops them — NOT sourced lyrics) | CC0-1.0 |
| `pdinfo_genre_sample.html` | Synthetic HTML mimicking `pd-music-genres` markup variant (`<span class="b">` year, `<i>music</i>` role tags; fabricated titles) | CC0-1.0 |
| `looperman_export_sample.json` | Synthetic hand-export rows — fabricated titles/uploaders, no real Looperman data; contains a `description`/`lyrics` field only to prove free text is refused | CC0-1.0 |
| `looperman_export_sample.csv` | Synthetic CSV hand-export — fabricated rows, no real Looperman data | CC0-1.0 |
| `jamendo_tracks_page.json` | Synthetic Jamendo v3 `/tracks` page — fabricated tracks/artists/lyrics (`meta_fixture: true`), real CC deed URLs only as license_ccurl values | CC0-1.0 |
| `jamendo_track_single.json` | Synthetic Jamendo v3 single-track response — fabricated | CC0-1.0 |
| `jamendo_rate_limit.json` | Synthetic Jamendo error envelope (`headers.code=6` rate-limit shape) | CC0-1.0 |
| `lrclib_get_response.json` | Synthetic LRCLIB record shape (`id/trackName/artistName/duration/instrumental/hasWordSync/plainLyrics/syncedLyrics/lyricsfile`) — gray-source rule: invented placeholder lyric strings only, NO real lyric text | CC0-1.0 |
| `lrclib_get_synced_only.json` | Synthetic LRCLIB record, synced-only variant | CC0-1.0 |
| `lrclib_instrumental.json` | Synthetic LRCLIB record, instrumental variant | CC0-1.0 |
| `lrclib_search_response.json` | Synthetic `/api/search` list — fabricated records | CC0-1.0 |
| `lrclib_seed.json` / `lrclib_seed.csv` | Synthetic seed files (artist/title/album/duration rows — fabricated) | CC0-1.0 |
| `hymnary_instances_export.csv` | Synthetic `in:instances` CSV export mimicking hymnary.org `&export=csv` columns — real PD title/author ("Amazing grace", John Newton; "O God our help", Isaac Watts) + fabricated boundary rows (TEST1931/GC2/NHCS1992-only) | CC0-1.0 (row metadata; hymn titles/attributions are public domain) |
| `hymnary_text_amazing_grace.html` | Synthetic `/text/` page mimicking authority-section markup; lyric text is "Amazing grace" (Newton, Olney Hymns 1779) — public domain | Public domain (markup authored for tests) |
| `hymnary_text_modern_rep.html` / `hymnary_text_1930.html` / `hymnary_text_1931.html` / `hymnary_text_nodate.html` | Synthetic `/text/` pages, fabricated verse text — boundary/gate cases only | CC0-1.0 |
| `sacred_texts_ch250_excerpt.html` | Synthetic SvelteKit page (`chapterContent.contentHtml`) carrying an excerpt of Child ballad 250 "Henry Martyn" — book is 1882–98, public domain; includes the transcription's real latin-1 mojibake shape | Public domain |
| `sacred_texts_no_chapter.html` / `sacred_texts_ch002_prose.html` | Synthetic page shells — no ballad text | CC0-1.0 |
| `mudcat_digitrad_sample.ask` | Synthetic askSam-shaped binary blob for the `mudcat_digitrad` parser — authored for tests (magic head + UI script fields + `\x1c`-separated records with `filename[` markers, provenance tails, chord brackets, cp1252 diacritics). ALL lyric text self-authored; copyright-flagged records carry fabricated notices only — no sourced lyric text, no real copyright content | CC0-1.0 |
| `mudcat_titles_sample.txt` | Synthetic DigiTrad `TITLES`-index-shaped two-column list — fabricated titles matching the .ask fixture | CC0-1.0 |
| `mw_sr_category_tree.json` | Synthetic MediaWiki `categorymembers` response tree shaped like sr.wikisource `Категорија:Народне песме` (fabricated pageids/titles; no lyric text) | CC0-1.0 |
| `mw_sr_parse_poem.json` | `action=parse&prop=wikitext` shape carrying a real PD Serbian folk-lyric stanza — opening of «Два бора и јела» (narodna pesma, sr.wikisource; anonymous folk text, published in Karadžić collections pre-1930) plus synthetic `{{Поезија}}`/`{{стих}}`/category markup | Public domain |
| `mw_sr_parse_nonpd.json` / `mw_sr_parse_ccsa.json` | Synthetic parse payloads with `CC-BY-NC` / `CC-BY-SA` license templates + invented verse lines, for the license-gate tests | CC0-1.0 |
| `mw_en_parse_ballad.json` | Synthetic en.wikisource page (`{{header}}` + `{{PD-US}}` + `<poem>`) carrying a real PD Child ballad #1B stanza («There were three sisters fair and bright», Child vol. I, 1882) | Public domain |
| `mw_en_parse_versions.json` | Synthetic `{{versions}}` disambiguation page (link list only, no lyric text) | CC0-1.0 |
| `pg_56625_excerpt.txt` | Excerpt shaped like PG #56625 «Songs of the West» (S. Baring-Gould, 1900/1928, PD): real first stanza of «By Chance It Was» + synthetic fixture stanzas (`FIXTURE`-marked) + PG header/footer markers | Public domain / CC0-1.0 |
| `pg_44969_excerpt.txt` | Excerpt shaped like PG #44969 Child vol. I: ballad 1 «Riddles Wisely Expounded» variants A+B — real PD stanza text (Child 1882) + synthetic apparatus lines | Public domain |
| `pg_27129_excerpt.txt` | Excerpt shaped like PG #27129 Elizabethan song-books: real PD texts «Come live with me» (Marlowe, 1599) + «There is a lady sweet and kind» (anon, 1607) with PG markers | Public domain |

Rule for future fixtures: real HTML/JSON samples may be committed **only**
from `release_ok=yes` tiers (`pd`, `cc0`, `cc-by` with attribution here);
gray-source fixtures must be synthetic structure with no lyric text
(megaplan F5; looperman lyric text is ToS-banned outright, R3 §1).
