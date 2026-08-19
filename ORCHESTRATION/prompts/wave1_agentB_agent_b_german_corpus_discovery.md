You are a EXPLORER agent. Your task is: Discover German-language content in the CrhymeTV catalogue and assess feasibility of German corpus expansion via the proven lyricsgenius extractor.

PROJECT ROOT: d:/Projects/Music-AI-Toolshop

INSTRUCTIONS:
1. Read AGENTS.md at d:\Projects\Music-AI-Toolshop\AGENTS.md for project rules.
2. Read the CrhymeTV catalogue generator: d:\Projects\Music-AI-Toolshop\generate_crhymetv_catalogue.py — understand what metadata it stores (artist names, track titles, language info if any).
3. Read the catalogue output at d:\Projects\Music-AI-Toolshop\results\crhymetv_re\ — look for catalogue.md or catalogue.json. List all artist names found.
4. Identify which artists/tracks are German-language. CrhymeTV is a Balkan trap/drill channel — German tracks may be from German drill artists featured on the channel.
5. Read the extractor scripts: d:\Projects\Music-AI-Toolshop\Genious_lyrics_extractor\extract_artists.py and extract_batch2.py and extract_batch3.py — understand the pattern for adding new artists.
6. Read the roadmap L6 section: d:\Projects\Music-AI-Toolshop\docs\superpowers\plans\2026-07-21-lyric-intelligence-roadmap-L3-L6.md lines 73-78 — it mentions '222 CrhymeTV artists' and 'phonemizer-de'.
7. Assess: How many German artists can be identified from the CrhymeTV catalogue? If few/no German artists in CrhymeTV, identify known German drill/trap artists that could be searched on Genius instead (e.g., Apache 207, RAF Camora, Capital Bra, Shirin David, SSIO, Kollegah, Farid Bang).
8. Document the lyricsgenius extractor pattern: what would need to change to support German artists? (Name variants, diacritics, Unicode handling for German umlauts ä/ö/ü/ß).
9. Assess phonemizer-de requirements: German is NOT phonetic (unlike Serbian which uses vowel skeletons). Read d:\Projects\Music-AI-Toolshop\toolshop\rhyme_miner.py to understand the current vowel-skeleton approach and why it won't work for German.
10. Check if espeak-ng German voice data is available alongside the existing installation at data/toolshop/espeak-ng/.
11. Write all findings to ORCHESTRATION/wave1/agent_b_handoff.md with sections: CrhymeTV German Artists Found, Extractor Compatibility Assessment, phonemizer-de Requirements, Recommended German Artist List, Risks & Mitigations.

SCOPE: results/crhymetv_re/ + generate_crhymetv_catalogue.py + Genious_lyrics_extractor/
OUTPUT: Write your findings to: ORCHESTRATION/wave1/agent_b_handoff.md

CONSTRAINTS:
- Read-only. Do NOT modify any files except your own handoff output file.
- Do NOT make any API calls or network requests.
- Do NOT install any packages.

CONTEXT BUDGET: 200k

HANDOFF: When done, return the file path and a 1-2 sentence summary.
