You are a IMPLEMENTER agent. Your task is: Set up German phonemization using phonemizer + espeak-ng, and create a minimal toolshop/phonemizer_de.py wrapper module with TDD tests.

PROJECT ROOT: d:/Projects/Music-AI-Toolshop

INSTRUCTIONS:
1. Read AGENTS.md at d:\Projects\Music-AI-Toolshop\AGENTS.md for project rules.
2. Check if phonemizer is installed: .venv\Scripts\python.exe -c "import phonemizer; print(phonemizer.__version__)"
3. Check if espeak-ng German voice is available: look in data/toolshop/espeak-ng/ for German voice data (espeak-ng-data/voices/de).
4. Read the current rhyme mining approach: d:\Projects\Music-AI-Toolshop\toolshop\rhyme_miner.py — understand vowel_skeleton() and _word_skeleton() functions. German needs real phonemization because spelling doesn't reliably indicate pronunciation (e.g., 'ei' = /aɪ/, 'ie' = /iː/, 'eu' = /ɔɪ/, 'sch' = /ʃ/, 'ch' = /x/ or /ç/).
5. Write tests first: d:\Projects\Music-AI-Toolshop\tests\test_phonemizer_de.py — test phonemization of common German words (e.g., 'ich' -> /ɪç/, 'auch' -> /aʊx/, 'sein' -> /zaɪn/, 'licht' -> /lɪçt/). Test vowel skeleton extraction from phonemized output. Use function-level imports so module is importable without phonemizer installed.
6. Implement d:\Projects\Music-AI-Toolshop\toolshop\phonemizer_de.py: phonemize_german(text) -> str (returns IPA), german_vowel_skeleton(word) -> str (extracts vowel pattern from IPA for rhyme matching), and a combined function that phonemizes then extracts skeleton.
7. Run tests: .venv\Scripts\python.exe -m pytest tests/test_phonemizer_de.py -v
8. If phonemizer or German voice data is not available, document the setup steps needed and create the module with stubs that raise ImportError with helpful messages.
9. Write findings to ORCHESTRATION/wave4/agent_h_handoff.md with sections: Setup Status, Module Created, Test Results, phonemizer-de vs Serbian vowel skeleton comparison, Setup Steps for User.

SCOPE: toolshop/ + data/ + tests/
OUTPUT: Write your findings to: ORCHESTRATION/wave4/agent_h_handoff.md

CONSTRAINTS:
- Use the venv Python: .venv\Scripts\python.exe
- Follow TDD: write tests first, then implement.
- espeak-ng is installed at data/toolshop/espeak-ng/ — check if German voice data is available.
- Do NOT install packages without checking if they're already available.
- Function-level imports for optional deps (same pattern as similarity_retriever.py).
- Keep the module minimal — just phonemize German text and extract vowel skeletons for rhyme mining.

CONTEXT BUDGET: 200k

HANDOFF: When done, return the file path and a 1-2 sentence summary.
