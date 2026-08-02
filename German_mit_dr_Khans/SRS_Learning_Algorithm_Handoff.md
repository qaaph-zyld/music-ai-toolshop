# SRS & Learning Algorithm Handoff

**Project:** German mit Dr. Khans — Desktop-first German learning app
**Date:** 2026-08-02
**Prepared by:** Research Agent (Agent 4 — SRS & Learning Progression)
**Companion to:** `Framework_and_Architecture_Handoff.md`, `Content_Data_Sources_Handoff.md`, `existing_apps_analysis_and_gap_handoff.md`

---

## Table of Contents

1. [fsrs-rs Integration Design](#1-fsrs-rs-integration-design)
2. [Multi-Content-Type SRS Strategy](#2-multi-content-type-srs-strategy)
3. [Card Type System Design](#3-card-type-system-design)
4. [Unified SQLite Schema](#4-unified-sqlite-schema)
5. [Progression and Motivation System](#5-progression-and-motivation-system)
6. [Review Session State Machine](#6-review-session-state-machine)
7. [Mistake Tracking and Adaptive Review](#7-mistake-tracking-and-adaptive-review)
8. [Next Steps for Orchestrator](#8-next-steps-for-orchestrator)

---

## 1. fsrs-rs Integration Design

### 1.1 Crate Overview

The [`fsrs`](https://crates.io/crates/fsrs) crate (BSD-licensed) provides the Free Spaced Repetition Scheduler in Rust. It includes both a **scheduler** (for daily review scheduling) and an **optimizer** (for tuning parameters from review history).

**Key types:**

| Type | Description |
|---|---|
| `FSRS` | Main scheduler instance. Holds 21 `f32` parameters. Created via `FSRS::default()` (average-person params) or `FSRS::new(&params)` (custom/optimized). |
| `MemoryState` | Per-card memory state: `{ stability: f32, difficulty: f32 }`. DSR model — Difficulty, Stability, Retrievability (derived). |
| `NextStates` | Returned by `next_states()`. Contains four `ItemState` variants: `again`, `hard`, `good`, `easy`. Each has `{ memory: MemoryState, interval: f32 }`. |
| `FSRSItem` | A card's review history: `{ reviews: Vec<FSRSReview> }`. Used for optimization. |
| `FSRSReview` | A single review: `{ rating: u32 (1=Again, 2=Hard, 3=Good, 4=Easy), delta_t: u32 (days since previous review) }`. |

**Cargo.toml:**

```toml
[dependencies]
fsrs = "0.7"
chrono = { version = "0.4", default-features = false, features = ["std", "clock"] }
rusqlite = { version = "0.31", features = ["bundled"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
```

### 1.2 Core Scheduling Flow (Rust)

```rust
use chrono::{DateTime, Duration, Utc};
use fsrs::{FSRS, MemoryState};

pub fn apply_rating(
    fsrs: &FSRS,
    current_state: Option<MemoryState>,
    desired_retention: f32,
    elapsed_days: u32,
    rating: u32,
) -> Result<CardUpdate, fsrs::Error> {
    let next_states = fsrs.next_states(current_state, desired_retention, elapsed_days)?;
    let chosen = match rating {
        1 => next_states.again,
        2 => next_states.hard,
        3 => next_states.good,
        4 => next_states.easy,
        _ => next_states.good,
    };
    let interval_days = chosen.interval.round().max(1.0) as u32;
    let due = Utc::now() + Duration::days(interval_days as i64);
    Ok(CardUpdate { memory_state: chosen.memory, scheduled_days: interval_days, due })
}

pub struct CardUpdate {
    pub memory_state: MemoryState,
    pub scheduled_days: u32,
    pub due: DateTime<Utc>,
}
```

### 1.3 Storing FSRS Card State in SQLite

`MemoryState` has two `f32` fields stored directly as REAL columns:

```sql
CREATE TABLE srs_state (
    card_id INTEGER PRIMARY KEY,
    stability REAL,
    difficulty REAL,
    due TEXT NOT NULL,
    last_review TEXT,
    scheduled_days INTEGER DEFAULT 0,
    reps INTEGER DEFAULT 0,
    lapses INTEGER DEFAULT 0,
    state INTEGER DEFAULT 0,           -- 0=New, 1=Learning, 2=Review, 3=Relearning
    step_index INTEGER DEFAULT 0,
    custom_retention REAL,             -- Override deck's desired_retention
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
);
```

**Rust save/load:**

```rust
pub fn save_srs_state(conn: &Connection, card_id: i64, update: &CardUpdate, reps: u32, lapses: u32, state: u32) -> Result<(), rusqlite::Error> {
    conn.execute(
        "INSERT OR REPLACE INTO srs_state (card_id, stability, difficulty, due, last_review, scheduled_days, reps, lapses, state, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, datetime('now'))",
        params![card_id, update.memory_state.stability, update.memory_state.difficulty, update.due.to_rfc3339(), Utc::now().to_rfc3339(), update.scheduled_days, reps, lapses, state],
    )
}

pub fn load_srs_state(conn: &Connection, card_id: i64) -> Result<Option<(MemoryState, u32, String, String)>, rusqlite::Error> {
    let mut stmt = conn.prepare("SELECT stability, difficulty, scheduled_days, due, last_review FROM srs_state WHERE card_id = ?1")?;
    match stmt.query_row(params![card_id], |row| {
        Ok((MemoryState { stability: row.get(0)?, difficulty: row.get(1)? }, row.get(2)?, row.get(3)?, row.get(4)?))
    }) {
        Ok(data) => Ok(Some(data)),
        Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
        Err(e) => Err(e),
    }
}
```

### 1.4 Learning Steps and Relearning Steps

**Desktop learning steps strategy:** No enforced real-time waiting. Learning-step cards are re-queued within the same session (placed at the end of the review queue). The user sees them again before the session ends.

| Step Type | Steps | Desktop Behavior |
|---|---|---|
| **Learning** | 1min → 10min | Card re-shown later in session. "Good" on first showing → graduates (due tomorrow). "Again" → 10min step (re-shown). |
| **Relearning** | 10min | "Again" on Review card → Relearning. Re-shown in session. |
| **Graduating** | 1 day | After learning steps complete. |
| **Easy** | 4 days | "Easy" on new card → skips steps. |

```rust
const DEFAULT_LEARNING_STEPS: &[u32] = &[1, 10];
const DEFAULT_RELEARNING_STEPS: &[u32] = &[10];

pub enum NextAction {
    Graduate, GraduateEasy, GraduateRelearning, ScheduleNext,
    AdvanceStep { next_step: usize },
    RelearnInSession { step_index: usize },
    EnterRelearning { step_index: usize },
}

pub fn determine_next_action(state: u32, step_index: usize, rating: u32, learning_steps: &[u32], relearning_steps: &[u32]) -> NextAction {
    match (state, rating) {
        (0 | 1, 1) => NextAction::RelearnInSession { step_index: 0 },
        (0 | 1, 2) => NextAction::RelearnInSession { step_index: step_index.min(learning_steps.len() - 1) },
        (0 | 1, 3) => if step_index + 1 >= learning_steps.len() { NextAction::Graduate } else { NextAction::AdvanceStep { next_step: step_index + 1 } },
        (0 | 1, 4) => NextAction::GraduateEasy,
        (2, 1) => NextAction::EnterRelearning { step_index: 0 },
        (2, _) => NextAction::ScheduleNext,
        (3, 1) => NextAction::RelearnInSession { step_index: 0 },
        (3, _) => if step_index + 1 >= relearning_steps.len() { NextAction::GraduateRelearning } else { NextAction::AdvanceStep { next_step: step_index + 1 } },
        _ => NextAction::ScheduleNext,
    }
}
```

### 1.5 Per-Preset Desired Retention

```rust
#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct DeckPreset {
    pub desired_retention: f32,
    pub maximum_interval: u32,
    pub learning_steps: Vec<u32>,
    pub relearning_steps: Vec<u32],
    pub enable_fuzz: bool,
}

impl Default for DeckPreset {
    fn default() -> Self { Self { desired_retention: 0.9, maximum_interval: 36500, learning_steps: vec![1, 10], relearning_steps: vec![10], enable_fuzz: true } }
}

pub fn default_presets() -> HashMap<&'static str, DeckPreset> {
    let mut p = HashMap::new();
    p.insert("vocabulary", DeckPreset { desired_retention: 0.90, ..Default::default() });
    p.insert("grammar", DeckPreset { desired_retention: 0.95, ..Default::default() });
    p.insert("listening", DeckPreset { desired_retention: 0.85, ..Default::default() });
    p
}
```

### 1.6 Parameter Optimization

After 1000+ reviews, review logs can be fed to the optimizer:

```rust
use fsrs::{ComputeParametersInput, FSRSItem, FSRSReview, compute_parameters};

pub fn optimize_parameters(review_history: Vec<(i64, NaiveDate, u32)>) -> Result<Vec<f32>, fsrs::Error> {
    let mut card_reviews: HashMap<i64, Vec<(NaiveDate, u32)>> = HashMap::new();
    for (card_id, date, rating) in review_history {
        card_reviews.entry(card_id).or_default().push((date, rating));
    }
    let mut items = Vec::new();
    for (_, mut reviews) in card_reviews {
        reviews.sort_by_key(|(d, _)| *d);
        let mut accumulated = Vec::new();
        let mut last = reviews[0].0;
        for (date, rating) in reviews {
            let delta_t = (date - last).num_days().max(0) as u32;
            accumulated.push(FSRSReview { rating, delta_t });
            items.push(FSRSItem { reviews: accumulated.clone() });
            last = date;
        }
    }
    let parameters = compute_parameters(ComputeParametersInput { train_set: items, ..Default::default() })?;
    Ok(parameters)
}
```

**Trigger:** "Optimize SRS Parameters" button in Settings, enabled when review count ≥ 1000. Runs in background thread. Results stored in `settings` table as JSON array. Fallback: `FSRS::default()` uses global average parameters.

### 1.7 SM-2 Migration Path

```rust
pub fn migrate_sm2_to_fsrs(ease_factor: f32, interval: f32, sm2_retention: f32) -> Result<fsrs::MemoryState, fsrs::Error> {
    let fsrs = FSRS::default();
    fsrs.memory_state_from_sm2(ease_factor, interval, sm2_retention)
}

pub fn migrate_sm2_with_history(ease_factor: f32, interval: f32, sm2_retention: f32, history: &[(u32, u32)]) -> Result<fsrs::MemoryState, fsrs::Error> {
    let fsrs = FSRS::default();
    let initial = fsrs.memory_state_from_sm2(ease_factor, interval, sm2_retention)?;
    let reviews: Vec<FSRSReview> = history.iter().map(|&(r, t)| FSRSReview { rating: r, delta_t: t }).collect();
    fsrs.memory_state(FSRSItem { reviews }, Some(initial))
}
```

### 1.8 Tauri IPC Command Signatures

```rust
pub struct AppState {
    pub db: Mutex<Connection>,
    pub fsrs: FSRS,
}

#[tauri::command]
pub fn srs_get_due_cards(state: State<AppState>, deck_id: Option<i64>, limit: Option<u32>) -> Result<Vec<DueCard>, String>;

#[tauri::command]
pub fn srs_submit_review(state: State<AppState>, card_id: i64, rating: u32, duration_ms: u32) -> Result<ReviewResult, String>;

#[tauri::command]
pub fn srs_get_session_preview(state: State<AppState>, deck_ids: Vec<i64>) -> Result<SessionPreview, String>;

#[tauri::command]
pub fn srs_optimize_parameters(state: State<AppState>) -> Result<OptimizeResult, String>;

#[tauri::command]
pub fn srs_get_stats(state: State<AppState>, range: Option<String>) -> Result<Stats, String>;

#[tauri::command]
pub fn srs_import_apkg(state: State<AppState>, file_path: String, target_deck_id: i64) -> Result<ImportResult, String>;
```

**Frontend (TypeScript):**

```typescript
import { invoke } from '@tauri-apps/api/core';

export const srsApi = {
  getDueCards: (deckId?: number, limit?: number) => invoke<DueCard[]>('srs_get_due_cards', { deckId, limit }),
  submitReview: (cardId: number, rating: number, durationMs: number) => invoke<ReviewResult>('srs_submit_review', { cardId, rating, durationMs }),
  getSessionPreview: (deckIds: number[]) => invoke<SessionPreview>('srs_get_session_preview', { deckIds }),
  optimizeParameters: () => invoke<OptimizeResult>('srs_optimize_parameters'),
  getStats: (range?: string) => invoke<Stats>('srs_get_stats', { range }),
  importApkg: (filePath: string, targetDeckId: number) => invoke<ImportResult>('srs_import_apkg', { filePath, targetDeckId }),
};
```

**Return types:**

```rust
#[derive(serde::Serialize)]
pub struct DueCard { pub card_id: i64, pub deck_id: i64, pub card_type: String, pub front: String, pub back: String, pub audio_path: Option<String>, pub extra: Option<String>, pub state: u32, pub step_index: usize, pub is_new: bool }

#[derive(serde::Serialize)]
pub struct ReviewResult { pub next_due: String, pub scheduled_days: u32, pub new_state: u32, pub session_complete: bool, pub remaining: u32 }

#[derive(serde::Serialize)]
pub struct SessionPreview { pub new_count: u32, pub learning_count: u32, pub review_count: u32, pub total_due: u32 }

#[derive(serde::Serialize)]
pub struct Stats { pub total_reviews: u32, pub reviews_today: u32, pub retention_rate: f32, pub retention_rate_per_deck: Vec<(String, f32)>, pub cards_new: u32, pub cards_learning: u32, pub cards_young: u32, pub cards_mature: u32, pub streak_days: u32, pub time_studied_today_ms: u64, pub forecast: Vec<(String, u32)> }
```

### 1.9 FSRS Instance Lifecycle

```
App Launch → Open user.db → ATTACH content.db → Run migrations → Load fsrs_params from settings
  → If params exist: FSRS::new(&params) → optimized instance
  → Else: FSRS::default() → default instance
  → Store in AppState

Settings → "Optimize" → Load review_logs → compute_parameters() → Save to settings → Reconstruct FSRS
```

---

## 2. Multi-Content-Type SRS Strategy

### 2.1 Deck and Preset System

Each deck has an associated **preset** defining FSRS parameters. Decks group cards by content type and/or CEFR level.

```
Decks
├── A1 Vocabulary          (preset: vocabulary, desired_retention: 0.90)
├── A2 Vocabulary          (preset: vocabulary, desired_retention: 0.90)
├── B1 Vocabulary          (preset: vocabulary, desired_retention: 0.90)
├── A1 Grammar             (preset: grammar, desired_retention: 0.95)
├── A2 Grammar             (preset: grammar, desired_retention: 0.95)
├── B1 Grammar             (preset: grammar, desired_retention: 0.95)
├── A2 Listening           (preset: listening, desired_retention: 0.85)
├── B1 Listening           (preset: listening, desired_retention: 0.85)
├── Custom Deck (user)     (preset: custom, user-configurable)
└── Imported Anki Deck     (preset: vocabulary, desired_retention: 0.90)
```

### 2.2 Unified Review Queue vs Separate Sessions

**Decision: Unified review queue with type-aware rendering.**

All due cards from all active decks merge into a single review queue. The frontend renders each card according to its `card_type`.

**Rationale:**
- Reduces friction — one session reviews everything due
- Matches Anki's mixed-deck approach (proven UX)
- Avoids "which session do I start?" decision paralysis
- Card type determines UI, not the session

**Queue composition algorithm:**

```rust
pub fn build_review_queue(conn: &Connection, deck_ids: &[i64], limits: &SessionLimits) -> Result<Vec<i64>, rusqlite::Error> {
    let mut review_cards = get_due_review_cards(conn, deck_ids, limits.review_limit)?;
    let mut learning_cards = get_learning_cards(conn, deck_ids)?;
    let mut new_cards = get_new_cards(conn, deck_ids, limits.new_card_limit)?;

    let mut queue = Vec::new();
    queue.append(&mut learning_cards);  // Learning cards first (in-session steps)

    // Interleave review and new cards (3:1 ratio, configurable)
    let mut ri = 0; let mut ni = 0;
    let rc = review_cards.len(); let nc = new_cards.len();
    while ri < rc || ni < nc {
        for _ in 0..3 { if ri < rc { queue.push(review_cards[ri]); ri += 1; } }
        if ni < nc { queue.push(new_cards[ni]); ni += 1; }
    }
    Ok(queue)
}
```

**Session configuration (user can override):**
- **All decks** (default) — unified queue from all active decks
- **Specific decks** — select one or more decks
- **By content type** — "Only vocabulary", "Only grammar" (filters by preset)

### 2.3 Grammar Exercises as SRS Cards

Grammar exercises (fill-blank, cloze, conjugation, word order, MC) are SRS cards. Each exercise has a front (prompt) and back (answer + explanation). The user answers, then rates their performance. Higher desired retention (95%) means more frequent reviews.

| Exercise Type | Card Front | Card Back | Card Type |
|---|---|---|---|
| Fill-blank (article) | "Ich habe ___ Buch." (der/die/das) | "das" + "Buch is neuter" | `article` |
| Fill-blank (case) | "Ich gebe ___ Mann das Buch." (dem/den/des) | "dem" + "Dativ for 'geben'" | `cloze` |
| Conjugation | "sein, Präsens, ich" | "ist" + audio | `conjugation` |
| Word order | Scrambled: "Buch / ich / lese / ein" | "Ich lese ein Buch." | `word_order` |
| Grammar MC | "Which case follows 'mit'?" | "Dativ" + explanation | `grammar_mc` |

### 2.4 Cloze Deletion Cards

Sentence-based: a sentence with a blanked-out word. The blanked word is grammar-critical (article, verb ending, preposition, conjugated form).

```typescript
interface ClozeCardData {
  sentence_de: string;      // "Ich habe ein Buch gekauft."
  sentence_en: string;      // "I bought a book."
  cloze_text: string;       // "Ich habe ein Buch ___."
  cloze_answer: string;     // "gekauft"
  cloze_hint: string | null;// "past participle of 'kaufen'"
  alternatives: string[];   // ["gekauft", "Gekauft"]
  audio_path: string | null;
}
```

**Cloze generation:** The content pipeline generates cloze cards by parsing Tatoeba sentences with spaCy, blanking grammar-critical words, and storing as exercises in `content.exercises`.

### 2.5 Reading Comprehension — No SRS

Reading passages follow **linear progression** (not SRS-scheduled):
- Passages organized by CEFR level (A1 → C2)
- User reads in order or by choice
- Completion tracked: unread → in_progress → completed
- Comprehension questions CAN be SRS cards (`reading_comp` type) — allows revisiting difficult concepts without re-reading the full passage

```sql
CREATE TABLE reading_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    passage_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'unread',
    scroll_position REAL DEFAULT 0,
    time_spent_ms INTEGER DEFAULT 0,
    last_read_at TEXT,
    comprehension_score REAL,
    UNIQUE(passage_id)
);
```

### 2.6 Listening Comprehension — FSRS 85%

Listening cards use FSRS with 85% desired retention. Lower retention = fewer reviews = more content exposure. Goal is breadth of ear training, not perfect recall.

**Listening card flow:**
1. Play audio clip (auto-play on card show)
2. User can replay, adjust speed (0.75x, 1x, 1.25x)
3. Comprehension question shown
4. User answers → rates (Again/Hard/Good/Easy)
5. Back: transcript + translation + answer explanation

| Listening Card | Front | Back | Card Type |
|---|---|---|---|
| Basic listening | Audio clip (auto-play) | Transcript + translation | `listening` |
| Cloze listening | Audio + partial transcript with blank | Full transcript + blank word | `listening` |
| Comprehension | Audio + question | Answer + explanation | `listening` |

---

## 3. Card Type System Design

### 3.1 Unified Card Table Approach

All card types stored in a single `cards` table. Type-specific fields are JSON in the `extra` column. Content references link to content.db via soft FKs.

```sql
CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL,
    card_type TEXT NOT NULL,
    word_id INTEGER,           -- → content.words.id
    sentence_id INTEGER,       -- → content.sentences.id
    exercise_id INTEGER,       -- → content.exercises.id
    passage_id INTEGER,        -- → content.reading_passages.id
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    audio_path TEXT,
    extra TEXT,                -- JSON: type-specific fields
    tags TEXT,
    notes TEXT,
    is_starred INTEGER NOT NULL DEFAULT 0,
    is_suspended INTEGER NOT NULL DEFAULT 0,
    is_custom INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE
);
```

### 3.2 Card Type Definitions

#### Type 1: `basic_vocab` — Basic Vocabulary

| Field | Content |
|---|---|
| **Front** | German word + audio button: "Haus" 🔊 |
| **Back** | English translation + article + plural + IPA + example sentence |
| **`extra`** | `{"article":"das","plural":"Häuser","ipa":"haʊ̯s","example_de":"Das Haus ist groß.","example_en":"The house is big.","pos":"noun","cefr":"A1"}` |
| **Content link** | `word_id` → `content.words.id` |

#### Type 2: `cloze` — Cloze Deletion

| Field | Content |
|---|---|
| **Front** | Sentence with blank: "Ich ___ ein Buch." + optional hint |
| **Back** | Full sentence + translation + audio |
| **`extra`** | `{"cloze_text":"Ich ___ ein Buch.","cloze_answer":"habe","cloze_hint":null,"alternatives":["habe","Habe"],"full_sentence_de":"Ich habe ein Buch.","full_sentence_en":"I have a book.","cloze_type":"verb_conjugation"}` |
| **Content link** | `sentence_id` → `content.sentences.id` |

#### Type 3: `article` — Article Selection

| Field | Content |
|---|---|
| **Front** | Noun without article: "___ Haus" + options: der/die/das |
| **Back** | Correct article + plural + audio + example |
| **`extra`** | `{"noun":"Haus","correct_article":"das","options":["der","die","das"],"plural":"Häuser","example_de":"Das Haus ist schön.","example_en":"The house is beautiful."}` |
| **Content link** | `word_id` → `content.words.id` |

#### Type 4: `conjugation` — Verb Conjugation

| Field | Content |
|---|---|
| **Front** | Verb + tense + person: "sein, Präsens, ich" |
| **Back** | Conjugated form + full conjugation table + audio |
| **`extra`** | `{"verb":"sein","tense":"Präsens","person":"ich","answer":"bin","full_conjugation":{"ich":"bin","du":"bist","er/sie/es":"ist","wir":"sind","ihr":"seid","sie/Sie":"sind"},"audio_path":"vocab/sein_ich.mp3"}` |
| **Content link** | `word_id` → `content.words.id` |

#### Type 5: `grammar_mc` — Grammar Multiple Choice

| Field | Content |
|---|---|
| **Front** | Question about a grammar rule + 4 options |
| **Back** | Correct answer + explanation + rule reference |
| **`extra`** | `{"question":"Which case follows 'mit'?","options":["Nominativ","Akkusativ","Dativ","Genitiv"],"correct_index":2,"explanation":"'mit' always takes Dativ.","rule_id":"prep_dativ","lesson_id":5}` |
| **Content link** | `exercise_id` → `content.exercises.id` |

#### Type 6: `listening` — Listening Comprehension

| Field | Content |
|---|---|
| **Front** | Audio player (auto-play) + comprehension question |
| **Back** | Transcript + translation + answer + explanation |
| **`extra`** | `{"audio_path":"listening/a2_001.mp3","duration_seconds":15,"question":"What does the speaker want to buy?","options":["Bread","Milk","Eggs","All"],"correct_index":3,"transcript_de":"Ich möchte Brot, Milch und Eier kaufen.","transcript_en":"I want to buy bread, milk, and eggs."}` |
| **Content link** | `exercise_id` → `content.exercises.id` |

#### Type 7: `reading_comp` — Reading Comprehension

| Field | Content |
|---|---|
| **Front** | Passage excerpt + question |
| **Back** | Answer + explanation + link to full passage |
| **`extra`** | `{"passage_id":42,"passage_title":"Der Brief","question":"Why did the protagonist go to the post office?","options":["Buy stamps","Send a letter","Meet a friend","None"],"correct_index":1,"explanation":"Text says 'Er ging zum Postamt, um einen Brief abzuschicken.'","passage_excerpt":"Er ging zum Postamt, um einen Brief abzuschicken."}` |
| **Content link** | `passage_id` → `content.reading_passages.id` |

#### Type 8: `word_order` — Word Order Arrangement

| Field | Content |
|---|---|
| **Front** | Scrambled words: ["Buch", "ich", "lese", "ein"] |
| **Back** | Correct sentence + translation + audio |
| **`extra`** | `{"scrambled_words":["Buch","ich","lese","ein"],"correct_sentence":"Ich lese ein Buch.","translation":"I am reading a book.","audio_path":"sentences/ich_lese_ein_buch.mp3"}` |
| **Content link** | `sentence_id` → `content.sentences.id` |

### 3.3 Card Type Registry (Frontend)

```typescript
// src/components/cards/CardRenderer.tsx
const CARD_COMPONENTS: Record<string, React.FC<CardProps>> = {
  basic_vocab: BasicVocabCard,
  cloze: ClozeCard,
  article: ArticleCard,
  conjugation: ConjugationCard,
  grammar_mc: GrammarMCCard,
  listening: ListeningCard,
  reading_comp: ReadingCompCard,
  word_order: WordOrderCard,
};

export function CardRenderer({ card, onAnswer, onRate }: CardRendererProps) {
  const Component = CARD_COMPONENTS[card.card_type] ?? BasicVocabCard;
  return <Component card={card} onAnswer={onAnswer} onRate={onRate} />;
}
```

### 3.4 User-Created Cards

For custom vocabulary not in content.db, `is_custom = 1` and `word_id = NULL`. All content stored directly in `front`, `back`, `audio_path`, `extra`.

**Custom card creation flow:**
1. User enters a German word
2. App searches content.db for a match
3. If found: auto-fills from `content.words`, sets `word_id`
4. If not found: user manually enters fields
5. Audio: user can record or use Piper TTS (runtime)
6. Card inserted with `is_custom = 1`

---

## 4. Unified SQLite Schema

### 4.1 Architecture: Two-DB with ATTACH

```
┌─────────────────────────────────────────────────────┐
│                    user.db (main)                     │
│                   Runtime, read-write                  │
│                                                       │
│  Tables:                                              │
│    decks, cards, srs_state, review_logs,              │
│    study_sessions, settings, streaks,                 │
│    mistake_history, reading_progress                  │
│                                                       │
│  ATTACH DATABASE 'content.db' AS content              │
│                                                       │
│  Cross-DB query example:                              │
│    SELECT c.*, w.lemma, w.ipa, w.audio_path           │
│    FROM main.cards c                                  │
│    JOIN content.words w ON c.word_id = w.id           │
│    WHERE c.deck_id = 1                                │
└──────────────────────┬──────────────────────────────┘
                       │ ATTACH
┌──────────────────────▼──────────────────────────────┐
│                  content.db (content)                  │
│              Read-only, bundled with app               │
│                                                       │
│  Tables:                                              │
│    words, sentences, grammar_rules, grammar_lessons,  │
│    exercises, reading_passages, reading_questions,    │
│    listening_exercises, listening_questions           │
│                                                       │
│  ~80 MB, pre-built by Python pipeline                 │
│  Swappable: replace file + restart to update content  │
└─────────────────────────────────────────────────────┘
```

**Startup sequence (Rust):**

```rust
pub fn init_database(app_data_dir: &Path, content_db_path: &Path) -> Result<Connection, rusqlite::Error> {
    let user_db_path = app_data_dir.join("user.db");
    let conn = Connection::open(&user_db_path)?;
    conn.execute("PRAGMA foreign_keys = ON", [])?;
    conn.execute(&format!("ATTACH DATABASE '{}' AS content", content_db_path.display()), [])?;
    run_migrations(&conn)?;
    check_content_version(&conn)?;
    Ok(conn)
}
```

**Cross-DB FK note:** SQLite does NOT enforce FK constraints across attached databases. Content references (`word_id`, `sentence_id`, `exercise_id`, `passage_id`) are **soft references** — INTEGER columns validated at query time. If content.db is updated and IDs change, a migration script remaps references.

**Content version tracking:**

```sql
INSERT OR REPLACE INTO settings (key, value) VALUES ('content_version', '1');
```

### 4.2 Content Database Schema (content.db)

Pre-built by the Python data pipeline, bundled as a Tauri resource, opened read-only at runtime.

```sql
PRAGMA journal_mode = WAL;

-- Words (~50,000 entries) — Wiktionary, Grundwortschatz, DAFlex, GLC
CREATE TABLE words (
    id INTEGER PRIMARY KEY,
    lemma TEXT NOT NULL,
    word TEXT NOT NULL,
    pos TEXT,
    gender TEXT,
    ipa TEXT,
    plural TEXT,
    cefr_level TEXT,
    cefr_source TEXT,
    grade_level INTEGER,
    frequency_rank INTEGER,
    definition_de TEXT,
    definition_en TEXT,
    translation_en TEXT,
    inflections TEXT,           -- JSON: conjugation/declension table
    synonyms TEXT,              -- JSON array
    antonyms TEXT,              -- JSON array
    example_de TEXT,
    example_en TEXT,
    audio_path TEXT,
    audio_source TEXT,          -- "lingua_libre", "edge_tts", "piper"
    source_attribution TEXT
);
CREATE INDEX idx_words_lemma ON words(lemma);
CREATE INDEX idx_words_cefr ON words(cefr_level);
CREATE INDEX idx_words_pos ON words(pos);
CREATE INDEX idx_words_frequency ON words(frequency_rank);

-- Sentences (~100,000) — Tatoeba (CC BY 2.0 FR), GLC
CREATE TABLE sentences (
    id INTEGER PRIMARY KEY,
    sentence_de TEXT NOT NULL,
    sentence_en TEXT,
    cefr_level TEXT,
    word_count INTEGER,
    grammar_features TEXT,      -- JSON: {"tense":"Präsens","case":"Akkusativ"}
    source TEXT,
    source_attribution TEXT,
    audio_path TEXT
);
CREATE INDEX idx_sentences_cefr ON sentences(cefr_level);
CREATE INDEX idx_sentences_word_count ON sentences(word_count);

-- Grammar Rules (365) — German Language Community (CC BY-SA 4.0)
CREATE TABLE grammar_rules (
    id INTEGER PRIMARY KEY,
    rule_id TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    cefr_level TEXT,
    rule TEXT NOT NULL,
    explanation TEXT,
    examples TEXT               -- JSON array: [{"de":"...","en":"..."}]
);
CREATE INDEX idx_grammar_rules_category ON grammar_rules(category);
CREATE INDEX idx_grammar_rules_cefr ON grammar_rules(cefr_level);

-- Grammar Lessons (~100 original) — MIT license
CREATE TABLE grammar_lessons (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    cefr_level TEXT NOT NULL,
    category TEXT NOT NULL,
    summary TEXT,
    content_markdown TEXT NOT NULL,
    rule_ids TEXT,              -- JSON array of grammar_rules.rule_id
    exercise_ids TEXT,          -- JSON array of exercise IDs
    order_index INTEGER DEFAULT 0,
    audio_path TEXT
);
CREATE INDEX idx_grammar_lessons_cefr ON grammar_lessons(cefr_level);
CREATE INDEX idx_grammar_lessons_category ON grammar_lessons(category);
CREATE INDEX idx_grammar_lessons_order ON grammar_lessons(category, order_index);

-- Exercises (~10,000 generated)
CREATE TABLE exercises (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,         -- "fill_blank_article","fill_blank_case","fill_blank_verb","cloze","word_order","grammar_mc","translation"
    cefr_level TEXT NOT NULL,
    grammar_rule_id TEXT,
    prompt TEXT NOT NULL,
    prompt_translation TEXT,
    answer TEXT NOT NULL,
    options TEXT,               -- JSON array (for MC)
    explanation TEXT,
    sentence_id INTEGER,
    difficulty INTEGER DEFAULT 3,
    source TEXT DEFAULT 'generated'
);
CREATE INDEX idx_exercises_type ON exercises(type);
CREATE INDEX idx_exercises_cefr ON exercises(cefr_level);
CREATE INDEX idx_exercises_rule ON exercises(grammar_rule_id);
CREATE INDEX idx_exercises_sentence ON exercises(sentence_id);

-- Reading Passages (~150 curated + Gutenberg)
CREATE TABLE reading_passages (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    cefr_level TEXT NOT NULL,
    category TEXT,              -- "article","story","news","poem"
    content TEXT NOT NULL,
    word_count INTEGER,
    reading_time_minutes INTEGER,
    source TEXT NOT NULL,       -- "tatoeba","curated","gutenberg","user"
    source_attribution TEXT,
    audio_path TEXT
);
CREATE INDEX idx_reading_passages_cefr ON reading_passages(cefr_level);
CREATE INDEX idx_reading_passages_category ON reading_passages(category);

-- Reading Comprehension Questions
CREATE TABLE reading_questions (
    id INTEGER PRIMARY KEY,
    passage_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    options TEXT,
    question_type TEXT DEFAULT 'open',
    order_index INTEGER DEFAULT 0,
    FOREIGN KEY (passage_id) REFERENCES reading_passages(id) ON DELETE CASCADE
);
CREATE INDEX idx_reading_questions_passage ON reading_questions(passage_id);

-- Listening Exercises
CREATE TABLE listening_exercises (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    cefr_level TEXT NOT NULL,
    audio_path TEXT NOT NULL,
    transcript TEXT,
    transcript_translation TEXT,
    duration_seconds INTEGER,
    source TEXT NOT NULL,       -- "tts","librivox","user"
    source_attribution TEXT
);
CREATE INDEX idx_listening_exercises_cefr ON listening_exercises(cefr_level);

-- Listening Comprehension Questions
CREATE TABLE listening_questions (
    id INTEGER PRIMARY KEY,
    exercise_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    options TEXT,
    question_type TEXT DEFAULT 'open',
    order_index INTEGER DEFAULT 0,
    FOREIGN KEY (exercise_id) REFERENCES listening_exercises(id) ON DELETE CASCADE
);
CREATE INDEX idx_listening_questions_exercise ON listening_questions(exercise_id);

-- Content metadata
CREATE TABLE content_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT INTO content_metadata (key, value) VALUES
    ('content_version', '1'),
    ('build_date', '2026-08-02'),
    ('word_count', '50000'),
    ('sentence_count', '100000'),
    ('grammar_rule_count', '365'),
    ('exercise_count', '10000'),
    ('reading_passage_count', '150'),
    ('listening_exercise_count', '500');
```

### 4.3 User Data Schema (user.db)

Created at runtime via Rust migrations. Stores all user-specific data.

```sql
PRAGMA foreign_keys = ON;

-- Schema version tracking
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Decks — Groups of cards with shared FSRS preset
CREATE TABLE decks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    preset TEXT NOT NULL DEFAULT 'vocabulary',
    desired_retention REAL NOT NULL DEFAULT 0.90,
    learning_steps TEXT NOT NULL DEFAULT '[1,10]',
    relearning_steps TEXT NOT NULL DEFAULT '[10]',
    maximum_interval INTEGER NOT NULL DEFAULT 36500,
    enable_fuzz INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'builtin',
    cefr_level TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    new_cards_per_day INTEGER DEFAULT 20,
    review_limit_per_day INTEGER DEFAULT 200,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Cards — User's SRS cards (references content.db via soft FKs)
CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL,
    card_type TEXT NOT NULL,
    word_id INTEGER,
    sentence_id INTEGER,
    exercise_id INTEGER,
    passage_id INTEGER,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    audio_path TEXT,
    extra TEXT,
    tags TEXT,
    notes TEXT,
    is_starred INTEGER NOT NULL DEFAULT 0,
    is_suspended INTEGER NOT NULL DEFAULT 0,
    is_custom INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE
);
CREATE INDEX idx_cards_deck ON cards(deck_id);
CREATE INDEX idx_cards_type ON cards(card_type);
CREATE INDEX idx_cards_word ON cards(word_id);
CREATE INDEX idx_cards_exercise ON cards(exercise_id);
CREATE INDEX idx_cards_starred ON cards(is_starred);
CREATE INDEX idx_cards_suspended ON cards(is_suspended);

-- SRS State — FSRS scheduling state per card (1:1 with cards)
CREATE TABLE srs_state (
    card_id INTEGER PRIMARY KEY,
    stability REAL,
    difficulty REAL,
    due TEXT NOT NULL,
    last_review TEXT,
    scheduled_days INTEGER DEFAULT 0,
    reps INTEGER DEFAULT 0,
    lapses INTEGER DEFAULT 0,
    state INTEGER DEFAULT 0,       -- 0=New, 1=Learning, 2=Review, 3=Relearning
    step_index INTEGER DEFAULT 0,
    custom_retention REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
);
CREATE INDEX idx_srs_state_due ON srs_state(due);
CREATE INDEX idx_srs_state_state ON srs_state(state);

-- Review Logs — Every review event (for analytics + optimization)
CREATE TABLE review_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL,
    deck_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,       -- 1=Again, 2=Hard, 3=Good, 4=Easy
    state INTEGER NOT NULL,        -- Card state before review
    stability REAL,
    difficulty REAL,
    elapsed_days INTEGER,
    scheduled_days INTEGER,
    reviewed_at TEXT NOT NULL DEFAULT (datetime('now')),
    duration_ms INTEGER,
    mistake_type TEXT,             -- 'article_error', 'case_error', etc. (NULL if correct)
    user_answer TEXT,
    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
    FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE
);
CREATE INDEX idx_review_logs_card ON review_logs(card_id);
CREATE INDEX idx_review_logs_deck ON review_logs(deck_id);
CREATE INDEX idx_review_logs_date ON review_logs(reviewed_at);
CREATE INDEX idx_review_logs_mistake ON review_logs(mistake_type);

-- Study Sessions — Analytics per session
CREATE TABLE study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_type TEXT NOT NULL,    -- 'mixed_review','vocab_review','grammar','reading','listening'
    deck_ids TEXT,                 -- JSON array of deck IDs
    started_at TEXT NOT NULL,
    ended_at TEXT,
    cards_reviewed INTEGER DEFAULT 0,
    cards_again INTEGER DEFAULT 0,
    cards_hard INTEGER DEFAULT 0,
    cards_good INTEGER DEFAULT 0,
    cards_easy INTEGER DEFAULT 0,
    new_cards_learned INTEGER DEFAULT 0,
    duration_ms INTEGER,
    current_card_id INTEGER,       -- For interruption recovery
    remaining_queue TEXT,          -- JSON array of remaining card IDs
    is_complete INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (current_card_id) REFERENCES cards(id) ON DELETE SET NULL
);
CREATE INDEX idx_study_sessions_date ON study_sessions(started_at);
CREATE INDEX idx_study_sessions_type ON study_sessions(session_type);

-- Settings — Key-value store
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT OR IGNORE INTO settings (key, value) VALUES
    ('fsrs_parameters', 'null'),
    ('fsrs_optimized_at', 'null'),
    ('fsrs_review_count_at_optimization', '0'),
    ('content_version', '0'),
    ('daily_new_card_limit', '20'),
    ('daily_review_limit', '200'),
    ('daily_goal_minutes', '15'),
    ('theme', 'system'),
    ('audio_enabled', 'true'),
    ('audio_playback_rate', '1.0'),
    ('auto_play_audio', 'true'),
    ('show_timer', 'false'),
    ('keyboard_shortcuts_enabled', 'true'),
    ('interface_language', 'en'),
    ('first_run', 'true'),
    ('streak_freeze_count', '1'),
    ('streak_freeze_max', '1'),
    ('cefr_level_estimate', 'A1'),
    ('session_interleave_ratio', '3');

-- Streaks — Daily study tracking
CREATE TABLE streaks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    studied INTEGER NOT NULL DEFAULT 0,
    reviews_count INTEGER DEFAULT 0,
    new_cards_count INTEGER DEFAULT 0,
    time_studied_ms INTEGER DEFAULT 0,
    used_freeze INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_streaks_date ON streaks(date);

-- Mistake History — Error tracking for adaptive review
CREATE TABLE mistake_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL,
    mistake_type TEXT NOT NULL,    -- 'article_error','case_error','word_order_error','spelling_error','translation_error','conjugation_error'
    user_answer TEXT,
    correct_answer TEXT,
    context TEXT,                  -- Card front for reference
    grammar_category TEXT,         -- 'cases','articles','verbs','word_order'
    cefr_level TEXT,
    occurred_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
);
CREATE INDEX idx_mistake_card ON mistake_history(card_id);
CREATE INDEX idx_mistake_type ON mistake_history(mistake_type);
CREATE INDEX idx_mistake_category ON mistake_history(grammar_category);
CREATE INDEX idx_mistake_date ON mistake_history(occurred_at);

-- Reading Progress — Track reading passage completion
CREATE TABLE reading_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    passage_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'unread',
    scroll_position REAL DEFAULT 0,
    time_spent_ms INTEGER DEFAULT 0,
    last_read_at TEXT,
    comprehension_score REAL,
    UNIQUE(passage_id)
);
CREATE INDEX idx_reading_progress_status ON reading_progress(status);
```

### 4.4 Key Query Patterns

**Get due cards with content (cross-DB JOIN):**

```sql
SELECT c.id, c.deck_id, c.card_type, c.front, c.back, c.audio_path, c.extra,
       s.state, s.step_index, s.stability, s.difficulty, s.due, s.last_review,
       w.lemma, w.ipa, w.gender, w.plural, w.translation_en
FROM main.cards c
JOIN main.srs_state s ON c.id = s.card_id
LEFT JOIN content.words w ON c.word_id = w.id
WHERE c.deck_id IN (1, 2, 3)
  AND c.is_suspended = 0
  AND s.state = 2
  AND s.due <= datetime('now')
ORDER BY s.due ASC
LIMIT 200;
```

**Get new cards (no SRS state yet):**

```sql
SELECT c.id, c.deck_id, c.card_type, c.front, c.back, c.audio_path, c.extra
FROM main.cards c
LEFT JOIN main.srs_state s ON c.id = s.card_id
WHERE c.deck_id IN (1, 2, 3)
  AND c.is_suspended = 0
  AND s.card_id IS NULL
ORDER BY c.id ASC
LIMIT 20;
```

**Get cards by content type (for filtered sessions):**

```sql
SELECT c.*, s.*
FROM main.cards c
JOIN main.srs_state s ON c.id = s.card_id
JOIN main.decks d ON c.deck_id = d.id
WHERE d.preset = 'grammar'
  AND s.due <= datetime('now')
  AND c.is_suspended = 0;
```

---

## 5. Progression and Motivation System

### 5.1 CEFR Level Tracking

The app estimates the user's current CEFR level from two signals: vocabulary mastery and grammar exercise performance.

**Estimation algorithm:**

```rust
pub fn estimate_cefr_level(conn: &Connection) -> Result<String, rusqlite::Error> {
    let vocab_scores = query_vocab_mastery_by_cefr(conn)?;
    let grammar_scores = query_grammar_accuracy_by_cefr(conn)?;

    let levels = ["A1", "A2", "B1", "B2", "C1", "C2"];
    let mut current_level = "A1";

    for (i, level) in levels.iter().enumerate() {
        let vocab_coverage = vocab_scores.get(*level).copied().unwrap_or(0.0);
        let vocab_retention = vocab_retention.get(*level).copied().unwrap_or(0.0);
        let grammar_acc = grammar_scores.get(*level).copied().unwrap_or(0.0);

        // mastery = coverage*0.4 + retention*0.3 + grammar_accuracy*0.3
        let mastery = vocab_coverage * 0.4 + vocab_retention * 0.3 + grammar_acc * 0.3;

        if mastery >= 0.80 {
            current_level = levels.get(i + 1).unwrap_or(&"C2");
        }
    }
    Ok(current_level.to_string())
}
```

**Vocabulary mastery query:**

```sql
SELECT w.cefr_level,
    COUNT(DISTINCT c.id) AS total_cards,
    COUNT(DISTINCT CASE WHEN s.state >= 2 THEN c.id END) AS learned_cards,
    COUNT(CASE WHEN r.rating >= 3 THEN 1 END) AS correct_reviews,
    COUNT(r.id) AS total_reviews
FROM main.cards c
JOIN content.words w ON c.word_id = w.id
LEFT JOIN main.srs_state s ON c.id = s.card_id
LEFT JOIN main.review_logs r ON c.id = r.card_id AND r.reviewed_at >= datetime('now', '-30 days')
WHERE c.card_type IN ('basic_vocab', 'article', 'conjugation')
GROUP BY w.cefr_level;
```

**Grammar accuracy query:**

```sql
SELECT e.cefr_level,
    COUNT(CASE WHEN r.rating >= 3 THEN 1 END) AS correct,
    COUNT(r.id) AS total
FROM main.cards c
JOIN content.exercises e ON c.exercise_id = e.id
JOIN main.review_logs r ON c.id = r.card_id
WHERE c.card_type IN ('grammar_mc', 'cloze', 'word_order')
GROUP BY e.cefr_level;
```

**Dashboard display:** "Your level: **B1** (A1: 95% mastered, A2: 88% mastered, B1: 72% mastered)" with a progress bar toward the next level.

### 5.2 Streak Tracking

**Daily study detection:** A day counts as "studied" if the user completes at least 1 review. Intentionally low-friction.

**Streak calculation:**

```rust
pub fn calculate_streak(conn: &Connection) -> Result<StreakInfo, rusqlite::Error> {
    let entries = query_recent_streak_entries(conn, 30)?;
    let today = chrono::Local::now().date_naive();
    let mut streak_count = 0;
    let mut freezes_used = 0;
    let max_freeze = get_setting(conn, "streak_freeze_max")?;

    let mut check_date = today;
    for entry in entries.iter().rev() {
        let entry_date = chrono::NaiveDate::parse_from_str(&entry.date, "%Y-%m-%d")?;
        if entry.studied == 1 {
            streak_count += 1;
            check_date = check_date.pred();
        } else if entry.used_freeze == 1 {
            streak_count += 1;
            freezes_used += 1;
            check_date = check_date.pred();
        } else {
            break;
        }
    }
    let today_studied = entries.iter().any(|e| e.date == today.format("%Y-%m-%d").to_string() && e.studied == 1);
    Ok(StreakInfo { current_streak: streak_count, today_studied, freezes_available: max_freeze.saturating_sub(freezes_used), freezes_max: max_freeze })
}
```

**Streak freeze logic:**
- User starts with 1 free freeze (configurable)
- If a day passes with no study and a freeze is available, it's automatically consumed
- Freezes regenerate after 7 days of consecutive study
- Dashboard: "🔥 12 day streak | 🧊 1 freeze available"

**Streak update on review:**

```rust
pub fn update_streak_on_review(conn: &Connection) -> Result<(), rusqlite::Error> {
    let today = chrono::Local::now().format("%Y-%m-%d").to_string();
    conn.execute(
        "INSERT INTO streaks (date, studied, reviews_count) VALUES (?1, 1, 1)
         ON CONFLICT(date) DO UPDATE SET studied = 1, reviews_count = reviews_count + 1",
        [&today],
    )
}
```

### 5.3 Daily Goals

| Goal | Default | Setting Key | Description |
|---|---|---|---|
| New cards | 20 | `daily_new_card_limit` | Max new cards introduced per day |
| Reviews | 200 | `daily_review_limit` | Max review cards per session/day |
| Study time | 15 min | `daily_goal_minutes` | Target study time per day |

**Display:** Three progress bars on dashboard: "New cards: 15/20", "Reviews: 87/200", "Study time: 12m/15m". When all three are met: "Daily goal complete ✓" — no confetti, no fanfare.

### 5.4 Statistics

| Stat | Computation | Display |
|---|---|---|
| Total reviews | `COUNT(*) FROM review_logs` | "12,847 reviews" |
| Reviews today | `COUNT(*) WHERE reviewed_at >= today` | "87 today" |
| Retention rate | `COUNT(rating >= 3) / COUNT(*)` | "89% retention" |
| Retention per deck | Same, grouped by deck_id | Table or bar chart |
| Cards by state | `COUNT GROUP BY state` | "New: 1,200, Learning: 45, Young: 3,400, Mature: 2,100" |
| Time studied today | `SUM(duration_ms) WHERE reviewed_at >= today` | "23 minutes today" |
| Time studied total | `SUM(duration_ms)` | "147 hours total" |

**Card state definitions:**

| State | FSRS State | Interval | Description |
|---|---|---|---|
| New | 0 | — | Never reviewed |
| Learning | 1 | < 1 day | In learning steps |
| Young | 2 | 1–21 days | Review state, short interval |
| Mature | 2 | ≥ 21 days | Review state, long interval |
| Relearning | 3 | < 1 day | Lapsed, in relearning steps |

**Forecast graph (next 14 days):**

```sql
SELECT DATE(s.due) AS due_date, COUNT(*) AS predicted_reviews
FROM srs_state s
JOIN cards c ON s.card_id = c.id
WHERE s.due >= datetime('now') AND s.due < datetime('now', '+14 days') AND c.is_suspended = 0
GROUP BY DATE(s.due) ORDER BY due_date;
```

### 5.5 Calendar Heatmap

GitHub-style calendar heatmap showing study activity per day for the past year.

```sql
SELECT date, reviews_count, time_studied_ms, new_cards_count
FROM streaks WHERE date >= date('now', '-365 days') ORDER BY date;
```

**Color scale (5 levels):**

| Level | Reviews | Color |
|---|---|---|
| 0 | 0 | Light gray |
| 1 | 1–20 | Light green |
| 2 | 21–50 | Medium green |
| 3 | 51–100 | Dark green |
| 4 | 100+ | Darkest green |

**Implementation:** `react-calendar-heatmap` or custom SVG. Clean — subtle title attribute with date and count.

### 5.6 No Gamification (Explicitly)

This app deliberately avoids: ❌ XP, ❌ Levels, ❌ Leaderboards, ❌ Hearts/lives, ❌ Leagues, ❌ Achievements/badges, ❌ Notifications (beyond optional daily reminder), ❌ Confetti.

**What we keep:** ✅ Streak counter (with freeze), ✅ Statistics dashboard, ✅ CEFR level estimate, ✅ Daily goal completion checkmark, ✅ Calendar heatmap.

---

## 6. Review Session State Machine

### 6.1 State Flow Diagram

```
                    ┌─────────┐
                    │  IDLE   │ ← User on dashboard, no active session
                    └────┬────┘
                         │ User clicks "Start Review"
                         ▼
                    ┌─────────┐
                    │ LOADING │ ← Fetch due cards from Rust backend
                    └────┬────┘
                         │ Cards loaded
                         ▼
                    ┌──────────┐
                    │ REVIEWING│ ← Session active, cards in queue
                    └────┬─────┘
                         │ Pop next card from queue
                         ▼
              ┌──────────────────┐
              │   CARD_SHOW      │ ← Display card front (audio auto-play)
              │ (front visible)  │
              └────────┬─────────┘
                       │ User presses Space or "Show Answer"
                       ▼
              ┌──────────────────┐
              │  CARD_ANSWER     │ ← Display card back + rating buttons
              │ (back visible)   │
              └────────┬─────────┘
                       │ User selects rating (1/2/3/4)
                       ▼
                   ┌────────┐
                   │ RATING │ ← Submit to Rust backend (srs_submit_review)
                   └────┬───┘
                        │ Review result received
                        ▼
                   ┌─────────────┐
                   │  NEXT_CARD  │ ← Check: more cards in queue?
                   └──────┬──────┘
                          │
                    ┌─────┴─────┐
                    │ Yes       │ No
                    ▼           ▼
              ┌──────────┐  ┌──────────────────┐
              │ CARD_SHOW│  │ SESSION_COMPLETE │ ← Show summary screen
              └──────────┘  └────────┬─────────┘
                                     │ User clicks "Done"
                                     ▼
                                ┌─────────┐
                                │  IDLE   │
                                └─────────┘
```

**Interruption path (app closed mid-review):**

```
REVIEWING/CARD_SHOW/CARD_ANSWER
  │ App closed or navigated away
  ▼
  Session state persisted to study_sessions table:
    - current_card_id = card being reviewed
    - remaining_queue = JSON array of remaining card IDs
    - is_complete = 0
  │
  │ App reopened → User clicks "Resume Session"
  ▼
  LOADING → Restore queue from study_sessions → REVIEWING
```

### 6.2 Session Interruption Handling

When the user closes the app or navigates away mid-review, the session state is persisted to the `study_sessions` table. On next launch, the dashboard detects an incomplete session and offers "Resume Session".

```rust
#[tauri::command]
pub fn srs_save_session_state(
    state: State<AppState>,
    session_id: i64,
    current_card_id: i64,
    remaining_queue: Vec<i64>,
) -> Result<(), String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "UPDATE study_sessions SET current_card_id = ?1, remaining_queue = ?2 WHERE id = ?3",
        params![current_card_id, serde_json::to_string(&remaining_queue).map_err(|e| e.to_string())?, session_id],
    ).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn srs_resume_session(
    state: State<AppState>,
    session_id: i64,
) -> Result<Option<ResumedSession>, String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    let mut stmt = conn.prepare("SELECT current_card_id, remaining_queue FROM study_sessions WHERE id = ?1 AND is_complete = 0")
        .map_err(|e| e.to_string())?;
    match stmt.query_row(params![session_id], |row| {
        let current_card_id: i64 = row.get(0)?;
        let queue_json: String = row.get(1)?;
        let queue: Vec<i64> = serde_json::from_str(&queue_json).unwrap_or_default();
        Ok(ResumedSession { current_card_id, remaining_queue: queue })
    }) {
        Ok(data) => Ok(Some(data)),
        Err(_) => Ok(None),
    }
}
```

### 6.3 Learning Steps Timing in Desktop Context

**No enforced real-time waiting.** Learning-step cards are re-queued within the session. The card is placed at the end of the review queue and re-shown before the session ends. This matches Anki's interleaving behavior.

If the user rates "Good" on a first-showing new card, it graduates immediately (due tomorrow). If "Again", it goes to the next learning step and is re-shown later in the session.

### 6.4 Keyboard Shortcuts

| Key | Action | Context |
|---|---|---|
| `Space` | Show answer (flip card) | CARD_SHOW state |
| `1` | Again | CARD_ANSWER state |
| `2` | Hard | CARD_ANSWER state |
| `3` | Good | CARD_ANSWER state |
| `4` | Easy | CARD_ANSWER state |
| `S` | Star card (toggle) | Any review state |
| `D` | Delete/suspend card | Any review state (with confirmation) |
| `U` | Undo last review | Any review state |
| `Esc` | End session early | REVIEWING state (with confirmation) |
| `R` | Replay audio | CARD_SHOW or CARD_ANSWER |

**Implementation (React):**

```typescript
// src/hooks/useReviewShortcuts.ts
useEffect(() => {
  if (!shortcutsEnabled) return;

  const handler = (e: KeyboardEvent) => {
    if (e.key === ' ' && phase === 'show') { e.preventDefault(); flipCard(); }
    else if (phase === 'answer') {
      if (e.key === '1') submitRating(1);
      else if (e.key === '2') submitRating(2);
      else if (e.key === '3') submitRating(3);
      else if (e.key === '4') submitRating(4);
    }
    if (e.key === 's') toggleStar();
    if (e.key === 'r') replayAudio();
    if (e.key === 'Escape') confirmEndSession();
  };

  window.addEventListener('keydown', handler);
  return () => window.removeEventListener('keydown', handler);
}, [phase, shortcutsEnabled]);
```

### 6.5 Session Summary Screen

After session completion, display:

```
┌─────────────────────────────────────┐
│         Session Complete            │
│                                     │
│  Reviewed:           87 cards       │
│  Again:              8  (9%)        │
│  Hard:              12  (14%)       │
│  Good:              55  (63%)       │
│  Easy:              12  (14%)       │
│                                     │
│  Time:           14m 32s            │
│  Retention:         91%             │
│  New cards:         15              │
│                                     │
│  Streak: 🔥 12 days                 │
│                                     │
│  [ Done ]    [ Review Again ]       │
└─────────────────────────────────────┘
```

**Data source:**

```sql
SELECT
    COUNT(*) AS reviewed,
    SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) AS again,
    SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) AS hard,
    SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) AS good,
    SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) AS easy,
    SUM(duration_ms) AS total_time_ms,
    ROUND(CAST(SUM(CASE WHEN rating >= 3 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 1) AS retention_pct
FROM review_logs
WHERE reviewed_at >= ?1  -- session start time
  AND reviewed_at <= ?2; -- session end time
```

---

## 7. Mistake Tracking and Adaptive Review

### 7.1 Error Categorization

Errors are categorized by type, enabling targeted weakness analysis. Inspired by deutsch-ai-tutor's pattern (MIT-licensed reference).

| Error Type | Description | Example | Triggered By Card Types |
|---|---|---|---|
| `article_error` | Wrong gender/article | "der Haus" instead of "das Haus" | `article`, `basic_vocab`, `cloze` |
| `case_error` | Wrong grammatical case | "Ich gebe den Mann das Buch" (should be "dem") | `cloze`, `grammar_mc` |
| `word_order_error` | Incorrect word arrangement | "Ich ein Buch lese" instead of "Ich lese ein Buch" | `word_order` |
| `spelling_error` | Misspelled word | "Hause" instead of "Haus" | `basic_vocab`, `conjugation`, `cloze` |
| `translation_error` | Wrong translation | "Buch" → "pen" instead of "book" | `basic_vocab` |
| `conjugation_error` | Wrong verb form | "ich ist" instead of "ich bin" | `conjugation`, `cloze` |

### 7.2 Mistake Tracking System

When a user rates "Again" or "Hard" on an exercise-type card, the mistake is logged with its category. The frontend determines the error type by comparing the user's answer to the correct answer.

```rust
#[tauri::command]
pub fn srs_log_mistake(
    state: State<AppState>,
    card_id: i64,
    mistake_type: String,
    user_answer: String,
    correct_answer: String,
    context: String,
    grammar_category: String,
    cefr_level: String,
) -> Result<(), String> {
    let conn = state.db.lock().map_err(|e| e.to_string())?;
    conn.execute(
        "INSERT INTO mistake_history (card_id, mistake_type, user_answer, correct_answer, context, grammar_category, cefr_level)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
        params![card_id, mistake_type, user_answer, correct_answer, context, grammar_category, cefr_level],
    ).map_err(|e| e.to_string())
}
```

**Frontend error classification:**

```typescript
// src/lib/mistakeClassifier.ts
export function classifyMistake(
  cardType: string,
  userAnswer: string,
  correctAnswer: string,
  extra: any
): string | null {
  if (userAnswer === correctAnswer) return null; // No mistake

  switch (cardType) {
    case 'article':
      return 'article_error';
    case 'conjugation':
      return 'conjugation_error';
    case 'word_order':
      return 'word_order_error';
    case 'cloze':
      // Determine if it's a case error or conjugation error based on cloze_type
      if (extra?.cloze_type === 'case') return 'case_error';
      if (extra?.cloze_type === 'verb_conjugation') return 'conjugation_error';
      return 'spelling_error';
    case 'grammar_mc':
      // Determine category from the question topic
      if (extra?.rule_id?.includes('case')) return 'case_error';
      if (extra?.rule_id?.includes('article')) return 'article_error';
      if (extra?.rule_id?.includes('word_order')) return 'word_order_error';
      return 'case_error'; // Default for grammar
    case 'basic_vocab':
      // Check if it's a translation or spelling error
      if (userAnswer.toLowerCase() === correctAnswer.toLowerCase()) return null;
      const editDistance = levenshtein(userAnswer, correctAnswer);
      if (editDistance <= 2) return 'spelling_error';
      return 'translation_error';
    default:
      return 'spelling_error';
  }
}
```

### 7.3 Weighted Review Queue Selection

Inspired by deutsch-ai-tutor's adaptive quiz pattern (40% weak items, 30% SRS due, 30% random), we weight the review queue to prioritize weak areas.

**Queue composition with mistake weighting:**

```rust
pub fn build_adaptive_review_queue(
    conn: &Connection,
    deck_ids: &[i64],
    limits: &SessionLimits,
) -> Result<Vec<i64>, rusqlite::Error> {
    // 1. Get SRS-due cards (standard FSRS scheduling)
    let due_cards = get_due_review_cards(conn, deck_ids, limits.review_limit)?;

    // 2. Get weak cards (cards with recent mistakes, not yet due)
    let weak_cards = get_weak_cards(conn, deck_ids, limits.review_limit / 3)?;

    // 3. Get new cards
    let new_cards = get_new_cards(conn, deck_ids, limits.new_card_limit)?;

    // 4. Get learning/relearning cards (in-session steps)
    let learning_cards = get_learning_cards(conn, deck_ids)?;

    // 5. Compose queue:
    //    - Learning cards first (in-session priority)
    //    - Then interleave: 40% weak, 30% due, 30% new
    let mut queue = Vec::new();
    queue.extend(learning_cards);

    let mut w_idx = 0;  // weak
    let mut d_idx = 0;  // due
    let mut n_idx = 0;  // new
    let wc = weak_cards.len();
    let dc = due_cards.len();
    let nc = new_cards.len();

    // Round-robin with 40/30/30 weighting (simplified: 2 weak : 2 due : 1 new per cycle, approximating 40/40/20)
    // Adjusted to prioritize weak items while maintaining SRS schedule
    while w_idx < wc || d_idx < dc || n_idx < nc {
        // 2 weak cards
        for _ in 0..2 { if w_idx < wc { queue.push(weak_cards[w_idx]); w_idx += 1; } }
        // 2 due cards
        for _ in 0..2 { if d_idx < dc { queue.push(due_cards[d_idx]); d_idx += 1; } }
        // 1 new card
        if n_idx < nc { queue.push(new_cards[n_idx]); n_idx += 1; }
    }

    Ok(queue)
}

/// Get cards with recent mistakes that aren't yet due.
/// Prioritizes cards with more mistakes and more recent mistakes.
fn get_weak_cards(conn: &Connection, deck_ids: &[i64], limit: u32) -> Result<Vec<i64>, rusqlite::Error> {
    let mut stmt = conn.prepare(
        "SELECT c.id, COUNT(m.id) AS mistake_count, MAX(m.occurred_at) AS last_mistake
         FROM cards c
         JOIN mistake_history m ON c.id = m.card_id
         JOIN srs_state s ON c.id = s.card_id
         WHERE c.deck_id IN (/* deck_ids */)
           AND c.is_suspended = 0
           AND m.occurred_at >= datetime('now', '-7 days')
           AND s.due > datetime('now')  -- Not yet due
         GROUP BY c.id
         ORDER BY mistake_count DESC, last_mistake DESC
         LIMIT ?1"
    )?;
    // ... execute and collect
}
```

**Weighting rationale:**
- **40% weak items:** Cards the user recently got wrong are re-shown sooner than FSRS would schedule. This reinforces learning from mistakes.
- **30% SRS due:** Standard FSRS-scheduled reviews maintain the spaced repetition integrity.
- **30% new:** New cards continue to be introduced, ensuring progression.
- The 40/30/30 split is configurable via a setting (`adaptive_queue_weights`).

### 7.4 Weak Area Surfacing

The dashboard includes a "Weak Areas" widget that shows the user's grammar weak spots based on mistake history.

**Weak areas query:**

```sql
SELECT
    grammar_category,
    mistake_type,
    COUNT(*) AS error_count,
    ROUND(CAST(SUM(CASE WHEN r.rating = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 1) AS again_pct
FROM mistake_history m
JOIN review_logs r ON m.card_id = r.card_id
WHERE m.occurred_at >= datetime('now', '-30 days')
GROUP BY grammar_category, mistake_type
ORDER BY error_count DESC
LIMIT 5;
```

**Dashboard widget display:**

```
┌─────────────────────────────────────┐
│  Weak Areas (last 30 days)          │
│                                     │
│  ⚠️ Akkusativ (cases)    23 errors  │
│  ⚠️ der/die/das (articles) 18 errors│
│  ⚠️ Präteritum (verbs)   12 errors  │
│                                     │
│  [ Practice Weak Areas ]            │
└─────────────────────────────────────┘
```

The "Practice Weak Areas" button starts a focused review session containing only cards from the weak categories — bypassing the normal FSRS schedule for a targeted practice session.

**Per-card mistake summary (card detail view):**

```sql
SELECT
    mistake_type,
    user_answer,
    correct_answer,
    occurred_at
FROM mistake_history
WHERE card_id = ?1
ORDER BY occurred_at DESC
LIMIT 10;
```

This shows the user's recent mistakes on a specific card, helping them understand what they keep getting wrong.

---

## 8. Next Steps for Orchestrator

### Implementation Priorities

| Priority | Task | Dependency | Est. Effort |
|---|---|---|---|
| **P0** | Scaffold Tauri 2 project (React 19 + TS + Tailwind + Zustand) | None | S (1-2 days) |
| **P0** | Implement Rust DB layer: `init_database()`, ATTACH content.db, schema migrations | Tauri scaffold | S (1 day) |
| **P0** | Integrate `fsrs` crate: `FSRS::default()`, `next_states()`, `apply_rating()` | DB layer | M (2-3 days) |
| **P0** | Implement Tauri IPC commands: `srs_get_due_cards`, `srs_submit_review` | FSRS integration | M (2-3 days) |
| **P0** | Build review session UI: card renderer, flashcard flip, 4-button rating, keyboard shortcuts | IPC commands | M (3-5 days) |
| **P0** | Create built-in decks from content.db (A1-B2 vocab, A1-B1 grammar) | DB layer + content.db | S (1 day) |
| **P1** | Deck management UI: create/edit decks, card list, tag filtering | Review UI | M (2-3 days) |
| **P1** | Dashboard: streak counter, reviews today, retention rate, card state counts | IPC commands | M (2-3 days) |
| **P1** | Settings page: desired retention, daily limits, theme, audio settings | None | S (1 day) |
| **P1** | Session interruption recovery: save/resume session state | Review UI | S (1 day) |
| **P2** | Card type components: cloze, article, conjugation, grammar_mc, word_order | Review UI | M (3-5 days) |
| **P2** | Grammar lesson reader: markdown rendering, navigation by topic/CEFR | Content.db | M (2-3 days) |
| **P2** | Mistake tracking: error classification, mistake_history logging | Review UI | S (1-2 days) |
| **P2** | CEFR level estimation algorithm | Review logs (1000+ reviews) | S (1 day) |
| **P2** | Calendar heatmap + forecast graph | Streaks data | S (1-2 days) |
| **P3** | Adaptive review queue (40/30/30 weak/due/new weighting) | Mistake tracking | M (2-3 days) |
| **P3** | Weak areas dashboard widget + "Practice Weak Areas" session | Mistake tracking | S (1-2 days) |
| **P3** | FSRS parameter optimization UI (enabled at 1000+ reviews) | 1000+ review logs | M (2-3 days) |
| **P3** | Listening comprehension: audio player, transcript, comprehension questions | Content.db + audio | M (3-5 days) |
| **P3** | Reading comprehension: passage reader, progress tracking, comprehension questions | Content.db | M (3-5 days) |
| **P4** | Anki .apkg import (SM-2 → FSRS migration) | FSRS integration | M (2-3 days) |
| **P4** | Custom card creation UI (manual word entry, auto-enrich from content.db) | Content.db | S (1-2 days) |
| **P4** | Streak freeze logic (auto-consume, regeneration) | Streaks | S (1 day) |
| **P4** | Daily goals progress bars | Streaks + settings | S (1 day) |

### Architecture Decisions Confirmed

| # | Decision | Choice |
|---|---|---|
| 1 | SRS engine | `fsrs-rs` crate in Rust backend (not ts-fsrs) |
| 2 | Database | Two SQLite files: content.db (read-only) + user.db (runtime), ATTACH pattern |
| 3 | ID strategy | Auto-increment integers |
| 4 | FSRS presets | Vocab 90%, Grammar 95%, Listening 85%, Reading = no SRS |
| 5 | Review queue | Unified (all due cards mixed), type-aware rendering |
| 6 | Learning steps | No enforced timing — re-queue within session |
| 7 | Card storage | Unified `cards` table with `card_type` + `extra` JSON |
| 8 | Cross-DB FKs | Soft references (no SQLite enforcement across ATTACH) |
| 9 | Gamification | Light only: streaks, stats, heatmap. No XP/leagues/hearts |
| 10 | Adaptive queue | 40% weak / 30% due / 30% new (configurable) |

### Open Questions for Orchestrator

1. **Content.db generation timeline:** The Python data pipeline (10 scripts) must produce content.db before the app can function. Should this run in parallel with app development, or is content.db already available from Agent 2/3 work?
2. **Audio bundling strategy:** Full audio (~1.1 GB) vs optimized (~700 MB) vs minimal (~300 MB). Affects download size and time-to-first-use.
3. **Initial content seeding:** When the app first launches, should it auto-create decks from content.db (A1-B2 vocab, A1-B1 grammar), or should the user manually select which decks to create?
4. **FSRS version pinning:** Which version of the `fsrs` crate to pin in Cargo.toml? Latest stable vs specific version for reproducibility.
5. **Android ATTACH path:** On Android, content.db is copied from APK assets to app data dir on first launch. Need to verify the ATTACH path works correctly with Android's sandboxed file system.

---

*End of document. Research conducted 2026-08-02. Based on fsrs-rs API (github.com/open-spaced-repetition/fsrs-rs), FlexiLingo Desk architecture study, and Phase 1 research from Agents 1-3.*
