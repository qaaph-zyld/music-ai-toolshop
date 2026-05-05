# Session Start: Vocal Cleanup & Gap Removal

@ai_dev_meta_layer/framework_loader.md

**Task**: Implement automated vocal cleanup module that detects and removes breath sounds, silences between phrases, and background noise, then tightens timing by "closing the gaps" between vocal segments.

**Session Type**: New Feature

**Context**: 
- OpenDAW has RNNoise for noise suppression and Demucs for stem separation
- Missing: Automated silence/breath detection and gap removal ("close the bridge")
- User wants all three: breath removal, noise cleanup, and gap tightening

---

## Toolkit Selection

| Toolkit | Selected | Rationale |
|---------|----------|-----------|
| Superpowers | [x] Yes | TDD workflow required, systematic development |
| UI UX Pro Max | [x] Yes | New dialog needed for Vocal Cleanup settings |
| Frontend Design | [x] Yes | C++ UI integration into MainComponent |
| Claude-Mem | [x] Yes | OpenDAW is long-term project |
| Awesome Claude Code | [ ] No | Not researching new tech |

**Meta Layer Skills Emphasized**:
- [x] systematic-debugging
- [x] test-driven-development
- [x] writing-plans
- [x] verification-before-completion
- [ ] brainstorming (already done)

---

## Documentation Plan

**Utilization Log**: `ai_dev_meta_layer/utilization_logs/session_2026-05-04_150800.md`

**Planned Checkpoints**:
- [x] Post-bootstrap (immediate) - THIS FILE
- [ ] Post-plan (after planning) - Re-evaluated plan below
- [ ] Mid-implementation (every 20 min / 2 phases)
- [ ] Pre-completion (before claiming done)
- [ ] Post-completion (final verification)

---

## Re-Evaluated Plan (Per Dev Framework)

### Architecture Decision
Following TDD and systematic approach:

**Phase 1: Python AI Module (TDD)**
1. Write failing tests for silence detection
2. Implement silence_detector.py
3. Verify tests pass
4. Write failing tests for breath detection
5. Implement breath_detector.py
6. Write failing tests for gap removal
7. Implement gap_remover.py
8. Integration test full pipeline

**Phase 2: Rust FFI Bridge (TDD)**
1. Write failing FFI tests
2. Implement vocal_cleanup.rs + vocal_cleanup_ffi.rs
3. Verify FFI integration

**Phase 3: C++ UI (TDD)**
1. Write test plan for dialog
2. Implement VocalCleanupDialog
3. Integrate into MainComponent
4. E2E test

### Bite-Sized Tasks (2-5 min each)

#### Phase 1A: Silence Detector (Python)
- [ ] Create ai_modules/vocal_cleanup/ directory
- [ ] Create requirements.txt
- [ ] Write test_silence_detector.py (failing tests)
- [ ] Implement silence_detector.py minimal code
- [ ] Verify tests pass

#### Phase 1B: Breath Detector (Python)
- [ ] Write test_breath_detector.py
- [ ] Implement breath_detector.py
- [ ] Verify tests pass

#### Phase 1C: Gap Remover (Python)
- [ ] Write test_gap_remover.py
- [ ] Implement gap_remover.py
- [ ] Verify tests pass

#### Phase 1D: Pipeline Integration
- [ ] Write test_pipeline.py
- [ ] Implement pipeline.py
- [ ] Full integration test

#### Phase 2: Rust FFI
- [ ] Write vocal_cleanup.rs with tests
- [ ] Write vocal_cleanup_ffi.rs
- [ ] Update lib.rs exports
- [ ] Verify build + tests

#### Phase 3: C++ UI
- [ ] Create VocalCleanupDialog.h/.cpp
- [ ] Add Tools menu to MainComponent
- [ ] Wire FFI calls
- [ ] Build + test

---

## Execution Order

1. **START**: Phase 1A - Silence Detector (Python TDD)
2. **CONTINUE**: Phase 1B - Breath Detector
3. **CONTINUE**: Phase 1C - Gap Remover
4. **CONTINUE**: Phase 1D - Pipeline
5. **CONTINUE**: Phase 2 - Rust FFI
6. **CONTINUE**: Phase 3 - C++ UI
7. **COMPLETE**: Final verification + handoff

---

Proceed with systematic approach per Core Memories.
