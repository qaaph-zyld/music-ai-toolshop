# OpenDAW TDD Workflow Reference

**Framework:** dev_framework (Superpowers)  
**Skill:** test-driven-development  
**Status:** Active compliance

---

## RED-GREEN-REFACTOR Cycle

### 1. RED - Write the Failing Test

```rust
#[test]
fn test_new_feature_behavior() {
    // Arrange
    let input = create_test_input();
    
    // Act
    let result = new_feature(&input);
    
    // Assert
    assert_eq!(result.expected_property, expected_value);
}
```

**Requirements:**
- Test must fail initially (function doesn't exist)
- Clear test name describing behavior
- One concept per test
- Use real code, avoid mocks when possible

### 2. Verify RED - Watch It Fail

```bash
cargo test test_new_feature_behavior -- --nocapture
```

**Expected:** FAIL with "function not found" or similar
**Verify:** Failure reason matches expectation (not a typo)

### 3. GREEN - Minimal Implementation

```rust
pub fn new_feature(input: &Input) -> Result {
    // Minimal code to pass the test
    Result { expected_property: expected_value }
}
```

**Requirements:**
- Just enough code to pass
- No premature optimization
- No additional features

### 4. Verify GREEN - Watch It Pass

```bash
cargo test test_new_feature_behavior -- --nocapture
```

**Expected:** PASS

### 5. Commit

```bash
git add src/feature.rs tests/feature_tests.rs
git commit -m "feat: add new_feature with TDD"
```

### 6. Refactor (while green)

```bash
cargo test --lib  # All tests must still pass
cargo clippy      # Zero warnings
```

---

## Test Organization

### Module Structure

```
daw-engine/src/
├── feature.rs          # Implementation
└── lib.rs              # mod feature;

daw-engine/tests/
└── feature_tests.rs    # Integration tests (if needed)
```

### Test Module Pattern

```rust
// In src/feature.rs
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_specific_behavior() {
        // Test implementation
    }
}
```

---

## Running Tests

### Full Test Suite
```bash
cd d:\Project\music-ai-toolshop\projects\06-opendaw\daw-engine
cargo test --lib
```

### Single Test
```bash
cargo test test_name -- --nocapture
```

### With Output
```bash
cargo test -- --nocapture
```

### Check Only (fast)
```bash
cargo check
```

---

## Current Test Baseline

**Total Tests:** 82 passing  
**Categories:**
- Base engine: 54 tests
- FFI bridge: 5 tests
- Real-time: 6 tests
- Cloud sync: 3 tests
- Plugin system: 17 tests
- Reverse engineering: 20 tests

**Maintenance Rule:** Never decrease test count. Add tests for new features.

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Wrong | Correct Approach |
|--------------|---------------|------------------|
| "I'll test after" | Tests after prove nothing | Test FIRST, always |
| "This is too simple" | Simple = where assumptions hide | Even 1-line changes get tests |
| Mocks everywhere | Tests implementation, not behavior | Test real code |
| One giant test | Hard to identify failures | Many small, focused tests |
| Testing internals | Brittle tests | Test public API only |
| No fail verification | Typos pass silently | Always watch test fail first |

---

## Test Naming Conventions

```rust
// Good - describes behavior
fn test_transport_stops_at_end_when_not_looping()
fn test_mixer_applies_gain_to_all_channels()
fn test_plugin_chain_processes_in_series_order()

// Avoid - vague names
fn test_transport()           // Too broad
fn test_mixer()               // What about mixer?
fn test_plugin()              // Which behavior?
```

---

## Assertions

```rust
// Equality
assert_eq!(actual, expected);
assert_ne!(actual, unexpected);

// Boolean
assert!(condition);
assert!(!condition);

// Results
assert!(result.is_ok());
assert!(result.is_err());
let value = result.unwrap();

// Floats (with tolerance)
assert!((actual - expected).abs() < 0.001);

// Panics
#[should_panic(expected = "error message")]
fn test_panics_on_invalid_input() {
    function_that_panics();
}
```

---

## Test Fixtures

```rust
#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_mixer() -> Mixer {
        Mixer::new(2, 44100.0)
    }

    fn create_test_sample() -> Sample {
        Sample::new(vec![0.0; 1024], 2, 44100.0)
    }

    #[test]
    fn test_mixer_with_sample() {
        let mixer = create_test_mixer();
        let sample = create_test_sample();
        // Test code
    }
}
```

---

## Before Commit Checklist

- [ ] All new functions have tests
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason
- [ ] Minimal code to pass each test
- [ ] All 82+ tests pass
- [ ] Zero compiler warnings (excluding test-only code)
- [ ] `cargo clippy` clean
- [ ] Committed with clear message

---

*Reference version: April 1, 2026*  
*Framework: dev_framework (Superpowers) - test-driven-development skill*
