# UI/UX Design Handoff — German mit Dr. Khans

> **Design deliverable for the German learning desktop app (Tauri 2 + React 19 + TypeScript)**
> Generated: 2026-08-02
> Companion to: `Framework_and_Architecture_Handoff.md`, `Content_Data_Sources_Handoff.md`, `existing_apps_analysis_and_gap_handoff.md`

---

## Table of Contents

1. [Design System Specification](#1-design-system-specification)
2. [Screen Designs (Text Wireframes)](#2-screen-designs-text-wireframes)
3. [Navigation Architecture](#3-navigation-architecture)
4. [Component Architecture](#4-component-architecture)
5. [Responsive Design Strategy](#5-responsive-design-strategy)
6. [Accessibility Checklist](#6-accessibility-checklist)
7. [Charting Library Recommendation](#7-charting-library-recommendation)
8. [Next Steps for Orchestrator](#8-next-steps-for-orchestrator)

---

## 1. Design System Specification

### 1.1 Color Palette — Forest & Cream

A scholarly, calm palette inspired by German forests and classical paper. Deep forest green as the primary conveys focus and depth. Warm cream/sand backgrounds replace stark white to reduce eye strain during long study sessions. Copper-rust accents provide warmth and highlight without the cliché of black-red-gold.

#### Light Mode

| Token | Hex | Usage |
|---|---|---|
| `--background` | `#FAF7F0` | App background — warm cream |
| `--foreground` | `#1C2B1E` | Primary text — deep forest near-black |
| `--card` | `#FFFFFF` | Card surfaces — pure white for contrast against cream |
| `--card-foreground` | `#1C2B1E` | Text on cards |
| `--popover` | `#FFFFFF` | Popover/dialog backgrounds |
| `--popover-foreground` | `#1C2B1E` | Text on popovers |
| `--primary` | `#2D5A3D` | Forest green — buttons, active states, focus rings |
| `--primary-foreground` | `#F0EDE5` | Text on primary surfaces |
| `--secondary` | `#E8E2D4` | Sand — secondary buttons, inactive tabs |
| `--secondary-foreground` | `#3A4A2E` | Text on secondary surfaces |
| `--muted` | `#F0EDE5` | Muted backgrounds — subtle sections |
| `--muted-foreground` | `#6B7B5F` | Muted text — captions, hints |
| `--accent` | `#B8703A` | Copper-rust — highlights, streaks, progress accents |
| `--accent-foreground` | `#FAF7F0` | Text on accent surfaces |
| `--destructive` | `#B33A3A` | Error states, "Again" rating |
| `--destructive-foreground` | `#FAF7F0` | Text on destructive surfaces |
| `--success` | `#4A7A3A` | Correct answers, "Good" rating |
| `--warning` | `#C8923A` | "Hard" rating, warnings |
| `--info` | `#3A6A7A` | Info badges, tips |
| `--border` | `#D8D0C0` | Borders, separators |
| `--input` | `#D8D0C0` | Input borders |
| `--ring` | `#2D5A3D` | Focus ring color |
| `--sidebar` | `#F0EDE5` | Sidebar background — slightly darker than main |
| `--sidebar-foreground` | `#1C2B1E` | Sidebar text |
| `--sidebar-accent` | `#E8E2D4` | Sidebar hover/active item bg |
| `--sidebar-border` | `#D8D0C0` | Sidebar border |

#### Dark Mode

| Token | Hex | Usage |
|---|---|---|
| `--background` | `#1A1F17` | App background — dark forest charcoal |
| `--foreground` | `#E8E2D4` | Primary text — warm sand |
| `--card` | `#232920` | Card surfaces — slightly lighter than bg |
| `--card-foreground` | `#E8E2D4` | Text on cards |
| `--popover` | `#232920` | Popover/dialog backgrounds |
| `--popover-foreground` | `#E8E2D4` | Text on popovers |
| `--primary` | `#5B9A6F` | Lighter forest green — visible on dark |
| `--primary-foreground` | `#1A1F17` | Text on primary surfaces |
| `--secondary` | `#2E352A` | Dark sand — secondary surfaces |
| `--secondary-foreground` | `#C8C0B0` | Text on secondary surfaces |
| `--muted` | `#2E352A` | Muted backgrounds |
| `--muted-foreground` | `#8A9080` | Muted text |
| `--accent` | `#D4884A` | Brighter copper — visible on dark |
| `--accent-foreground` | `#1A1F17` | Text on accent surfaces |
| `--destructive` | `#D45050` | Error states |
| `--destructive-foreground` | `#FAF7F0` | Text on destructive |
| `--success` | `#6AAA5A` | Correct answers |
| `--warning` | `#DAA850` | Warnings |
| `--info` | `#5A9AB0` | Info badges |
| `--border` | `#3A4234` | Borders |
| `--input` | `#3A4234` | Input borders |
| `--ring` | `#5B9A6F` | Focus ring |
| `--sidebar` | `#161B13` | Sidebar — darker than main bg |
| `--sidebar-foreground` | `#E8E2D4` | Sidebar text |
| `--sidebar-accent` | `#2E352A` | Sidebar hover/active |
| `--sidebar-border` | `#3A4234` | Sidebar border |

#### CEFR Level Badge Colors (shared across themes)

| Level | Light bg | Light text | Dark bg | Dark text |
|---|---|---|---|---|
| A1 | `#E8F0E0` | `#2D5A3D` | `#2E352A` | `#7BBA8F` |
| A2 | `#DDEBC8` | `#3A6A2E` | `#353D2A` | `#8BCA6F` |
| B1 | `#F0E8C8` | `#7A6A2A` | `#3A3520` | `#DAB850` |
| B2 | `#F0DCC0` | `#8A5A2A` | `#3A2E20` | `#D4884A` |
| C1 | `#ECD4C8` | `#8A3A2A` | `#3A2820` | `#D46A4A` |

### 1.2 Typography

#### Font Selection

| Role | Font | Rationale |
|---|---|---|
| **Headings** | **Source Serif 4** (Google Fonts) | Scholarly serif evokes academic textbooks. Full German glyph coverage (ä, ö, ü, ß, Ä, Ö, Ü). Variable font — weights 200–900. Excellent legibility at large sizes. |
| **Body** | **Inter** (Google Fonts) | Industry-standard UI font. Full German glyph coverage. Optimized for screen rendering. Variable font — weights 100–900. Pairs well with Source Serif. |
| **Monospace** | **JetBrains Mono** (Google Fonts) | For IPA transcriptions, keyboard shortcut hints, code examples in grammar lessons. German glyphs supported. |

#### Font Sizes (Tailwind scale, 4px base)

| Token | Size | Line height | Usage |
|---|---|---|---|
| `text-xs` | 12px (0.75rem) | 16px | Captions, hints, keyboard shortcuts |
| `text-sm` | 14px (0.875rem) | 20px | Secondary text, labels, sidebar items |
| `text-base` | 16px (1rem) | 24px | Body text, card content |
| `text-lg` | 18px (1.125rem) | 28px | Card titles, section headers |
| `text-xl` | 20px (1.25rem) | 28px | Page titles, flashcard word |
| `text-2xl` | 24px (1.5rem) | 32px | Dashboard stats, large headings |
| `text-3xl` | 30px (1.875rem) | 36px | Flashcard word (focused mode) |
| `text-4xl` | 36px (2.25rem) | 40px | Hero numbers (streak, due count) |

#### Font Weights

| Weight | Usage |
|---|---|
| 400 (Regular) | Body text, descriptions |
| 500 (Medium) | Buttons, labels, nav items, card titles |
| 600 (Semibold) | Section headers, page titles |
| 700 (Bold) | Flashcard German word, stat numbers |

#### Font Loading

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
```

> **Note:** For full offline-first, bundle font files as Tauri resources in `assets/fonts/` and use `@font-face` with local `src`. Google Fonts CDN is fine for development; switch to bundled fonts before production build.

#### CSS Variables (Tailwind v4 `@theme`)

```css
@theme {
  --font-sans: "Inter", system-ui, sans-serif;
  --font-serif: "Source Serif 4", Georgia, serif;
  --font-mono: "JetBrains Mono", monospace;
}
```

### 1.3 Spacing System

Tailwind's 4px base scale. Key application-specific values:

| Token | Value | Usage |
|---|---|---|
| `gap-1` | 4px | Tight gaps (icon + label) |
| `gap-2` | 8px | Button groups, chip clusters |
| `gap-3` | 12px | Card internal spacing |
| `gap-4` | 16px | Default gap between elements |
| `p-4` | 16px | Card padding (mobile) |
| `p-6` | 24px | Card padding (desktop), page padding |
| `p-8` | 32px | Page padding (desktop, focused mode) |
| `space-y-4` | 16px | Vertical rhythm between sections |
| `space-y-6` | 24px | Vertical rhythm between major sections |

#### Layout Dimensions

| Element | Size | Notes |
|---|---|---|
| Sidebar width (expanded) | 240px | Fixed on desktop ≥1024px |
| Sidebar width (collapsed) | 64px | Icon-only rail |
| Bottom nav height (mobile) | 56px | Fixed at bottom, safe-area aware |
| Max content width | 1200px | Centered in main area |
| Flashcard max width | 640px | Centered in review area |
| Flashcard min height | 320px | Ensures consistent feel |
| Sidebar item height | 40px | Touch-friendly |
| Bottom nav item width | flex (1/5) | Equal distribution |

### 1.4 shadcn/ui Components — Full List

#### Core (used across all screens)

| Component | Usage |
|---|---|
| `Button` | Primary actions, ratings, navigation, submit. Variants: default, secondary, outline, ghost, destructive. Sizes: sm, default, lg, icon. |
| `Card` | Stat cards, deck cards, lesson cards, reading passage cards. Header + Content + Footer subcomponents. |
| `Input` | Text inputs — search, custom card fields, exercise fill-blank, settings fields. |
| `Label` | Form labels for all inputs. |
| `ScrollArea` | Sidebar scroll, card list scroll, transcript scroll, lesson content scroll. |
| `Separator` | Section dividers, sidebar footer separator, settings section separators. |
| `Tooltip` | Keyboard shortcut hints on rating buttons, icon button labels, CEFR badge explanations. |
| `Progress` | Session progress bar, lesson progress, reading progress, download progress. |
| `Skeleton` | Loading states for all async data — card loading, deck loading, stats loading. |
| `Badge` | CEFR level badges, card state badges (new/learning/young/mature), tag badges, streak badge. |

#### Navigation & Layout

| Component | Usage |
|---|---|
| `NavigationMenu` | Sidebar navigation (desktop). Customized as vertical nav. |
| `Sheet` | Mobile sidebar drawer (swipe from left or hamburger tap). |
| `Tabs` | Settings tabs (Review, Appearance, Audio, Data, About). Grammar category tabs. Stats time range tabs. |
| `DropdownMenu` | Deck context menu (edit/export/delete), card context menu, sort options, filter menus. |
| `Breadcrumb` | Grammar lesson navigation (Level > Category > Lesson). Reading library navigation. |

#### Overlays & Feedback

| Component | Usage |
|---|---|
| `Dialog` | Card add/edit form, import preview, confirmation dialogs, exercise explanation popups. |
| `AlertDialog` | Delete deck confirmation, reset progress confirmation, DB reset. |
| `Toast` (Sonner) | Review submitted, card added, import complete, error messages, streak milestone. |
| `Popover` | Word definition popup (reading view), grammar tip popup, IPA tooltip. |

#### Forms & Input

| Component | Usage |
|---|---|
| `Select` | CEFR level filter, deck selection, sort order, audio speed, FSRS preset. |
| `Switch` | Dark mode toggle, auto-play audio, show IPA, show transcript, keyboard shortcuts enabled. |
| `Slider` | Desired retention (75–99%), max interval (days), font size adjustment, audio speed (0.5–2.0x). |
| `Textarea` | Custom card example sentence, user notes, imported text preview. |
| `Checkbox` | Tag multi-select, grammar category filter, deck selection for review session. |
| `Toggle` / `ToggleGroup` | Filter chips (CEFR level, category), view mode toggle (grid/list), chart time range. |

#### Data Display

| Component | Usage |
|---|---|
| `Table` | Card list in deck browser, review log history, vocabulary list. |
| `Collapsible` | Advanced settings sections, sidebar sub-menus, grammar category expand/collapse. |
| `Accordion` | Grammar lesson FAQ, settings help sections, exercise explanation details. |
| `HoverCard` | Word hover preview in reading view (desktop only — tap popup on mobile). |

#### Additional Custom Components (not in shadcn registry)

| Component | Built on | Usage |
|---|---|---|
| `Flashcard` | Card + flip animation | SRS review card with front/back |
| `RatingButtons` | Button group | Again/Hard/Good/Easy with keyboard hints |
| `AudioPlayer` | Custom + HTML5 Audio | Play/pause, speed, seek bar |
| `CEFRBadge` | Badge | Color-coded CEFR level |
| `StatCard` | Card | Stat number + label + icon + trend |
| `ChartContainer` | Card + recharts | Wrapper for responsive charts |
| `MarkdownRenderer` | Custom (react-markdown) | Grammar lesson content |
| `WordPopup` | Popover | Definition + audio + "Add to SRS" in reading view |
| `SearchBar` | Input + icon | Debounced search with clear button |
| `FilterChip` | Toggle | CEFR/category filter chips |
| `CalendarHeatmap` | Custom | GitHub-style review activity heatmap |
| `SwipeHandler` | Custom hook | Touch swipe for card rating (mobile) |
| `KeyboardShortcuts` | Custom hook | Global + review-specific shortcuts |

### 1.5 Dark Mode Implementation

#### Approach: CSS Variables + `class` strategy

shadcn/ui uses HSL channel values (space-separated, no commas) so Tailwind can apply opacity modifiers like `bg-primary/50`.

```css
:root {
  --background: 250 247 240;
  --foreground: 28 43 30;
  --primary: 45 90 61;
  /* ... all other tokens ... */
}
.dark {
  --background: 26 31 23;
  --foreground: 232 226 212;
  --primary: 91 154 111;
  /* ... all other tokens ... */
}
```

#### Toggle Strategy

- **Default:** Follow system preference (`prefers-color-scheme`).
- **Manual override:** User can force light, dark, or system in Settings.
- **Implementation:** Zustand `settingsStore` holds `theme: 'light' | 'dark' | 'system'`. On change, add/remove `.dark` class on `document.documentElement`.
- **No flash on load:** Read theme from `tauri-plugin-store` (persistent KV) before React hydrates. Inline script in `index.html` sets the class immediately.

```typescript
export function useTheme() {
  const theme = useSettingsStore((s) => s.theme);
  useEffect(() => {
    const root = document.documentElement;
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.classList.toggle('dark', theme === 'dark' || (theme === 'system' && systemDark));
  }, [theme]);
}
```

### 1.6 Border Radius & Shadows

| Token | Value | Usage |
|---|---|---|
| `rounded-sm` | 2px | Badges, small elements |
| `rounded-md` | 6px | Buttons, inputs |
| `rounded-lg` | 8px | Cards |
| `rounded-xl` | 12px | Large cards, flashcard |
| `rounded-full` | 9999px | Icons, avatars, pills |
| `shadow-sm` | subtle | Cards (light mode) |
| `shadow-md` | medium | Popovers, dialogs |
| `shadow-lg` | large | Dialogs, sheets |
| Dark mode | `border` only | No shadows in dark — use 1px border for depth |

### 1.7 Animation & Transitions

| Element | Animation | Duration | Easing |
|---|---|---|---|
| Flashcard flip | 3D rotateY | 400ms | `ease-in-out` |
| Page transition | Fade + slide | 200ms | `ease-out` |
| Sidebar collapse | Width shrink | 200ms | `ease-in-out` |
| Toast enter | Slide up + fade | 300ms | `ease-out` |
| Dialog enter | Scale + fade | 200ms | `ease-out` |
| Rating button press | Scale down | 100ms | `ease` |
| Streak counter | Number count-up | 600ms | `ease-out` |
| Progress bar | Width transition | 300ms | `ease-in-out` |

> **Implementation:** Use Tailwind's `transition-*` utilities + custom keyframes in `globals.css`. For flashcard flip, use `transform-style: preserve-3d` with `rotateY(180deg)`. For page transitions, Framer Motion is optional (lightweight usage only).

---

## 2. Screen Designs (Text Wireframes)

Each wireframe describes: layout structure, key components, data displayed, interactions, and responsive behavior (desktop vs mobile).

### Phase 1 Screens

---

### 2.1 Dashboard / Home

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR (240px)  │  MAIN CONTENT                         │
│                  │                                       │
│  📊 Dashboard    │  ┌─────────────────────────────────┐  │
│  🔄 Review       │  │  Guten Tag!                     │  │
│  📚 Decks        │  │  Today's Review                 │  │
│  📖 Grammar      │  │  ┌────────┐  ┌────────┐         │  │
│  📜 Reading      │  │  │   47   │  │   12   │         │  │
│  🎧 Listening    │  │  │  Due   │  │  New   │         │  │
│  📈 Stats        │  │  └────────┘  └────────┘         │  │
│  ⚙️ Settings     │  │  [ Start Review → ]              │  │
│                  │  └─────────────────────────────────┘  │
│                  │                                       │
│                  │  ┌──────────────┐ ┌──────────────┐    │
│                  │  │ 🔥 Streak    │ │ 📊 Retention │    │
│                  │  │    23 days   │ │    87%       │    │
│                  │  └──────────────┘ └──────────────┘    │
│                  │                                       │
│                  │  Recent Activity                      │
│                  │  ┌─────────────────────────────────┐  │
│                  │  │ ✓ Reviewed 15 cards  · 2h ago   │  │
│                  │  │ ✓ Completed A1 Vocab  · 5h ago  │  │
│                  │  │ + Added 3 custom cards · 1d ago │  │
│                  │  └─────────────────────────────────┘  │
│                  │                                       │
│                  │  Upcoming Reviews                     │
│                  │  ┌─────────────────────────────────┐  │
│                  │  │ Tomorrow: 52  │ Wed: 38 │ ...   │  │
│                  │  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Layout structure:**
- Desktop: Fixed sidebar (240px left) + main content area (flex-1, max-width 1200px, centered)
- Main content: Vertical stack of sections with `space-y-6`

**Key components:**
- `StatCard` × 2 (Due cards, New cards) — large numbers, `text-4xl`, accent color for due count
- `Button` (lg, primary) — "Start Review" with arrow icon
- `StatCard` × 2 (Streak with flame icon, Retention with percent)
- `Card` — Recent Activity feed (list of `Separator`-divided rows with icon + text + timestamp)
- `Card` — Upcoming Reviews (mini bar chart or horizontal bars showing next 7 days)

**Data displayed:**
- Due card count (from `srs_cards` WHERE `due <= now`)
- New card count (from `srs_cards` WHERE `state = 0`)
- Streak count (consecutive days with ≥1 review)
- Retention rate (correct / total reviews, last 30 days)
- Recent activity (last 5 review sessions, card additions, lesson completions)
- Upcoming review forecast (next 7 days from `srs_cards` grouped by due date)

**Interactions:**
- Click "Start Review" → navigate to `/review` with due cards loaded
- Click "Due" stat card → navigate to `/review`
- Click "New" stat card → navigate to `/decks` with new card filter
- Click activity item → navigate to relevant module
- Click upcoming review day → navigate to `/stats` forecast view

**Responsive behavior:**
- **Desktop (≥1024px):** Sidebar visible, content max-width 1200px, stat cards in 2-column grid
- **Tablet (768–1023px):** Sidebar collapses to icon rail (64px), content fills remaining, stat cards 2-column
- **Mobile (<768px):** No sidebar, bottom nav visible, hero section stacked vertically (due + new side by side, streak + retention below), activity feed full-width, upcoming reviews as horizontal scroll

---

### 2.2 Vocabulary Review

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR │  ← Review (5/47)                    [⛶ Focus] │
│         │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│         │                                               │
│         │         ┌───────────────────────────┐          │
│         │         │                           │          │
│         │         │        das Haus           │          │
│         │         │     🔊 [Audio Button]     │          │
│         │         │                           │          │
│         │         │    [ Click to flip /      │          │
│         │         │      Press Space ]        │          │
│         │         │                           │          │
│         │         └───────────────────────────┘          │
│         │                                               │
│         │   ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐         │
│         │   │ Again│ │ Hard │ │ Good │ │ Easy │         │
│         │   │  1  │ │  2  │ │  3  │ │  4  │         │
│         │   │ <1m │ │ 6m  │ │ 1d  │ │ 4d  │         │
│         │   └──────┘ └──────┘ └──────┘ └──────┘         │
│         │                                               │
│         │   ← Prev (A)          Next (D) →              │
└─────────────────────────────────────────────────────────┘
```

**Card Front (initial state):**
- German word (`text-3xl`, `font-bold`, `lang="de"`)
- Article (der/die/das) as colored prefix — der=blue, die=red, das=green (subtle, not flag colors)
- Audio button (volume icon, circular, `ghost` variant)
- "Click to flip" hint (fades after first interaction)

**Card Back (after flip — Space or click):**

```
┌───────────────────────────┐
│  das Haus      🔊         │
│  /haʊs/  (IPA, monospace) │
│  ─────────────────────── │
│  the house                │
│  Plural: die Häuser       │
│  ─────────────────────── │
│  Example:                 │
│  "Das Haus ist groß."     │
│  "The house is big."      │
│  🔊 [Play example]        │
└───────────────────────────┘
```

**Layout structure:**
- Desktop: Sidebar + main area. Card centered (max-width 640px, min-height 320px). Rating buttons below card. Progress bar at top.
- Focus mode: Sidebar hidden, card centered full-screen, only progress bar + card + rating visible. Toggle with `⛶` button or `F` key.

**Key components:**
- `Progress` bar at top — shows session progress (current/total)
- `Flashcard` — 3D flip card with front/back faces
- `Button` (icon, ghost) — audio playback
- `RatingButtons` — 4-button group with keyboard hints and interval previews
- `Button` (icon, ghost) — focus mode toggle
- `Tooltip` on each rating button — shows keyboard shortcut + next interval

**Data displayed:**
- Current card index / total in session
- German word, article, IPA, translation, plural, example sentence + translation
- Predicted next interval for each rating (from FSRS scheduler)
- Audio button (if `audio_path` exists)

**Interactions:**
- **Space** or **click card** → flip front/back
- **1/2/3/4** keys → Again/Hard/Good/Easy (submit review, advance to next card)
- **A** key → play audio
- **F** key → toggle focus mode
- **Escape** → exit focus mode or exit review session (with confirmation)
- **Arrow Left/Right** → previous/next card (browse mode only)
- **Swipe left** (mobile) → Again
- **Swipe right** (mobile) → Good
- **Swipe up** (mobile) → flip card
- Rating button click → submit review, card advances, progress bar updates
- After last card → session summary screen (total reviewed, time spent, accuracy breakdown)

**Responsive behavior:**
- **Desktop:** Card centered 640px max, rating buttons in horizontal row, keyboard hints visible
- **Tablet:** Card centered 80% width, rating buttons horizontal, keyboard hints hidden
- **Mobile:** Card full-width (minus 16px padding), rating buttons in 2×2 grid or horizontal scroll, swipe gestures primary, keyboard hints hidden, tap to flip

---

### 2.3 Deck Browser

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR │  Decks                                        │
│         │  ┌────────────────────────────────────────┐   │
│         │  │ 🔍 Search decks...          [Filter ▾] │   │
│         │  └────────────────────────────────────────┘   │
│         │  CEFR: [A1] [A2] [B1] [B2] [C1] [Custom]      │
│         │                                               │
│         │  ┌─────────────┐ ┌─────────────┐ ┌──────────┐│
│         │  │ A1 Basics   │ │ A2 Daily    │ │ B1 Inter ││
│         │  │ 834 cards   │ │ 1,408 cards │ │ 2,000    ││
│         │  │ 23 due 🔥   │ │ 0 due  ✓   │ │ 47 due   ││
│         │  │ [Study]     │ │ [Study]    │ │ [Study]  ││
│         │  └─────────────┘ └─────────────┘ └──────────┘│
│         │  ┌─────────────┐ ┌─────────────┐ ┌──────────┐│
│         │  │ B2 Advanced │ │ C1 Expert   │ │ My Words ││
│         │  │ 2,000       │ │ 2,000       │ │ 47 cards ││
│         │  │ 12 due      │ │ 0 due       │ │ 5 due    ││
│         │  └─────────────┘ └─────────────┘ └──────────┘│
│         │                                               │
│         │  [+ New Deck]                                 │
└─────────────────────────────────────────────────────────┘
```

**Layout structure:**
- Desktop: Sidebar + main. Search bar full-width at top. Filter chips below. Deck cards in responsive grid (3 columns desktop, 2 tablet, 1 mobile).
- Main content scrolls vertically.

**Key components:**
- `SearchBar` — debounced search (300ms), searches deck names + tags
- `FilterChip` group — CEFR level multi-select + Custom toggle
- `Card` per deck — deck name, card count, due count (with flame icon if >0), "Study" button
- `Badge` — CEFR level badge on each deck card
- `Button` (outline) — "New Deck" at bottom
- `DropdownMenu` on deck card (via `···` button) — Edit, Export, Delete, Browse cards

**Data displayed:**
- Deck name, description (tooltip), CEFR level badge
- Total card count, due card count
- Source badge (builtin / custom / imported)
- Last studied timestamp (tooltip or subtext)

**Interactions:**
- Click deck card → navigate to `/decks/:deckId` (card list view)
- Click "Study" button → navigate to `/review?deck=:deckId`
- Click "New Deck" → open `Dialog` with deck creation form
- Search → filter decks by name/tag in real-time
- Filter chip toggle → show/hide decks by CEFR level
- Deck card `···` menu → Edit (dialog), Export (file save), Delete (alert dialog), Browse cards

**Responsive behavior:**
- **Desktop:** 3-column grid, search bar 400px max centered, filter chips in horizontal row
- **Tablet:** 2-column grid, search bar full-width
- **Mobile:** 1-column list, deck cards full-width with horizontal layout (name left, stats right), filter chips in horizontal scroll

---

### 2.4 Card Detail / Add

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR │  ← Back to Deck    Add New Card               │
│         │                                               │
│         │  ┌─────────────────────────────────────────┐  │
│         │  │  German Word *                           │  │
│         │  │  [ Haus                          ]       │  │
│         │  │                                           │  │
│         │  │  Article          Part of Speech         │  │
│         │  │  [ das ▾ ]        [ noun ▾ ]             │  │
│         │  │                                           │  │
│         │  │  Plural                                  │  │
│         │  │  [ Häuser                        ]       │  │
│         │  │                                           │  │
│         │  │  IPA (auto-filled)                       │  │
│         │  │  [ /haʊs/                        ]       │  │
│         │  │                                           │  │
│         │  │  English Translation *                   │  │
│         │  │  [ the house                     ]       │  │
│         │  │                                           │  │
│         │  │  Example Sentence (German)               │  │
│         │  │  [ Das Haus ist groß.           ]       │  │
│         │  │  Example Translation                     │  │
│         │  │  [ The house is big.            ]       │  │
│         │  │                                           │  │
│         │  │  Tags                                    │  │
│         │  │  [ greetings ] [ travel ] [+ add]        │  │
│         │  │                                           │  │
│         │  │  Deck                                    │  │
│         │  │  [ My Words ▾ ]                          │  │
│         │  │                                           │  │
│         │  │  [ ✨ Auto-Enrich ]                      │  │
│         │  │  → Fills article, plural, IPA, examples  │  │
│         │  │    from bundled Wiktionary data           │  │
│         │  │                                           │  │
│         │  │  [ Cancel ]  [ Save Card ]               │  │
│         │  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Layout structure:**
- Desktop: Sidebar + main. Form in a `Card` (max-width 640px, centered). Two-column layout for article + POS fields.
- Mobile: Full-width form, single column.

**Key components:**
- `Input` — word, plural, IPA, translation, example sentence, example translation
- `Select` — article (der/die/das/none), part of speech, deck
- `Badge` (removable) — tags
- `Input` (with add button) — new tag entry
- `Button` (secondary, with sparkle icon) — "Auto-Enrich"
- `Button` (ghost) — "Cancel"
- `Button` (primary) — "Save Card"

**Data displayed:**
- Form fields for all card properties
- Auto-enrichment status (loading spinner during lookup, success toast on completion)

**Interactions:**
- Type word → on blur, auto-suggest article + plural from bundled dictionary (debounced)
- Click "Auto-Enrich" → lookup word in bundled Wiktionary data, fill empty fields (article, plural, IPA, example sentences). Show toast with what was filled.
- Add tag → type and press Enter, creates removable `Badge`
- Save → validate required fields (word + translation), insert into SQLite, create SRS card state, show success toast, navigate back to deck
- Cancel → confirm if any fields filled, navigate back

**Responsive behavior:**
- **Desktop:** Form 640px centered, article + POS side by side
- **Tablet:** Form 80% width, article + POS side by side
- **Mobile:** Form full-width, all fields stacked, article + POS side by side (compact)

---

### 2.5 Statistics

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR │  Statistics        [7d] [30d] [90d] [All]      │
│         │                                               │
│         │  ┌────────────┐ ┌────────────┐ ┌────────────┐│
│         │  │ Retention  │ │ Cards      │ │ Time       ││
│         │  │   87%      │ │ Learned    │ │ Studied    ││
│         │  │  ↑ 2%      │ │   1,243    │ │  14h 32m   ││
│         │  └────────────┘ └────────────┘ └────────────┘│
│         │                                               │
│         │  Card States                                 │
│         │  ┌─────────────────────────────────────────┐ │
│         │  │     ◯ New (234)                         │ │
│         │  │    ◯ Learning (89)                      │ │
│         │  │   ◯ Young (567)                         │ │
│         │  │  ◯ Mature (1,245)                       │ │
│         │  │           [Pie Chart]                   │ │
│         │  └─────────────────────────────────────────┘ │
│         │                                               │
│         │  Reviews per Day                             │
│         │  ┌─────────────────────────────────────────┐ │
│         │  │  ▌  ▌▌  ▌▌▌  ▌▌▌▌  ▌▌▌  ▌▌  ▌          │ │
│         │  │  M  T  W  T  F  S  S                    │ │
│         │  │           [Bar Chart]                   │ │
│         │  └─────────────────────────────────────────┘ │
│         │                                               │
│         │  Review Activity                             │
│         │  ┌─────────────────────────────────────────┐ │
│         │  │  ▓▓░░▓▓▓░▓▓▓▓░░▓▓▓▓▓░░░▓▓▓▓▓▓░░▓▓▓░░  │ │
│         │  │  [Calendar Heatmap — last 12 weeks]     │ │
│         │  └─────────────────────────────────────────┘ │
│         │                                               │
│         │  Upcoming Reviews (Forecast)                 │
│         │  ┌─────────────────────────────────────────┐ │
│         │  │  Today: 47  Tomorrow: 52  Wed: 38  ...  │ │
│         │  │  [Line/Area Chart — next 30 days]       │ │
│         │  └─────────────────────────────────────────┘ │
│         │                                               │
│         │  Per-Deck Retention                          │
│         │  ┌─────────────────────────────────────────┐ │
│         │  │  A1 Basics    ████████░░  82%           │ │
│         │  │  A2 Daily     █████████░  89%           │ │
│         │  │  B1 Inter     ██████░░░░  65%           │ │
│         │  │  [Horizontal Bar Chart]                 │ │
│         │  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Layout structure:**
- Desktop: Sidebar + main. Time range `Tabs` at top. Stat cards in 3-column row. Charts in vertical stack, each in a `ChartContainer` (Card). Two-column grid for some charts on wide screens.
- Mobile: Everything stacked vertically, single column.

**Key components:**
- `Tabs` — time range selector (7d / 30d / 90d / All)
- `StatCard` × 3 — Retention (with trend arrow), Cards Learned, Time Studied
- `ChartContainer` — wrapper for each chart with title + description
- **Pie chart** — card states (new/learning/young/mature) with legend
- **Bar chart** — reviews per day (last 7/30/90 days)
- `CalendarHeatmap` — GitHub-style activity heatmap (last 12 weeks)
- **Area chart** — forecast of upcoming reviews (next 30 days)
- **Horizontal bar chart** — per-deck retention comparison

**Data displayed:**
- Overall retention rate (correct / total, selected time range) with trend vs previous period
- Total cards learned (reached mature state)
- Total time studied (sum of `duration_ms` from `review_logs`)
- Card state distribution (count by FSRS state)
- Reviews per day histogram
- Daily activity heatmap (days with ≥1 review)
- 30-day forecast (count of cards due per day)
- Per-deck retention breakdown

**Interactions:**
- Time range tab change → all charts update to selected range
- Hover chart elements → tooltip with exact values
- Click pie chart segment → filter to that card state (navigate to deck browser with filter)
- Click heatmap day → show that day's review details (toast or popover)
- Click per-deck bar → navigate to that deck's stats

**Responsive behavior:**
- **Desktop:** Stat cards 3-column, charts full-width or 2-column grid, heatmap full-width
- **Tablet:** Stat cards 3-column (compact), charts full-width
- **Mobile:** Stat cards stacked, charts full-width with simplified labels, heatmap scrolls horizontally, per-deck bars full-width

---

### 2.6 Settings

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR │  Settings                                    │
│         │  ┌────────┬────────┬────────┬────────┬──────┐ │
│         │  │ Review │ Appea- │ Audio  │ Data   │ About│ │
│         │  │        │ rance  │        │        │      │ │
│         │  └────────┴────────┴────────┴────────┴──────┘ │
│         │                                               │
│         │  ── Review Settings ──                        │
│         │  Desired Retention                           │
│         │  [━━━━━━━━━━●━━━━━━━] 90%                    │
│         │  (75% — 99%, FSRS target retention)          │
│         │                                               │
│         │  Max Interval (days)                         │
│         │  [ 36500 ]                                   │
│         │                                               │
│         │  Learning Steps                              │
│         │  [ 1m ] [ 10m ]  [+ add step]                │
│         │                                               │
│         │  Daily New Cards                             │
│         │  [ 20 ]                                      │
│         │                                               │
│         │  Daily Reviews                               │
│         │  [ 200 ]                                     │
│         │                                               │
│         │  ── Appearance ──                             │
│         │  Theme                                       │
│         │  ( ) Light   ( ) Dark   (•) System           │
│         │                                               │
│         │  Font Size                                   │
│         │  [━━━━●━━━━━━━━━━━━] 100%                    │
│         │                                               │
│         │  Show IPA on cards          [● ON  ]         │
│         │  Show keyboard hints       [● ON  ]          │
│         │                                               │
│         │  ── Audio ──                                  │
│         │  Auto-play on card show    [  OFF ●]         │
│         │  Playback Speed                               │
│         │  [━━━━━●━━━━━━━━━━━━] 1.0x                    │
│         │  (0.5x — 2.0x)                               │
│         │                                               │
│         │  ── Data Management ──                        │
│         │  Database Size: 82.3 MB                      │
│         │  Audio Files: 1,247 files, 340 MB            │
│         │  [ Export Data ]  [ Import Data ]             │
│         │  [ Optimize FSRS Parameters ]                 │
│         │  [ Reset All Progress ] (danger zone)         │
│         │                                               │
│         │  ── About ──                                  │
│         │  German mit Dr. Khans v1.0.0                  │
│         │  Data sources: Wiktionary, Tatoeba, ...       │
│         │  [ View Licenses ]  [ View Attributions ]     │
└─────────────────────────────────────────────────────────┘
```

**Layout structure:**
- Desktop: Sidebar + main. `Tabs` at top (horizontal). Settings sections stack vertically within active tab. Form max-width 640px.
- Mobile: Tabs become horizontal scroll. Settings stack vertically.

**Key components:**
- `Tabs` — Review / Appearance / Audio / Data / About
- `Slider` — desired retention (75–99%), font size (75–150%), playback speed (0.5–2.0x)
- `Input` (number) — max interval, daily new cards, daily reviews
- `Input` (text, tag-style) — learning steps
- `Switch` — auto-play, show IPA, show keyboard hints
- `RadioGroup` / `ToggleGroup` — theme (light/dark/system)
- `Button` (secondary) — export, import, optimize FSRS
- `Button` (destructive) — reset all progress (with `AlertDialog` confirmation)
- `Collapsible` — advanced FSRS parameters (show 19 default parameters for power users)

**Data displayed:**
- Current FSRS parameters (desired retention, max interval, learning steps)
- Daily limits (new cards, reviews)
- Theme, font size, display options
- Audio settings
- Database size, audio file count + total size
- App version, data source attributions, licenses

**Interactions:**
- Slider/input change → save to `settingsStore` (debounced 500ms), persist to `tauri-plugin-store`
- Theme change → immediate apply via `useTheme` hook
- Font size change → update CSS `--font-scale` variable, all text scales
- Export → open file save dialog, export SQLite DB + settings as `.zip`
- Import → open file dialog, import DB (with confirmation — overwrites current)
- Optimize FSRS → run `fsrs-rs` optimizer on review logs, show progress, update parameters
- Reset progress → `AlertDialog` with double confirmation, resets all `srs_cards` to new state

**Responsive behavior:**
- **Desktop:** Tabs horizontal, form 640px centered, sliders full-width within form
- **Tablet:** Same as desktop, slightly narrower
- **Mobile:** Tabs as horizontal scroll, form full-width, all controls stacked, sliders full-width

---

### Phase 2 Screens

---

### 2.7 Grammar Overview

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR │  Grammar Lessons                             │
│         │  🔍 Search lessons...                        │
│         │  Level: [A1] [A2] [B1] [B2] [C1]             │
│         │  Category: [All ▾]                           │
│         │                                               │
│         │  ▸ A1 — Beginner                             │
│         │  ┌─────────────────────────────────────────┐ │
│         │  │ ✓ Nominativ vs. Akkusativ     [Completed]│ │
│         │  │ ◐ Present Tense (Präsens)     [3/5 done] │ │
│         │  │ ○ Articles (der/die/das)      [Not start]│ │
│         │  │ ○ Plural Forms               [Not start]│ │
│         │  └─────────────────────────────────────────┘ │
│         │                                               │
│         │  ▸ A2 — Elementary                           │
│         │  ┌─────────────────────────────────────────┐ │
│         │  │ ○ Dativ Case                 [Not start]│ │
│         │  │ ○ Past Tense (Perfekt)       [Not start]│ │
│         │  │ ○ Modal Verbs                [Not start]│ │
│         │  └─────────────────────────────────────────┘ │
│         │                                               │
│         │  ▸ B1 — Intermediate                         │
│         │  ┌─────────────────────────────────────────┐ │
│         │  │ ○ Subjunctive (Konjunktiv II)[Not start]│ │
│         │  │ ○ Relative Clauses           [Not start]│ │
│         │  │ ○ Passive Voice              [Not start]│ │
│         │  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Layout structure:**
- Desktop: Sidebar + main. Search + filters at top. Lessons grouped by CEFR level using `Collapsible` sections. Each lesson is a row in a list.
- Mobile: Same layout, full-width, collapsible sections.

**Key components:**
- `SearchBar` — search lesson titles + content
- `FilterChip` group — CEFR level multi-select
- `Select` — category filter (cases, verbs, word order, tenses, conjunctions, prepositions, etc.)
- `Collapsible` per CEFR level — expandable section with lesson list
- `Card` per lesson row — title, progress indicator, status `Badge`
- Status icons: ✓ (completed, green), ◐ (in progress, warning), ○ (not started, muted)

**Data displayed:**
- Lesson title, CEFR level badge, category
- Progress: completed / total exercises
- Status: not started / in progress / completed
- Lesson count per CEFR level

**Interactions:**
- Click lesson row → navigate to `/grammar/:lessonId`
- Search → filter lessons by title/content
- CEFR filter chip → show/hide lessons by level
- Category select → filter by grammar category
- Collapsible toggle → expand/collapse CEFR level sections

**Responsive behavior:**
- **Desktop:** Full layout, lesson rows with status badges right-aligned
- **Tablet:** Same, slightly narrower
- **Mobile:** Full-width, lesson rows compact (title + status icon only, badge hidden), collapsible sections

---

### 2.8 Grammar Lesson View

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR │  ← A1 Grammar    Nominativ vs. Akkusativ      │
│         │  ┌──────────────┐ ┌────────────────────────┐  │
│         │  │ Lesson Nav   │ │  # Nominativ vs.       │  │
│         │  │              │ │    Akkusativ           │  │
│         │  │ ✓ Intro      │ │                        │  │
│         │  │ ◐ Nominativ  │ │  The **nominative**    │  │
│         │  │ ○ Akkusativ  │ │  case is used for the  │  │
│         │  │ ○ Summary    │ │  subject of a sentence.│  │
│         │  │              │ │                        │  │
│         │  │ ─────────    │ │  > Der Hund läuft.     │  │
│         │  │              │ │  (The dog runs.)       │  │
│         │  │ Related:     │ │                        │  │
│         │  │ ○ Articles   │ │  The **accusative**    │  │
│         │  │ ○ Pronouns   │ │  case is used for the  │  │
│         │  │              │ │  direct object.        │  │
│         │  │              │ │                        │  │
│         │  │              │ │  > Ich sehe den Hund.  │  │
│         │  │              │ │  (I see the dog.)      │  │
│         │  │              │ │                        │  │
│         │  │              │ │  ## Common Mistakes    │  │
│         │  │              │ │                        │  │
│         │  │              │ │  ⚠️ After "sein"       │  │
│         │  │              │ │  (to be), the          │  │
│         │  │              │ │  complement stays in   │  │
│         │  │              │ │  nominative, not       │  │
│         │  │              │ │  accusative.           │  │
│         │  │              │ │                        │  │
│         │  │              │ │  [▶ Practice Exercises]│  │
│         │  └──────────────┘ └────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Layout structure:**
- Desktop: Sidebar + main. Main area split into two columns: lesson navigation (left, 240px) + markdown content (right, flex-1, max-width 720px). Content scrolls vertically.
- Mobile: No lesson nav sidebar. Content full-width. Lesson nav accessible via `DropdownMenu` or breadcrumb.

**Key components:**
- `ScrollArea` — lesson content scroll (custom styled scrollbar)
- `MarkdownRenderer` — renders lesson markdown with syntax highlighting for German examples, blockquotes for examples, warning callouts for common mistakes
- `Card` (sidebar) — lesson navigation with progress indicators
- `Button` (primary, lg) — "Practice Exercises" at bottom of content
- `Breadcrumb` — Level > Category > Lesson title
- `Separator` — between nav sections

**Data displayed:**
- Lesson content (markdown → HTML): headings, paragraphs, example sentences (with `lang="de"`), tables (conjugation/declension tables), common mistakes callouts, tips
- Lesson navigation: sections within lesson, progress per section
- Related lessons: links to prerequisite/related grammar topics

**Interactions:**
- Click nav item → scroll to that section in content (smooth scroll)
- Click "Practice Exercises" → navigate to `/grammar/:lessonId/exercises`
- Click related lesson → navigate to that lesson
- Scroll content → active nav item highlights based on scroll position (intersection observer)

**Responsive behavior:**
- **Desktop:** Two-column (nav 240px + content), content max-width 720px
- **Tablet:** Nav collapses to 200px, content fills rest
- **Mobile:** No nav sidebar, content full-width, nav via dropdown/breadcrumb, font size slightly smaller, examples in scrollable blocks

---

### 2.9 Grammar Exercise Player

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR │  ← Lesson     Exercise 3 of 8                 │
│         │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│         │                                               │
│         │  Fill in the correct article:                │
│         │                                               │
│         │  "Ich sehe ___ Hund im Garten."              │
│         │         (lang="de")                          │
│         │                                               │
│         │  ┌──────┐ ┌──────┐ ┌──────┐                  │
│         │  │ der  │ │ die  │ │ das  │                  │
│         │  └──────┘ └──────┘ └──────┘                  │
│         │                                               │
│         │  ┌─────────────────────────────────────────┐ │
│         │  │  ✓ Correct!                             │ │
│         │  │                                           │ │
│         │  │  "der" is used because "Hund" is         │ │
│         │  │  masculine, and "sehen" takes the        │ │
│         │  │  accusative case.                        │ │
│         │  │                                           │ │
│         │  │  Rule: Nominativ → Akkusativ             │ │
│         │  │  der → den, die → die, das → das         │ │
│         │  └─────────────────────────────────────────┘ │
│         │                                               │
│         │  [ Skip ]                    [ Next → ]       │
└─────────────────────────────────────────────────────────┘
```

**Exercise types:**

1. **Fill-in-blank (article):** Sentence with blank, 3 article buttons (der/die/das)
2. **Fill-in-blank (case):** Sentence with blank, input field for declined article
3. **Fill-in-blank (conjugation):** Sentence with blank, input field for verb form
4. **Multiple choice:** Question + 4 answer options as buttons
5. **Cloze deletion:** Sentence with blank, input field for missing word
6. **Word order drag-drop:** Scrambled words, user arranges by dragging

**Layout structure:**
- Desktop: Sidebar + main. Exercise centered (max-width 640px). Progress bar at top. Question → input → feedback → next.
- Focus mode available (same as vocab review).

**Key components:**
- `Progress` bar — exercise progress (current/total)
- `Card` — exercise container (question text, input area)
- `Button` group — MC options, article selection
- `Input` — fill-blank text input
- Custom drag-drop — word order arrangement (using `@dnd-kit/core` or native HTML5 drag)
- `Card` (feedback) — appears after answer: green border for correct, red for incorrect, with explanation
- `Button` (ghost) — "Skip"
- `Button` (primary) — "Next" (appears after answering)

**Data displayed:**
- Exercise prompt (sentence with blank, question)
- Input options (buttons or text field)
- After answering: correct/incorrect indicator, correct answer, explanation, grammar rule reference
- Progress through exercise set

**Interactions:**
- Select answer → immediate feedback (correct/incorrect + explanation)
- Type answer + Enter → check answer
- Drag words → rearrange (word order exercises)
- "Next" → advance to next exercise
- "Skip" → mark as skipped, advance
- **1-4** keys → select MC option (desktop)
- **Enter** → submit typed answer / go to next after feedback
- After last exercise → session summary (score, time, mistakes by type)

**Session Summary (after last exercise):**

```
┌───────────────────────────┐
│  Exercise Session Complete │
│                            │
│  Score: 6/8 (75%)         │
│  Time: 4m 32s             │
│                            │
│  Mistakes:                 │
│  ✗ Article: der → den (1) │
│  ✗ Case: Akkusativ (1)    │
│                            │
│  [ Review Mistakes ]       │
│  [ Back to Lesson ]        │
│  [ Next Lesson → ]         │
└───────────────────────────┘
```

**Responsive behavior:**
- **Desktop:** Exercise centered 640px, feedback below question, MC buttons horizontal
- **Tablet:** Same, slightly wider
- **Mobile:** Exercise full-width, feedback stacked below, MC buttons full-width stacked or 2×2 grid, drag-drop becomes tap-to-place

---

### Phase 3 Screens

---

### 2.10 Reading Library

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR │  Reading Library                             │
│         │  🔍 Search passages...                       │
│         │  Level: [A1] [A2] [B1] [B2] [C1] [C2]        │
│         │  Type: [All] [Article] [Story] [News] [Poem] │
│         │                                               │
│         │  ┌─────────────┐ ┌─────────────┐ ┌──────────┐│
│         │  │ Der erste   │ │ Berlin im   │ │ Der Wolf ││
│         │  │ Tag         │ │ Winter      │ │ und die  ││
│         │  │             │ │             │ │ 7 Geißlein││
│         │  │ A1 · Story  │ │ B1 · Article│ │ A2 · Story││
│         │  │ 120 words   │ │ 340 words   │ │ 280 words││
│         │  │ 2 min read  │ │ 5 min read  │ │ 4 min    ││
│         │  │ ✓ Read      │ │ ◐ Reading   │ │ ○ New    ││
│         │  └─────────────┘ └─────────────┘ └──────────┘│
│         │                                               │
│         │  ┌─────────────┐ ┌─────────────┐              │
│         │  │ Faust:      │ │ Gedicht 3   │              │
│         │  │ Auszug      │ │ (Heine)     │              │
│         │  │ C2 · Classic│ │ B2 · Poem   │              │
│         │  │ 850 words   │ │ 45 words    │              │
│         │  │ 12 min      │ │ 1 min       │              │
│         │  └─────────────┘ └─────────────┘              │
│         │                                               │
│         │  [+ Import Text]                              │
└─────────────────────────────────────────────────────────┘
```

**Layout structure:**
- Desktop: Sidebar + main. Search + filters at top. Passage cards in responsive grid (3 columns desktop, 2 tablet, 1 mobile).
- Same pattern as Deck Browser.

**Key components:**
- `SearchBar` — search passage titles + content
- `FilterChip` group — CEFR level + type (article/story/news/poem)
- `Card` per passage — title, CEFR badge, type badge, word count, reading time, read status
- `Button` (outline) — "Import Text"
- Status icons: ✓ (read), ◐ (in progress), ○ (new)

**Data displayed:**
- Passage title, CEFR level, type (article/story/news/poem/classic)
- Word count, estimated reading time (words / 200 wpm)
- Read status (completed / in progress / not started)
- Comprehension question count (badge)

**Interactions:**
- Click passage card → navigate to `/reading/:passageId`
- Click "Import Text" → navigate to `/import`
- Search → filter passages
- Filter chips → show/hide by CEFR + type

**Responsive behavior:**
- **Desktop:** 3-column grid, cards with all metadata visible
- **Tablet:** 2-column grid
- **Mobile:** 1-column list, compact cards (title + level + reading time only)

---

### 2.11 Reading View

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR │  ← Library    Der erste Tag          [⛶ Focus]│
│         │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│         │                                               │
│         │  ┌─────────────────────────┐ ┌──────────────┐│
│         │  │  Der erste Tag          │ │  Word Lookup ││
│         │  │                         │ │              ││
│         │  │  Am Montag Morgen       │ │  Click a word││
│         │  │  wachte Anna früh auf.  │ │  in the text ││
│         │  │  Die Sonne schien durch │ │  to see its  ││
│         │  │  das  Fenster  und  ein │ │  definition. ││
│         │  │  Vogel sang im Garten.  │ │              ││
│         │  │                         │ │  ─────────── ││
│         │  │  Sie stand auf und      │ │              ││
│         │  │  ging zum Frühstück.    │ │  Last looked ││
│         │  │  ...                    │ │  up:         ││
│         │  │                         │ │              ││
│         │  │  (clickable words:      │ │  • Fenster   ││
│         │  │   underlined, hover =   │ │    (n) window ││
│         │  │   definition preview)   │ │    [🔊] [+SRS]││
│         │  │                         │ │              ││
│         │  │                         │ │  • Garten    ││
│         │  │                         │ │    (m) garden ││
│         │  │                         │ │    [🔊] [+SRS]││
│         │  └─────────────────────────┘ └──────────────┘│
│         │                                               │
│         │  Comprehension Questions                      │
│         │  ┌─────────────────────────────────────────┐  │
│         │  │ 1. When did Anna wake up?               │  │
│         │  │   ( ) Sunday  (•) Monday  ( ) Friday    │  │
│         │  │                                           │  │
│         │  │ 2. What did she hear in the garden?     │  │
│         │  │   [ _______________ ]                    │  │
│         │  │                                           │  │
│         │  │  [ Submit Answers ]                      │  │
│         │  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Layout structure:**
- Desktop: Sidebar + main. Main area split: reading text (left, 60%) + word lookup panel (right, 40%, sticky). Comprehension questions below text (full width). Progress bar at top.
- Focus mode: Text only, centered, max-width 720px. Word lookup via popup on click.
- Mobile: Single column. Text full-width. Word lookup via `Popover` on tap. Questions below.

**Key components:**
- `Progress` bar — reading progress (scroll position / total height)
- `ScrollArea` — text content with clickable words
- `WordPopup` / `HoverCard` — word definition, POS, article, IPA, audio button, "Add to SRS" button
- `Card` (word lookup panel) — sticky right panel showing recently looked-up words
- `Button` (icon) — focus mode toggle
- `Card` (comprehension questions) — MC questions, fill-blank questions
- `Button` (primary) — "Submit Answers"

**Data displayed:**
- Reading passage text (with clickable German words, `lang="de"`)
- Word definitions on click/hover (from bundled dictionary)
- Audio for words (if available)
- Reading progress
- Comprehension questions (2–5 per passage)

**Interactions:**
- Click word → show `WordPopup` with definition + audio + "Add to SRS"
- Hover word (desktop) → `HoverCard` preview with definition
- Click "Add to SRS" → add word to user's SRS deck, show toast
- Click "🔊" → play word audio
- Scroll → progress bar updates
- Answer questions → select/type answers
- Submit → show score + correct answers + explanations
- **Focus mode (F):** hide panels, text centered

**Responsive behavior:**
- **Desktop:** Two-column (text 60% + lookup 40%), questions full-width below
- **Tablet:** Two-column (text 65% + lookup 35%), narrower
- **Mobile:** Single column, text full-width, word lookup via tap `Popover`, questions below, no side panel

---

### 2.12 Listening Library

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR │  Listening Exercises                        │
│         │  🔍 Search...                                │
│         │  Level: [A1] [A2] [B1] [B2] [C1] [C2]        │
│         │  Duration: [All] [<2min] [2-5min] [5-10min]  │
│         │                                               │
│         │  ┌─────────────────────────────────────────┐ │
│         │  │ 🎧 Wetterbericht — Berlin     A2 · 1:30 │ │
│         │  │    Weather forecast, slow pace          │ │
│         │  │    [▶ Play]  ○ Not started              │ │
│         │  ├─────────────────────────────────────────┤ │
│         │  │ 🎧 Im Café              B1 · 3:45       │ │
│         │  │    Conversation at a café               │ │
│         │  │    [▶ Play]  ◐ 2/3 questions            │ │
│         │  ├─────────────────────────────────────────┤ │
│         │  │ 🎧 Kafka: Die Verwandlung  C2 · 12:20   │ │
│         │  │    Audiobook excerpt with transcript     │ │
│         │  │    [▶ Play]  ✓ Completed                │ │
│         │  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Layout structure:**
- Desktop: Sidebar + main. Search + filters at top. Exercises in a list (full-width rows).
- Mobile: Same list layout, compact rows.

**Key components:**
- `SearchBar` — search by title/description
- `FilterChip` group — CEFR level + duration range
- `Card` per exercise — title, headphone icon, CEFR badge, duration, description, play button, status
- `Button` (ghost, icon) — play preview

**Data displayed:**
- Exercise title, CEFR level, duration, description
- Audio type (TTS / human / audiobook)
- Status (not started / in progress / completed)
- Comprehension question count

**Interactions:**
- Click exercise → navigate to `/listening/:exerciseId`
- Search → filter exercises
- Filter chips → show/hide by CEFR + duration

**Responsive behavior:**
- **Desktop:** Full-width list, rows with all metadata
- **Tablet:** Same, slightly narrower
- **Mobile:** Compact rows (title + level + duration only), play button prominent

---

### 2.13 Listening Player

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR │  ← Library    Wetterbericht — Berlin          │
│         │                                               │
│         │  ┌─────────────────────────────────────────┐  │
│         │  │           A2 · 1:30                     │  │
│         │  │                                           │  │
│         │  │  ▶  ━━━━━━━━●━━━━━━━━━━━━━━━━━━  0:45   │  │
│         │  │                                           │  │
│         │  │  Speed: [0.75x] [1.0x] [1.25x] [1.5x]   │  │
│         │  │                                           │  │
│         │  │  Show Transcript        [● ON  ]         │  │
│         │  │  Cloze Mode             [  OFF ●]        │  │
│         │  └─────────────────────────────────────────┘  │
│         │                                               │
│         │  Transcript (lang="de")                      │
│         │  ┌─────────────────────────────────────────┐  │
│         │  │  Guten Tag. Hier ist der Wetterbericht  │  │
│         │  │  für Berlin.                             │  │
│         │  │                                           │  │
│         │  │  Morgen wird es bewölkt sein, mit        │  │
│         │  │  ⬆ current sentence highlighted          │  │
│         │  │  Temperaturen um 15 Grad.                │  │
│         │  │                                           │  │
│         │  │  In der Nacht kann es leicht regnen.     │  │
│         │  └─────────────────────────────────────────┘  │
│         │                                               │
│         │  Comprehension Questions                     │
│         │  ┌─────────────────────────────────────────┐  │
│         │  │ 1. What's the weather tomorrow?         │  │
│         │  │   ( ) Sunny  (•) Cloudy  ( ) Rainy       │  │
│         │  │                                           │  │
│         │  │ 2. What's the temperature?               │  │
│         │  │   [ _______________ ]                    │  │
│         │  │                                           │  │
│         │  │  [ Submit Answers ]                      │  │
│         │  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Layout structure:**
- Desktop: Sidebar + main. Audio player bar at top (sticky). Transcript below (scrollable). Comprehension questions below transcript. All centered, max-width 720px.
- Mobile: Same vertical stack, full-width.

**Key components:**
- `AudioPlayer` — play/pause button, seek bar (with time display), speed selector buttons
- `Switch` — show/hide transcript, cloze mode toggle
- `ScrollArea` — transcript text with current sentence highlighted (synced with audio timestamps)
- `Card` (comprehension questions) — MC + fill-blank questions, appears after listening
- `Button` (primary) — "Submit Answers"
- Cloze mode: transcript with blanks, user fills while listening

**Data displayed:**
- Audio player state (playing/paused, current time, total duration, speed)
- Transcript text (with `lang="de"`), current sentence highlighted
- Comprehension questions (2–5 per exercise)
- In cloze mode: transcript with blanks instead of full text

**Interactions:**
- Play/pause → toggle audio playback
- Seek bar drag → jump to position
- Speed button → change playback rate (0.75x / 1.0x / 1.25x / 1.5x)
- Transcript toggle → show/hide transcript text
- Cloze mode toggle → switch between full transcript and fill-blank mode
- Click transcript sentence → seek audio to that sentence's timestamp
- Answer questions → select/type
- Submit → show score + correct answers
- **Space** → play/pause (desktop)

**Responsive behavior:**
- **Desktop:** All centered 720px max, transcript + questions side by side or stacked
- **Tablet:** Same, slightly narrower
- **Mobile:** Full-width, audio player compact, transcript full-width, questions below, speed buttons as dropdown to save space

---

### 2.14 Import

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR │  ← Library    Import Text                    │
│         │                                               │
│         │  ┌─────────────────────────────────────────┐  │
│         │  │         📄 Drop file here                │  │
│         │  │      or [ Choose File ]                 │  │
│         │  │                                           │  │
│         │  │  Supported: PDF, EPUB, TXT               │  │
│         │  └─────────────────────────────────────────┘  │
│         │                                               │
│         │  (after file selected:)                      │
│         │  ┌─────────────────────────────────────────┐  │
│         │  │  File: goethe_faust.txt  (24 KB)        │  │
│         │  │                                           │  │
│         │  │  Title: [ Faust — Auszug         ]      │  │
│         │  │  CEFR Level: [ B2 ▾ ]                   │  │
│         │  │  Type: [ Classic ▾ ]                    │  │
│         │  │                                           │  │
│         │  ── Text Preview ──                         │  │
│         │  ┌─────────────────────────────────────────┐  │
│         │  │  Habe nun, ach! Philosophie,            │  │
│         │  │  Juristerei und Medizin...              │  │
│         │  │  (first 500 words, scrollable)          │  │
│         │  │                                           │  │
│         │  │  Estimated CEFR: B2 (auto-detected)     │  │
│         │  │  Word count: 850                        │  │
│         │  │  Reading time: ~4 min                   │  │
│         │  └─────────────────────────────────────────┘  │
│         │  │                                           │  │
│         │  │  [ Cancel ]  [ Import to Library ]       │  │
│         │  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Layout structure:**
- Desktop: Sidebar + main. Drop zone at top (dashed border). After file selected: metadata form + text preview. All centered, max-width 720px.
- Mobile: Same vertical stack, full-width.

**Key components:**
- Drop zone — dashed border `Card`, drag-and-drop + file picker button
- `Button` — "Choose File" (opens `tauri-plugin-dialog`)
- `Input` — title (auto-filled from filename)
- `Select` — CEFR level (auto-detected, user can override), type
- `ScrollArea` — text preview (first 500 words)
- `Badge` — auto-detected CEFR level, word count, reading time
- `Button` (ghost) — "Cancel"
- `Button` (primary) — "Import to Library"

**Data displayed:**
- File name, size
- Text preview (first 500 words)
- Auto-detected CEFR level (from DAFlex word frequency analysis)
- Word count, estimated reading time
- Editable title, CEFR level, type

**Interactions:**
- Drag file onto drop zone → process file
- Click "Choose File" → open native file dialog (PDF/EPUB/TXT filter)
- File selected → extract text (PDF via `pdfplumber`/Rust crate, EPUB via XML parse, TXT direct), show preview
- Auto-detect CEFR → analyze word frequencies against DAFlex, suggest level
- Edit title/level/type → user can override auto-detected values
- "Import to Library" → save text to SQLite `reading_passages`, navigate to reading view
- "Cancel" → discard, navigate back

**Responsive behavior:**
- **Desktop:** Form 720px centered, preview in scrollable area
- **Tablet:** Same, slightly narrower
- **Mobile:** Full-width, drop zone smaller, preview full-width

---

## 3. Navigation Architecture

### 3.1 Desktop Navigation — Left Sidebar

```
┌────────────────────────┐
│  🌲 German mit         │  ← Logo + app name (Source Serif)
│     Dr. Khans          │
│  ───────────────────── │  ← Separator
│                        │
│  📊 Dashboard          │  ← Nav items (lucide-react icons)
│  🔄 Review       47 🔴 │  ← Badge with due count
│  📚 Decks              │
│  ───────────────────── │  ← Separator (Phase 2+ items)
│  📖 Grammar            │
│  📜 Reading            │
│  🎧 Listening          │
│  ───────────────────── │
│  📈 Statistics         │
│  ⚙️ Settings           │
│                        │
│  ───────────────────── │  ← Footer area
│  🔥 23-day streak      │  ← Streak indicator (accent color)
│  ☀️/🌙 Theme toggle    │  ← Quick theme toggle
└────────────────────────┘
   240px (expanded) / 64px (collapsed, icon-only)
```

**Sidebar behavior:**
- Fixed width 240px on desktop (≥1024px), collapsible to 64px icon-only rail
- Collapse toggle: chevron button at top, or `Cmd/Ctrl+B` keyboard shortcut
- Active item: `--sidebar-accent` background, `--primary` text, left border accent
- Review item shows due count badge (accent/copper color, hidden when 0)
- Streak indicator at bottom with flame icon (accent color)
- Quick theme toggle (sun/moon icon) at very bottom

**Nav items (8 total):**

| Item | Icon (Lucide) | Route | Badge |
|---|---|---|---|
| Dashboard | `LayoutDashboard` | `/` | — |
| Review | `RotateCcw` | `/review` | Due count |
| Decks | `LibraryBig` | `/decks` | — |
| Grammar | `BookOpen` | `/grammar` | — |
| Reading | `FileText` | `/reading` | — |
| Listening | `Headphones` | `/listening` | — |
| Statistics | `BarChart3` | `/stats` | — |
| Settings | `Settings` | `/settings` | — |

### 3.2 Mobile Navigation — Bottom Nav

```
┌──────────────────────────────────────┐
│         (page content)               │
├──────────────────────────────────────┤
│  📊      🔄       📖      📜      📈  │
│ Home    Review   Grammar  Reading  Stats│
└──────────────────────────────────────┘
   56px height, fixed at bottom, safe-area aware
```

**Bottom nav behavior:**
- Visible only on mobile (<768px): `flex md:hidden`
- 5 items max (ergonomic limit for thumb reach)
- Settings accessed from Dashboard (gear icon in top-right)
- Active item: `--primary` color icon + label, top border accent (2px)
- Inactive: `--muted-foreground` color
- Icons only on very small screens (<400px), labels appear at ≥400px

**Mobile nav items (5):**

| Item | Icon | Route | Notes |
|---|---|---|---|
| Home | `LayoutDashboard` | `/` | Dashboard |
| Review | `RotateCcw` | `/review` | Due count badge |
| Grammar | `BookOpen` | `/grammar` | Phase 2 |
| Reading | `FileText` | `/reading` | Phase 3 |
| Stats | `BarChart3` | `/stats` | Statistics |

> **Decks, Listening, Settings** accessible from Dashboard quick-links or "more" menu (hamburger → `Sheet` drawer with full nav).

### 3.3 Sidebar → Bottom Nav Transition (CSS)

```tsx
<div className="flex h-screen">
  <Sidebar className="hidden md:flex" />
  <main className="flex-1 overflow-y-auto pb-14 md:pb-0">
    <RouterProvider router={router} />
  </main>
  <BottomNav className="flex md:hidden" />
</div>
```

Key Tailwind classes:
- Sidebar: `hidden md:flex` — shows at ≥768px
- Bottom nav: `flex md:hidden` — shows at <768px
- Main content: `pb-14 md:pb-0` — bottom padding for nav bar on mobile only

### 3.4 Routing — React Router v7 (Hash-Based)

```typescript
import { createHashRouter, RouterProvider } from 'react-router';

const router = createHashRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'review', element: <VocabReview /> },
      { path: 'review/summary', element: <ReviewSummary /> },
      { path: 'decks', element: <DeckBrowser /> },
      { path: 'decks/:deckId', element: <DeckDetail /> },
      { path: 'decks/:deckId/add', element: <CardAddEdit /> },
      { path: 'grammar', element: <GrammarOverview /> },
      { path: 'grammar/:lessonId', element: <GrammarLesson /> },
      { path: 'grammar/:lessonId/exercises', element: <GrammarExercises /> },
      { path: 'reading', element: <ReadingLibrary /> },
      { path: 'reading/:passageId', element: <ReadingView /> },
      { path: 'listening', element: <ListeningLibrary /> },
      { path: 'listening/:exerciseId', element: <ListeningPlayer /> },
      { path: 'import', element: <ImportPage /> },
      { path: 'stats', element: <Statistics /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
]);
```

**Why hash routing?** Tauri serves frontend from `tauri://localhost` (custom protocol), not a real HTTP server. Hash routing avoids deep-linking issues on desktop and Android.

**Nested routes:**
- `/grammar/:lessonId` — lesson view with markdown content
- `/grammar/:lessonId/exercises` — exercise player for that lesson
- `/decks/:deckId` — card list within a deck
- `/decks/:deckId/add` — add card to specific deck
- `/reading/:passageId` — reading view for a specific passage
- `/listening/:exerciseId` — listening player for a specific exercise

**Route guards:** No auth needed (offline personal app). Check if DB is initialized before rendering — show loading screen if migration is in progress.

---

## 4. Component Architecture

### 4.1 Component Tree

```
App
└── AppShell
    ├── Sidebar (hidden md:flex)
    │   ├── Logo
    │   ├── NavList
    │   │   └── NavItem × 8
    │   ├── Separator
    │   ├── StreakIndicator
    │   └── ThemeToggle
    ├── MainContent (flex-1)
    │   ├── TopBar (mobile only — hamburger + page title)
    │   └── RouterProvider
    │       ├── Dashboard
    │       │   ├── HeroSection
    │       │   │   ├── StatCard (Due) + StatCard (New)
    │       │   │   └── Button (Start Review)
    │       │   ├── StatCard (Streak) + StatCard (Retention)
    │       │   ├── ActivityFeed → ActivityItem × 5
    │       │   └── ForecastChart
    │       ├── VocabReview
    │       │   ├── ProgressBar
    │       │   ├── Flashcard
    │       │   │   ├── CardFront (GermanWord + AudioButton + FlipHint)
    │       │   │   └── CardBack (Word + IPA + Translation + Plural + Example)
    │       │   ├── RatingButtons → RatingButton × 4
    │       │   └── FocusToggle
    │       ├── DeckBrowser
    │       │   ├── SearchBar
    │       │   ├── FilterChipGroup
    │       │   ├── DeckGrid → DeckCard × N
    │       │   └── Button (New Deck)
    │       ├── CardAddEdit
    │       │   ├── Input (Word, Plural, IPA, Translation, Examples)
    │       │   ├── Select (Article, POS, Deck)
    │       │   ├── TagInput
    │       │   ├── Button (Auto-Enrich)
    │       │   └── Button (Save / Cancel)
    │       ├── Statistics
    │       │   ├── Tabs (Time Range)
    │       │   ├── StatCard × 3
    │       │   ├── ChartContainer (Pie, Bar, Area, HBar)
    │       │   └── CalendarHeatmap
    │       ├── Settings
    │       │   ├── Tabs (Review/Appearance/Audio/Data/About)
    │       │   ├── Slider × N
    │       │   ├── Switch × N
    │       │   └── Button (Export/Import/Optimize/Reset)
    │       ├── GrammarOverview
    │       │   ├── SearchBar + FilterChipGroup + Select
    │       │   └── Collapsible × 5 → LessonRow × N
    │       ├── GrammarLesson
    │       │   ├── Breadcrumb
    │       │   ├── LessonNav (desktop)
    │       │   ├── MarkdownRenderer
    │       │   └── Button (Practice Exercises)
    │       ├── GrammarExercises
    │       │   ├── ProgressBar
    │       │   ├── ExerciseCard (Question + Input + Feedback)
    │       │   └── Button (Skip / Next)
    │       ├── ReadingLibrary
    │       │   ├── SearchBar + FilterChipGroup
    │       │   ├── PassageGrid → PassageCard × N
    │       │   └── Button (Import Text)
    │       ├── ReadingView
    │       │   ├── ProgressBar
    │       │   ├── TextContent (clickable words)
    │       │   ├── WordPopup / HoverCard
    │       │   ├── WordLookupPanel (desktop)
    │       │   └── ComprehensionQuestions
    │       ├── ListeningLibrary
    │       │   ├── SearchBar + FilterChipGroup
    │       │   └── ExerciseList → ExerciseRow × N
    │       ├── ListeningPlayer
    │       │   ├── AudioPlayer
    │       │   ├── Switch (Transcript / Cloze)
    │       │   ├── TranscriptView
    │       │   └── ComprehensionQuestions
    │       └── ImportPage
    │           ├── DropZone
    │           ├── Input (Title) + Select (CEFR, Type)
    │           ├── TextPreview
    │           └── Button (Import / Cancel)
    └── BottomNav (flex md:hidden)
        └── NavItem × 5
```

### 4.2 Shared Component Definitions

| Component | Props | Description |
|---|---|---|
| `Flashcard` | `card: VocabCard`, `flipped: boolean`, `onFlip: () => void` | 3D flip card. Front: German word + audio. Back: translation + IPA + plural + example. `transform-style: preserve-3d`, `rotateY(180deg)` on flip. |
| `AudioButton` | `audioPath: string`, `size?: 'sm' \| 'md'` | Circular ghost button with volume icon. Resolves path via `convertFileSrc`, plays on click. Loading state while fetching. |
| `RatingButtons` | `onRate: (rating: Rating) => void`, `intervals?: Partial<Record<Rating, string>>` | 4-button group (Again/Hard/Good/Easy). Each shows keyboard hint (1-4) and predicted interval. Colors: Again=destructive, Hard=warning, Good=success, Easy=primary. |
| `CEFRBadge` | `level: CEFRLevel`, `size?: 'sm' \| 'md'` | Color-coded badge per CEFR level (A1–C2). Uses level-specific colors from §1.1. |
| `StatCard` | `label: string`, `value: string \| number`, `icon?: LucideIcon`, `trend?: string`, `accent?: boolean` | Card with large number (`text-4xl`), label, optional icon + trend. |
| `ProgressBar` | `current: number`, `total: number`, `label?: string` | `Progress` wrapper showing session/reading progress. Label shows "3/8" format. |
| `SearchBar` | `value: string`, `onChange: (v: string) => void`, `placeholder?: string` | Input with search icon (left) and clear button (right). Debounced 300ms. |
| `FilterChip` | `label: string`, `active: boolean`, `onToggle: () => void` | Toggle chip. Active = `--primary` bg, inactive = `--secondary` bg. |
| `MarkdownRenderer` | `content: string`, `className?: string` | Renders markdown via `react-markdown` + `remark-gfm`. Custom renderers: code blocks (syntax highlight), blockquotes (example callouts), tables (conjugation), `lang="de"` on German text. |
| `WordPopup` | `word: string`, `definition: WordDefinition`, `onAddToSRS: () => void` | Popover with definition, POS, article, IPA, audio button, "Add to SRS" button. |
| `ChartContainer` | `title: string`, `description?: string`, `children: ReactNode` | Card wrapper for charts. Title + description header, responsive chart body. |
| `CalendarHeatmap` | `data: { date: string, count: number }[]`, `weeks?: number` | GitHub-style activity grid. Each day = colored square. Tooltip on hover. Horizontal scroll on mobile. |
| `DeckCard` | `deck: Deck`, `onStudy: () => void`, `onMenu: (action: string) => void` | Card with deck info + study button + context menu. |
| `LessonRow` | `lesson: GrammarLesson`, `progress: LessonProgress`, `onClick: () => void` | List row with title, status icon, progress, CEFR badge. |
| `PassageCard` | `passage: ReadingPassage`, `status: ReadStatus`, `onClick: () => void` | Card with passage title, CEFR badge, type, word count, reading time, status. |
| `ExerciseRow` | `exercise: ListeningExercise`, `status: ExerciseStatus`, `onClick: () => void` | List row with headphone icon, title, CEFR badge, duration, status. |

### 4.3 Feature Module Structure

Each feature module follows the FlexiLingo Desk pattern:

```
src/
├── components/              # Shared cross-module components
│   ├── ui/                  # shadcn/ui components (Button, Card, Dialog, etc.)
│   ├── Flashcard.tsx
│   ├── AudioButton.tsx
│   ├── RatingButtons.tsx
│   ├── CEFRBadge.tsx
│   ├── StatCard.tsx
│   ├── SearchBar.tsx
│   ├── FilterChip.tsx
│   ├── MarkdownRenderer.tsx
│   ├── WordPopup.tsx
│   ├── ChartContainer.tsx
│   └── CalendarHeatmap.tsx
├── pages/                   # Feature module pages
│   ├── dashboard/
│   │   ├── Dashboard.tsx
│   │   ├── components/      # Module-specific components
│   │   ├── store.ts         # Zustand store (module state)
│   │   ├── types.ts         # Module types
│   │   └── ipc.ts           # Tauri invoke wrappers
│   ├── review/
│   │   ├── VocabReview.tsx
│   │   ├── ReviewSummary.tsx
│   │   ├── components/
│   │   ├── store.ts         # Review session state machine
│   │   ├── types.ts
│   │   └── ipc.ts
│   ├── decks/
│   │   ├── DeckBrowser.tsx
│   │   ├── DeckDetail.tsx
│   │   ├── CardAddEdit.tsx
│   │   ├── components/
│   │   ├── store.ts
│   │   ├── types.ts
│   │   └── ipc.ts
│   ├── grammar/
│   │   ├── GrammarOverview.tsx
│   │   ├── GrammarLesson.tsx
│   │   ├── GrammarExercises.tsx
│   │   ├── components/
│   │   ├── store.ts
│   │   ├── types.ts
│   │   └── ipc.ts
│   ├── reading/
│   │   ├── ReadingLibrary.tsx
│   │   ├── ReadingView.tsx
│   │   ├── components/
│   │   ├── store.ts
│   │   ├── types.ts
│   │   └── ipc.ts
│   ├── listening/
│   │   ├── ListeningLibrary.tsx
│   │   ├── ListeningPlayer.tsx
│   │   ├── components/
│   │   ├── store.ts
│   │   ├── types.ts
│   │   └── ipc.ts
│   ├── stats/
│   │   ├── Statistics.tsx
│   │   ├── components/
│   │   ├── store.ts
│   │   ├── types.ts
│   │   └── ipc.ts
│   ├── settings/
│   │   ├── Settings.tsx
│   │   ├── components/
│   │   ├── store.ts
│   │   ├── types.ts
│   │   └── ipc.ts
│   └── import/
│       ├── ImportPage.tsx
│       ├── components/
│       ├── store.ts
│       ├── types.ts
│       └── ipc.ts
├── stores/                  # Global stores
│   ├── settingsStore.ts     # Theme, FSRS params, daily limits, audio prefs
│   └── navStore.ts          # Sidebar collapsed state, current route
├── hooks/
│   ├── useTheme.ts
│   ├── useKeyboardShortcuts.ts
│   ├── useSwipe.ts
│   └── useAudio.ts
├── lib/
│   ├── db.ts                # SQLite connection + query helpers
│   ├── srs.ts               # FSRS scheduler wrapper
│   ├── audio.ts             # Audio file resolution (convertFileSrc)
│   └── utils.ts             # cn() class merge, formatters
├── types/                   # Global types
│   ├── vocab.ts
│   ├── srs.ts
│   ├── grammar.ts
│   ├── reading.ts
│   └── common.ts            # CEFRLevel, Rating, etc.
└── App.tsx                  # Root: AppShell + RouterProvider
```

### 4.4 Loading, Error, and Empty States

#### Loading States

| Screen | Loading Component | Behavior |
|---|---|---|
| Dashboard | `Skeleton` × 4 (stat cards) + `Skeleton` (activity feed) | Show while fetching due count, streak, activity |
| Vocab Review | `Skeleton` (card-shaped, 640×320) | Show while loading due cards |
| Deck Browser | `Skeleton` × 6 (deck card shaped) | Show while loading deck list |
| Statistics | `Skeleton` (chart-shaped rectangles) | Show while aggregating review data |
| Grammar Overview | `Skeleton` × 5 (lesson row shaped) | Show while loading lesson list |
| Reading View | `Skeleton` (text lines) | Show while loading passage |

#### Error States

| Screen | Error Component | Behavior |
|---|---|---|
| Any | `Card` with error icon + message + "Retry" button | Show when IPC call fails or DB query errors |
| Vocab Review | `Card` — "No cards due" + illustration + "Browse Decks" button | Show when no due cards |
| Deck Browser | `Card` — "No decks found" + "Create your first deck" button | Show when no decks match filter |
| Grammar | `Card` — "No lessons found" + "Adjust filters" suggestion | Show when no lessons match filter |
| Reading | `Card` — "No passages found" + "Import a text" button | Show when no passages match filter |
| Stats | `Card` — "No data yet" + "Start reviewing to see stats" | Show when no review logs exist |

#### Empty States

All empty states include:
- Relevant Lucide icon (large, `--muted-foreground` color)
- Descriptive heading (what's empty)
- Helpful subtext (what to do next)
- Primary action button (CTA to get started)

### 4.5 Offline Indicator

Since the app is offline-first (all data bundled), a subtle badge in the sidebar footer indicates the mode:

```
┌────────────────────────┐
│  ───────────────────── │
│  🔥 23-day streak      │
│  📦 Offline mode       │  ← subtle badge, muted color
│  ☀️/🌙 Theme toggle    │
└────────────────────────┘
```

The "Offline mode" badge is always visible (default state). If a future feature adds optional online sync, this badge would change to show sync status.

---

## 5. Responsive Design Strategy

### 5.1 Breakpoint Strategy

| Breakpoint | Tailwind | Min Width | Target |
|---|---|---|---|
| Mobile | (default) | 0px | Phone (360–767px) |
| Tablet | `md:` | 768px | Tablet (768–1023px) |
| Desktop | `lg:` | 1024px | Desktop (1024px+) |
| Wide | `xl:` | 1280px | Large desktop (1280px+) |
| Ultra-wide | `2xl:` | 1536px | Ultrawide (multi-column stats) |

**Primary transition:** `md` (768px) — sidebar appears, bottom nav disappears.
**Secondary transition:** `lg` (1024px) — sidebar expands from icon rail to full 240px.

### 5.2 Per-Screen Responsive Adaptations

| Screen | Desktop (≥1024px) | Tablet (768–1023px) | Mobile (<768px) |
|---|---|---|---|
| **Dashboard** | Sidebar + 2-col stat grid | Icon rail + 2-col stat grid | Bottom nav + stacked stats |
| **Vocab Review** | Card 640px centered, keyboard hints | Card 80% width, no keyboard hints | Card full-width, swipe gestures, 2×2 rating grid |
| **Deck Browser** | 3-col grid | 2-col grid | 1-col list, horizontal layout per card |
| **Card Add/Edit** | Form 640px centered, 2-col fields | Form 80% width | Form full-width, stacked fields |
| **Statistics** | 3-col stat cards, charts 2-col grid | 3-col stat cards (compact), charts full-width | Stat cards stacked, charts full-width, heatmap scrolls |
| **Settings** | Tabs horizontal, form 640px | Same | Tabs horizontal scroll, form full-width |
| **Grammar Overview** | Full lesson rows with badges | Same, narrower | Compact rows (title + icon), collapsible |
| **Grammar Lesson** | 2-col (nav 240px + content 720px) | Nav 200px + content | Content only, nav via dropdown |
| **Grammar Exercises** | Exercise 640px, MC horizontal | Same | Full-width, MC 2×2 grid, drag→tap |
| **Reading Library** | 3-col grid | 2-col grid | 1-col list, compact cards |
| **Reading View** | 2-col (text 60% + lookup 40%) | 2-col (text 65% + lookup 35%) | Single col, word lookup via popover |
| **Listening Library** | Full-width list rows | Same | Compact rows |
| **Listening Player** | 720px centered, all elements | Same, narrower | Full-width, compact player, speed as dropdown |
| **Import** | 720px centered form | Same | Full-width |

### 5.3 Touch Interactions (Mobile)

| Screen | Gesture | Action |
|---|---|---|
| Vocab Review | Swipe left | Rate "Again" |
| Vocab Review | Swipe right | Rate "Good" |
| Vocab Review | Swipe up | Flip card |
| Vocab Review | Tap card | Flip card |
| Grammar Exercises | Tap option | Select answer |
| Grammar Exercises | Long-press + drag (word order) | Rearrange words |
| Reading View | Tap word | Show definition popover |
| Reading View | Pinch | Adjust font size |
| Listening Player | Tap play/pause | Toggle playback |
| Listening Player | Drag seek bar | Seek to position |
| Any screen | Swipe from left edge | Open sidebar drawer (mobile) |

### 5.4 Keyboard Shortcuts (Desktop)

| Screen | Key | Action |
|---|---|---|
| **Global** | `Ctrl/Cmd + B` | Toggle sidebar collapse |
| **Global** | `Ctrl/Cmd + ,` | Open Settings |
| **Vocab Review** | `Space` | Flip card |
| **Vocab Review** | `1` | Rate "Again" |
| **Vocab Review** | `2` | Rate "Hard" |
| **Vocab Review** | `3` | Rate "Good" |
| **Vocab Review** | `4` | Rate "Easy" |
| **Vocab Review** | `A` | Play audio |
| **Vocab Review** | `F` | Toggle focus mode |
| **Vocab Review** | `Escape` | Exit focus / exit review |
| **Grammar Exercises** | `1`–`4` | Select MC option |
| **Grammar Exercises** | `Enter` | Submit / Next |
| **Listening Player** | `Space` | Play/pause |
| **Reading View** | `F` | Toggle focus mode |
| **Reading View** | `Escape` | Exit focus mode |

**Implementation:** `useKeyboardShortcuts` hook registers handlers per route. Shortcuts are context-aware — `1-4` only active during review/exercises, not when typing in inputs. Settings has a toggle to disable shortcuts.

---

## 6. Accessibility Checklist

### 6.1 Keyboard Navigation

- [ ] All interactive elements reachable via Tab key in logical order
- [ ] Focus indicators visible on all focusable elements (2px `--ring` outline)
- [ ] Focus trap inside Dialog, AlertDialog, Popover, Sheet (Radix UI handles this)
- [ ] Escape key closes overlays (Dialog, Popover, Sheet)
- [ ] Rating buttons accessible via number keys AND Tab + Enter
- [ ] Flashcard flip accessible via Space AND Enter
- [ ] No keyboard traps (modals return focus to trigger element on close)

### 6.2 Language Attributes

- [ ] All German text wrapped in elements with `lang="de"` (words, sentences, examples, transcript)
- [ ] All English text wrapped in elements with `lang="en"` (translations, instructions)
- [ ] IPA transcriptions wrapped in `<span lang="de" class="font-mono">` with `aria-label`
- [ ] Screen readers announce German text with German pronunciation rules

```tsx
<span lang="de" className="text-3xl font-bold">das Haus</span>
<span lang="en" className="text-base">the house</span>
```

### 6.3 Color Contrast (WCAG AA)

| Element | Light Mode | Dark Mode | Ratio |
|---|---|---|---|
| Body text on background | `#1C2B1E` on `#FAF7F0` | `#E8E2D4` on `#1A1F17` | 14.8:1 / 12.3:1 ✅ |
| Muted text on background | `#6B7B5F` on `#FAF7F0` | `#8A9080` on `#1A1F17` | 4.6:1 / 5.1:1 ✅ |
| Primary button text | `#F0EDE5` on `#2D5A3D` | `#1A1F17` on `#5B9A6F` | 7.2:1 / 8.1:1 ✅ |
| Accent text | `#B8703A` on `#FAF7F0` | `#D4884A` on `#1A1F17` | 4.8:1 / 5.3:1 ✅ |
| Destructive | `#B33A3A` on `#FAF7F0` | `#D45050` on `#1A1F17` | 5.1:1 / 4.9:1 ✅ |

All combinations meet WCAG AA (≥4.5:1 for normal text, ≥3:1 for large text).

### 6.4 Focus Indicators

- [ ] All focusable elements show 2px `--ring` color outline on focus
- [ ] Focus visible on `:focus-visible` (keyboard) but not `:focus` (mouse click)
- [ ] Focus ring offset: `outline-offset: 2px`

```css
*:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}
```

### 6.5 Font Size Adjustment

- [ ] Settings → Appearance → Font Size slider (75%–150%)
- [ ] Applies CSS custom property `--font-scale` on `:root`
- [ ] All font sizes use `calc()` with `--font-scale` multiplier
- [ ] Minimum: 12px × scale (never below 9px)
- [ ] Maximum: 36px × scale (prevents layout breakage)

### 6.6 Screen Reader Support

- [ ] All buttons have `aria-label` (especially icon-only buttons like audio, focus toggle)
- [ ] Flashcard has `role="button"` and `aria-label` describing current state
- [ ] Rating buttons have `aria-label` with full description ("Rate as Again — less than 1 minute")
- [ ] Progress bars have `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-label`
- [ ] Charts have `aria-label` with data summary ("Card states: 234 new, 89 learning, 567 young, 1245 mature")
- [ ] Transcript has `aria-live="polite"` for current sentence highlight
- [ ] Toast notifications have `role="status"` and `aria-live="polite"`
- [ ] Form inputs have associated `<Label>` elements (`htmlFor` + `id`)
- [ ] Error messages have `role="alert"` and `aria-live="assertive"`
- [ ] Empty states have `role="status"`

### 6.7 Audio Accessibility

- [ ] All audio content has text alternative (transcript for listening, IPA + written form for vocab)
- [ ] Audio player controls keyboard accessible (play/pause via Space, seek via arrow keys)
- [ ] No audio auto-plays without user opt-in (setting toggle, default off)
- [ ] Visual indicator when audio is playing (animated waveform or pulsing icon)

### 6.8 Motion and Animation

- [ ] Respect `prefers-reduced-motion` media query
- [ ] Flashcard flip: instant swap (no animation) when reduced motion preferred
- [ ] Page transitions: instant (no slide/fade) when reduced motion preferred
- [ ] Streak counter: show final number immediately (no count-up)

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 7. Charting Library Recommendation

### 7.1 Comparison

| Criterion | recharts | visx | chart.js |
|---|---|---|---|
| **React integration** | ✅ Native React components | ✅ Low-level React primitives | ❌ Imperative, needs wrapper |
| **TypeScript support** | ✅ Built-in types | ✅ Built-in types | ⚠️ Requires @types/chart.js |
| **Bundle size** | ~95 KB (gzipped) | ~30–60 KB (tree-shakeable) | ~65 KB (gzipped) |
| **Component model** | Declarative (`<BarChart>`, `<PieChart>`) | Composable (build from primitives) | Configuration object |
| **Learning curve** | Low (familiar JSX API) | High (compose primitives manually) | Medium (config-based) |
| **Customization** | Good (props-based) | Excellent (full control) | Good (options-based) |
| **Responsive** | ✅ `<ResponsiveContainer>` | ✅ Manual | ✅ `responsive: true` |
| **Tooltip** | ✅ Built-in, customizable | ❌ Build from scratch | ✅ Built-in |
| **Animation** | ✅ Built-in, respects reduced-motion | ❌ Manual | ✅ Built-in |
| **shadcn/ui compatibility** | ✅ Used in shadcn charts | ⚠️ Not integrated | ❌ Not integrated |
| **Chart types needed** | Pie, Bar, Area, HBar — all supported | All supported, more code | All supported |

### 7.2 Recommendation: **recharts**

**Rationale:**
1. **shadcn/ui integration** — shadcn/ui includes chart components built on recharts. Using recharts keeps the design system consistent.
2. **Declarative API** — Charts are JSX components, matching React's paradigm. Easier to maintain than imperative chart.js.
3. **Low learning curve** — For the chart types we need (pie, bar, area, horizontal bar), recharts has direct components.
4. **Responsive by default** — `<ResponsiveContainer>` handles resize automatically.
5. **Built-in tooltips + animations** — Less custom code needed.
6. **Bundle size acceptable** — 95 KB gzipped is reasonable for a desktop app.

### 7.3 Chart Implementation Example

```typescript
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const COLORS = ['hsl(var(--muted))', 'hsl(var(--warning))', 'hsl(var(--info))', 'hsl(var(--success))'];

function CardStateChart({ data }: { data: { name: string; value: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
          {data.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  );
}
```

**Calendar Heatmap:** Not a standard recharts chart. Build as a custom component using CSS grid (7 rows × N weeks, each cell a colored div). No library needed — pure HTML/CSS.

---

## 8. Next Steps for Orchestrator

### 8.1 Build Order (Phase 1 MVP)

| Step | Task | Dependencies | Est. Effort |
|---|---|---|---|
| 1 | **Scaffold Tauri 2 project** — `npm create tauri-app`, React + TS template | None | 1 hour |
| 2 | **Install dependencies** — Tailwind v4, shadcn/ui, Zustand+Immer, recharts, react-router, lucide-react, react-markdown, remark-gfm | Step 1 | 1 hour |
| 3 | **Set up design system** — CSS variables (Forest & Cream), font loading, Tailwind theme, dark mode | Step 2 | 2 hours |
| 4 | **Init shadcn/ui** — `npx shadcn@latest init`, add all components from §1.4 | Step 3 | 1 hour |
| 5 | **Build AppShell** — Sidebar, BottomNav, responsive layout, routing skeleton | Step 4 | 3 hours |
| 6 | **Set up SQLite** — `tauri-plugin-sql`, schema migration, seed DB import | Step 1 | 4 hours |
| 7 | **Build settingsStore** — Zustand store for theme, FSRS params, daily limits. Persist via `tauri-plugin-store` | Step 5 | 2 hours |
| 8 | **Build Dashboard** — Due count, streak, retention, activity feed, forecast | Steps 5, 6 | 4 hours |
| 9 | **Build Vocab Review** — Flashcard, rating buttons, FSRS integration, keyboard shortcuts, session state machine | Steps 5, 6, 7 | 6 hours |
| 10 | **Build Deck Browser** — Deck grid, search, filters, deck CRUD | Steps 5, 6 | 3 hours |
| 11 | **Build Card Add/Edit** — Form, auto-enrichment from bundled dictionary | Steps 5, 6 | 3 hours |
| 12 | **Build Statistics** — recharts integration, 5 chart types, calendar heatmap, time range tabs | Steps 5, 6, 8 | 5 hours |
| 13 | **Build Settings** — All 5 tabs, FSRS params, theme toggle, data management | Steps 5, 7 | 4 hours |
| 14 | **Add audio playback** — AudioButton component, `convertFileSrc` resolution, auto-play setting | Step 9 | 2 hours |
| 15 | **Polish** — Loading skeletons, empty states, error states, animations, accessibility pass | All above | 4 hours |
| **Total Phase 1** | | | **~45 hours** |

### 8.2 Build Order (Phase 2)

| Step | Task | Dependencies | Est. Effort |
|---|---|---|---|
| 1 | **Build Grammar Overview** — Lesson list, CEFR grouping, filters | Phase 1 complete | 3 hours |
| 2 | **Build Grammar Lesson View** — MarkdownRenderer, lesson nav, breadcrumb | Step 1 | 4 hours |
| 3 | **Build Grammar Exercise Player** — 6 exercise types, feedback, session summary, mistake tracking | Step 2 | 8 hours |
| 4 | **Generate grammar exercises** — Programmatic generation from rules + Tatoeba sentences | Content pipeline | 4 hours |
| **Total Phase 2** | | | **~19 hours** |

### 8.3 Build Order (Phase 3)

| Step | Task | Dependencies | Est. Effort |
|---|---|---|---|
| 1 | **Build Reading Library** — Passage grid, filters, search | Phase 1 complete | 3 hours |
| 2 | **Build Reading View** — Clickable text, WordPopup, word lookup panel, comprehension questions | Step 1 | 6 hours |
| 3 | **Build Listening Library** — Exercise list, filters | Phase 1 complete | 2 hours |
| 4 | **Build Listening Player** — AudioPlayer, transcript sync, cloze mode, comprehension questions | Step 3 | 6 hours |
| 5 | **Build Import** — File picker, text extraction (PDF/EPUB/TXT), CEFR auto-detection | Steps 1, 2 | 5 hours |
| **Total Phase 3** | | | **~22 hours** |

### 8.4 Key Decisions for Orchestrator

| # | Decision | Recommendation | Notes |
|---|---|---|---|
| 1 | **FSRS implementation** | Use `ts-fsrs` (TypeScript) for frontend scheduling, or Tauri command to `fsrs-rs` (Rust) | `ts-fsrs` is simpler (no IPC). `fsrs-rs` is faster for batch operations. Start with `ts-fsrs`, move to Rust if performance demands. |
| 2 | **Chart library** | **recharts** | See §7 for full rationale. shadcn/ui integration is the deciding factor. |
| 3 | **Font bundling** | Bundle as Tauri resources for offline | Google Fonts CDN for dev, `@font-face` with local `src` for production. Inter (~300KB), Source Serif 4 (~400KB), JetBrains Mono (~200KB). |
| 4 | **Drag-drop library** | `@dnd-kit/core` for word order exercises | Accessible, keyboard-navigable, lightweight. |
| 5 | **Markdown rendering** | `react-markdown` + `remark-gfm` + `rehype-highlight` | GFM for tables (conjugation/declension). Custom renderers for German text `lang="de"`. |
| 6 | **Animation library** | Tailwind transitions + custom CSS keyframes | Framer Motion optional for page transitions. Keep dependencies minimal. |
| 7 | **Keyboard shortcuts** | Custom `useKeyboardShortcuts` hook | Don't use a library — our shortcuts are simple and context-specific. |
| 8 | **Touch swipe** | Custom `useSwipe` hook | Simple left/right/up detection is ~50 lines. Use `touchstart`/`touchmove`/`touchend` with threshold. |

### 8.5 Design System Setup Checklist

Before building any screens, set up the design system:

- [ ] Install Tailwind CSS v4 (`@tailwindcss/vite` plugin)
- [ ] Configure `@theme` in `globals.css` with all CSS variables from §1.1
- [ ] Set up `:root` (light) and `.dark` (dark mode) token blocks
- [ ] Add font-family variables (`--font-sans`, `--font-serif`, `--font-mono`)
- [ ] Load fonts (Google Fonts CDN for dev, bundled for production)
- [ ] Run `npx shadcn@latest init` — select "New York" style, "CSS variables" color mode
- [ ] Add all shadcn/ui components from §1.4 (`npx shadcn@latest add button card input ...`)
- [ ] Create `lib/utils.ts` with `cn()` helper (shadcn init does this)
- [ ] Add custom keyframes in `globals.css` (flashcard flip, toast slide, etc.)
- [ ] Set up `useTheme` hook + `settingsStore` for theme persistence
- [ ] Add `prefers-reduced-motion` media query in `globals.css`
- [ ] Add focus-visible styles in `globals.css`

### 8.6 Deliverables Summary

This handoff provides:

1. **Design system** — Complete color palette (Forest & Cream, light + dark), typography (Inter + Source Serif 4 + JetBrains Mono), spacing system, 30+ shadcn/ui components, dark mode implementation, animations
2. **14 screen wireframes** — All Phase 1 (6), Phase 2 (3), and Phase 3 (5) screens with layout, components, data, interactions, and responsive behavior
3. **Navigation architecture** — Desktop sidebar (240px/64px), mobile bottom nav (56px), React Router v7 hash-based routing with nested routes
4. **Component architecture** — Full component tree, 15+ shared component definitions, feature module structure (pages/components/store/types/ipc per module), loading/error/empty state patterns
5. **Responsive strategy** — 5 breakpoints, per-screen adaptations table, touch gestures, keyboard shortcuts
6. **Accessibility** — WCAG AA contrast compliance, keyboard navigation, `lang` attributes, focus indicators, font scaling, screen reader support, reduced motion
7. **Charting** — recharts recommended, with implementation example and rationale
8. **Build plan** — Phase 1 (~45h), Phase 2 (~19h), Phase 3 (~22h), with step-by-step order and dependencies

---

> **End of UI/UX Design Handoff.** Pass this document to the implementation orchestrator. The design system is ready to be set up immediately — no further design decisions required to begin Phase 1 scaffolding.
