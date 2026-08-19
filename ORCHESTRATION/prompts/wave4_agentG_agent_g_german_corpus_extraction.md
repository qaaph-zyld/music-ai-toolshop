You are a IMPLEMENTER agent. Your task is: Extract German-language artist lyrics from Genius using the proven lyricsgenius extractor pattern. Save to data/toolshop/lyrics/genius_german/.

PROJECT ROOT: d:/Projects/Music-AI-Toolshop

INSTRUCTIONS:
1. Read AGENTS.md at d:\Projects\Music-AI-Toolshop\AGENTS.md for project rules.
2. Read the existing extractor pattern: d:\Projects\Music-AI-Toolshop\Genious_lyrics_extractor\extract_artists.py — understand the lyricsgenius API usage, artist name variant matching, and output format.
3. Read extract_batch2.py and extract_batch3.py for the batch extraction pattern (new script per batch, imports shared functions).
4. Create a new extraction script: d:\Projects\Music-AI-Toolshop\Genious_lyrics_extractor\extract_german.py — following the same pattern but targeting German drill/trap artists.
5. Target German artists (based on Wave 1 Agent B findings, or if unavailable, use this list): Apache 207, RAF Camora, Capital Bra, Shirin David, SSIO, Kollegah, Farid Bang, Bushido, Luciano, Ufo361, Bonez MC, Gzuz, 18Karat. Include name variants with umlauts.
6. Run the extraction script. Monitor for API token expiry (tokens expire frequently — pre-validate with direct HTTP request).
7. Document: artist count, track count per artist (solo vs featured), any extraction issues.
8. Write findings to ORCHESTRATION/wave4/agent_g_handoff.md with sections: Artists Targeted, Extraction Results, Track Counts, Issues Encountered, Files Created.

SCOPE: Genious_lyrics_extractor/ + data/
OUTPUT: Write your findings to: ORCHESTRATION/wave4/agent_g_handoff.md

CONSTRAINTS:
- Use the venv Python: .venv\Scripts\python.exe
- Do NOT modify existing source files. New files only.
- Genius API token is in Genious_lyrics_extractor/.env as Genious_API='...'
- Follow the existing extractor pattern exactly (extract_artists.py, extract_batch2.py).
- German artist names must include umlaut variants (ä/ae, ö/oe, ü/ue, ß/ss).
- Save extracted lyrics to data/toolshop/lyrics/genius_german/ (new directory).
- If API token is expired or extraction fails, document the error and list the target artists for manual extraction.

CONTEXT BUDGET: 200k

HANDOFF: When done, return the file path and a 1-2 sentence summary.
