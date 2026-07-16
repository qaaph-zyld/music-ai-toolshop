You can build this around Genius’s official API plus open‑source scraping libraries, with a clear separation between “fetch HTML” and “parse / analyze lyrics.” Below is a detailed, implementation‑oriented prompt you can give to an AI coder. [apis](https://apis.io/apis/genius/genius/)

***

## Goal and constraints

We want a small, open source, free tool that:

- Fetches lyrics from Genius song pages (example: the given Maya Berović URL). [stackoverflow](https://stackoverflow.com/questions/47400466/using-genius-api)
- Normalizes them into a clean text representation suitable for learning, NLP, and analysis.  
- Uses only open source libraries (Python preferred) and respects Genius API + robots.txt as much as possible. [apis](https://apis.io/apis/genius/genius/)
- Is designed so we can later plug in additional sources (other lyrics sites, local .txt, etc.).

Target example URL:  
`https://genius.com/Maya-berovic-pravo-vreme-lyrics` [stackoverflow](https://stackoverflow.com/questions/47400466/using-genius-api)

***

## Functional requirements

Ask the AI coder to implement:

1. **CLI tool / small library**

   - Language: Python 3.x.  
   - Entrypoint: a CLI command, e.g. `lyrics_fetch` with subcommands:  
     - `lyrics_fetch fetch --url <genius_song_url>`  
     - `lyrics_fetch search --title "Song" --artist "Artist"`  
     - `lyrics_fetch analyze --input <file_or_raw_text>`.  
   - Package structure: installable with `pip` (local), but runnable as a simple script too.

2. **Genius integration (API + HTML)**

   - Use Genius official API (search endpoint) when available to locate song pages. [apis](https://apis.io/apis/genius/genius/)
   - For the first version, assume we use:  
     - `https://api.genius.com/search?q=<query>` with Bearer token. [stackoverflow](https://stackoverflow.com/questions/47400466/using-genius-api)
   - For the target URL, support direct URL input so no search step is needed.

   - Implement a small `GeniusClient` class that can:  
     - `search_song(title, artist)` → returns canonical Genius URL, song ID, metadata.  
     - `get_song_page(url)` → returns HTML content for the song page.  
     - **Config**: `GENIUS_ACCESS_TOKEN` via env var or config file.

3. **HTML parsing of lyrics**

   - Use `requests` for HTTP and `beautifulsoup4` for parsing. [stackoverflow](https://stackoverflow.com/questions/47400466/using-genius-api)
   - Implement a `GeniusLyricsParser` that:  
     - Extracts lyrics from the relevant container; note that old examples use `div.lyrics`, but Genius now tends to use nested containers (e.g. `div[data-lyrics-container="true"]`). [stackoverflow](https://stackoverflow.com/questions/47400466/using-genius-api)
     - Joins multiple lyric containers into a single text, preserving line breaks.  
     - Removes extraneous annotations like `[Chorus]`, `[Verse 1]` only if configurable; default: preserve structure tags for analysis.  
     - Normalizes whitespace and encodings (UTF‑8, newlines).

   - Parser outputs:  
     ```json
     {
       "title": "...",
       "artist": "...",
       "url": "https://genius.com/...",
       "language": "sr" | "auto-detected",
       "raw_lyrics": "full text with tags",
       "clean_lyrics": "normalized text, optional removal of section labels",
       "sections": [
         { "label": "Verse 1", "content": "..." },
         { "label": "Chorus", "content": "..." }
       ]
     }
     ```

4. **Legal / robots.txt awareness**

   - Before fetching HTML, check `https://genius.com/robots.txt` and honor disallow rules. [stackoverflow](https://stackoverflow.com/questions/47400466/using-genius-api)
   - Implement a `RobotsPolicy` helper that:  
     - Fetches robots.txt once and caches.  
     - Provides `can_fetch(path)` check; if disallowed, return a clear error message.  
   - Keep request rate low: simple delay (e.g. 1–2 seconds between requests) and no massive crawling.

5. **Config and environment**

   - Single `config.yaml` or `.env` support:  
     - `GENIUS_ACCESS_TOKEN` (for search API). [apis](https://apis.io/apis/genius/genius/)
     - Optional proxy, timeout settings.  
   - All secrets loaded from env variables, no hard‑coding.  
   - CLI options to override config for token and proxy.

6. **Output formats**

   - Support saving results as:  
     - Plain `.txt` (just `clean_lyrics`).  
     - `.json` with full metadata (see structure above). [lyricsgenius.readthedocs](https://lyricsgenius.readthedocs.io/en/stable/reference/song.html)
   - Default behavior: print a short summary to stdout (title, artist, language, lines count) and store JSON + TXT in a configurable output directory.

7. **Analysis hooks (for learning/NLP)**

   For now, keep analysis basic but design for extensibility:

   - Implement a `LyricsAnalyzer` with basic features:  
     - Tokenization by lines and words.  
     - Frequency counts of words (normalized, case‑insensitive).  
     - Line length distribution (for rhythm analysis).  
   - Provide `lyrics_fetch analyze --input path/to/lyrics.json` which:  
     - Loads `clean_lyrics`.  
     - Prints stats (word count, unique words, most common n words, average line length).  
     - Optionally exports a small JSON report.

   This gives clear extension points to plug in more advanced models later (sentiment, rhyme schemes, syllable count, etc.).

***

## Technical stack and structure

Ask the coder to use:

- **Python libraries (all open source / free):**  
  - `requests` for HTTP. [stackoverflow](https://stackoverflow.com/questions/47400466/using-genius-api)
  - `beautifulsoup4` for HTML parsing. [stackoverflow](https://stackoverflow.com/questions/47400466/using-genius-api)
  - `python-dotenv` or `pydantic-settings` for env/config.  
  - `argparse` or `typer` for CLI.  
  - `langdetect` (optional) for language detection of lyrics.  

- **Project layout:**

  ```
  lyrics_tool/
    __init__.py
    cli.py
    config.py
    genius_client.py
    genius_parser.py
    robots.py
    analyzer.py
  ```

- **Core classes / functions:**

  - `Config` (loads env + config file).  
  - `GeniusClient` (API & HTML fetch).  
  - `GeniusLyricsParser` (HTML → structured lyrics).  
  - `RobotsPolicy` (robots.txt handling).  
  - `LyricsAnalyzer` (basic NLP stats).  
  - `main()` in `cli.py` exposing `fetch`, `search`, `analyze`.

***

## Detailed prompt to give to AI coder

You can paste this verbatim as the coding prompt:

> Build a Python 3 tool called `lyrics_tool` to fetch and analyze song lyrics from Genius.
> 
> Requirements:
> 
> 1. Provide a CLI with commands:
>    - `lyrics_fetch fetch --url <genius_song_url> --outdir <path>`  
>    - `lyrics_fetch search --title "Song" --artist "Artist" --outdir <path>`  
>    - `lyrics_fetch analyze --input <lyrics_json>`  
> 
> 2. Implement a `Config` that loads environment variables (via `.env` or OS env), including:
>    - `GENIUS_ACCESS_TOKEN` for Genius API search.  
>    - Optional `HTTP_PROXY`, `REQUEST_TIMEOUT`, `REQUEST_DELAY_SECONDS`.  
> 
> 3. Implement `GeniusClient`:
>    - Method `search_song(title, artist)`:
>      - Calls `https://api.genius.com/search?q=<title+artist>` with Bearer token in `Authorization` header.  
>      - Parses JSON response to find best match (first hit) and returns a small object with:
>        - `title`, `artist`, `url`, `id`.  
>    - Method `get_song_page(url)`:
>      - Validates robots.txt rules for Genius before fetching.  
>      - Uses `requests.get(url)` with timeout, delay between requests, error handling.  
>      - Returns HTML text.
> 
> 4. Implement `RobotsPolicy`:
>    - On initialization, fetch `https://genius.com/robots.txt`.  
>    - Parse disallowed paths.  
>    - Offer `can_fetch(path: str) -> bool`.  
>    - Use this in `get_song_page`; if path is disallowed, raise a user‑friendly error.
> 
> 5. Implement `GeniusLyricsParser`:
>    - Accept HTML and (optionally) song metadata.  
>    - Use BeautifulSoup to find all lyric containers.  
>      - Prefer `div[data-lyrics-container="true"]` (current Genius layout).  
>      - Fall back to older `div.lyrics` pattern if needed.  
>    - Extract text, preserving line breaks.  
>    - Build structured result:
>      ```python
>      class ParsedLyrics(BaseModel):
>          title: str
>          artist: str
>          url: str
>          language: Optional[str]
>          raw_lyrics: str
>          clean_lyrics: str
>          sections: List[Section]
> 
>      class Section(BaseModel):
>          label: Optional[str]
>          content: str
>      ```
>    - Provide a simple cleaning function:
>      - Normalize whitespace.  
>      - Optionally strip inline tags like `[Chorus]` if `strip_section_labels=True`.  
> 
> 6. Language detection (optional):
>    - Use `langdetect` on `clean_lyrics` to set `language` field.
> 
> 7. Output:
>    - When running `fetch` or `search`, write:
>      - JSON file with all fields of `ParsedLyrics`.  
>      - TXT file with just `clean_lyrics`.  
>    - Filenames: derive from `artist-title`, slugified.
> 
> 8. Implement `LyricsAnalyzer`:
>    - Function `analyze_text(lyrics: str) -> dict` with:
>      - `total_words`, `unique_words`, `top_20_words` (sorted by frequency).  
>      - `total_lines`, `avg_line_length`, `max_line_length`.  
>    - `lyrics_fetch analyze --input <lyrics_json>`:
>      - Load JSON.  
>      - Run analyzer on `clean_lyrics`.  
>      - Print a concise report to stdout and save the report as JSON.
> 
> 9. Coding style:
>    - Use type hints and dataclasses or Pydantic models.  
>    - Include basic exception handling with meaningful error messages.  
>    - Keep external dependencies minimal and open source only (`requests`, `beautifulsoup4`, `python-dotenv` or equivalent, `langdetect`, `typer` or `argparse`).
> 
> 10. Test using this sample URL:
>     - `https://genius.com/Maya-berovic-pravo-vreme-lyrics`  
>     - Verify that `fetch` produces a JSON + TXT where `clean_lyrics` contains the full lyrics text, properly separated into lines, and the analyzer command works on this output.

***

## One concrete usage example

Once the coder implements this:

1. Set env:  
   - `GENIUS_ACCESS_TOKEN=...`  
2. Run:  
   - `lyrics_fetch fetch --url "https://genius.com/Maya-berovic-pravo-vreme-lyrics" --outdir ./out`  
   - `lyrics_fetch analyze --input ./out/maya-berovic-pravo-vreme.json`  

You then get:

- A clean text file you can feed into any learning pipeline.  
- A JSON with structure and basic stats ready for further AI‑based analysis.