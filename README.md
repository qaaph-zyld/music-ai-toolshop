# music-ai-toolshop

CLI toolshop to orchestrate:

- Suno library sync and inspection
- BPM / key analysis (planned)
- YouTube scraping (planned)
- YouTube summarization (planned)
- Track reverse engineering (planned)

This repo is a thin orchestration layer over your existing specialist repos
(`Suno`, `suno_extractor`, `bpm_key_recognize`, `yt_scraper`, `yt_summarize`,
`track_reverse_engineering`).

## Installation

From the `music-ai-toolshop` folder:

```bash
pip install -e .
```

This installs a `toolshop` CLI entrypoint.

## Usage

### Suno tools

Sync liked clips into a local library (reusing your existing bulk downloader):

```bash
toolshop suno sync-liked --output-dir path/to/suno_library
```

List tracks from the local Suno library by scanning metadata JSON files:

```bash
toolshop suno list --root path/to/suno_library
```

By default both commands assume a `suno_library` directory relative to the
current working directory.

### Repository layout

- `toolshop/cli.py` – CLI entrypoint and argument parsing
- `toolshop/suno_adapter.py` – thin wrapper around the existing Suno bulk
  downloader and local library listing
- `toolshop/bpm_adapter.py` – placeholder adapter for `bpm_key_recognize`
- `toolshop/yt_scraper_adapter.py` – placeholder adapter for `yt_scraper`
- `toolshop/yt_summarizer_adapter.py` – placeholder adapter for `yt_summarize`
- `toolshop/reverse_engineering_adapter.py` – placeholder adapter for
  `track_reverse_engineering`

For now, only the `suno` subcommands are wired; the other adapters are
stubs that will be connected to their respective repos later.
