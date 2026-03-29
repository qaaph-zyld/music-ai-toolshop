# Music Projects Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate all music-related projects into `music-ai-toolshop` with clean `dev_framework` structure

**Architecture:** Move ACE-Step, reorganize Suno library with numbered prefix, create placeholder structure for future projects, establish docs/superpowers structure for specifications and plans.

**Tech Stack:** PowerShell file operations, directory management

---

## File Structure (Final State)

```
music-ai-toolshop/
├── docs/
│   └── superpowers/
│       ├── specs/                 # Design documents
│       └── plans/                 # Implementation plans
├── projects/
│   ├── 01-suno-library/          # Renamed from Suno (2,633 songs preserved)
│   ├── 02-ace-step/             # Moved from ACE_AI_Music/ACE-Step/
│   ├── 03-lyrics-writer/        # Placeholder (was Lyrics_writter)
│   ├── 04-stem-extractor/       # Placeholder (was stem-extractor)
│   └── 05-track-reverse-engineering/  # Placeholder (was Track_reverse_engineering)
├── src/                          # Shared utilities (created if needed)
└── tests/                        # Test suite (created if needed)
```

---

### Task 1: Create docs/superpowers Directory Structure

**Files:**
- Create: `docs/superpowers/specs/` directory
- Create: `docs/superpowers/plans/` directory

- [ ] **Step 1: Create specs directory**

Run: `mkdir -Force docs/superpowers/specs`
Expected: Directory created successfully

- [ ] **Step 2: Create plans directory**

Run: `mkdir -Force docs/superpowers/plans`
Expected: Directory created successfully

- [ ] **Step 3: Commit**

```bash
git add docs/
git commit -m "chore: create docs/superpowers structure for specifications and plans"
```

---

### Task 2: Rename Suno to 01-suno-library

**Files:**
- Move/Rename: `projects/Suno/` → `projects/01-suno-library/`

- [ ] **Step 1: Verify Suno directory exists and contains data**

Run: `Test-Path projects/Suno/suno_library.db`
Expected: TRUE (2,633 songs database exists)

- [ ] **Step 2: Rename directory**

Run: `Rename-Item -Path "projects/Suno" -NewName "projects/01-suno-library"`
Expected: Directory renamed, all 58 items preserved

- [ ] **Step 3: Verify rename succeeded**

Run: `Test-Path projects/01-suno-library/suno_library.db`
Expected: TRUE

- [ ] **Step 4: Commit**

```bash
git add projects/
git commit -m "refactor: rename Suno to 01-suno-library for ordered project structure"
```

---

### Task 3: Move ACE-Step from ACE_AI_Music

**Files:**
- Move: `ACE_AI_Music/ACE-Step/` → `projects/02-ace-step/`

- [ ] **Step 1: Verify ACE-Step source exists**

Run: `Test-Path ../../ACE_AI_Music/ACE-Step`
Expected: TRUE

- [ ] **Step 2: Create 02-ace-step directory**

Run: `mkdir -Force projects/02-ace-step`
Expected: Directory created

- [ ] **Step 3: Move ACE-Step contents**

Run: `Move-Item -Path "../../ACE_AI_Music/ACE-Step/*" -Destination "projects/02-ace-step/" -Force`
Expected: All contents moved (0 items in source after move)

- [ ] **Step 4: Verify move**

Run: `Test-Path projects/02-ace-step/acestep`
Expected: TRUE (main package directory exists)

- [ ] **Step 5: Commit**

```bash
git add projects/02-ace-step/
git commit -m "refactor: move ACE-Step to projects/02-ace-step"
```

---

### Task 4: Create Placeholder Projects

**Files:**
- Create: `projects/03-lyrics-writer/README.md`
- Create: `projects/04-stem-extractor/README.md`
- Create: `projects/05-track-reverse-engineering/README.md`

- [ ] **Step 1: Create 03-lyrics-writer directory and README**

Run: 
```powershell
mkdir -Force projects/03-lyrics-writer
"# Lyrics Writer Project`n`nStatus: Placeholder - Future Development`n`n## Purpose`nAI-powered lyrics generation and analysis tools.`n`n## Related`n- See 01-suno-library for 893 extracted lyrics examples" | Out-File -FilePath "projects/03-lyrics-writer/README.md" -Encoding UTF8
```
Expected: File created with 92 bytes

- [ ] **Step 2: Create 04-stem-extractor directory and README**

Run:
```powershell
mkdir -Force projects/04-stem-extractor
"# Stem Extractor Project`n`nStatus: Placeholder - Future Development`n`n## Purpose`nAudio source separation and stem extraction utilities." | Out-File -FilePath "projects/04-stem-extractor/README.md" -Encoding UTF8
```
Expected: File created

- [ ] **Step 3: Create 05-track-reverse-engineering directory and README**

Run:
```powershell
mkdir -Force projects/05-track-reverse-engineering
"# Track Reverse Engineering Project`n`nStatus: Placeholder - Future Development`n`n## Purpose`nAnalyze and reverse engineer music production techniques.`n`n## Related`n- See 01-suno-library/style_report.md for 896 style examples" | Out-File -FilePath "projects/05-track-reverse-engineering/README.md" -Encoding UTF8
```
Expected: File created

- [ ] **Step 4: Verify all placeholders**

Run: `Get-ChildItem projects/ | Where-Object { $_.Name -match '^0[3-5]-' }`
Expected: 3 directories listed

- [ ] **Step 5: Commit**

```bash
git add projects/03-lyrics-writer/ projects/04-stem-extractor/ projects/05-track-reverse-engineering/
git commit -m "chore: create placeholder projects 03-05 for future development"
```

---

### Task 5: Update Root Documentation

**Files:**
- Create: `PROJECTS_INDEX.md`
- Modify: `README.md` (if exists)

- [ ] **Step 1: Create PROJECTS_INDEX.md**

Run:
```powershell
$content = @"
# Music AI Toolshop - Projects Index

## Active Projects

| # | Project | Status | Description |
|---|---------|--------|-------------|
| 01 | suno-library | ✅ Active | 2,633 Suno songs with lyrics, styles, metadata |
| 02 | ace-step | ✅ Active | AI music generation with ACE-Step |
| 03 | lyrics-writer | ⏳ Planned | AI lyrics generation tools |
| 04 | stem-extractor | ⏳ Planned | Audio source separation |
| 05 | track-reverse-engineering | ⏳ Planned | Production technique analysis |

## Directory Structure

Each project follows dev_framework principles:
- `docs/` - Project documentation
- `src/` - Source code
- `tests/` - Test suite (TDD enforced)
- `README.md` - Project overview

## Quick Navigation

- [01-suno-library](./projects/01-suno-library/) - Extracted Suno collection
- [02-ace-step](./projects/02-ace-step/) - Music generation
- [docs/superpowers/specs](./docs/superpowers/specs/) - Design documents
- [docs/superpowers/plans](./docs/superpowers/plans/) - Implementation plans
"@
$content | Out-File -FilePath "PROJECTS_INDEX.md" -Encoding UTF8
```
Expected: File created

- [ ] **Step 2: Commit**

```bash
git add PROJECTS_INDEX.md
git commit -m "docs: add PROJECTS_INDEX.md with project overview and navigation"
```

---

### Task 6: Final Verification

- [ ] **Step 1: Verify all directories exist**

Run:
```powershell
$expected = @(
    "docs/superpowers/specs",
    "docs/superpowers/plans",
    "projects/01-suno-library",
    "projects/02-ace-step",
    "projects/03-lyrics-writer",
    "projects/04-stem-extractor",
    "projects/05-track-reverse-engineering"
)
$expected | ForEach-Object { Test-Path $_ }
```
Expected: All TRUE

- [ ] **Step 2: Verify Suno data preserved**

Run:
```powershell
$lyrics = Get-ChildItem projects/01-suno-library/suno_library/lyrics -File | Measure-Object
$styles = Get-ChildItem projects/01-suno-library/suno_library/styles -File | Measure-Object
Write-Host "Lyrics: $($lyrics.Count), Styles: $($styles.Count)"
```
Expected: Lyrics: ~893, Styles: ~896

- [ ] **Step 3: Verify ACE-Step moved**

Run: `Test-Path projects/02-ace-step/acestep`
Expected: TRUE

- [ ] **Step 4: Check git status**

Run: `git status`
Expected: working tree clean

- [ ] **Step 5: Final commit if needed**

If any uncommitted changes:
```bash
git add .
git commit -m "refactor: consolidate all music projects into dev_framework structure"
```

---

## Verification Checklist

Before marking complete:
- [ ] All 5 project directories exist with proper numbering
- [ ] docs/superpowers structure created
- [ ] Suno library renamed and intact (2,633 songs)
- [ ] ACE-Step moved and functional
- [ ] Placeholder projects have READMEs
- [ ] PROJECTS_INDEX.md created
- [ ] All changes committed
- [ ] Working tree clean
