# OpenDAW Superpowers Documentation

**Location:** `docs/superpowers/`  
**Purpose:** Living documentation for dev_framework principles and reusable patterns  
**Updated:** April 4, 2026

---

## Quick Navigation

| Document | Purpose | Status |
|----------|---------|--------|
| [patterns/COMPONENT_INTEGRATION.md](patterns/COMPONENT_INTEGRATION.md) | 7-step pattern for integrating 71-catalog components | Proven (32 uses) |
| [../daw-engine/docs/DEV_FRAMEWORK_APPLICATION.md](../daw-engine/docs/DEV_FRAMEWORK_APPLICATION.md) | Evidence of TDD and systematic development | Active |
| specs/ | Design specifications for complex features | As needed |

---

## Documentation Philosophy

This directory follows the **Living Documentation** approach:

1. **Evidence-Based** - Every claim has concrete examples from the codebase
2. **Pattern-Driven** - Reusable templates extracted from successful implementations
3. **Versioned Updates** - Append updates with date stamps, don't overwrite history
4. **Cross-Referenced** - Link to actual files, not abstract descriptions

---

## Available Patterns

### COMPONENT_INTEGRATION.md
**Use when:** Adding any component from the 71-catalog  
**Coverage:** Phases A-J (32/71 components integrated as of April 2026)

**Key Sections:**
- RED-GREEN-REFACTOR TDD cycle
- File structure template
- Copy-paste test templates
- Build.rs integration
- Common issues and solutions

**Example Usage:**
```bash
# Integrating Dexed (Phase F)
cd d:\Project\music-ai-toolshop\projects\06-opendaw
# Follow patterns/COMPONENT_INTEGRATION.md Step 1-7
```

---

## Design Specifications

Complex features require pre-implementation design specs in `specs/`:

| Spec | Feature | Date | Status |
|------|---------|------|--------|
| `2026-04-01-clap-plugin-hosting-design.md` | CLAP SDK Integration | 2026-04-01 | Implemented |

**Template for new specs:**
```markdown
# [Feature] Design Spec

## Problem Statement
## Proposed Solutions
## Architecture Decision
## Implementation Plan
## Risks & Mitigation
```

---

## Dev Framework Integration

**EverMemOS Memory:** Store patterns and decisions automatically
```bash
# After using a pattern successfully
python daw-engine/scripts/memory_cli.py decision \
  --decision "Used COMPONENT_INTEGRATION.md for Surge XT" \
  --reasoning "Proven pattern, 30 min implementation, 12 tests passing" \
  --files "src/surge.rs,third_party/surge/surge_ffi.c"
```

**Documentation Updates:** Append to existing files with date stamps
```markdown
## Update - April 4, 2026
Added EverMemOS integration pattern to Component Integration doc.
```

---

## Maintenance Schedule

| Task | Frequency | Owner |
|------|-----------|-------|
| Pattern review | After every 10 integrations | Development team |
| Spec archival | After feature completion | Tech lead |
| Link verification | Monthly | CI/CD |
| Cross-reference update | Quarterly | Documentation owner |

---

## Related Documentation

- **HANDOFF.md** - Per-session development status and next steps
- **CHANGELOG.md** - All changes with dev_framework context
- **DEV_FRAMEWORK_APPLICATION.md** - Evidence of framework principles in practice

---

*This README is a living document - append updates rather than overwriting.*
