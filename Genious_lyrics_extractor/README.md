# Genius Lyrics Extractor

Integrated into the `toolshop` CLI as the `lyrics` subcommand.

## Quick Start

```bash
# Install lyrics extras
pip install -e ".[lyrics]"

# Set your Genius API token
echo "GENIUS_ACCESS_TOKEN=your_token_here" > .env

# Fetch lyrics by URL (no API token needed — uses HTML scraping)
toolshop lyrics fetch --url "https://genius.com/Maya-berovic-pravo-vreme-lyrics"

# Search by title/artist (requires valid API token)
toolshop lyrics search --title "Pravo Vreme" --artist "Maya Berovic"

# Analyze a previously fetched JSON
toolshop lyrics analyze --input lyrics_output/maya-berovic-pravo-vreme.json
```

## CLI Commands

| Command | Description | API Token Required |
|---------|-------------|-------------------|
| `lyrics fetch --url <url>` | Fetch lyrics from a Genius song page URL | No |
| `lyrics search --title <t> --artist <a>` | Search Genius API and fetch lyrics | Yes |
| `lyrics analyze --input <json>` | Word/line stats on fetched lyrics | No |

### Options

- `--outdir <path>` — output directory for JSON + TXT (default: `lyrics_output/`)
- `--strip-sections` — remove `[Chorus]`, `[Verse 1]`, etc. from clean lyrics
- `--report <path>` — save analysis report as JSON

## Architecture

```
toolshop/
├── genius_parser.py      # HTML → ParsedLyrics (BeautifulSoup, no network)
├── genius_adapter.py     # GeniusClient (API + HTML fetch) + RobotsPolicy
├── lyrics_analyzer.py    # Word/line stats (pure Python, no deps)
└── cli.py                # `lyrics` subparser + dispatch

tests/
├── test_genius_parser.py     # 9 tests
├── test_genius_adapter.py    # 11 tests
└── test_lyrics_analyzer.py   # 9 tests
```

### Design Decisions

- **Separation of concerns**: parser (no network), adapter (network + API), analyzer (pure stats)
- **Robots.txt compliance**: `RobotsPolicy` parses user-agent sections — only applies `User-agent: *` rules, ignores AI-bot-specific blocks (ChatGPT, ClaudeBot, etc.)
- **Artist extraction**: uses `og:title` meta tag (format: `Artist (Ft. ...) – Title`) since Genius removed `data-artist_id` anchors
- **Header junk stripping**: removes leading "N Contributors" and "Title Lyrics" echo lines from raw lyrics
- **Lazy imports**: `requests`, `beautifulsoup4` imported with try/except guard

## Categorization Rules

Songs are categorized by which tracked artists (Buba Corelli, Jala Brat, Coby) appear
in the primary artist or featured artists fields:

| Category | Rule |
|----------|------|
| `buba-solo` | Only Buba Corelli among tracked artists (primary or featured) |
| `jala-solo` | Only Jala Brat among tracked artists |
| `coby-solo` | Only Coby among tracked artists |
| `jala-buba-duo` | Both Jala Brat and Buba Corelli (no Coby) |
| `jala-buba-coby-trio` | All three tracked artists |
| `other-collab` | Multiple tracked artists not matching duo/trio (e.g. Jala+Coby without Buba) |

**Featured artists:** Songs by a tracked artist featuring non-tracked artists stay in the
tracked artist's solo bucket. The `featured_artists` field in the index records the non-tracked
collaborators. `other-collab` is reserved for combinations of multiple tracked artists that
don't match the duo or trio patterns.

## Index Rebuild

To rebuild `_index.json` and `_summary.md` from existing files on disk (no API calls):

```bash
python extract_artists.py --rebuild --outdir D:\MusicData\toolshop\lyrics\genius
```

The rebuild deduplicates by normalized (title, primary_artist) key, populates the `file`
field in each index entry, and writes a reconciliation summary.

## Output Format

### JSON (`{artist}-{title}.json`)
```json
{
  "title": "Pravo vreme",
  "artist": "Maya Berović",
  "url": "https://genius.com/...",
  "language": null,
  "raw_lyrics": "[Strofa 1: ...]\nZo-zore sviću...",
  "clean_lyrics": "Zo-zore sviću...",
  "sections": [{"label": "Strofa 1", "content": "..."}]
}
```

### TXT (`{artist}-{title}.txt`)
Clean lyrics text with section labels preserved.

## Sample Output

See `samples/` directory for a live fetch of Maya Berović — Pravo Vreme.

## Spec

See `intial_prompt.md` for the original implementation specification.

## Dependencies

- `requests>=2.28` — HTTP client
- `beautifulsoup4>=4.12` — HTML parsing
- `python-dotenv>=1.0` — .env loading (optional)
- `langdetect>=1.0` — language detection (optional)
