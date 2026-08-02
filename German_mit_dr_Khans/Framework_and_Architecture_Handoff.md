# Framework & Architecture Handoff

**Project:** German mit Dr. Khans — Desktop-first German learning app  
**Date:** 2026-08-02  
**Prepared by:** Research Agent  
**Target platform:** Windows (desktop-first), Android (future migration)

---

## Executive Recommendation

**Recommendation: Tauri 2 + React + TypeScript**  
**Confidence: High (85%)**

Tauri 2 is the recommended framework for this project. It is stable at v2.11.5 (July 2026), has been production-ready on desktop since October 2024, and offers the smallest possible pivot cost given the user's existing TypeScript/React expertise. The Android target is functional with real-world shipped apps, though it requires accepting some maturity gaps (no auto-updater on mobile, plugin coverage varies). The Rust learning curve is the primary risk, but for an offline-first learning app the Rust surface area is minimal — most logic lives in the TypeScript frontend.

Flutter is a viable fallback but requires learning Dart, a new widget paradigm, and code generation tooling (drift). It should be kept as a contingency, not a first choice.

| Criterion | Tauri 2 | Flutter |
|---|---|---|
| Leverages existing TS/React skills | ✅ Direct | ❌ New language + paradigm |
| Desktop (Windows) maturity | ✅ Stable, production-ready | ✅ Stable, Canonical-led |
| Android maturity | ⚠️ Functional, maturing | ✅ First-class, primary target |
| Binary size (Windows) | ~3–10 MB | ~20–30 MB |
| SRS library | `ts-fsrs` (FSRS v6) | `dart-fsrs` v2.0.0 |
| SQLite | `tauri-plugin-sql` or `rusqlite` | `drift` (type-safe, codegen) |
| Auto-updater (desktop) | ✅ Built-in plugin | ❌ Manual / third-party |
| Auto-updater (Android) | ❌ Not supported | ✅ Via Google Play |
| Offline audio | ✅ HTML5 Audio + asset protocol | ✅ `audioplayers` / `just_audio` |
| Code sharing desktop→mobile | ✅ Shared frontend, platform-specific Rust | ✅ Single codebase, all platforms |
| Learning curve | Low (TS/React known, minimal Rust) | Medium (Dart, widget system, codegen) |

---

## 1. Tauri 2 Desktop (Windows)

### 1.1 Current Stable Version & Maturity

- **Latest stable:** v2.11.5 (July 1, 2026)
- **Stable since:** October 2, 2024 (v2.0.0 promoted to stable)
- **Release cadence:** Frequent point releases (2–4 weeks apart in 2026)
- **GitHub:** 109K+ stars, 1,424 open issues, active development
- **Status badge:** `stable` on GitHub README
- **Verdict:** Production-ready for Windows desktop. No concerns about maturity.

### 1.2 Project Setup

Use the `create-tauri-app` wizard with React + TypeScript template:

```bash
npm create tauri-app@latest
# Choose: Project name → german-mit-dr-khans
# Choose: Frontend → React / TypeScript
# Choose: Package manager → npm (or pnpm)
```

This generates:
- `src/` — React + TypeScript frontend (Vite-bundled)
- `src-tauri/` — Rust backend with `main.rs`, `Cargo.toml`, `tauri.conf.json`
- Vite config pre-wired for Tauri dev server

### 1.3 SQLite Integration

Two viable approaches:

#### Option A: `tauri-plugin-sql` (Official, Recommended)

- Uses `sqlx` under the hood
- Official Tauri plugin, maintained by the Tauri team
- JavaScript bindings: `@tauri-apps/plugin-sql`
- Supports SQLite, MySQL, PostgreSQL (enable `sqlite` feature)
- No transaction support in the JS API (use Rust commands for transactions)

```toml
# src-tauri/Cargo.toml
cargo add tauri-plugin-sql --features sqlite
```

```typescript
// Frontend usage
import Database from '@tauri-apps/plugin-sql';
const db = await Database.load('sqlite:german.db');
await db.execute('INSERT INTO vocab ...');
const rows = await db.select('SELECT * FROM vocab WHERE ...');
```

**Pros:** Official, well-documented, simple JS API.  
**Cons:** No explicit transaction control from JS side; uses async sqlx pool.

#### Option B: `tauri-plugin-rusqlite2` (Community, Advanced)

- Uses `rusqlite` (synchronous, bundled SQLite)
- Community fork with transaction support, migrations, SQLCipher
- Better for complex transactional workflows
- v2.2.8 on crates.io

```toml
# src-tauri/Cargo.toml
[dependencies]
tauri-plugin-rusqlite2 = "2.2"
```

**Pros:** Transactions, migrations, SQLCipher encryption, bundled SQLite.  
**Cons:** Community-maintained fork, more Rust code required.

#### Recommendation

Start with **`tauri-plugin-sql`** (Option A) for simplicity. The JS API is sufficient for a vocab/SRS app. If transactional complexity grows (e.g., atomic review + scheduling updates), write custom Tauri commands in Rust that use `rusqlite` directly, or switch to Option B.

### 1.4 Audio Playback (Offline)

Tauri 2 uses the system WebView (WebView2 on Windows). Audio playback works via the HTML5 Audio API with Tauri's asset protocol:

1. **Bundle audio files** as Tauri resources in `tauri.conf.json`:
```json
{
  "bundle": {
    "resources": ["assets/audio/**/*.mp3"]
  }
}
```

2. **Configure CSP** to allow media from the asset protocol:
```json
{
  "security": {
    "csp": "default-src 'self'; media-src 'self' asset: https://asset.localhost",
    "assetProtocol": {
      "enable": true,
      "scope": ["**"]
    }
  }
}
```

3. **Play audio from frontend:**
```typescript
import { join, resourceDir } from '@tauri-apps/api/path';
import { convertFileSrc } from '@tauri-apps/api/core';

const resourceDirPath = await resourceDir();
const filePath = await join(resourceDirPath, 'assets/audio/lesson01_greeting.mp3');
const audioUrl = convertFileSrc(filePath);
const audio = new Audio(audioUrl);
await audio.play();
```

**Supported formats:** MP3, WAV, OGG, FLAC, M4A, M4B (whatever WebView2 supports).

**For Web Audio API (equalizer, visualization):** A custom protocol with CORS headers may be needed, as demonstrated by the ABPlayer project (registers `audiostream://` protocol in Rust). For basic playback, the asset protocol is sufficient.

### 1.5 File System Access (Importing Texts/Articles)

Use `tauri-plugin-fs` for reading/writing files from the frontend:

```toml
# src-tauri/Cargo.toml
cargo add tauri-plugin-fs
```

```typescript
import { readTextFile, readFile, exists, BaseDirectory } from '@tauri-apps/plugin-fs';

// Read a text file the user imported
const content = await readTextFile('articles/goethe_faust.txt', {
  baseDir: BaseDirectory.AppData,
});
```

**For file picker dialogs**, use `tauri-plugin-dialog`:

```typescript
import { open } from '@tauri-apps/plugin-dialog';

const filePath = await open({
  filters: [{ name: 'Text files', extensions: ['txt', 'md', 'json'] }],
  multiple: false,
});
```

**Security model:** The fs plugin uses scope-based access control (glob patterns). Configure allowed paths in capabilities JSON:

```json
{
  "permissions": [
    "fs:allow-read-text-file",
    "fs:allow-write-text-file",
    {
      "identifier": "fs:scope",
      "allow": ["$APPDATA/**/*", "$RESOURCE/**/*"]
    }
  ]
}
```

### 1.6 Bundle Size & Memory on Windows

**Bundle size:**
- Minimal Tauri 2 app: ~2.5–3 MB (binary only)
- Realistic app with plugins (sql, fs, dialog, updater): ~5–10 MB
- WebView2 runtime: NOT bundled by default (system-installed on Windows 10/11). Can optionally embed bootstrapper (+1.8 MB) or offline installer (+127 MB) for Windows 7/8 support.
- For comparison: Electron apps typically start at 60–100 MB.

**Memory:**
- Typical idle: ~50–100 MB RAM (WebView2 process)
- WebView2 has a ~2 GB memory ceiling (Chromium-based)
- Known issue: WebView2 cache directory can grow to 200+ MB over time (`EBWebView/` folder with shader caches). Tauri v2 provides `clear_all_browsing_data()` API. For a learning app with modest UI, this is unlikely to be a problem.
- **Mitigation:** Avoid pushing large data via `Eval/ExecJS` from Rust to frontend. Use pull-based IPC (frontend calls Tauri commands to fetch data).

### 1.7 Auto-Update Mechanism

Tauri 2 provides a first-party updater plugin (`tauri-plugin-updater`):

```toml
# src-tauri/Cargo.toml (desktop only)
[target."cfg(not(any(target_os = \"android\", target_os = \"ios\")))".dependencies]
tauri-plugin-updater = "2"
```

**How it works:**
1. Generate signing key pair: `npx tauri signer generate -w ~/.tauri/german.key`
2. Configure endpoint in `tauri.conf.json`:
```json
{
  "plugins": {
    "updater": {
      "endpoints": ["https://your-domain.com/updates/latest.json"],
      "pubkey": "YOUR_PUBLIC_KEY"
    }
  }
}
```
3. Build with signing: `TAURI_SIGNING_PRIVATE_KEY=... npm run tauri build`
4. Host a static JSON manifest + installer bundle (GitHub Releases, S3, etc.)
5. Check for updates in frontend:
```typescript
import { check } from '@tauri-apps/plugin-updater';
import { relaunch } from '@tauri-apps/plugin-process';

const update = await check();
if (update) {
  await update.downloadAndInstall();
  await relaunch();
}
```

**Windows install modes:** `passive` (default, progress bar, no interaction), `basicUi`, `quiet`.

**Platform support:** ✅ Windows, ✅ macOS, ✅ Linux, ❌ Android, ❌ iOS.

### 1.8 Known Windows-Specific Issues

| Issue | Severity | Mitigation |
|---|---|---|
| WebView2 cache growth (200+ MB) | Low | Call `clear_all_browsing_data()` on startup; not critical for a learning app |
| WebView2 ~2 GB memory ceiling | Low | Avoid large data via Eval; use pull-based IPC |
| Bundle size doubled from v1→v2 (~3→6 MB) | Low | Fixed in #12890 (dead code elimination); acceptable for personal use |
| WebView2 not preinstalled on Windows 7/8 | Low | Embed bootstrapper (+1.8 MB) or require Win10+ |
| Rust compilation is slow (first build) | Low | Use `sccache`, incremental compilation; only affects dev experience |

---

## 2. Tauri 2 Android

### 2.1 Current Maturity

- **Status:** Stable (part of v2.0.0 stable release since Oct 2024)
- **Minimum Android version:** Android 7.0 (Nougat, SDK 24), practically Android 8.0+
- **Runtime:** Android System WebView (Chromium-based)
- **Tauri team's own assessment:** "You can develop production ready mobile applications with Tauri NOW" but "don't want to raise expectations that Tauri 2.0 will be the 'mobile as a first class citizen' release"
- **Verdict:** Functional and shipped by multiple apps, but less battle-tested than the desktop target. Expect occasional rough edges.

### 2.2 Build Process

**Prerequisites:**
- Android Studio (latest)
- Android SDK + NDK
- Rust Android targets: `rustup target add aarch64-linux-android armv7-linux-androideabi i686-linux-android x86_64-linux-android`
- Tauri CLI: `npm run tauri android init` (one-time setup)

**Build commands:**
```bash
npm run tauri android init    # Generate Android project scaffold
npm run tauri android dev     # Dev mode (connects to device/emulator)
npm run tauri android build   # Production APK/AAB
```

**Output:** Universal APK/AAB (all architectures) or per-ABI split with `--split-per-abi`.

**Google Play distribution:** Tauri generates standard AAB files. No automated Play Store upload (manual or via CI/CD with `gradlew`).

### 2.3 Known Limitations vs Desktop

| Feature | Desktop | Android |
|---|---|---|
| Auto-updater | ✅ `tauri-plugin-updater` | ❌ Not supported |
| System tray | ✅ | ❌ |
| Custom protocols | ✅ Full support | ⚠️ Limited (resources use `asset://localhost/` prefix) |
| File system access | ✅ Full `tauri-plugin-fs` | ⚠️ Sandboxed; resources stored in APK assets |
| Window management | ✅ Multi-window | ❌ Single window |
| Native menus | ✅ | ❌ |

### 2.4 Plugin Availability on Android

| Plugin | Desktop | Android | Notes |
|---|---|---|---|
| `tauri-plugin-sql` (SQLite) | ✅ | ✅ | Works via sqlx with bundled SQLite |
| `tauri-plugin-fs` | ✅ | ✅ | Sandboxed; resources accessed via `asset://localhost/` |
| `tauri-plugin-dialog` | ✅ | ✅ | Native dialogs |
| `tauri-plugin-updater` | ✅ | ❌ | Desktop only |
| `tauri-plugin-process` | ✅ | ✅ | |
| `tauri-plugin-notification` | ✅ | ✅ | |
| `tauri-plugin-store` | ✅ | ✅ | Key-value store |

### 2.5 UI Responsiveness on Mobile

- Uses **Android System WebView** (Chromium-based, auto-updated via Google Play)
- Performance is comparable to a Chrome tab — generally smooth for list/card-based UIs
- Not native rendering (no Skia/Impeller), but for a learning app (flashcards, text, audio) this is perfectly adequate
- Responsive CSS + Tailwind handles desktop/mobile layout switching

### 2.6 Real-World Apps Shipped on Android with Tauri 2

| App | Description | Stack |
|---|---|---|
| **LettuceAI** | AI roleplay & storytelling app, 156 releases, desktop + Android | Tauri v2, React, TypeScript |
| **Baajit** | ADHD task/habit manager, Android APK available (51 MB) | Tauri v2, React 19, TanStack Router, SQLite |
| **Terax** | Terminal-first AI dev workspace, Android port | Tauri 2, React 19, xterm.js |
| **zelland** | SSH terminal client for Android + Linux | Tauri v2, Svelte 5, wgpu |
| **ABPlayer** | Offline audiobook player (desktop, demonstrates audio + Tauri 2) | Tauri v2, Svelte 5 |

**Key takeaway:** Multiple production Android apps exist. The pattern is: build desktop first, then `tauri android init` + adjust for mobile-specific issues. Baajit is particularly relevant — it's a React + SQLite + Tauri 2 app on Android.

### 2.7 Estimated Migration Effort (Desktop → Android)

| Task | Effort | Notes |
|---|---|---|
| `tauri android init` + toolchain setup | 2–4 hours | Install Android Studio, NDK, Rust targets |
| Responsive CSS / mobile layout | 1–2 days | Tailwind responsive classes, mobile-specific components |
| Test SQLite on Android | 2–4 hours | Verify `tauri-plugin-sql` works on Android (it does) |
| Audio playback on Android | 2–4 hours | Asset protocol differs slightly (`asset://localhost/`) |
| Disable/replace updater | 1 hour | Conditional compilation: `#[cfg(desktop)]` |
| Handle file system sandboxing | 2–4 hours | Resources in APK, app data dir differs |
| Testing + bug fixing | 2–5 days | WebView quirks, touch interactions, keyboard handling |
| **Total estimated effort** | **~1–2 weeks** | For a single developer familiar with the codebase |

---

## 3. Flutter as Fallback

### 3.1 Flutter Desktop on Windows — Maturity

- **Current version:** Flutter 3.44 (mid-2026)
- **Desktop status:** Stable on Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+)
- **Canonical partnership:** As of Google I/O 2026, Canonical is now the lead maintainer and strategic steward for Flutter Desktop (Windows, macOS, Linux embedders)
- **Impeller renderer:** Now the default on Windows (as of June 2026 commit), replacing the legacy Canvas/Skia backend
- **Multi-window support:** Experimental (tooltips, popups, content-sized windows)
- **Verdict:** Mature and production-ready for Windows desktop. Canonical's involvement signals long-term commitment.

### 3.2 Flutter + dart-fsrs for SRS

- **Package:** `fsrs` v2.0.0 on pub.dev
- **Algorithm:** FSRS (Free Spaced Repetition Scheduler)
- **API:**
```dart
import 'package:fsrs/fsrs.dart';

var scheduler = Scheduler();
final card = await Card.create();
final (updatedCard, reviewLog) = scheduler.review(card, Rating.Good);
```
- **Features:** Custom parameters, learning/relearning steps, fuzzing, serialization/deserialization, retrievability calculation
- **Verdict:** Fully functional, mirrors the TypeScript `ts-fsrs` API

### 3.3 Flutter SQLite (sqflite, drift)

#### sqflite
- SQLite plugin for Flutter
- Supports iOS, Android, macOS natively
- Linux/Windows/DartVM via `sqflite_common_ffi`
- Raw SQL strings, no type safety, no code generation
- Simpler but less powerful

#### drift (Recommended for Flutter)
- Type-safe, reactive persistence library built on SQLite
- Code generation for DAOs, data classes, companions
- Cross-platform: Android, iOS, Windows, Linux, macOS, Web (WASM)
- Uses `NativeDatabase` from `package:drift/native.dart` (FFI-based) for desktop + mobile
- Starting from drift v2.32.0, SQLite is automatically bundled (no `sqlite3_flutter_libs` needed)
- Built-in reactive streams (`watch()` queries), structured migrations, transactions
- **Verdict:** Best-in-class for Flutter local databases

```yaml
# pubspec.yaml
dependencies:
  drift: ^2.34.2
  path_provider: ^2.1.4
dev_dependencies:
  drift_dev: ^2.34.5
  build_runner: ^2
```

### 3.4 Code Sharing Between Flutter Desktop and Android

- **Single codebase** for all platforms (Android, iOS, Windows, macOS, Linux, Web)
- Platform-specific code via conditional imports or platform channels
- Database backend selection:
  - Mobile + Desktop: `NativeDatabase` (FFI, bundled SQLite)
  - Web: `WasmDatabase` (SQLite compiled to WASM)
- No separate "desktop" vs "mobile" codebases — same Dart code runs everywhere
- **Verdict:** Superior code sharing compared to Tauri 2 (where Rust backend may need platform-specific code)

### 3.5 Learning Curve for TS/React Developer

| Concept | Effort |
|---|---|
| Dart language | Low–Medium (similar to TS, strong typing, async/await) |
| Widget tree (vs JSX) | Medium (declarative but different mental model) |
| State management (Riverpod/Provider) | Medium (similar to React Context/Zustand) |
| Code generation (drift, build_runner) | Low (automated, just run `build_runner`) |
| Flutter tooling (flutter CLI, pub) | Low (similar to npm/cargo) |
| No HTML/CSS | Medium (Flutter uses its own layout system, no CSS) |
| **Overall** | **~1–2 weeks to become productive** |

---

## 4. Architecture Sketch

### 4.1 Proposed Project Structure (Monorepo)

```
german-mit-dr-khans/
├── src/                          # React + TypeScript frontend
│   ├── components/               # Reusable UI components
│   │   ├── Flashcard.tsx         # SRS flashcard component
│   │   ├── FlashcardReview.tsx   # Review session UI
│   │   ├── GrammarLesson.tsx     # Grammar lesson viewer
│   │   ├── ReadingText.tsx       # Reading comprehension text viewer
│   │   ├── AudioPlayer.tsx       # Audio playback component
│   │   ├── ProgressChart.tsx     # SRS statistics / progress
│   │   └── Sidebar.tsx           # Navigation sidebar
│   ├── pages/                    # Route-level pages
│   │   ├── Dashboard.tsx         # Home / overview
│   │   ├── VocabReview.tsx       # SRS review session
│   │   ├── VocabList.tsx         # Browse/manage vocabulary
│   │   ├── Grammar.tsx           # Grammar lessons list + detail
│   │   ├── Reading.tsx           # Reading comprehension
│   │   ├── Listening.tsx         # Listening comprehension
│   │   ├── Settings.tsx          # App settings
│   │   └── Import.tsx            # Import texts/articles
│   ├── hooks/                    # Custom React hooks
│   │   ├── useDatabase.ts        # SQLite connection hook
│   │   ├── useSrs.ts             # FSRS scheduling hook
│   │   ├── useAudio.ts           # Audio playback hook
│   │   └── useReviewSession.ts   # Review session state machine
│   ├── lib/                      # Core logic (non-React)
│   │   ├── db.ts                 # Database initialization + queries
│   │   ├── srs.ts                # ts-fsrs scheduler wrapper
│   │   ├── audio.ts              # Audio file resolution + playback
│   │   ├── import.ts             # Text/article import logic
│   │   └── migrations.ts         # DB schema migrations
│   ├── store/                    # Zustand state stores
│   │   ├── reviewStore.ts        # Current review session state
│   │   ├── settingsStore.ts      # User preferences
│   │   └── navStore.ts           # Navigation / UI state
│   ├── types/                    # TypeScript type definitions
│   │   ├── vocab.ts              # Vocab card types
│   │   ├── grammar.ts            # Grammar lesson types
│   │   ├── reading.ts            # Reading text types
│   │   └── srs.ts                # FSRS card/review types
│   ├── styles/                   # Global styles
│   │   └── globals.css           # Tailwind directives + base styles
│   ├── App.tsx                   # Root component + router
│   ├── main.tsx                  # Entry point
│   └── vite-env.d.ts             # Vite type declarations
├── src-tauri/                    # Rust backend
│   ├── src/
│   │   ├── main.rs               # Entry point (desktop)
│   │   ├── lib.rs                # Plugin registration, mobile entry point
│   │   ├── commands.rs           # Tauri commands (IPC handlers)
│   │   └── migrations.rs         # DB migration SQL (if using Rust-side)
│   ├── capabilities/             # Permission configurations
│   │   └── main.json             # fs, sql, dialog, updater permissions
│   ├── gen/                      # Generated Android/iOS projects
│   │   └── android/              # (created by `tauri android init`)
│   ├── Cargo.toml                # Rust dependencies
│   ├── tauri.conf.json           # Tauri configuration
│   └── build.rs                  # Build script
├── assets/                       # Bundled offline content
│   ├── audio/                    # Audio files (MP3)
│   │   ├── vocab/                # Vocabulary pronunciation
│   │   ├── grammar/              # Grammar lesson audio
│   │   └── listening/            # Listening comprehension audio
│   ├── texts/                    # Reading texts (JSON/Markdown)
│   │   ├── articles/
│   │   └── stories/
│   └── data/                     # Seed data
│       └── seed_vocab.json       # Initial vocabulary deck
├── public/                       # Static assets served by Vite
│   └── icon.png
├── package.json                  # Node.js dependencies
├── tsconfig.json                 # TypeScript config
├── vite.config.ts                # Vite config (Tauri integration)
├── tailwind.config.js            # Tailwind CSS config
├── postcss.config.js             # PostCSS config
└── README.md                     # Project documentation
```

### 4.2 State Management

**Recommended: Zustand**

- Minimal boilerplate, no providers/context trees
- Perfect for a personal app — simple, fast, TypeScript-native
- Works seamlessly with Tauri's async IPC

```typescript
// store/reviewStore.ts
import { create } from 'zustand';
import { fetchDueCards, submitReview } from '../lib/db';

interface ReviewState {
  dueCards: VocabCard[];
  currentIndex: number;
  isLoading: boolean;
  loadDueCards: () => Promise<void>;
  submitReview: (cardId: string, rating: Rating) => Promise<void>;
}

export const useReviewStore = create<ReviewState>((set, get) => ({
  dueCards: [],
  currentIndex: 0,
  isLoading: false,
  loadDueCards: async () => {
    set({ isLoading: true });
    const cards = await fetchDueCards();
    set({ dueCards: cards, currentIndex: 0, isLoading: false });
  },
  submitReview: async (cardId, rating) => {
    await submitReview(cardId, rating);
    const next = get().currentIndex + 1;
    set({ currentIndex: next });
  },
}));
```

**Alternatives considered:**
- **Jotai:** Atomic state, good for fine-grained reactivity. Overkill for this app's state shape.
- **Redux Toolkit:** Too much boilerplate for a personal app. Zustand covers the same ground with 1/10th the code.

### 4.3 Database Schema Approach

SQLite via `tauri-plugin-sql`. Schema managed through migration SQL files executed on app startup.

**Design principles:**
- All SRS scheduling data stored in SQLite (not in-memory)
- FSRS card state serialized as JSON columns for flexibility
- Review logs kept for analytics + parameter optimization
- Grammar and reading content stored as structured data (not just text blobs)
- Audio file paths reference bundled resources (relative paths)

### 4.4 How to Bundle Offline Content

**Strategy: Hybrid — embedded SQLite seed DB + JSON assets + audio files**

1. **Vocabulary & grammar metadata:** Seed SQLite database bundled as a Tauri resource. On first launch, copy to app data dir and run migrations. This gives instant access to all content without parsing JSON at startup.

2. **Reading texts:** JSON files in `assets/texts/` bundled as Tauri resources. Loaded on demand via `readTextFile` + `resolveResource`. JSON is easier to edit than SQL for content authoring.

3. **Audio files:** MP3 files in `assets/audio/` bundled as Tauri resources. Accessed via `convertFileSrc` + asset protocol. For large audio libraries, consider download-on-demand (see below).

**Alternative: All-in-one SQLite DB**
- Embed all content (vocab, grammar, reading texts, audio metadata) in a single SQLite database
- Pro: Single file, easy to update/replace
- Con: Audio files still need to be separate (SQLite BLOBs for audio are impractical at scale)

**Recommended approach:** SQLite for structured data (vocab, reviews, grammar exercises) + JSON for long-form text content + MP3 files for audio.

### 4.5 Audio Storage Strategy

| Strategy | When to use | Pros | Cons |
|---|---|---|---|
| **Bundled (all audio in app)** | Core content (essential vocab pronunciation, lesson audio) | Works 100% offline, no download needed | Increases app size |
| **Download-on-demand** | Extended content (additional listening exercises, optional audio) | Smaller initial download, user chooses what to fetch | Requires internet for first access, needs download manager |

**Recommendation:** Bundle core audio (essential vocab + lesson audio, ~50–100 MB). Implement download-on-demand for extended listening content. Store downloaded audio in `$APPDATA/audio/`.

### 4.6 Routing

**Recommended: React Router v7**

- Industry standard, excellent TypeScript support
- Nested routes for grammar lessons / reading sections
- Works with Tauri's WebView (hash-based routing recommended for desktop)

```typescript
// App.tsx
import { createHashRouter, RouterProvider } from 'react-router';

const router = createHashRouter([
  { path: '/', element: <Dashboard /> },
  { path: '/review', element: <VocabReview /> },
  { path: '/vocab', element: <VocabList /> },
  { path: '/grammar/:lessonId', element: <GrammarLesson /> },
  { path: '/reading/:textId', element: <ReadingText /> },
  { path: '/listening', element: <Listening /> },
  { path: '/import', element: <Import /> },
  { path: '/settings', element: <Settings /> },
]);
```

**Why hash routing?** Tauri serves the frontend from a custom protocol (`tauri://localhost`), not a real HTTP server. Hash routing avoids issues with deep linking on desktop. For Android, the same applies.

**Alternative: TanStack Router** — Type-safe, file-based routing. More modern but steeper learning curve. Overkill for this app's route count.

---

## 5. Proposed SQLite Schema

```sql
-- ============================================================
-- German mit Dr. Khans — SQLite Schema v1
-- ============================================================

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- Vocabulary
-- ============================================================

CREATE TABLE IF NOT EXISTS decks (
    id TEXT PRIMARY KEY,                    -- UUID
    name TEXT NOT NULL,                     -- e.g., "A1 Basics", "Dr. Khans Lesson 1"
    description TEXT,
    source TEXT,                            -- 'builtin', 'imported', 'custom'
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS vocab_cards (
    id TEXT PRIMARY KEY,                    -- UUID
    deck_id TEXT NOT NULL,
    front TEXT NOT NULL,                    -- German word/phrase
    back TEXT NOT NULL,                     -- Translation/meaning
    example_sentence TEXT,                  -- Example usage in German
    example_translation TEXT,               -- Translation of example
    part_of_speech TEXT,                    -- noun, verb, adjective, etc.
    gender TEXT,                            -- der/die/das (for nouns)
    plural TEXT,                            -- Plural form (for nouns)
    pronunciation_ipa TEXT,                -- IPA transcription
    audio_path TEXT,                        -- Relative path to audio file (e.g., "vocab/haus.mp3")
    tags TEXT,                              -- Comma-separated tags (e.g., "greetings,travel")
    notes TEXT,                             -- User notes
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vocab_cards_deck_id ON vocab_cards(deck_id);
CREATE INDEX IF NOT EXISTS idx_vocab_cards_tags ON vocab_cards(tags);

-- ============================================================
-- SRS (FSRS) — Card scheduling state
-- ============================================================

CREATE TABLE IF NOT EXISTS srs_cards (
    id TEXT PRIMARY KEY,                    -- Same as vocab_cards.id (1:1)
    -- FSRS card state
    due TEXT NOT NULL,                      -- ISO 8601 datetime (next review due)
    stability REAL,                         -- FSRS stability (days)
    difficulty REAL,                        -- FSRS difficulty (1-10)
    elapsed_days INTEGER DEFAULT 0,         -- Days since last review
    scheduled_days INTEGER DEFAULT 0,       -- Days scheduled for current interval
    reps INTEGER DEFAULT 0,                 -- Total review count
    lapses INTEGER DEFAULT 0,               -- Total lapse count (forgot)
    state INTEGER DEFAULT 0,               -- FSRS state: 0=New, 1=Learning, 2=Review, 3=Relearning
    last_review TEXT,                       -- ISO 8601 datetime of last review
    -- FSRS parameters (per-card customization, optional)
    custom_params TEXT,                     -- JSON: optional per-card FSRS parameters
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (id) REFERENCES vocab_cards(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_srs_cards_due ON srs_cards(due);
CREATE INDEX IF NOT EXISTS idx_srs_cards_state ON srs_cards(state);

-- ============================================================
-- SRS Review Logs
-- ============================================================

CREATE TABLE IF NOT EXISTS review_logs (
    id TEXT PRIMARY KEY,                    -- UUID
    card_id TEXT NOT NULL,
    rating INTEGER NOT NULL,                -- FSRS rating: 1=Again, 2=Hard, 3=Good, 4=Easy
    state INTEGER NOT NULL,                 -- Card state before review (0=New, 1=Learning, 2=Review, 3=Relearning)
    due TEXT,                               -- Due date before this review
    stability REAL,                         -- Stability before this review
    difficulty REAL,                        -- Difficulty before this review
    elapsed_days INTEGER,                   -- Elapsed days at time of review
    last_elapsed_days INTEGER,              -- Previous elapsed days
    scheduled_days INTEGER,                 -- Scheduled days at time of review
    reviewed_at TEXT NOT NULL DEFAULT (datetime('now')),
    duration_ms INTEGER,                    -- Time spent on this card (milliseconds)
    FOREIGN KEY (card_id) REFERENCES vocab_cards(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_review_logs_card_id ON review_logs(card_id);
CREATE INDEX IF NOT EXISTS idx_review_logs_reviewed_at ON review_logs(reviewed_at);

-- ============================================================
-- Grammar Lessons
-- ============================================================

CREATE TABLE IF NOT EXISTS grammar_lessons (
    id TEXT PRIMARY KEY,                    -- UUID
    title TEXT NOT NULL,                    -- e.g., "Nominativ vs. Akkusativ"
    level TEXT NOT NULL,                    -- A1, A2, B1, B2, C1
    category TEXT,                          -- e.g., "cases", "verbs", "word_order"
    summary TEXT,                           -- Short summary
    content TEXT NOT NULL,                  -- Full lesson content (Markdown or HTML)
    audio_path TEXT,                        -- Optional audio explanation
    order_index INTEGER DEFAULT 0,          -- Display order within category
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_grammar_lessons_level ON grammar_lessons(level);
CREATE INDEX IF NOT EXISTS idx_grammar_lessons_category ON grammar_lessons(category);

-- ============================================================
-- Grammar Exercises
-- ============================================================

CREATE TABLE IF NOT EXISTS grammar_exercises (
    id TEXT PRIMARY KEY,                    -- UUID
    lesson_id TEXT NOT NULL,
    type TEXT NOT NULL,                     -- 'fill_blank', 'multiple_choice', 'reorder', 'translate'
    question TEXT NOT NULL,                 -- Question prompt (German)
    question_translation TEXT,              -- English translation (optional hint)
    answer TEXT NOT NULL,                   -- Correct answer
    options TEXT,                           -- JSON array of options (for multiple_choice)
    explanation TEXT,                       -- Why the answer is correct
    difficulty INTEGER DEFAULT 1,           -- 1-5 difficulty scale
    order_index INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (lesson_id) REFERENCES grammar_lessons(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_grammar_exercises_lesson_id ON grammar_exercises(lesson_id);

-- ============================================================
-- Grammar Exercise Attempts
-- ============================================================

CREATE TABLE IF NOT EXISTS grammar_exercise_attempts (
    id TEXT PRIMARY KEY,                    -- UUID
    exercise_id TEXT NOT NULL,
    user_answer TEXT NOT NULL,
    is_correct INTEGER NOT NULL,            -- 0 or 1
    attempted_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (exercise_id) REFERENCES grammar_exercises(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_grammar_attempts_exercise_id ON grammar_exercise_attempts(exercise_id);

-- ============================================================
-- Reading Texts
-- ============================================================

CREATE TABLE IF NOT EXISTS reading_texts (
    id TEXT PRIMARY KEY,                    -- UUID
    title TEXT NOT NULL,
    author TEXT,
    level TEXT NOT NULL,                    -- A1, A2, B1, B2, C1
    category TEXT,                          -- 'article', 'story', 'news', 'poem'
    content TEXT NOT NULL,                  -- Full text (Markdown or plain text)
    word_count INTEGER,                     -- Total word count
    reading_time_minutes INTEGER,           -- Estimated reading time
    audio_path TEXT,                        -- Optional audio narration
    source TEXT,                            -- 'builtin', 'imported'
    file_path TEXT,                         -- Original file path (if imported)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_reading_texts_level ON reading_texts(level);
CREATE INDEX IF NOT EXISTS idx_reading_texts_category ON reading_texts(category);

-- ============================================================
-- Reading Comprehension Questions
-- ============================================================

CREATE TABLE IF NOT EXISTS reading_questions (
    id TEXT PRIMARY KEY,                    -- UUID
    text_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    options TEXT,                           -- JSON array (for multiple choice)
    question_type TEXT DEFAULT 'open',      -- 'open', 'multiple_choice', 'true_false'
    order_index INTEGER DEFAULT 0,
    FOREIGN KEY (text_id) REFERENCES reading_texts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reading_questions_text_id ON reading_questions(text_id);

-- ============================================================
-- Reading Progress
-- ============================================================

CREATE TABLE IF NOT EXISTS reading_progress (
    id TEXT PRIMARY KEY,                    -- UUID
    text_id TEXT NOT NULL,
    status TEXT DEFAULT 'unread',           -- 'unread', 'in_progress', 'completed'
    scroll_position REAL DEFAULT 0,         -- Scroll position (0.0-1.0)
    time_spent_ms INTEGER DEFAULT 0,        -- Total time spent reading
    last_read_at TEXT,
    FOREIGN KEY (text_id) REFERENCES reading_texts(id) ON DELETE CASCADE
);

-- ============================================================
-- Listening Comprehension
-- ============================================================

CREATE TABLE IF NOT EXISTS listening_exercises (
    id TEXT PRIMARY KEY,                    -- UUID
    title TEXT NOT NULL,
    level TEXT NOT NULL,                    -- A1, A2, B1, B2, C1
    audio_path TEXT NOT NULL,               -- Path to audio file
    transcript TEXT,                        -- Full transcript (German)
    transcript_translation TEXT,            -- English translation
    duration_seconds INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_listening_exercises_level ON listening_exercises(level);

CREATE TABLE IF NOT EXISTS listening_questions (
    id TEXT PRIMARY KEY,
    exercise_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    options TEXT,                           -- JSON array (for multiple choice)
    question_type TEXT DEFAULT 'open',
    order_index INTEGER DEFAULT 0,
    FOREIGN KEY (exercise_id) REFERENCES listening_exercises(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_listening_questions_exercise_id ON listening_questions(exercise_id);

-- ============================================================
-- App Settings (key-value store)
-- ============================================================

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,                    -- JSON-encoded value
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Default settings
INSERT OR IGNORE INTO app_settings (key, value) VALUES
    ('fsrs_params', '{"request_retention": 0.9, "maximum_interval": 36500, "enable_fuzz": true, "learning_steps": ["1m", "10m"], "relearning_steps": ["10m"]}'),
    ('daily_review_limit', '200'),
    ('daily_new_card_limit', '20'),
    ('theme', 'system'),
    ('audio_enabled', 'true'),
    ('audio_playback_rate', '1.0'),
    ('language_interface', 'en'),
    ('first_run', 'true');

-- ============================================================
-- Study Sessions (analytics)
-- ============================================================

CREATE TABLE IF NOT EXISTS study_sessions (
    id TEXT PRIMARY KEY,                    -- UUID
    session_type TEXT NOT NULL,             -- 'vocab_review', 'grammar', 'reading', 'listening'
    started_at TEXT NOT NULL,
    ended_at TEXT,
    cards_reviewed INTEGER DEFAULT 0,
    cards_correct INTEGER DEFAULT 0,
    new_cards_learned INTEGER DEFAULT 0,
    duration_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_study_sessions_started_at ON study_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_study_sessions_type ON study_sessions(session_type);
```

---

## 6. Key Risks and Mitigations

### Ranked by Severity

| # | Risk | Severity | Likelihood | Impact | Mitigation |
|---|---|---|---|---|---|
| 1 | **Tauri 2 Android maturity gaps** — Updater not supported, plugin coverage incomplete, WebView rendering inconsistencies across Android versions | **High** | Medium | High | Build desktop-first. Use `#[cfg(desktop)]` / `#[cfg(mobile)]` conditional compilation. For Android updates, use Google Play (manual AAB upload). Test on real devices early. |
| 2 | **Rust learning curve** — User is new to Rust; backend logic (commands, plugin setup) requires Rust knowledge | **Medium** | High | Medium | Minimize Rust surface area. Use `tauri-plugin-sql` JS API for DB access. Write only thin Tauri commands for operations not possible in JS. Copy patterns from Baajit (React + Tauri 2 + SQLite). |
| 3 | **WebView2 memory ceiling (~2 GB)** — Large data sets or heavy DOM could hit the limit | **Low** | Low | High | Use virtualized lists (react-window / @tanstack/react-virtual). Avoid loading all cards in DOM. Use pull-based IPC (don't push large payloads via Eval). |
| 4 | **Audio playback issues on Android** — Asset protocol differs on mobile (`asset://localhost/` vs desktop file paths) | **Low** | Medium | Low | Abstract audio path resolution behind a platform-aware utility. Test audio early on Android. ABPlayer demonstrates working audio patterns. |
| 5 | **Plugin abandonment** — `tauri-plugin-rusqlite2` is community-maintained | **Low** | Low | Medium | Use official `tauri-plugin-sql` instead. Only use community plugins if absolutely needed. |
| 6 | **Content authoring workflow** — Creating vocab decks, grammar lessons, reading texts requires tooling | **Medium** | High | Low | Build a simple JSON-based content format. Create a basic admin/import page in the app. Seed with existing German learning content. |
| 7 | **Framework pivot cost** — If Tauri 2 Android proves unworkable, migrating to Flutter means rewriting everything | **Medium** | Low | High | Keep business logic in TypeScript (not Rust). If pivot needed, port SRS logic to `dart-fsrs` (same algorithm). SQLite schema is portable. Content assets (JSON, audio) are framework-agnostic. |

### Fallback Plan (If Tauri 2 Android Fails)

1. **Trigger:** After attempting Android build, if critical plugins don't work or WebView rendering is unacceptable on target devices.
2. **Pivot to Flutter:**
   - Port SQLite schema directly (SQL is portable)
   - Replace `ts-fsrs` with `dart-fsrs` (same FSRS algorithm, similar API)
   - Replace React components with Flutter widgets
   - Use `drift` for type-safe SQLite access
   - Content assets (JSON, MP3) transfer directly
   - Estimated effort: 2–3 weeks for a single developer
3. **Hybrid option:** Keep Tauri 2 desktop app, build a separate Flutter Android app. Share content via SQLite DB file + JSON assets. More maintenance but lower risk per platform.

---

## 7. Recommended Libraries & Packages

### Frontend (TypeScript / React)

| Package | Version | Purpose |
|---|---|---|
| `react` | ^19.0.0 | UI framework |
| `react-dom` | ^19.0.0 | DOM renderer |
| `react-router` | ^7.0.0 | Routing (hash-based) |
| `zustand` | ^5.0.0 | State management |
| `ts-fsrs` | ^4.0.0 | FSRS v6 spaced repetition scheduler |
| `@tauri-apps/api` | ^2.11.0 | Tauri core JS API |
| `@tauri-apps/plugin-sql` | ^2.0.0 | SQLite database access |
| `@tauri-apps/plugin-fs` | ^2.0.0 | File system access |
| `@tauri-apps/plugin-dialog` | ^2.0.0 | File picker dialogs |
| `@tauri-apps/plugin-updater` | ^2.0.0 | Auto-updater (desktop only) |
| `@tauri-apps/plugin-process` | ^2.0.0 | Process control (relaunch after update) |
| `@tauri-apps/plugin-notification` | ^2.0.0 | Study reminders |
| `tailwindcss` | ^4.0.0 | Utility-first CSS |
| `lucide-react` | ^0.400.0 | Icon set |
| `clsx` | ^2.1.0 | Conditional class names |
| `date-fns` | ^4.0.0 | Date utilities (SRS scheduling) |
| `react-markdown` | ^9.0.0 | Render Markdown content (grammar lessons, reading texts) |
| `@tanstack/react-virtual` | ^3.0.0 | Virtualized lists (large vocab decks) |

### Backend (Rust / Tauri)

| Crate | Version | Purpose |
|---|---|---|
| `tauri` | ^2.11.0 | App framework |
| `tauri-plugin-sql` | ^2.0.0 | SQLite plugin (with `sqlite` feature) |
| `tauri-plugin-fs` | ^2.0.0 | File system plugin |
| `tauri-plugin-dialog` | ^2.0.0 | Dialog plugin |
| `tauri-plugin-updater` | ^2.0.0 | Updater plugin (desktop only) |
| `tauri-plugin-process` | ^2.0.0 | Process plugin |
| `tauri-plugin-notification` | ^2.0.0 | Notification plugin |
| `serde` | ^1.0 | Serialization |
| `serde_json` | ^1.0 | JSON handling |

### Dev Dependencies

| Package | Version | Purpose |
|---|---|---|
| `typescript` | ^5.6.0 | Type checking |
| `vite` | ^6.0.0 | Build tool / dev server |
| `@vitejs/plugin-react` | ^4.0.0 | React plugin for Vite |
| `tailwindcss` | ^4.0.0 | CSS framework |
| `postcss` | ^8.4.0 | CSS processing |
| `autoprefixer` | ^10.4.0 | CSS vendor prefixes |
| `eslint` | ^9.0.0 | Linting |
| `@typescript-eslint/eslint-plugin` | ^8.0.0 | TS linting rules |

### Flutter Fallback (If Needed)

| Package | Version | Purpose |
|---|---|---|
| `flutter` | 3.44+ | Framework |
| `fsrs` | ^2.0.0 | FSRS spaced repetition |
| `drift` | ^2.34.0 | Type-safe SQLite ORM |
| `drift_dev` | ^2.34.0 | Code generation (dev) |
| `build_runner` | ^2.0.0 | Code generation runner (dev) |
| `path_provider` | ^2.1.0 | File system paths |
| `audioplayers` | ^6.0.0 | Audio playback |
| `flutter_riverpod` | ^2.5.0 | State management |
| `go_router` | ^14.0.0 | Routing |

---

## 8. Next Steps for Orchestrator

### Decisions to Be Made

1. **SQLite plugin choice:** `tauri-plugin-sql` (official, simpler) vs `tauri-plugin-rusqlite2` (community, transactions). **Recommendation:** Start with official `tauri-plugin-sql`.

2. **Content sourcing:** Where will the initial German learning content come from?
   - Manual creation (JSON files)?
   - Import from existing resources (Anki decks, CSV)?
   - Curated from Dr. Khans' materials?
   - **Action needed:** Define content format + source before implementation.

3. **Audio content:** Will audio be:
   - Pre-recorded and bundled?
   - Generated via TTS (Text-to-Speech) at build time?
   - Downloaded from an online source?
   - **Action needed:** Determine audio source and storage strategy.

4. **UI framework:** Tailwind CSS + custom components vs a component library (shadcn/ui)?
   - **Recommendation:** Tailwind + shadcn/ui for rapid, consistent UI.

5. **Routing strategy:** Hash routing (recommended for Tauri) vs browser history routing?
   - **Recommendation:** Hash routing (`createHashRouter`).

6. **Android timeline:** When is Android needed?
   - Immediately (build mobile-first)?
   - After desktop MVP (recommended)?
   - Never (desktop only)?
   - **Action needed:** Define Android priority to scope the initial build.

7. **FSRS parameters:** Use default FSRS v6 parameters or customize?
   - **Recommendation:** Start with defaults (0.9 retention, 36500 max interval). Optimize later using review logs with `@open-spaced-repetition/binding`.

### Recommended Implementation Order

| Phase | Scope | Est. Time |
|---|---|---|
| **Phase 1: Scaffold** | `create-tauri-app`, Tailwind, routing, SQLite setup, schema migration | 1–2 days |
| **Phase 2: Vocab + SRS** | Flashcard UI, `ts-fsrs` integration, review session, due card queue | 3–5 days |
| **Phase 3: Grammar** | Lesson viewer (Markdown), exercise types (fill-blank, MC), attempt tracking | 2–3 days |
| **Phase 4: Reading** | Text viewer, comprehension questions, progress tracking, import workflow | 2–3 days |
| **Phase 5: Listening** | Audio player UI, transcript display, comprehension questions | 1–2 days |
| **Phase 6: Polish** | Dashboard/stats, settings, auto-updater, notifications | 2–3 days |
| **Phase 7: Android** | `tauri android init`, responsive layout, mobile testing, Play Store prep | 1–2 weeks |
| **Total (desktop MVP)** | Phases 1–6 | **~2–3 weeks** |
| **Total (with Android)** | Phases 1–7 | **~4–5 weeks** |

### Open Questions for User

- [ ] Confirm: Desktop-first, Android later? (Assumed yes)
- [ ] Confirm: No AI conversation feature? (Stated in requirements)
- [ ] What German level(s) to target? (A1–C1? Specific level?)
- [ ] Any existing content to import, or starting from scratch?
- [ ] Preference for UI style? (Minimal/clean vs colorful/engaging)
- [ ] Need for multiple user profiles, or single-user only?

---

## Appendix A: Key References

- Tauri 2 docs: https://v2.tauri.app/
- Tauri 2 releases: https://v2.tauri.app/release/tauri/ (v2.11.5, Jul 2026)
- `tauri-plugin-sql`: https://v2.tauri.app/plugin/sql/
- `tauri-plugin-fs`: https://v2.tauri.app/plugin/file-system/
- `tauri-plugin-updater`: https://v2.tauri.app/plugin/updater/
- Tauri 2 audio (resources + asset protocol): https://v2.tauri.app/develop/resources/
- `ts-fsrs` (FSRS v6): https://github.com/open-spaced-repetition/ts-fsrs
- `dart-fsrs`: https://github.com/open-spaced-repetition/dart-fsrs
- Flutter 3.44: https://flutter.dev/blog/whats-new-in-flutter-3-44
- Drift (Flutter SQLite): https://drift.simonbinder.eu/
- Baajit (Tauri 2 + React + SQLite on Android): https://github.com/kaafihai/baajit
- LettuceAI (Tauri 2 on Android): https://github.com/LettuceAI/app
- ABPlayer (Tauri 2 audio patterns): https://github.com/kurohige/ABPlayer

## Appendix B: Tauri 2 Android Build Quick Reference

```bash
# 1. Install Rust Android targets
rustup target add aarch64-linux-android armv7-linux-androideabi i686-linux-android x86_64-linux-android

# 2. Initialize Android project
npm run tauri android init

# 3. Development (requires emulator or device)
npm run tauri android dev

# 4. Production build (generates APK + AAB)
npm run tauri android build

# 5. Per-ABI split (smaller APKs)
npm run tauri android build -- --split-per-abi

# 6. Configure minSdkVersion in tauri.conf.json
# "bundle": { "android": { "minSdkVersion": 24 } }
```
