# Performance Analysis Documentation

## Overview

The OpenDAW audio engine includes comprehensive performance analysis tools for establishing baselines, measuring real-time safety, and identifying optimization candidates.

## Features

- **PerformanceAnalyzer**: Statistical timing collection and analysis
- **Real-time Safety Scoring**: 0-100 scoring based on budget compliance and consistency
- **Baseline Measurements**: Standardized tests for engine components
- **Optimization Identification**: Automatic detection of performance bottlenecks

## Usage

### Basic Performance Measurement

```rust
use daw_engine::{PerformanceAnalyzer, BaselineMeasurements};

// Create analyzer for 48kHz/128 samples (2.67ms budget)
let mut analyzer = PerformanceAnalyzer::with_config(48000, 128);

// Measure a function
analyzer.measure(|| {
    mixer.process(&mut output);
});

// Generate report
let report = analyzer.generate_report();
println!("{}", report);
```

### Real-time Safety Check

```rust
let metrics = analyzer.metrics();
let budget = 2666.67; // µs for 48kHz/128 samples

if metrics.is_realtime_safe(budget) {
    println!("✅ Real-time safe! Score: {}", metrics.realtime_score(budget));
} else {
    println!("⚠️  Needs optimization. Score: {}", metrics.realtime_score(budget));
}
```

### Performance Report Output

```
Performance Report
==================
Budget: 2666.67 µs
Average: 156.32 µs
Min: 142.10 µs
Max: 203.45 µs
Std Dev: 18.56 µs
Samples: 1000
CPU Estimate: 5.9%
Score: 94/100
Real-time Safe: YES
```

## Baseline Tests

Run baseline measurements with:

```bash
cd daw-engine
cargo test --test stress_test baseline
```

### Available Baseline Tests

| Test | Description | Threshold |
|------|-------------|-----------|
| `baseline_mixer_8tracks` | 8-track mixer performance | avg < 500µs, max < 2000µs |
| `baseline_sample_player` | Sample playback speed | avg < 1000µs, max < 2000µs |
| `baseline_transport_clock` | Clock advancement | avg < 10µs |
| `baseline_midi_engine` | MIDI processing (100 notes) | avg < 100µs, max < 500µs |
| `baseline_scaling_linear` | Track scaling check | 16 tracks < 2.5x 8 tracks |

## Scoring Algorithm

The real-time score (0-100) is calculated as:

```
score = budget_score + consistency_score

budget_score:
  - If max ≤ budget: 50 points
  - If max > budget: 50 - (over_ratio × 50)

consistency_score:
  - Based on coefficient of variation (std_dev / avg)
  - score = (1 - cv) × 50, clamped to [0, 50]
```

### Grading Scale

| Score | Grade | Interpretation |
|-------|-------|----------------|
| 90-100 | A | Excellent - ready for production |
| 80-89 | B | Good - suitable for real-time |
| 70-79 | C | Acceptable - monitor closely |
| 60-69 | D | Marginal - optimize recommended |
| 0-59 | F | Needs optimization |

## Optimization Candidates

Components are flagged as optimization candidates when:

- Real-time score < 70, OR
- Maximum processing time > 1.5× budget

### Common Optimization Targets

1. **Mixer**: Large track counts (64+)
2. **Sample Player**: Large file seeking
3. **MIDI Engine**: Dense note patterns (1000+ notes)
4. **Session View**: Large clip grids (1000+ clips)

## Tracy Integration

Combine with Tracy profiler for detailed analysis:

```bash
# Build with Tracy
cargo build --features tracy --profile release-tracy

# Run with profiling
OPENDAW_TRACY=1 cargo test --features tracy --test stress_test baseline
```

Tracy zones are instrumented in:
- `audio_callback` - Main callback entry
- `mixer_process` - Mixer processing
- `clip_player` - Clip/sample playback
- `transport_sync` - Transport synchronization

## Benchmarks

Criterion benchmarks provide detailed performance data:

```bash
cargo bench
```

Results saved to `target/criterion/` with HTML reports.

### Available Benchmarks

- `mixer/process` - Track count scaling (1, 2, 4, 8, 16, 32, 64)
- `sample_player/process_stereo_48k` - Buffer size scaling (64, 128, 256, 512, 1024)
- `transport_clock/advance_and_beats` - Sample count scaling
- `midi_engine/process_notes` - Note count scaling (10, 50, 100, 500, 1000)
- `realtime/callback_128_samples` - Consistency measurement

## Real-time Budgets

Standard buffer configurations and their budgets:

| Sample Rate | Buffer Size | Budget (µs) | Budget (ms) |
|-------------|-------------|-------------|---------------|
| 48 kHz | 128 | 2666.67 | 2.67 |
| 48 kHz | 256 | 5333.33 | 5.33 |
| 48 kHz | 512 | 10666.67 | 10.67 |
| 44.1 kHz | 128 | 2902.49 | 2.90 |
| 44.1 kHz | 256 | 5804.99 | 5.80 |

Target: Stay under 50% of budget for safety margin.

## CI Integration

Performance tests run in CI to detect regressions:

```yaml
- name: Performance Tests
  run: |
    cd daw-engine
    cargo test --test stress_test baseline
```

## Best Practices

1. **Measure in release mode** for production baselines
2. **Warm up before measuring** (100+ iterations)
3. **Use 1000+ samples** for statistical significance
4. **Monitor both avg and max** - consistency matters
5. **Set alerts for score < 70** - investigate immediately

## API Reference

### PerformanceAnalyzer

```rust
impl PerformanceAnalyzer {
    pub fn new() -> Self;
    pub fn with_config(sample_rate: u32, buffer_size: usize) -> Self;
    pub fn realtime_budget_us(&self) -> f64;
    pub fn measure<F, R>(&mut self, f: F) -> R;
    pub fn metrics(&self) -> PerformanceMetrics;
    pub fn reset(&mut self);
    pub fn generate_report(&self) -> PerformanceReport;
}
```

### PerformanceMetrics

```rust
pub struct PerformanceMetrics {
    pub avg_us: f64,
    pub min_us: f64,
    pub max_us: f64,
    pub std_dev_us: f64,
    pub sample_count: usize,
    pub cpu_percent: f64,
}

impl PerformanceMetrics {
    pub fn realtime_score(&self, budget_us: f64) -> u8;
    pub fn is_realtime_safe(&self, budget_us: f64) -> bool;
}
```

### BaselineMeasurements

```rust
pub struct BaselineMeasurements;

impl BaselineMeasurements {
    pub const BUDGET_48K_128: f64 = 2666.67;
    pub const BUDGET_48K_256: f64 = 5333.33;
    pub const BUDGET_44K_128: f64 = 2902.49;
    
    pub fn is_optimization_candidate(metrics: &PerformanceMetrics, budget: f64) -> bool;
    pub fn grade_performance(score: u8) -> &'static str;
}
```

## Files

- `src/performance_analysis.rs` - Core analysis module
- `tests/stress_test.rs` - Baseline tests
- `benches/engine_benchmarks.rs` - Criterion benchmarks
- `docs/performance_analysis.md` - This documentation
