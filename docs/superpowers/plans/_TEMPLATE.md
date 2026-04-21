# OpenDAW Implementation Plan Template

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---

## File Structure

| File | Purpose | Action |
|------|---------|--------|
| `src/feature.rs` | Main implementation | Create |
| `src/feature/module.rs` | Sub-module | Create |
| `tests/feature_tests.rs` | Integration tests | Create |

---

## Tasks

### Task 1: [Component/Feature]

**Files:**
- Create: `src/feature.rs`
- Test: `src/feature.rs` (inline tests)

- [ ] **Step 1: Write the failing test**

```rust
#[test]
fn test_feature_behavior() {
    let result = feature_function(input);
    assert_eq!(result, expected);
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cargo test test_feature_behavior -- --nocapture`

Expected: FAIL with "function not found"

- [ ] **Step 3: Write minimal implementation**

```rust
pub fn feature_function(input: Input) -> Output {
    // Minimal code to pass
    expected_output
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cargo test test_feature_behavior -- --nocapture`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/feature.rs
git commit -m "feat: add feature_function with TDD"
```

---

### Task 2: [Next Component]

[Repeat same structure]

---

## Verification Checklist

Before marking complete:

- [ ] All tests pass (`cargo test --lib`)
- [ ] Zero compiler warnings (`cargo build --lib`)
- [ ] `cargo clippy` clean
- [ ] Each feature has tests
- [ ] Each test was watched failing then passing
- [ ] Commits are clean and focused

---

## Post-Implementation

1. Update HANDOFF.md with new test count
2. Update FRAMEWORK_COMPLIANCE.md if needed
3. Run full test suite to verify baseline

---

*Template version: April 1, 2026*  
*Framework: dev_framework (Superpowers) - writing-plans skill*
