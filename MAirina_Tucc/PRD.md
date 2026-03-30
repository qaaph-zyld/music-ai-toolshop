# Product Requirements Document (PRD)
**Project Name:** MAirina Tucc (formerly RimerSR)
**Vision:** A personal, professional-grade AI creative writing suite tailored for Serbian songwriting, evolving from a rhyme dictionary into an end-to-end lyric and music production assistant.
**Target Audience:** Solo developer / Serbian songwriter (Personal Use).

---

## 1. Core Objectives
1. **Idea to Song:** Provide a structured environment where raw concepts can be expanded into fully structured lyrics (verses, choruses, bridges).
2. **Professional Accuracy:** Advanced linguistic analysis for Serbian (perfect rhymes, syllable counting, rhythm/meter analysis).
3. **Deep Customization:** Total control over rhyme constraints, structure rules, and AI generation parameters.
4. **AI Music Integration (Long-term):** Bridge the gap between written lyrics and audio generation/music production workflows.

## 2. Phased Roadmap

### Phase 1: Advanced Linguistic Foundation (The "Pro Rimer")
*Current state: Basic rhyme finding using a dictionary.*
* **Syllable & Meter Counting:** Algorithm to accurately count syllables in Serbian words to help maintain rhythm.
* **Perfect vs. Slant Rhymes:** Upgrade the rhyme engine to distinguish between exact phonetic matches and assonance/consonance.
* **Contextual Synonyms & Metaphors:** Integration with a Serbian thesaurus or WordNet to find semantically related words that fit a specific meter.

### Phase 2: The Songwriter's IDE (Structure & Ideation)
* **Project/Song Management:** Save, load, and version-control individual songs.
* **Structure Builder:** Canvas for organizing song parts (Verse 1, Pre-Chorus, Chorus).
* **LLM Integration for Ideation:** Connect to a local (Ollama/Llama.cpp) or remote LLM (OpenAI/Anthropic) to expand on "raw ideas" in Serbian.
    * *Example feature:* "Generate 4 lines about [topic] ending with [specific rhyme scheme AABB]."
* **Interactive Rhyme Suggestions:** Highlight a word in the editor to instantly see context-aware rhymes and synonyms in a side panel.

### Phase 3: AI Music Production Integration (The "Suite")
* **Prompt Engineering for Audio:** Automatically format finished lyrics into optimal prompts for AI music generators (e.g., Suno, Udio).
* **MIDI/Audio Sketching:** Potential integration with local models to generate melody sketches based on the syllable meter of the written lyrics.
* **Export Workflows:** Export lyrics with chords, or export metadata that DAWs (Ableton, FL Studio) can utilize.

---

## 3. Proposed Tech Stack Upgrade

Since the goal has shifted to a highly customized, personal "IDE for Songwriting," we should transition the architecture to support more complex UI and local AI integrations.

### Backend (Python - Data & AI layer)
* **Framework:** FastAPI (Better suited for API endpoints than Streamlit, handles async LLM calls well).
* **NLP/Linguistics:** 
  * `srbai` (existing) + custom phonetic parsers.
  * Local LLM bindings (`langchain` or `llama-index`) for interacting with local models (e.g., Mistral/Llama3 fine-tuned on Serbian) for privacy and zero cost.
* **Database:** SQLite / SQLAlchemy (for storing song drafts, versions, and vocabulary lists locally).

### Frontend (User Interface)
* *Option A (Modern Web):* **React / Next.js** with TailwindCSS. Allows for a highly interactive text editor (like Notion or Google Docs) with drag-and-drop song sections and floating rhyme tooltips.
* *Option B (Desktop Native):* **PyQt / PySide6** or **Tauri** if you want a strict desktop application feel without a browser.
* *Recommendation:* **Web UI (Next.js/React)**. It offers the most flexibility for building a rich text editor and can be easily wrapped in Electron/Tauri later.

### AI Integrations
* **Text Generation:** OpenAI API (GPT-4o) or Local LLMs via Ollama.
* **Audio Generation:** APIs for Suno/Udio, or local Audiocraft/MusicGen deployments.

---

## 4. Next Immediate Steps (Action Plan)
1. **Restructure Project:** Move the current engine into a modular Python package.
2. **Upgrade NLP Engine:** Implement syllable counting for Serbian words (vowel counting: a, e, i, o, u, and syllabic 'r').
3. **Draft the API:** Create a FastAPI wrapper around the rhyme engine.
4. **Prototype the Editor UI:** Build a basic React/HTML frontend to replace Streamlit, focusing on a split-pane view (Editor on left, Rhymes/AI tools on right).
