Copy/paste this into Windsurf AI (or any VS Code AI coder) and tell it to **generate the full project**:

```text
You are a senior engineer. Build a Windows-friendly, open-source-only Serbian rhyme suggester that works offline inside VS Code/Windsurf terminal and via a simple local UI.

GOAL
Create a tool that suggests Serbian words that rhyme with whatever the user types or pastes (lyrics). Serbian only for now. Must support both Latin + Cyrillic input. Must be 100% open-source dependencies + open dictionary.

TECH STACK (keep it simple on Windows)
- Python 3.10+ (venv)
- Streamlit for UI
- SrbAI (Python) for Cyrillic<->Latin transliteration
- Use Serbian Hunspell dictionary wordlist (download script) as the word corpus:
  Prefer downloading the ZIP from devbase.net: https://devbase.net/dict-sr/hunspell-sr-20130715.zip
  After extraction, use sr-Latn.dic and/or sr.dic as the word list.

PROJECT OUTPUT
Generate a complete repo with this exact structure and file contents:

rimer-sr/
  app.py
  cli.py
  rhyme_engine.py
  requirements.txt
  README.md
  .vscode/
    settings.json
    launch.json
  scripts/
    setup.ps1
    run.ps1
    fetch_dict.ps1
  data/                (created by fetch script; do not commit large dict files)
  tests/
    test_rhyme_engine.py

FUNCTIONAL REQUIREMENTS
1) UI (Streamlit)
   - Title: "RimerSR (offline)"
   - Tab 1: "Single word"
       * input box accepts Latin or Cyrillic
       * controls:
         - rhyme tightness slider: 1..3 (approx syllables from the end)
         - max results slider: 10..200
         - checkbox: "Show Cyrillic output too"
       * output: list of rhyming words, ranked
   - Tab 2: "Paste lyrics"
       * textarea
       * extract last word of each non-empty line
       * for each last word, show rhymes underneath (same controls apply)
   - Must be fast: cache dictionary load + index build.

2) CLI
   - `python cli.py word --syllables 2 --max 50`
   - `python cli.py --file lyrics.txt --syllables 2 --max 50`
   - Output in a clean, readable format.

3) Dictionary handling
   - `scripts/fetch_dict.ps1`:
       * downloads the ZIP to data/ if missing
       * expands it into data/dict/
       * ensures sr-Latn.dic exists (and optionally sr.dic)
   - Tool must work offline AFTER the initial download.
   - The engine must accept a custom dictionary path via env var or UI field.

4) Rhyme algorithm (practical, Serbian-focused)
   - Normalize input:
       * transliterate Cyrillic->Latin using SrbAI
       * lowercase
       * keep only Serbian letters a-z + č ć đ š ž (strip punctuation/dashes)
   - Treat digraphs as single sounds for matching:
       * nj, lj, dž
     (collapse them to single placeholders before keying)
   - Compute a “rhyme key” by taking substring starting at the Nth vowel from the end (N = syllables slider).
     Vowels: a e i o u
     If no vowels, fallback to full word.
   - Index all words by rhyme_key for fast lookup.
   - Ranking:
       * exclude exact match
       * sort primarily by closeness of length to query
       * then alphabetically
     (keep it deterministic)

5) Quality safeguards
   - Don’t crash on missing dict: show clear error + how to run fetch script
   - Unit tests cover:
       * normalization Cyrillic/Latin
       * digraph collapsing
       * rhyme_key correctness on a few Serbian examples
       * find_rhymes returns deterministic ordering

WINDOWS UX REQUIREMENTS
- `scripts/setup.ps1`:
    * creates .venv
    * activates and installs requirements
    * runs fetch_dict.ps1
- `scripts/run.ps1`:
    * activates venv
    * runs: `streamlit run app.py`
- README must include copy-paste commands for PowerShell, and explain how to run inside VS Code/Windsurf terminal.
- Include note about licenses and attribution in README (dictionary source + SrbAI).

CODING NOTES
- Keep code clean and modular: rhyme_engine.py should be importable by both app.py and cli.py
- Avoid heavy deps; keep requirements minimal.
- Use Streamlit caching (@st.cache_data) for dictionary load/index.
- Use pathlib, zipfile, and standard libraries where possible.

DELIVERABLE
Output the full file contents for every file listed above (except large dictionary files), ready for me to paste into my workspace and run immediately.
```

This approach is built on two genuinely open sources: the Serbian Hunspell dictionary (tri-licensed GPL/LGPL/MPL with CC BY-SA option) ([GitHub][1]) and SrbAI (MIT) for transliteration ([GitHub][2]). Streamlit’s install/venv flow is well-documented and Windows-friendly. ([docs.streamlit.io][3])

[1]: https://github.com/grakic/hunspell-sr "GitHub - grakic/hunspell-sr: Serbian (Cyrillic and Latin) Hunspell Spelling Dictionary"
[2]: https://github.com/Serbian-AI-Society/SrbAI "GitHub - Serbian-AI-Society/SrbAI: Python library for Serbian Natural language processing (NLP)"
[3]: https://docs.streamlit.io/get-started/installation/command-line "Install Streamlit using command line - Streamlit Docs"
