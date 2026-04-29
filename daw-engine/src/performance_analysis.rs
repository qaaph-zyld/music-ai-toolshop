//! Performance Analysis Module
//!
//! Provides baseline measurements and performance metrics collection
//! for identifying optimization candidates in the audio engine.
//!
//! # Usage
//!
//! ```rust
//! use daw_engine::PerformanceAnalyzer;
//!
//! let mut analyzer = PerformanceAnalyzer::new();
//! analyzer.baseline_mixer_8tracks();
//! let report = analyzer.generate_report();
//! ```

use std::time::Instant;

/// Performance metrics for a single measurement
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PerformanceMetrics {
    /// Average processing time in microseconds
    pub avg_us: f64,
    /// Minimum processing time in microseconds
    pub min_us: f64,
    /// Maximum processing time in microseconds
    pub max_us: f64,
    /// Standard deviation in microseconds
    pub std_dev_us: f64,
    /// Number of samples collected
    pub sample_count: usize,
    /// CPU usage percentage (estimated)
    pub cpu_percent: f64,
}

impl Default for PerformanceMetrics {
    fn default() -> Self {
        Self {
            avg_us: 0.0,
            min_us: f64::MAX,
            max_us: 0.0,
            std_dev_us: 0.0,
            sample_count: 0,
            cpu_percent: 0.0,
        }
    }
}

impl PerformanceMetrics {
    /// Calculate real-time safety score (0-100)
    /// Higher is better. Based on consistency and staying within budget.
    pub fn realtime_score(&self, budget_us: f64) -> u8 {
        if self.sample_count == 0 {
            return 0;
        }

        // Budget compliance: what percentage of samples stay under budget
        let budget_score = if self.max_us <= budget_us {
            50 // Full budget compliance
        } else {
            let over_ratio = (self.max_us - budget_us) / budget_us;
            let penalty = (over_ratio * 50.0).min(50.0) as u8;
            50 - penalty
        };

        // Consistency score based on coefficient of variation
        let cv = if self.avg_us > 0.0 {
            self.std_dev_us / self.avg_us
        } else {
            1.0
        };
        let consistency_score = ((1.0 - cv.min(1.0)) * 50.0) as u8;

        budget_score + consistency_score
    }

    /// Returns true if this performance is acceptable for real-time audio
    pub fn is_realtime_safe(&self, budget_us: f64) -> bool {
        self.max_us <= budget_us && self.realtime_score(budget_us) >= 80
    }
}

/// Collects timing measurements for statistical analysis
pub struct TimingCollector {
    measurements: Vec<f64>,
}

impl TimingCollector {
    pub fn new() -> Self {
        Self {
            measurements: Vec::with_capacity(1000),
        }
    }

    pub fn record(&mut self, duration_us: f64) {
        self.measurements.push(duration_us);
    }

    pub fn compute_metrics(&self) -> PerformanceMetrics {
        if self.measurements.is_empty() {
            return PerformanceMetrics::default();
        }

        let sum: f64 = self.measurements.iter().sum();
        let avg = sum / self.measurements.len() as f64;
        let min = self.measurements.iter().fold(f64::MAX, |a, &b| a.min(b));
        let max = self.measurements.iter().fold(f64::MIN, |a, &b| a.max(b));

        // Calculate standard deviation
        let variance: f64 = self
            .measurements
            .iter()
            .map(|&x| (x - avg).powi(2))
            .sum::<f64>()
            / self.measurements.len() as f64;
        let std_dev = variance.sqrt();

        PerformanceMetrics {
            avg_us: avg,
            min_us: min,
            max_us: max,
            std_dev_us: std_dev,
            sample_count: self.measurements.len(),
            cpu_percent: (avg / 2900.0) * 100.0, // Estimate based on 2.9ms @ 48kHz/128 samples
        }
    }

    pub fn clear(&mut self) {
        self.measurements.clear();
    }
}

/// Performance analyzer for establishing baselines
pub struct PerformanceAnalyzer {
    collector: TimingCollector,
    sample_rate: u32,
    buffer_size: usize,
}

impl PerformanceAnalyzer {
    pub fn new() -> Self {
        Self {
            collector: TimingCollector::new(),
            sample_rate: 48000,
            buffer_size: 128,
        }
    }

    pub fn with_config(sample_rate: u32, buffer_size: usize) -> Self {
        Self {
            collector: TimingCollector::new(),
            sample_rate,
            buffer_size,
        }
    }

    /// Calculate the real-time budget in microseconds
    pub fn realtime_budget_us(&self) -> f64 {
        let samples_per_ms = self.sample_rate as f64 / 1000.0;
        let budget_ms = self.buffer_size as f64 / samples_per_ms;
        budget_ms * 1000.0 // Convert to microseconds
    }

    /// Measure a function and record timing
    pub fn measure<F, R>(&mut self, f: F) -> R
    where
        F: FnOnce() -> R,
    {
        let start = Instant::now();
        let result = f();
        let duration = start.elapsed();
        self.collector
            .record(duration.as_secs_f64() * 1_000_000.0);
        result
    }

    /// Get current metrics
    pub fn metrics(&self) -> PerformanceMetrics {
        self.collector.compute_metrics()
    }

    /// Reset measurements
    pub fn reset(&mut self) {
        self.collector.clear();
    }

    /// Generate performance report
    pub fn generate_report(&self) -> PerformanceReport {
        let metrics = self.metrics();
        let budget = self.realtime_budget_us();

        PerformanceReport {
            metrics,
            realtime_budget_us: budget,
            score: metrics.realtime_score(budget),
            is_safe: metrics.is_realtime_safe(budget),
        }
    }
}

/// Comprehensive performance report
#[derive(Debug, Clone)]
pub struct PerformanceReport {
    pub metrics: PerformanceMetrics,
    pub realtime_budget_us: f64,
    pub score: u8,
    pub is_safe: bool,
}

impl std::fmt::Display for PerformanceReport {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        writeln!(f, "Performance Report")?;
        writeln!(f, "==================")?;
        writeln!(f, "Budget: {:.2} µs", self.realtime_budget_us)?;
        writeln!(f, "Average: {:.2} µs", self.metrics.avg_us)?;
        writeln!(f, "Min: {:.2} µs", self.metrics.min_us)?;
        writeln!(f, "Max: {:.2} µs", self.metrics.max_us)?;
        writeln!(f, "Std Dev: {:.2} µs", self.metrics.std_dev_us)?;
        writeln!(f, "Samples: {}", self.metrics.sample_count)?;
        writeln!(f, "CPU Estimate: {:.1}%", self.metrics.cpu_percent)?;
        writeln!(f, "Score: {}/100", self.score)?;
        writeln!(f, "Real-time Safe: {}", if self.is_safe { "YES" } else { "NO" })
    }
}

/// Baseline measurements for different engine components
pub struct BaselineMeasurements;

impl BaselineMeasurements {
    /// Expected budget for 48kHz/128 samples (2.67ms)
    pub const BUDGET_48K_128: f64 = 2666.67;

    /// Expected budget for 48kHz/256 samples (5.33ms)
    pub const BUDGET_48K_256: f64 = 5333.33;

    /// Expected budget for 44.1kHz/128 samples (2.90ms)
    pub const BUDGET_44K_128: f64 = 2902.49;

    /// Performance thresholds for optimization candidates
    pub fn is_optimization_candidate(metrics: &PerformanceMetrics, budget: f64) -> bool {
        let score = metrics.realtime_score(budget);
        score < 70 || metrics.max_us > budget * 1.5
    }

    /// Grade performance (A-F scale)
    pub fn grade_performance(score: u8) -> &'static str {
        match score {
            90..=100 => "A (Excellent)",
            80..=89 => "B (Good)",
            70..=79 => "C (Acceptable)",
            60..=69 => "D (Marginal)",
            _ => "F (Needs Optimization)",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_performance_metrics_default() {
        let metrics = PerformanceMetrics::default();
        assert_eq!(metrics.sample_count, 0);
        assert_eq!(metrics.avg_us, 0.0);
    }

    #[test]
    fn test_realtime_score_perfect() {
        let metrics = PerformanceMetrics {
            avg_us: 500.0,
            min_us: 450.0,
            max_us: 550.0,
            std_dev_us: 20.0,
            sample_count: 100,
            cpu_percent: 20.0,
        };

        // Perfect score: under budget, low variance
        let score = metrics.realtime_score(2666.67);
        assert!(score >= 95, "Perfect performance should score >= 95, got {}", score);
    }

    #[test]
    fn test_realtime_score_over_budget() {
        // High variance + over budget should give poor score
        let metrics = PerformanceMetrics {
            avg_us: 2500.0,
            min_us: 1000.0,
            max_us: 5000.0, // Way over budget
            std_dev_us: 1500.0, // High variance
            sample_count: 100,
            cpu_percent: 80.0,
        };

        let score = metrics.realtime_score(2666.67);
        // High variance plus over budget should score poorly
        assert!(score < 70, "High variance + over-budget should score < 70, got {}", score);
        assert!(!metrics.is_realtime_safe(2666.67), "Should not be realtime safe with max=5000, budget=2666");
    }

    #[test]
    fn test_timing_collector() {
        let mut collector = TimingCollector::new();

        for i in 0..10 {
            collector.record(100.0 + i as f64 * 10.0);
        }

        let metrics = collector.compute_metrics();
        assert_eq!(metrics.sample_count, 10);
        assert!(metrics.avg_us > 0.0);
        assert!(metrics.min_us <= metrics.max_us);
    }

    #[test]
    fn test_realtime_budget_calculation() {
        let analyzer = PerformanceAnalyzer::with_config(48000, 128);
        let budget = analyzer.realtime_budget_us();
        // 128 samples @ 48kHz = 2.666... ms
        assert!((budget - 2666.67).abs() < 1.0);
    }

    #[test]
    fn test_performance_report_display() {
        let report = PerformanceReport {
            metrics: PerformanceMetrics {
                avg_us: 1000.0,
                min_us: 900.0,
                max_us: 1100.0,
                std_dev_us: 50.0,
                sample_count: 100,
                cpu_percent: 35.0,
            },
            realtime_budget_us: 2666.67,
            score: 85,
            is_safe: true,
        };

        let output = format!("{}", report);
        assert!(output.contains("Performance Report"));
        assert!(output.contains("Budget:"));
        assert!(output.contains("Real-time Safe: YES"));
    }

    #[test]
    fn test_grade_performance() {
        assert_eq!(BaselineMeasurements::grade_performance(95), "A (Excellent)");
        assert_eq!(BaselineMeasurements::grade_performance(85), "B (Good)");
        assert_eq!(BaselineMeasurements::grade_performance(75), "C (Acceptable)");
        assert_eq!(BaselineMeasurements::grade_performance(65), "D (Marginal)");
        assert_eq!(BaselineMeasurements::grade_performance(50), "F (Needs Optimization)");
    }

    #[test]
    fn test_optimization_candidate_detection() {
        let good = PerformanceMetrics {
            avg_us: 500.0,
            min_us: 450.0,
            max_us: 550.0,
            std_dev_us: 20.0,
            sample_count: 100,
            cpu_percent: 20.0,
        };

        let bad = PerformanceMetrics {
            avg_us: 2500.0,
            min_us: 2000.0,
            max_us: 5000.0, // Way over budget
            std_dev_us: 800.0,
            sample_count: 100,
            cpu_percent: 85.0,
        };

        assert!(!BaselineMeasurements::is_optimization_candidate(&good, 2666.67));
        assert!(BaselineMeasurements::is_optimization_candidate(&bad, 2666.67));
    }
}
