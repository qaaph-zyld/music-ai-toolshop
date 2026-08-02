# Existing Apps Analysis & Gap Handoff

> **Research deliverable for the German learning desktop app project (Tauri 2 + React + TS)**
> Generated: 2026-08-02

---

## Table of Contents

1. [Open-Source App Deep-Dive Analysis](#1-open-source-app-deep-dive-analysis)
2. [Commercial Apps Feature Comparison](#2-commercial-apps-feature-comparison)
3. [Feature Comparison Matrix](#3-feature-comparison-matrix)
4. [Reusable Components & Projects Table](#4-reusable-components--projects-table)
5. [SRS Implementation Comparison](#5-srs-implementation-comparison)
6. [Gap Analysis](#6-gap-analysis)
7. [Recommended MVP Feature Scope](#7-recommended-mvp-feature-scope)
8. [Phase 1 / 2 / 3 Feature Breakdown](#8-phase-1--2--3-feature-breakdown)
9. [Unique Value Proposition](#9-unique-value-proposition)
10. [Next Steps for Orchestrator](#10-next-steps-for-orchestrator)

---

## 1. Open-Source App Deep-Dive Analysis

### 1.1 DeutschPath

| Attribute | Detail |
|---|---|
| **Repo** | [github.com/sjelodari/DeutschPath](https://github.com/sjelodari/DeutschPath) |
| **Stars** | 10 |
| **Tech Stack** | Next.js (frontend) + FastAPI/Python (backend) + SQLite |
| **Architecture** | Full-stack web app, single-user local-first, SQLAlchemy ORM, auto-migration on startup (no Alembic) |
| **SRS Algorithm** | SM-2 (SuperMemo 2) — same method as Anki, implemented in Python backend |
| **Content Sources** | User-uploaded PDFs (pdfplumber for text, Gemini Vision OCR for scanned), Gemini 2.5 Flash for analysis |
| **AI Integration** | Google Gemini 2.5 Flash (text analysis, chat, OCR, grammar, writing), Gemini TTS for voice |
| **Key Features** | PDF book reader with word/phrase highlighting, grammar rule detection, vocab SRS, A1→C2 grammar roadmap (15 rules), conversation scenarios (10 role-plays), writing practice with diff-view correction, 16 supported languages |
| **Data Model** | Single SQLite file: vocabulary, progress, grammar mastery, uploaded PDFs. `CREATE TABLE IF NOT EXISTS` + `_migrate_sqlite()` on startup |
| **UI/UX** | Web-based, page-based reader with sidebar analysis, chat panel for AI tutor |
| **License** | **Dual: AGPL v3 + Commercial** — free for personal/educational/non-commercial; commercial use requires separate license |
| **Reusable** | SM-2 implementation pattern, grammar roadmap structure (A1→C2 with 15 rules), PDF reading + word highlight UX, writing diff-view concept. **Cannot fork directly** due to AGPL + commercial dual license, but architecture and UX patterns are referenceable |
| **Missing** | No offline TTS (requires Gemini API), no listening comprehension beyond voice chat, no structured grammar exercises (only AI-corrected), no cloze/fill-in-blank exercises, Electron/web only (not a true desktop app) |

### 1.2 FlexiLingo Desk

| Attribute | Detail |
|---|---|
| **Repo** | [github.com/flexilingo/Flexi-Desk](https://github.com/flexilingo/Flexi-Desk) |
| **Stars** | 5 |
| **Tech Stack** | **Tauri 2 + Rust** (backend) + **React 19** (frontend) + SQLite + Zustand/Immer + Tailwind CSS v4 |
| **Architecture** | Offline-first desktop app, modular feature modules (each module has Rust backend + React frontend), 214 unit tests, in-memory SQLite for tests |
| **SRS Algorithm** | **Three algorithms: Leitner, SM-2, and FSRS** — user-selectable, all implemented in Rust (`src-tauri/src/srs/`) |
| **Content Sources** | PodcastIndex + RSS feeds, Whisper transcription, spaCy NLP for CEFR subtitles |
| **AI Integration** | GPT-4o-mini (tutor conversations), Whisper (transcription), Ollama (local LLM support) |
| **Key Features** | Podcast player with transcription, SRS review (3 algorithms), dashboard with streaks/stats, live caption, AI tutor (63 scenarios), deck hub (flashcard creation + Anki export), 10 languages |
| **Module Pattern** | Each feature: `src-tauri/src/{module}/` (mod.rs, types.rs, logic) + `src-tauri/src/commands/{module}.rs` (IPC) + `src/pages/{module}/` (React page, store, types) |
| **Data Model** | SQLite with schema migrations in `db/schema.rs`, IDs as `lower(hex(randomblob(16)))` — 32-char hex strings |
| **UI/UX** | Sage/Terracotta/Olive palette, Radix UI primitives, lucide-react icons, Zustand+Immer stores |
| **License** | **AGPL v3** — copyleft, modifications must be open-sourced |
| **Reusable** | **Most architecturally relevant project for our app** — same tech stack (Tauri 2 + Rust + React + SQLite). Module pattern, SRS implementation (Leitner/SM-2/FSRS in Rust), Zustand store pattern, schema migration approach, IPC command conventions. **Cannot fork due to AGPL** but can study architecture closely |
| **Missing** | Reading module is "planned" not built, no grammar lessons/exercises, no German-specific content, podcast-focused (not reading-focused), AI tutor is central (we're skipping AI conversation) |

### 1.3 Danki

| Attribute | Detail |
|---|---|
| **Repo** | [github.com/udaysidhu99/danki](https://github.com/udaysidhu99/danki) |
| **Stars** | N/A (low) |
| **Tech Stack** | Cross-platform desktop app (macOS + Windows), likely Electron or similar |
| **SRS Algorithm** | None built-in — relies on **AnkiConnect** to push cards to Anki, which handles SRS |
| **Content Sources** | 20,000-word offline dictionary, Google Gemini or OpenAI for enrichment, edge-tts for audio |
| **AI Integration** | Google Gemini or OpenAI (auto-detected from API key) |
| **Key Features** | German vocab → Anki pipeline, article/plural/conjugation auto-generation, 3 example sentences per word, offline TTS audio, verb conjugation tables, phrase support, AnkiConnect integration |
| **Data Model** | No persistent storage — generates and pushes to Anki |
| **UI/UX** | Simple GUI: word input, deck selection, settings toggles |
| **License** | **Not explicitly stated** (no LICENSE file visible) |
| **Reusable** | AnkiConnect integration pattern, offline dictionary approach, edge-tts for German audio, card field schema (base_d, base_e, artikel_d, plural_d, conjugations, sentences + audio) |
| **Missing** | No SRS of its own, no grammar lessons, no reading/listening comprehension, no structured curriculum, requires Anki to be useful |

### 1.4 babblr

| Attribute | Detail |
|---|---|
| **Repo** | [github.com/pkuppens/babblr](https://github.com/pkuppens/babblr) |
| **Stars** | 0 |
| **Tech Stack** | Electron + React + TypeScript + Vite (frontend), FastAPI + Python (backend), SQLite |
| **SRS Algorithm** | None — focused on conversational practice, not spaced repetition |
| **Content Sources** | AI-generated conversations by topic (business, travel, shopping, restaurants) |
| **AI Integration** | Anthropic Claude (conversation), OpenAI Whisper (STT), Edge TTS (TTS) |
| **Key Features** | Natural voice conversation with AI, Whisper transcription, contextual error correction, vocabulary tracking, adaptive CEFR difficulty (A1-C2), topic-based learning, conversation history |
| **Data Model** | SQLite for conversations and vocabulary |
| **UI/UX** | Desktop app, chat-style interface, voice recording |
| **License** | **AGPL v3** |
| **Reusable** | CEFR-based adaptive prompt system (templates per level), vocabulary tracking from conversations, conversation history storage pattern |
| **Missing** | No SRS, no reading/listening comprehension, no grammar lessons, no vocab drills, entirely AI-conversation focused (opposite of our app's goals), Electron (heavy, not Tauri) |

### 1.5 SprachNinja

| Attribute | Detail |
|---|---|
| **Repo** | [github.com/vpk11/SprachNinja](https://github.com/vpk11/SprachNinja) |
| **Stars** | N/A (low) |
| **Tech Stack** | Android, Kotlin, Jetpack Compose, Material 3, Room Database, Retrofit, MVVM + Clean Architecture |
| **SRS Algorithm** | None — uses AI-generated questions with level progression |
| **Content Sources** | Google Gemini API generates questions dynamically |
| **AI Integration** | Google Gemini (BYOK — bring your own key) |
| **Key Features** | AI-powered question generation, CEFR A1→B2 curriculum, 3 practice modes (vocab multiple-choice, grammar fill-in-blank, translation), local-first data storage, EncryptedSharedPreferences for API key |
| **Data Model** | Room Database (SQLite on Android), local-first |
| **UI/UX** | Mobile-first, Material 3, onboarding flow, settings screen |
| **License** | **MIT** — most permissive, freely reusable |
| **Reusable** | CEFR A1→B2 structure, 3 practice modes (vocab MC, grammar fill-blank, translation), Clean Architecture pattern (adaptable to our app), BYOK concept. **MIT license allows code reference/adaptation** |
| **Missing** | Android-only (Kotlin, not our stack), no SRS, no reading/listening comprehension, no structured grammar lessons, AI-dependent (no offline content), no desktop support |

### 1.6 German Vocabulary Manager

| Attribute | Detail |
|---|---|
| **Repo** | [github.com/AlirezaDa-jc/german-vocabulary-manager](https://github.com/AlirezaDa-jc/german-vocabulary-manager) |
| **Stars** | 0 |
| **Tech Stack** | Python + Excel workbook (openpyxl), Windows GUI (packaged as .exe) |
| **SRS Algorithm** | None — vocabulary storage and enrichment only |
| **Content Sources** | German Wiktionary (primary), Wikimedia Commons (audio), Tatoeba (sentences), OpenThesaurus (synonyms), Google Translator (fallback) |
| **AI Integration** | None — all free public APIs, no API key needed |
| **Key Features** | Type a word → autofill article, plural, conjugation, declension, adjective comparison, IPA, example sentences, synonyms/antonyms, pronunciation audio. Statistics sheet. No paid services |
| **Data Model** | Excel workbook (`vocabulary.xlsx`): Word sheet, grammar reference, verb conjugations, adjective comparisons, statistics, settings |
| **UI/UX** | 4-button GUI (create/reset, autofill, open workbook, open folder) |
| **License** | **MIT** — freely reusable |
| **Reusable** | **Wiktionary data pipeline is gold** — article, plural, conjugation, declension, IPA, examples, synonyms, audio all from free sources. The `dictionary.py` + `parsers.py` pattern for Wiktionary parsing is directly adaptable. Tatoeba sentence integration. **MIT license allows code reuse** |
| **Missing** | No SRS, no grammar lessons, no reading/listening, Excel-based (not a real app), no spaced review, no structured curriculum, online-only for enrichment |

### 1.7 deutsch-ai-tutor

| Attribute | Detail |
|---|---|
| **Repo** | [github.com/Dev-Adnani/deutsch-ai-tutor](https://github.com/Dev-Adnani/deutsch-ai-tutor) |
| **Stars** | N/A (low) |
| **Tech Stack** | FastAPI + SQLAlchemy + ChromaDB (vector DB) + JWT auth |
| **SRS Algorithm** | SM-2 — implemented in `spaced_repetition.py`, quality ratings 0-5 |
| **Content Sources** | User-uploaded PDFs/text → OpenAI extracts vocabulary, grammar rules, topics |
| **AI Integration** | OpenAI API (content extraction, quiz generation) |
| **Key Features** | Concept-based learning (study before practice), adaptive quiz generation (mistake-driven: 40% weak items, 30% SRS, 30% random), concept-scoped quizzes, multiple question types (translation, fill-blank, article selection, MC), progress dashboard, semantic search (ChromaDB) |
| **Data Model** | SQLAlchemy ORM, JWT auth, ChromaDB for vector embeddings |
| **UI/UX** | Web-based, study-first flow (learn → mark studied → practice → review) |
| **License** | **MIT** — freely reusable |
| **Reusable** | SM-2 implementation in Python (`spaced_repetition.py`), mistake-tracking system (categorize errors by type: article_error, translation_error), adaptive quiz weighting (40/30/30), concept-scoped quiz pattern, study-first flow UX. **MIT license allows code reuse** |
| **Missing** | No reading/listening comprehension, no native desktop app, requires OpenAI API, no offline content, web-only, auth system unnecessary for personal app |

### 1.8 DeutschQuest

| Attribute | Detail |
|---|---|
| **Repo** | [github.com/NickEvans4130/DeutschQuest](https://github.com/NickEvans4130/DeutschQuest) |
| **Stars** | 0 |
| **Tech Stack** | TypeScript (95.9%), React, Zustand stores, Web-based |
| **SRS Algorithm** | SM-2 — implemented in `lib/srs.ts` |
| **Content Sources** | Google Gemini API for daily content generation, 3 static fallback sessions for offline |
| **AI Integration** | Google Gemini (content pipeline) |
| **Key Features** | RPG character progression (4 classes: Sprachkrieger, Wanderer, Gelehrter, Bayer), 10-minute daily session (5 modules: news → flashcards → dialect → flashcards → summary), XP/leveling/streaks, Bavarian dialect exposure, word bank with due-date tracking, Anki export (APKG) |
| **Data Model** | Zustand stores: usePlayerStore (XP, stats, level, class), useSessionStore (active session, history), useWordBankStore (SRS word bank), useStreakStore (streak + shield) |
| **UI/UX** | RPG-themed, character card, XP bar, session router, progress stepper, bottom nav |
| **License** | **Not explicitly stated** (no LICENSE file visible) |
| **Reusable** | SM-2 in TypeScript (`lib/srs.ts`), RPG progression system design, daily session structure (news + flashcard + dialect + review), XP calculation and leveling thresholds, streak with shield mechanic, word bank with due-date tracking, Anki APKG export |
| **Missing** | No grammar lessons, no structured curriculum, AI-dependent for daily content, no reading comprehension (only news digests), no listening comprehension, web-only, Bavarian dialect is niche |

---

## 2. Commercial Apps Feature Comparison

### 2.1 Duolingo

| Aspect | Analysis |
|---|---|
| **Core Features** | Gamified lessons (3-5 min), skill tree progression, streaks, XP/leagues, hearts (lives), daily quests, monthly quests, achievements |
| **Lesson Structure** | 8-10 exercise types per lesson (matching, sentence construction, typing, speaking, listening), progressive difficulty within lesson (easy→hard→easy ending), immediate feedback |
| **Gamification** | Streaks with freeze, leaderboards/leagues, gems currency, XP boosts, achievements (Personal Records + Awards), push notifications with emotional triggers |
| **Relevant to Us** | Lesson structure pattern (varied exercise types, progressive difficulty, end on success), streak mechanic (simple, motivating), daily goal setting, bite-sized sessions |
| **Avoid** | Hearts/lives system (punishes learning), aggressive push notifications, leaderboard competition (personal app), energy/gem monetization, over-gamification that prioritizes engagement over learning depth |

### 2.2 Anki

| Aspect | Analysis |
|---|---|
| **Core Features** | SM-2 and FSRS algorithms, customizable card types (basic, cloze, image occlusion), deck organization, tags, filtered decks, add-ons ecosystem, cross-platform sync |
| **SRS** | SM-2 (legacy) with ease factor, learning steps, graduating interval; FSRS (modern) with DSR memory model, desired retention (default 90%), parameter optimization from review history |
| **Customization** | Card templates (HTML/CSS), note types with arbitrary fields, deck options per preset, add-ons (Python), review sorting options |
| **Relevant to Us** | FSRS algorithm (use `fsrs-rs` crate), card type flexibility (vocab cards, cloze cards, grammar cards), deck/tag organization, filtered review sessions, review statistics |
| **Avoid** | Complex card template editor (too technical for personal app), add-on system (unnecessary scope), sync infrastructure (we're offline-first), UI complexity |

### 2.3 Babbel

| Aspect | Analysis |
|---|---|
| **Core Features** | Structured lessons (10-15 min), explicit grammar instruction, speech recognition, review manager (SRS), cultural context, native speaker audio, AI dialogue partner |
| **Lesson Structure** | Dialogue-first → vocabulary intro → fill-in-blank → spelling → typing in context → speech recognition. CEFR-aligned, L1-tailored content |
| **Grammar** | Explicit explanations within lessons (unlike Duolingo's implicit approach), English comparisons |
| **Relevant to Us** | Explicit grammar instruction pattern, dialogue-first lesson structure, review manager (SRS for vocab + phrases), L1-tailored explanations, CEFR alignment, lesson = practical dialogue + grammar breakdown |
| **Avoid** | Speech recognition (complex, not core for us), AI dialogue partner, subscription model, limited content ceiling (B1/B2) |

### 2.4 Clozemaster

| Aspect | Analysis |
|---|---|
| **Core Features** | Cloze deletion exercises (fill-in-blank sentences), SRS (4 intervals: 1d, 10d, 30d, 180d), Fluency Fast Track (frequency-ordered), listening mode, grammar challenges, cloze reading |
| **Method** | Sentences with missing word → type or multiple-choice → audio after answer. Mastery score 0-100% (25% per correct, reset on wrong) |
| **Relevant to Us** | Cloze deletion exercise format (excellent for grammar + vocab in context), sentence-based learning (not isolated words), frequency-ordered vocabulary, listening mode (hear sentence → fill blank), grammar challenges by concept |
| **Avoid** | Retro game UI, lack of structure (no learning path), no grammar explanations, thin sentences sometimes, not for beginners |

### 2.5 Seedlang

| Aspect | Analysis |
|---|---|
| **Core Features** | Video flashcards with native speakers, sentence cards with video/audio/translation/discussion, lesson tree (A1-B2), custom review decks, vocab/gender/plural/conjugation trainers, trivia games |
| **Method** | ~300 handcrafted video lessons with stories, each sentence is a card with video + translation + discussion, add sentences to personal review decks with SRS |
| **Relevant to Us** | Sentence card concept (sentence + translation + grammar info one click away), SRS for sentences (not just words), grammar info always one click away, gender/plural/conjugation trainers as separate drill types |
| **Avoid** | Video production (expensive, not feasible for personal app), no offline mode, recording without feedback, subscription model |

### 2.6 Memrise

| Aspect | Analysis |
|---|---|
| **Core Features** | SRS vocabulary review, native speaker video clips ("Learn With Locals"), mems (mnemonic devices), gamification (streaks, points, leaderboards), AI conversation practice |
| **Method** | Show word + video of native speaker → quiz → SRS review. Community-created courses (now reduced) |
| **Relevant to Us** | Native speaker audio/video for pronunciation (we can use edge-tts or pre-recorded audio), mems/mnemonics concept (user-created memory hooks), SRS for vocabulary, wide course variety |
| **Avoid** | AI conversation feature, community course marketplace, gamification overload, expensive Pro tier, removal of community features |

### 2.7 Nemo German

| Aspect | Analysis |
|---|---|
| **Core Features** | Phrase-based flashcards, native speaker audio (all offline), Speech Studio (record + compare pronunciation), customizable word/phrase selection, Review Mode, progress tracking per word |
| **Method** | Not lesson-based — pick up/put down throughout day. Frequency-ordered word lists. Foundation pack adds directions, food, shopping, travel, sentence patterns |
| **Relevant to Us** | **Fully offline** (all audio downloaded to device), phrase-based approach (not just single words), frequency-ordered vocabulary, customizable learning content (skip/select words), Review Mode for spaced repetition, progress tracking per item, doubles as phrasebook/translator |
| **Avoid** | iOS-only, Speech Studio (complex), one-time purchase model (not relevant), no grammar instruction, no structured curriculum |

---

## 3. Feature Comparison Matrix

### Open-Source Apps

| Feature | DeutschPath | FlexiLingo Desk | Danki | babblr | SprachNinja | German Vocab Manager | deutsch-ai-tutor | DeutschQuest |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Tech Stack** | Next.js+FastAPI | Tauri 2+Rust+React | Desktop GUI | Electron+FastAPI | Android/Kotlin | Python+Excel | FastAPI+ChromaDB | React+TS |
| **Offline-first** | Partial | Yes | Partial | Partial | Yes (data) | Partial | No | Partial |
| **SRS** | SM-2 | Leitner+SM-2+FSRS | None (Anki) | None | None | None | SM-2 | SM-2 |
| **Vocab/Flashcards** | Yes | Yes | Yes (→Anki) | Track only | Yes (MC) | Yes (Excel) | Yes | Yes |
| **Grammar Lessons** | Roadmap (A1-C2) | No | No | No | Fill-blank | Reference data | Concept-based | No |
| **Grammar Exercises** | AI-corrected | No | No | No | Fill-blank | No | Quizzes | No |
| **Reading Comprehension** | PDF reader | Planned | No | No | No | No | PDF upload | News digests |
| **Listening Comprehension** | Voice chat | Podcasts | TTS audio | Voice conv. | No | Audio clips | No | Dialect audio |
| **Cloze Deletion** | No | No | No | No | No | No | Fill-blank | No |
| **AI Conversation** | Yes (Gemini) | Yes (GPT-4o-mini) | No | Yes (Claude) | Yes (Gemini) | No | Yes (OpenAI) | Yes (Gemini) |
| **CEFR Aligned** | A1-C2 | No | No | A1-C2 | A1-B2 | No | No | A2-B2 |
| **Gamification** | No | Streaks | No | No | No | Stats | Dashboard | RPG+XP+streaks |
| **German-Specific** | Yes | No (10 langs) | Yes | No (5 langs) | Yes | Yes | Yes | Yes |
| **Desktop App** | Web | Yes (Tauri) | Yes | Yes (Electron) | No (Android) | Yes (Windows) | Web | Web |
| **License** | AGPL+Commercial | AGPL-3 | Unstated | AGPL-3 | MIT | MIT | MIT | Unstated |

### Commercial Apps

| Feature | Duolingo | Anki | Babbel | Clozemaster | Seedlang | Memrise | Nemo German |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **SRS** | Custom | SM-2/FSRS | Custom | Custom (4-tier) | Custom | Custom | Custom |
| **Vocab/Flashcards** | Yes | Yes (flexible) | Yes | Yes (sentences) | Yes | Yes | Yes (phrases) |
| **Grammar Lessons** | Implicit | No | Explicit | No | Some | Minimal | No |
| **Grammar Exercises** | Yes | No | Yes | Grammar challenges | Some | No | No |
| **Reading** | Minimal | No | Some | Cloze reading | No | No | No |
| **Listening** | Yes (TTS) | Audio cards | Native audio | Listening mode | Native video | Native video | Native audio |
| **Cloze Deletion** | No | Yes (card type) | Fill-blank | Core method | No | No | No |
| **Offline** | Partial | Yes | Yes (download) | Pro only | No | Pro only | Yes (full) |
| **Gamification** | Heavy | None | Light | Light | Light | Medium | None |
| **CEFR Aligned** | Partial | No | Yes | No | A1-B2 | Partial | No |
| **German-Specific** | No (35+ langs) | No | No (13 langs) | No (50+ langs) | **Yes** | No (35 langs) | **Yes** |
| **Price** | Free/$6.99 mo | Free/$25 yr | $6.95 mo | $8 mo | ~$5 mo | $8.49 mo | $14.99 one-time |

---

## 4. Reusable Components & Projects Table

| Project / Component | License | Tech | What's Reusable | How to Use |
|---|---|---|---|---|
| **fsrs-rs** ([open-spaced-repetition/fsrs-rs](https://github.com/open-spaced-repetition/fsrs-rs)) | **BSD** | Rust | FSRS algorithm (scheduler + optimizer) | `cargo add fsrs` — directly include as dependency. Best-in-class SRS for Rust |
| **sm-2-rs** ([open-spaced-repetition/sm-2-rs](https://github.com/open-spaced-repetition/sm-2-rs)) | **BSD** (likely) | Rust | SM-2 algorithm | `cargo add sm-2` — alternative to FSRS if simpler algorithm needed |
| **FlexiLingo Desk** ([flexilingo/Flexi-Desk](https://github.com/flexilingo/Flexi-Desk)) | **AGPL-3** | Tauri 2+Rust+React | Architecture pattern, module structure, SRS implementation (Leitner/SM-2/FSRS in Rust), Zustand+Immer store pattern, schema migration approach, IPC conventions | **Study architecture, don't fork** (AGPL). Reference for Tauri 2 project structure |
| **SprachNinja** ([vpk11/SprachNinja](https://github.com/vpk11/SprachNinja)) | **MIT** | Kotlin/Android | CEFR A1→B2 structure, 3 practice modes (vocab MC, grammar fill-blank, translation), Clean Architecture pattern | **Can adapt code patterns** (MIT). Practice mode designs transferable to TS |
| **German Vocabulary Manager** ([AlirezaDa-jc/german-vocabulary-manager](https://github.com/AlirezaDa-jc/german-vocabulary-manager)) | **MIT** | Python | Wiktionary data pipeline (article, plural, conjugation, declension, IPA, examples, synonyms, audio), Tatoeba sentence integration, Wikimedia Commons audio | **Can adapt data pipeline** (MIT). Port Python parsers to Rust or use as CLI tool for content generation |
| **deutsch-ai-tutor** ([Dev-Adnani/deutsch-ai-tutor](https://github.com/Dev-Adnani/deutsch-ai-tutor)) | **MIT** | Python/FastAPI | SM-2 implementation, mistake-tracking system (error categorization), adaptive quiz weighting (40/30/30), study-first flow UX | **Can reference code** (MIT). SM-2 and mistake-tracking patterns adaptable |
| **DeutschQuest** ([NickEvans4130/DeutschQuest](https://github.com/NickEvans4130/DeutschQuest)) | **Unstated** | TypeScript/React | SM-2 in TS (`lib/srs.ts`), RPG progression design, daily session structure, XP/leveling, streak with shield, Anki APKG export | **Reference only** (no license). SM-2 TS implementation and session structure are design references |
| **DeutschPath** ([sjelodari/DeutschPath](https://github.com/sjelodari/DeutschPath)) | **AGPL+Commercial** | Next.js+FastAPI | Grammar roadmap (A1→C2, 15 rules), PDF reading UX, writing diff-view concept | **Reference only** (dual license). Grammar roadmap structure is design reference |
| **Danki** ([udaysidhu99/danki](https://github.com/udaysidhu99/danki)) | **Unstated** | Desktop | AnkiConnect integration pattern, card field schema, edge-tts for German audio | **Reference only** (no license). Card field schema and edge-tts pattern useful |
| **edge-tts** | **MIT** | Python/CLI | Free German TTS (KatjaNeural voice) | Use as CLI tool or Python script to pre-generate audio for vocabulary |
| **Wiktionary data** | **CC BY-SA** | Data | German word data (article, plural, conjugation, IPA, examples) | Free to use with attribution. Parse via API or XML dumps |
| **Tatoeba sentences** | **CC BY 2.0 FR** | Data | Example sentences in German with translations | Free to use with attribution. API available |
| **OpenSubtitles frequency list** | **CC BY-SA** | Data | German word frequency rankings | Free to use. Basis for frequency-ordered vocabulary |

---

## 5. SRS Implementation Comparison

### 5.1 DeutschPath — SM-2

- **Implementation**: Python backend (`words.py`), SQLAlchemy models
- **Algorithm**: Standard SM-2 with quality ratings 0-5
- **Scheduling**: Interval = previous_interval × ease_factor; ease_factor adjusted by quality rating
- **Data stored per card**: ease factor, interval, next review date, review history
- **Limitations**: No parameter optimization, no desired retention control, ease hell risk (repeated failures tank ease factor)
- **Verdict**: Basic but functional. Good reference for minimal SM-2 implementation

### 5.2 FlexiLingo Desk — Leitner + SM-2 + FSRS

- **Implementation**: Rust (`src-tauri/src/srs/` — `leitner.rs`, `sm2.rs`, `fsrs.rs`, `strategy.rs`, `types.rs`)
- **Algorithm**: User-selectable between three algorithms
- **Leitner**: Box-based system (Box 1: daily, Box 2: 3 days, Box 3: 7 days, Box 4: 14 days, Box 5: 30 days). Correct → advance box, wrong → reset to Box 1
- **SM-2**: Standard implementation with ease factor, 4-button rating (Again/Hard/Good/Easy)
- **FSRS**: Full FSRS implementation with DSR memory model (Difficulty, Stability, Retrievability), desired retention, parameter optimization
- **Data stored per card**: Algorithm-specific state (Leitner box number / SM-2 ease+interval / FSRS DSR values), review logs
- **Testing**: 214 unit tests covering all SRS algorithms
- **Verdict**: **Most comprehensive SRS implementation in Rust.** The modular strategy pattern (pluggable algorithms) is excellent architecture. Directly relevant to our Tauri 2 + Rust stack

### 5.3 Anki — SM-2 (legacy) + FSRS (modern)

- **SM-2 (legacy)**: Ease factor (default 2.5), 4-button review (Again/Hard/Good/Easy), learning steps (configurable), graduating interval, easy bonus, interval modifier, maximum interval. Ease decreases by 20pp on Again, 15pp on Hard. "Ease hell" problem when ease drops too low
- **FSRS (modern, since Anki 23.10)**: Three Component Model of Memory — Difficulty (D), Stability (S), Retrievability (R). Per-card memory state. Desired retention (default 90%, configurable per preset). Parameter optimization from review history (1000+ reviews for optimal, works with default params otherwise). FSRS-6 adds initial stability optimization per rating, long interval handling for mature cards
- **Key advantage of FSRS**: Targets specific retention level, fewer reviews for same retention vs SM-2, better handling of delayed reviews, no ease hell
- **Verdict**: **FSRS is the gold standard.** Use `fsrs-rs` crate (BSD-licensed) for our app

### 5.4 deutsch-ai-tutor — SM-2

- **Implementation**: Python (`spaced_repetition.py`)
- **Algorithm**: Standard SM-2, quality ratings 0-5
- **Integration**: Combined with mistake tracking — 40% weak items, 30% SRS due, 30% random in quiz generation
- **Verdict**: Interesting quiz composition pattern (weighted selection), but basic SM-2

### 5.5 DeutschQuest — SM-2

- **Implementation**: TypeScript (`lib/srs.ts`)
- **Algorithm**: SM-2 with due-date tracking in Zustand store
- **Integration**: Word bank store with due dates, flashcard flip animation + SM-2 rating
- **Verdict**: Clean TS implementation, good for reference if implementing SRS in frontend

### 5.6 Recommended SRS Approach for Our App

| Content Type | Recommended Algorithm | Rationale |
|---|---|---|
| **Vocabulary** | **FSRS** (via `fsrs-rs` crate) | Best retention per review, parameter optimization, handles delayed reviews well. Vocab is high-volume, benefits most from efficient scheduling |
| **Grammar rules** | **FSRS** with separate preset | Grammar needs deeper processing — higher desired retention (95%) and longer intervals. Separate preset allows different parameters |
| **Reading comprehension** | **No SRS** — linear progression | Reading is about exposure and flow, not memorization. Track completion, not scheduling. Re-read optionally |
| **Listening comprehension** | **SM-2 or Leitner** (simpler) | Listening clips are reviewed for comprehension, not memorized. Simpler algorithm reduces complexity. Can use FSRS with lower retention target (85%) |

**Architecture recommendation**: Use `fsrs-rs` crate as the primary SRS engine. Implement a strategy pattern (like FlexiLingo) allowing per-deck algorithm selection. Store FSRS memory state (D, S, R) per card in SQLite. Allow per-preset desired retention configuration.

**Should different content types use different SRS parameters?** Yes:
- Vocab cards: 90% desired retention (default)
- Grammar cards: 95% desired retention (higher stakes — wrong grammar = miscommunication)
- Listening cards: 85% desired retention (lower stakes — exposure is the goal)
- Use FSRS presets (like Anki) to group decks with similar parameters

---

## 6. Gap Analysis

### 6.1 Commonly Missing Features Across Existing Apps

| Gap | Affected Apps | Impact |
|---|---|---|
| **Structured grammar curriculum** | Most apps — only DeutschPath has a roadmap, Babbel has explicit grammar, most skip it | Learners lack systematic grammar foundation |
| **Grammar exercises (non-AI)** | Only SprachNinja and deutsch-ai-tutor have fill-blank; most rely on AI | Can't practice grammar offline without AI dependency |
| **Reading comprehension with exercises** | Only DeutschPath has PDF reading; none have structured reading exercises | No way to practice reading at appropriate CEFR level |
| **Listening comprehension (non-conversation)** | FlexiLingo (podcasts), Seedlang (videos), Clozemaster (listening mode) — but none are German-specific + offline + structured | Gap in structured listening practice |
| **Offline-first desktop (Tauri)** | Only FlexiLingo uses Tauri 2 — but it's podcast-focused, not German-specific | No German-specific offline desktop app exists |
| **Integrated vocab + grammar + reading + listening** | No single app covers all four. DeutschPath is closest (reading + vocab + grammar, but AI-dependent) | Learners use 3-4 apps simultaneously |
| **Content without AI dependency** | Most apps require Gemini/OpenAI/Claude. Only German Vocab Manager uses free sources (Wiktionary) | Can't learn offline without API keys |
| **Cloze deletion for grammar in context** | Only Clozemaster does this well (commercial). No open-source German app has it | Best exercise format for grammar is absent from OSS |

### 6.2 What Existing Apps Do Poorly (That We Can Do Better)

| Problem | Who Does It Poorly | Our Opportunity |
|---|---|---|
| **AI dependency** | DeutschPath, SprachNinja, DeutschQuest, babblr, deutsch-ai-tutor — all require external AI APIs | Pre-generate content offline using Wiktionary + Tatoeba + frequency lists. No API key needed |
| **No integrated learning path** | Most apps focus on one area (vocab OR grammar OR reading) | Combine vocab/SRS + grammar lessons + exercises + reading + listening in one app |
| **Over-gamification** | Duolingo, DeutschQuest — gamification can overshadow learning | Light gamification (streaks, progress bars) without hearts/leagues/notifications |
| **No German-specific offline desktop app** | FlexiLingo is multi-language + podcast-focused; Nemo is iOS-only; Anki is generic | Build specifically for German learning on desktop, offline-first |
| **Poor grammar instruction** | Most apps either skip grammar (Duolingo implicit) or require AI (DeutschPath) | Static grammar lessons with structured exercises, no AI needed |
| **No frequency-ordered curriculum** | Most apps have ad-hoc content ordering | Use OpenSubtitles/Goethe frequency lists to order vocabulary A1→C1 |
| **Subscription walls** | Babbel, Clozemaster, Seedlang, Memrise — all require payment | Free, personal, no subscription, no data leaves the machine |

### 6.3 Unique Value Proposition

> **The only offline-first, German-specific desktop app that integrates vocabulary SRS, structured grammar lessons with exercises, and reading + listening comprehension — with no AI dependency, no subscription, and no data leaving your machine.**

Key differentiators:
- **Offline-first Tauri 2 desktop app** — lightweight (~10MB vs Electron's ~150MB), native performance
- **German-specific** — not a generic language tool; content, grammar, and exercises tailored to German
- **No AI required** — all content pre-generated from free sources (Wiktionary, Tatoeba, frequency lists, Goethe word lists)
- **Integrated four-pillar approach** — vocab/SRS + grammar + reading + listening in one app (no other app does this)
- **FSRS-powered SRS** — state-of-the-art spaced repetition via `fsrs-rs` crate
- **Personal & private** — single SQLite file, no accounts, no sync, no telemetry
- **No subscription** — one-time build, yours forever

### 6.4 Forkable / Referenceable Projects

| Project | Can Fork? | Why / Why Not |
|---|---|---|
| **fsrs-rs** | **Yes (BSD)** | Direct dependency — `cargo add fsrs` |
| **sm-2-rs** | **Yes (BSD)** | Alternative SRS if needed |
| **SprachNinja** | **Yes (MIT)** | Adapt practice mode designs (Kotlin→TS) |
| **German Vocabulary Manager** | **Yes (MIT)** | Port Wiktionary pipeline to Rust or use as CLI tool |
| **deutsch-ai-tutor** | **Yes (MIT)** | Reference SM-2 + mistake tracking patterns |
| **FlexiLingo Desk** | **No (AGPL-3)** | Study architecture, don't fork — AGPL requires open-sourcing modifications |
| **DeutschPath** | **No (AGPL+Commercial)** | Reference only — dual license restricts use |
| **babblr** | **No (AGPL-3)** | Reference only |
| **Danki** | **No (no license)** | No license = all rights reserved. Reference only |
| **DeutschQuest** | **No (no license)** | No license = all rights reserved. Reference only |

### 6.5 Tauri 2 + React Language Learning Apps for Architecture Study

**FlexiLingo Desk** is the only Tauri 2 + React language learning app found. It is the primary architectural reference:

- **Module pattern**: Each feature = Rust backend module + React frontend module
- **IPC**: `#[tauri::command]` functions, snake_case, `Result<T, String>` returns
- **State**: Zustand + Immer stores per module
- **DB**: SQLite via rusqlite, schema in `db/schema.rs`, hex string IDs
- **Styling**: Tailwind CSS v4, Radix UI primitives, lucide-react icons
- **Testing**: 214 Rust unit tests, in-memory SQLite

---

## 7. Recommended MVP Feature Scope

### MVP Definition
The minimum viable product should deliver a **complete vocab/SRS experience** with a **basic grammar lesson reader** — enough to be a daily-use tool that replaces Anki for German learning.

### MVP Must-Have

| Feature | Description | Priority |
|---|---|---|
| **Vocabulary SRS (FSRS)** | Add words, review with FSRS scheduling, 4-button rating (Again/Hard/Good/Easy), due-date queue | Critical |
| **Word enrichment** | Auto-fill article, plural, IPA, translation, example sentences from Wiktionary + Tatoeba | Critical |
| **Audio pronunciation** | Pre-generated TTS audio (edge-tts) for each word | High |
| **Deck organization** | Group words by CEFR level (A1-C1) or custom decks, tag system | High |
| **Basic statistics** | Streak, reviews/day, retention rate, cards mature/young/new | High |
| **Grammar lesson reader** | Static markdown-based grammar lessons (A1→B1), structured by topic, with examples | Medium |
| **CEFR-structured vocab** | Pre-loaded frequency-ordered word lists tagged by Goethe/CEFR level | Medium |
| **Offline TTS playback** | Play pre-generated audio during review | Medium |
| **Dark mode** | Theme toggle | Low |

### MVP Explicitly Skip

| Feature | Why Skip |
|---|---|
| AI conversation / tutor | Out of scope — no AI feature |
| Speech recognition | Complex, not core to vocab/grammar/reading |
| Podcast player | FlexiLingo already does this well |
| Writing practice with AI correction | Requires AI |
| RPG gamification | Over-engineering for personal tool |
| Cloud sync | Offline-first, no accounts |
| Multi-language support | German-specific only |
| AnkiConnect integration | We have our own SRS |
| Video content | Production cost too high |
| Leaderboards / social | Personal app |

---

## 8. Phase 1 / 2 / 3 Feature Breakdown

### Phase 1: Core Vocab + SRS (MVP)

**Goal**: Replace Anki for German vocabulary learning with an offline desktop app

| # | Feature | Description | Est. Effort |
|---|---|---|---|
| 1.1 | **Tauri 2 project scaffolding** | Tauri 2 + React + TS + Tailwind + Zustand, module pattern (reference FlexiLingo) | S |
| 1.2 | **SQLite schema + migrations** | Tables: decks, cards, review_logs, fsrs_states, settings. Migration system in Rust | S |
| 1.3 | **FSRS engine integration** | `cargo add fsrs`, implement scheduler service in Rust, Tauri IPC commands | M |
| 1.4 | **Vocabulary card model** | Fields: word, article, plural, IPA, translation, example_sentences, audio_path, cefr_level, tags | S |
| 1.5 | **Review session UI** | Card display (front/back), 4-button rating, flip animation, session progress, session summary | M |
| 1.6 | **Deck management UI** | Create/edit decks, card list view, tag filtering, CEFR-level filtering | M |
| 1.7 | **Word enrichment pipeline** | Wiktionary API integration (port from German Vocab Manager's Python parsers to Rust, or use Python CLI tool for pre-generation) | L |
| 1.8 | **Audio generation** | edge-tts CLI script to pre-generate German audio for all words | S |
| 1.9 | **Pre-loaded A1-B2 vocabulary** | Import frequency-ordered word lists with Goethe/CEFR tags (from OpenSubtitles + Goethe word lists) | M |
| 1.10 | **Dashboard / statistics** | Streak counter, reviews today, retention rate, card counts (new/young/mature), simple chart | M |
| 1.11 | **Settings** | FSRS desired retention, theme, daily review limit, new cards/day limit | S |
| 1.12 | **Dark mode** | Tailwind dark mode toggle | S |

### Phase 2: Grammar Lessons + Exercises

**Goal**: Add structured grammar learning with offline exercises

| # | Feature | Description | Est. Effort |
|---|---|---|---|
| 2.1 | **Grammar lesson content** | Write/curate grammar lessons as structured markdown (A1→B1): articles, cases, declensions, tenses, word order, subjunctive, etc. | L |
| 2.2 | **Grammar lesson reader UI** | Structured lesson view: explanation, rules, examples, common mistakes. Navigation by topic + CEFR level | M |
| 2.3 | **Grammar exercise engine** | Fill-in-blank, multiple-choice, article selection, word order arrangement. Exercise generation from lesson content | L |
| 2.4 | **Grammar exercise UI** | Exercise player with immediate feedback, progress tracking, explanation on wrong answer | M |
| 2.5 | **Grammar SRS integration** | Track grammar concept mastery, schedule grammar exercise reviews using FSRS with separate preset (95% retention) | M |
| 2.6 | **Cloze deletion exercises** | Sentence-based cloze exercises for grammar in context (reference Clozemaster pattern). Source sentences from Tatoeba | M |
| 2.7 | **Mistake tracking** | Categorize errors by type (article_error, case_error, word_order_error, etc.). Weighted review selection (40% weak, 30% SRS, 30% random — reference deutsch-ai-tutor) | M |
| 2.8 | **Progress tracking by grammar topic** | Mastery score per grammar topic, visual progress map | S |

### Phase 3: Reading + Listening Comprehension

**Goal**: Add comprehension practice with authentic content

| # | Feature | Description | Est. Effort |
|---|---|---|---|
| 3.1 | **Reading passage library** | Curated German texts by CEFR level (A2→B2), sourced from public domain, Tatoeba, simplified news | L |
| 3.2 | **Reading reader UI** | Text display with clickable words (lookup → definition + add to SRS), highlight/annotate, progress tracking | M |
| 3.3 | **Reading comprehension exercises** | Multiple-choice questions per passage, cloze deletion within passage, vocabulary highlights | M |
| 3.4 | **Listening library** | Pre-generated audio clips (edge-tts) for passages and sentences, organized by CEFR level | M |
| 3.5 | **Listening player UI** | Audio player with speed control (0.75x, 1x, 1.25x), transcript toggle, cloze-listening mode (hear → fill blank) | M |
| 3.6 | **Listening comprehension exercises** | After listening: comprehension questions, transcript fill-blank, vocabulary from audio → SRS | M |
| 3.7 | **PDF import (optional)** | Import German PDFs, extract text, word lookup, add unknown words to SRS (reference DeutschPath) | L |
| 3.8 | **Vocabulary integration** | Words from reading/listening automatically added to SRS deck with context | S |
| 3.9 | **Anki export** | Export decks to .apkg for users who also use Anki (reference DeutschQuest's APKG export) | S |

---

## 9. Unique Value Proposition

### Statement

> **German Learning Studio** (working name) is an offline-first, German-specific desktop application built with Tauri 2 + React + TypeScript that integrates four learning pillars — vocabulary SRS, grammar lessons with exercises, reading comprehension, and listening comprehension — into a single, private, subscription-free tool powered by the FSRS algorithm and pre-generated content from free linguistic sources.

### Why This App Exists

| Problem | Our Solution |
|---|---|
| Learners use 3-4 apps simultaneously (Anki for vocab, Babbel for grammar, Clozemaster for sentences, Seedlang for listening) | One integrated app covering all four pillars |
| Every app either requires a subscription or an AI API key | No subscription, no API keys — content pre-generated from Wiktionary, Tatoeba, frequency lists |
| No German-specific offline desktop app exists | Built specifically for German, on desktop (Tauri 2), fully offline |
| Most apps use outdated SM-2 or custom SRS | FSRS (state-of-the-art) via the `fsrs-rs` Rust crate |
| Grammar is either skipped or requires AI | Static, curated grammar lessons with offline exercises |
| Reading and listening are afterthoughts in vocab apps | Dedicated reading and listening comprehension modules with exercises |

### What Makes It Different

- **vs Anki**: German-specific, integrated grammar + reading + listening, modern UI, FSRS by default (not opt-in)
- **vs Duolingo**: No gamification noise, explicit grammar instruction, real reading/listening, offline, no subscription
- **vs Babbel**: Free, offline, desktop-native, FSRS, no subscription, customizable
- **vs FlexiLingo Desk**: German-specific (not multi-language), grammar + reading focus (not podcast focus), no AI dependency
- **vs DeutschPath**: No AI dependency, true desktop app (Tauri, not web), grammar exercises (not just AI-corrected), no AGPL restrictions

---

## 10. Next Steps for Orchestrator

### Design Decisions Required

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | **SRS algorithm** | FSRS only / FSRS + SM-2 / FSRS + Leitner | FSRS only via `fsrs-rs` crate. Simplicity over flexibility for personal app |
| 2 | **Data storage** | SQLite (rusqlite) / SQLite (sqlx) / embedded DB | SQLite via rusqlite — matches FlexiLingo pattern, synchronous, simple |
| 3 | **Content generation pipeline** | Rust-native Wiktionary parser / Python CLI pre-generation / hybrid | Python CLI pre-generation (port German Vocab Manager's parsers), generate JSON, import at build time |
| 4 | **Audio strategy** | Pre-generated edge-tts files / Web Speech API / both | Pre-generated edge-tts (offline, consistent quality). Web Speech API as fallback |
| 5 | **Grammar lesson format** | Markdown files / JSON structured / database rows | Markdown files (human-editable, version-controlled) parsed to structured JSON at build time |
| 6 | **Exercise generation** | Static pre-authored / template-based generation / both | Template-based for grammar exercises (fill-blank from sentence banks), static for reading comprehension questions |
| 7 | **State management** | Zustand+Immer (like FlexiLingo) / Redux / Jotai | Zustand+Immer — proven pattern in Tauri 2 apps, lightweight |
| 8 | **UI component library** | Radix UI + Tailwind / shadcn/ui / custom | shadcn/ui (Radix primitives + Tailwind, copy-paste components, no runtime dependency) |
| 9 | **Reading content source** | Public domain texts / Tatoeba sentences / simplified Wikipedia / curated manual | Start with Tatoeba sentences + curated A2/B1 passages, expand to public domain short stories |
| 10 | **Module architecture** | FlexiLingo-style modules / flat structure / feature-based folders | FlexiLingo-style: `src-tauri/src/{module}/` + `src/pages/{module}/` — proven for Tauri 2 |
| 11 | **Card types** | Basic (front/back) / cloze / image occlusion / all | Basic + cloze for MVP. Image occlusion in Phase 3 |
| 12 | **ID strategy** | Hex strings (FlexiLingo) / auto-increment integers / UUID v7 | Auto-increment integers — simpler for personal app, no need for distributed IDs |
| 13 | **Testing strategy** | Rust unit tests + Vitest / Rust unit tests only / Playwright E2E | Rust unit tests (SRS logic) + Vitest (React components) — match FlexiLingo's 214-test approach |
| 14 | **Content licensing** | CC BY-SA (Wiktionary) / CC BY 2.0 (Tatoeba) / MIT (our content) | Our content: MIT. Attributed third-party data: respective CC licenses. Document in NOTICE file |
| 15 | **Project name** | German Learning Studio / Deutsch Studio / Dr. Khans Deutsch / other | TBD by user |

### Architecture Blueprint (Reference)

```
german-learning-studio/
├── src-tauri/
│   ├── src/
│   │   ├── main.rs
│   │   ├── lib.rs                    # invoke_handler registration
│   │   ├── db/
│   │   │   ├── mod.rs
│   │   │   ├── schema.rs             # SQLite schema + migrations
│   │   │   └── connection.rs         # DB pool
│   │   ├── srs/
│   │   │   ├── mod.rs
│   │   │   ├── scheduler.rs          # FSRS wrapper
│   │   │   └── types.rs              # Card, ReviewLog, Deck
│   │   ├── vocab/
│   │   │   ├── mod.rs
│   │   │   ├── types.rs
│   │   │   ├── enrichment.rs         # Wiktionary lookup
│   │   │   └── import.rs             # Bulk word import
│   │   ├── grammar/
│   │   │   ├── mod.rs
│   │   │   ├── types.rs
│   │   │   └── lessons.rs            # Lesson loader
│   │   ├── reading/
│   │   │   ├── mod.rs
│   │   │   └── types.rs
│   │   ├── listening/
│   │   │   ├── mod.rs
│   │   │   └── types.rs
│   │   ├── dashboard/
│   │   │   ├── mod.rs
│   │   │   └── analytics.rs
│   │   └── commands/
│   │       ├── mod.rs
│   │       ├── srs.rs
│   │       ├── vocab.rs
│   │       ├── grammar.rs
│   │       └── dashboard.rs
│   ├── Cargo.toml                    # fsrs, rusqlite, serde, chrono
│   └── tauri.conf.json
├── src/
│   ├── App.tsx
│   ├── pages/
│   │   ├── review/                   # SRS review session
│   │   ├── decks/                    # Deck management
│   │   ├── grammar/                  # Grammar lessons + exercises
│   │   ├── reading/                  # Reading comprehension
│   │   ├── listening/                # Listening comprehension
│   │   └── dashboard/                # Stats + overview
│   ├── stores/
│   │   ├── useSrsStore.ts
│   │   ├── useDeckStore.ts
│   │   ├── useSettingsStore.ts
│   │   └── useDashboardStore.ts
│   ├── components/
│   │   ├── ui/                       # shadcn/ui components
│   │   ├── cards/                    # Flashcard components
│   │   └── layout/                   # AppShell, Sidebar, Header
│   └── lib/
│       ├── ipc.ts                    # Tauri invoke wrappers
│       └── types.ts                  # Shared TS types
├── content/                          # Pre-generated content
│   ├── vocabulary/                   # JSON word lists by CEFR level
│   ├── grammar/                      # Markdown grammar lessons
│   ├── reading/                      # Reading passages
│   └── audio/                        # Pre-generated TTS audio
├── scripts/
│   ├── generate_audio.py             # edge-tts batch generation
│   ├── import_wiktionary.py          # Wiktionary enrichment pipeline
│   └── import_frequency_list.py      # Frequency-ordered vocab import
├── package.json
└── README.md
```

### Key Dependencies

| Dependency | Purpose | License |
|---|---|---|
| `fsrs` (Rust crate) | FSRS spaced repetition algorithm | BSD |
| `rusqlite` (Rust crate) | SQLite database driver | MIT |
| `tauri` v2 | Desktop app framework | MIT/Apache-2.0 |
| `react` v19 | UI framework | MIT |
| `zustand` + `immer` | State management | MIT |
| `tailwindcss` v4 | Styling | MIT |
| `shadcn/ui` (Radix UI) | Component library | MIT |
| `lucide-react` | Icons | ISC |
| `edge-tts` (Python) | German TTS audio generation | MIT |
| `chrono` (Rust crate) | Date/time for SRS scheduling | MIT/Apache-2.0 |

### Content Sources to Prepare

| Source | Data | License | How to Import |
|---|---|---|---|
| German Wiktionary API | Article, plural, conjugation, declension, IPA, examples | CC BY-SA | Python script (port from German Vocab Manager) |
| Tatoeba API | Example sentences with translations | CC BY 2.0 FR | Python script, filter for German-English pairs |
| OpenSubtitles frequency list | Word frequency rankings | CC BY-SA | CSV import, tag with CEFR levels |
| Goethe Institute word lists | Official A1-B2 vocabulary | Public | Parse from PDFs or use existing GitHub repos |
| edge-tts (KatjaNeural) | German pronunciation audio | Free | Python CLI batch generation |
| Curated grammar lessons | A1→B1 grammar topics | MIT (ours) | Write as markdown files |

---

*End of document. This analysis is based on research conducted on 2026-08-02. App features and licenses may change over time — verify before forking or reusing code.*
