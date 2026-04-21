//! Delta Analysis Module
//!
//! Compares two audio signals (dry vs processed) to detect
//! and quantify mix/mastering processing chains.

use crate::reverse_engineer::spectral::SpectralAnalyzer;

/// Detected processing types with confidence scores
#[derive(Debug, Clone, PartialEq, Default)]
pub struct ProcessingDetection {
    /// EQ changes detected (gain per frequency band in dB)
    pub eq_changes: Vec<(f32, f32)>, // (frequency_hz, gain_db)
    /// Compression amount detected (dB reduction)
    pub compression_db: f32,
    /// Confidence in compression detection (0-1)
    pub compression_confidence: f32,
    /// Reverb amount detected (RT60 estimate in seconds)
    pub reverb_rt60: f32,
    /// Confidence in reverb detection (0-1)
    pub reverb_confidence: f32,
    /// Stereo width change (1.0 = no change, >1 = wider, <1 = narrower)
    pub stereo_width_ratio: f32,
    /// Limiting/thresholding detected (boolean)
    pub limiting_detected: bool,
    /// Overall loudness change (LUFS difference)
    pub loudness_change_db: f32,
    /// Spectral balance shift (centroid difference)
    pub spectral_shift_hz: f32,
}

/// Delta features computed between two audio signals
#[derive(Debug, Clone, PartialEq, Default)]
pub struct DeltaFeatures {
    /// Spectral difference magnitude per frequency bin
    pub spectral_difference: Vec<f32>,
    /// RMS difference over time (envelope following)
    pub rms_difference_db: Vec<f32>,
    /// Dynamic range change (crest factor difference)
    pub crest_factor_change_db: f32,
    /// Transient response change
    pub transient_change: f32,
    /// Overall correlation coefficient (1.0 = identical)
    pub correlation: f32,
    /// Phase coherence (1.0 = perfectly in phase)
    pub phase_coherence: f32,
}

/// Analyzer for detecting processing differences between audio signals
pub struct DeltaAnalyzer {
    spectral_analyzer: SpectralAnalyzer,
    _fft_size: usize,
    _sample_rate: f32,
}

impl DeltaAnalyzer {
    /// Create new delta analyzer
    /// 
    /// # Arguments
    /// * `fft_size` - FFT window size (power of 2)
    /// * `sample_rate` - Audio sample rate in Hz
    pub fn new(fft_size: usize, sample_rate: f32) -> Self {
        Self {
            spectral_analyzer: SpectralAnalyzer::new(fft_size, sample_rate),
            _fft_size: fft_size,
            _sample_rate: sample_rate,
        }
    }
    
    /// Compare two mono audio buffers and detect processing
    /// 
    /// # Arguments
    /// * `dry` - Original unprocessed audio
    /// * `processed` - Processed audio to analyze
    pub fn compare(&mut self, dry: &[f32], processed: &[f32]) -> (DeltaFeatures, ProcessingDetection) {
        let delta = self.compute_delta(dry, processed);
        let detection = self.detect_processing(dry, processed, &delta);
        (delta, detection)
    }
    
    /// Compute delta features between two signals
    fn compute_delta(&mut self, dry: &[f32], processed: &[f32]) -> DeltaFeatures {
        let min_len = dry.len().min(processed.len());
        let dry = &dry[..min_len];
        let processed = &processed[..min_len];
        
        // Analyze both signals
        let dry_features = self.spectral_analyzer.analyze(dry);
        let processed_features = self.spectral_analyzer.analyze(processed);
        
        // Compute spectral difference (simplified - just comparing feature differences)
        let spectral_diff = vec![
            processed_features.spectral_centroid - dry_features.spectral_centroid,
            processed_features.spectral_rolloff - dry_features.spectral_rolloff,
            processed_features.spectral_flatness - dry_features.spectral_flatness,
        ];
        
        // Dynamic range change
        let crest_change = processed_features.crest_factor - dry_features.crest_factor;
        
        // Loudness envelope difference
        let rms_diff = processed_features.rms_db - dry_features.rms_db;
        
        // Compute correlation
        let correlation = self.compute_correlation(dry, processed);
        
        // Simple transient detection via zero crossing rate change
        let transient_change = processed_features.zero_crossing_rate - dry_features.zero_crossing_rate;
        
        // Phase coherence estimate (simplified)
        let phase_coherence = correlation.max(0.0); // Correlation approximates phase coherence
        
        DeltaFeatures {
            spectral_difference: spectral_diff,
            rms_difference_db: vec![rms_diff],
            crest_factor_change_db: crest_change,
            transient_change,
            correlation,
            phase_coherence,
        }
    }
    
    /// Detect specific processing types
    fn detect_processing(&self, dry: &[f32], processed: &[f32], delta: &DeltaFeatures) -> ProcessingDetection {
        // Loudness change
        let loudness_change = delta.rms_difference_db.iter().sum::<f32>() / delta.rms_difference_db.len() as f32;
        
        // Detect compression via crest factor reduction
        let compression_detected = delta.crest_factor_change_db < -3.0; // >3dB reduction suggests compression
        let compression_amount = if compression_detected {
            delta.crest_factor_change_db.abs()
        } else {
            0.0
        };
        let compression_confidence = if compression_detected {
            (delta.crest_factor_change_db.abs() / 10.0).min(1.0)
        } else {
            0.0
        };
        
        // Detect limiting via phase coherence and correlation drop
        let limiting = delta.correlation < 0.95 && delta.phase_coherence < 0.9;
        
        // Estimate spectral shift
        let spectral_shift = if !delta.spectral_difference.is_empty() {
            delta.spectral_difference[0] // Use centroid difference as shift indicator
        } else {
            0.0
        };
        
        // Estimate EQ changes (simplified - just a few broad bands)
        let eq_changes = self.estimate_eq_curve(dry, processed);
        
        // Reverb detection via phase coherence and tail analysis
        // Simplified: low correlation with sustained phase coherence suggests reverb
        let reverb_detected = delta.phase_coherence > 0.7 && delta.correlation < 0.8;
        let reverb_rt60 = if reverb_detected {
            // Rough estimate based on correlation drop
            (1.0 - delta.correlation) * 2.0 // Heuristic: 0-2 seconds range
        } else {
            0.0
        };
        let reverb_confidence = if reverb_detected {
            (delta.phase_coherence * (1.0 - delta.correlation)).min(1.0)
        } else {
            0.0
        };
        
        ProcessingDetection {
            eq_changes,
            compression_db: compression_amount,
            compression_confidence,
            reverb_rt60,
            reverb_confidence,
            stereo_width_ratio: 1.0, // Would need stereo analysis for real value
            limiting_detected: limiting,
            loudness_change_db: loudness_change,
            spectral_shift_hz: spectral_shift,
        }
    }
    
    /// Estimate EQ curve by comparing spectral envelopes
    fn estimate_eq_curve(&self, dry: &[f32], processed: &[f32]) -> Vec<(f32, f32)> {
        let bands = vec![
            (80.0, 120.0),     // Sub-bass
            (120.0, 250.0),    // Bass
            (250.0, 500.0),    // Low-mids
            (500.0, 1000.0),   // Mids
            (1000.0, 2000.0),  // High-mids
            (2000.0, 4000.0),  // Presence
            (4000.0, 8000.0),  // Brilliance
            (8000.0, 16000.0), // Air
        ];
        
        let mut changes = Vec::new();
        
        for (low, high) in bands {
            let center = (low + high) / 2.0;
            // Simplified: compare RMS in each band using basic filtering approximation
            let dry_energy = self.band_energy(dry, low, high);
            let proc_energy = self.band_energy(processed, low, high);
            
            if dry_energy > 0.0 && proc_energy > 0.0 {
                let gain_db = 10.0 * (proc_energy / dry_energy).log10();
                if gain_db.abs() > 0.5 { // Only report changes > 0.5 dB
                    changes.push((center, gain_db));
                }
            }
        }
        
        changes
    }
    
    /// Compute energy in a frequency band (simplified using time-domain approximation)
    fn band_energy(&self, signal: &[f32], _low_hz: f32, _high_hz: f32) -> f32 {
        // Simplified: just compute RMS of full signal
        // A real implementation would use bandpass filters
        let rms = (signal.iter().map(|&s| s * s).sum::<f32>() / signal.len() as f32).sqrt();
        rms * rms // Return energy (RMS squared)
    }
    
    /// Compute correlation coefficient between two signals
    fn compute_correlation(&self, a: &[f32], b: &[f32]) -> f32 {
        let n = a.len().min(b.len()) as f32;
        if n < 2.0 {
            return 0.0;
        }
        
        let mean_a = a.iter().sum::<f32>() / n;
        let mean_b = b.iter().sum::<f32>() / n;
        
        let mut num = 0.0;
        let mut den_a = 0.0;
        let mut den_b = 0.0;
        
        for i in 0..(n as usize) {
            let da = a[i] - mean_a;
            let db = b[i] - mean_b;
            num += da * db;
            den_a += da * da;
            den_b += db * db;
        }
        
        let denom = (den_a * den_b).sqrt();
        if denom > 0.0 {
            num / denom
        } else {
            0.0
        }
    }
    
    /// Generate a "production recipe" report from detection results
    pub fn generate_recipe(&self, detection: &ProcessingDetection) -> String {
        let mut recipe = String::from("Production Recipe:\n");
        
        if !detection.eq_changes.is_empty() {
            recipe.push_str("\nEQ Adjustments:\n");
            for (freq, gain) in &detection.eq_changes {
                recipe.push_str(&format!("  {:.0} Hz: {:+.1} dB\n", freq, gain));
            }
        }
        
        if detection.compression_confidence > 0.5 {
            recipe.push_str(&format!("\nCompression: {:.1} dB reduction (confidence: {:.0}%)\n",
                detection.compression_db,
                detection.compression_confidence * 100.0));
        }
        
        if detection.reverb_confidence > 0.5 {
            recipe.push_str(&format!("\nReverb: ~{:.2}s RT60 (confidence: {:.0}%)\n",
                detection.reverb_rt60,
                detection.reverb_confidence * 100.0));
        }
        
        if detection.limiting_detected {
            recipe.push_str("\nLimiting: Detected\n");
        }
        
        recipe.push_str(&format!("\nLoudness Change: {:+.1} LUFS\n", detection.loudness_change_db));
        recipe.push_str(&format!("Spectral Shift: {:+.0} Hz\n", detection.spectral_shift_hz));
        
        recipe
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    fn generate_sine(freq: f32, sample_rate: f32, duration_sec: f32) -> Vec<f32> {
        let samples = (sample_rate * duration_sec) as usize;
        (0..samples)
            .map(|i| {
                let phase = 2.0 * std::f32::consts::PI * freq * i as f32 / sample_rate;
                phase.sin() * 0.5
            })
            .collect()
    }
        
    fn generate_noise(sample_rate: f32, duration_sec: f32) -> Vec<f32> {
        let samples = (sample_rate * duration_sec) as usize;
        (0..samples)
            .enumerate()
            .map(|(i, _)| {
                let x = (i as f32 * 1.61803398875) % 1.0;
                (x - 0.5) * 2.0
            })
            .collect()
    }
        
    #[test]
    fn test_identical_signals() {
        let mut analyzer = DeltaAnalyzer::new(2048, 44100.0);
        let signal = generate_sine(1000.0, 44100.0, 0.5);
        
        let (delta, detection) = analyzer.compare(&signal, &signal);
        
        // Identical signals should have high correlation
        assert!(delta.correlation > 0.99, "Correlation should be ~1.0 for identical signals");
        assert!(!detection.limiting_detected);
        assert!(detection.compression_confidence < 0.5);
    }
    
    #[test]
    fn test_loudness_change_detection() {
        let mut analyzer = DeltaAnalyzer::new(2048, 44100.0);
        let dry = generate_sine(1000.0, 44100.0, 0.5);
        // Boost by 6 dB
        let processed: Vec<f32> = dry.iter().map(|&s| s * 2.0).collect();
        
        let (delta, detection) = analyzer.compare(&dry, &processed);
        
        // Should detect ~6 dB loudness increase
        assert!(detection.loudness_change_db > 4.0 && detection.loudness_change_db < 8.0,
            "Expected ~6 dB increase, got {} dB", detection.loudness_change_db);
        // Correlation should still be high (just gain change)
        assert!(delta.correlation > 0.95);
    }
    
    #[test]
    fn test_compression_detection() {
        let mut analyzer = DeltaAnalyzer::new(2048, 44100.0);
        
        // Create signal with high crest factor (peaks much higher than RMS)
        let mut dry = generate_sine(1000.0, 44100.0, 0.5);
        // Add sharp peaks
        for i in (0..dry.len()).step_by(100) {
            if i < dry.len() {
                dry[i] *= 3.0; // Sharp transient
            }
        }
        
        // "Compressed" version - reduce peaks
        let processed: Vec<f32> = dry.iter()
            .map(|&s| {
                if s.abs() > 0.7 {
                    s.signum() * 0.7 // Hard limiting / compression simulation
                } else {
                    s
                }
            })
            .collect();
        
        let (delta, _detection) = analyzer.compare(&dry, &processed);
        
        // Should detect compression (crest factor reduction)
        assert!(delta.crest_factor_change_db < -1.0,
            "Crest factor should decrease with compression, got {} dB",
            delta.crest_factor_change_db);
    }
    
    #[test]
    fn test_different_signals() {
        let mut analyzer = DeltaAnalyzer::new(2048, 44100.0);
        let dry = generate_sine(1000.0, 44100.0, 0.5);
        let processed = generate_sine(2000.0, 44100.0, 0.5); // Different frequency
        
        let (delta, detection) = analyzer.compare(&dry, &processed);
        
        // Different frequencies should have low correlation
        assert!(delta.correlation < 0.5, "Different frequencies should have low correlation");
        // Should detect spectral shift
        assert!(detection.spectral_shift_hz.abs() > 500.0,
            "Should detect ~1000 Hz shift, got {} Hz", detection.spectral_shift_hz);
    }
    
    #[test]
    fn test_recipe_generation() {
        let analyzer = DeltaAnalyzer::new(2048, 44100.0);
        let detection = ProcessingDetection {
            eq_changes: vec![(1000.0, 3.0), (5000.0, -2.0)],
            compression_db: 4.5,
            compression_confidence: 0.8,
            reverb_rt60: 1.2,
            reverb_confidence: 0.7,
            stereo_width_ratio: 1.0,
            limiting_detected: true,
            loudness_change_db: 6.0,
            spectral_shift_hz: 200.0,
        };
        
        let recipe = analyzer.generate_recipe(&detection);
        
        assert!(recipe.contains("EQ Adjustments"));
        assert!(recipe.contains("Compression"));
        assert!(recipe.contains("Reverb"));
        assert!(recipe.contains("Limiting"));
        assert!(recipe.contains("6.0 LUFS"));
    }
    
    #[test]
    fn test_correlation_computation() {
        let analyzer = DeltaAnalyzer::new(2048, 44100.0);
        
        // Perfect correlation
        let a = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let b = vec![2.0, 4.0, 6.0, 8.0, 10.0]; // Scaled version
        let corr = analyzer.compute_correlation(&a, &b);
        assert!((corr - 1.0).abs() < 0.01, "Perfect correlation expected, got {}", corr);
        
        // Negative correlation
        let c = vec![1.0, 2.0, 3.0];
        let d = vec![-1.0, -2.0, -3.0];
        let corr_neg = analyzer.compute_correlation(&c, &d);
        assert!((corr_neg - (-1.0)).abs() < 0.01, "Negative correlation expected, got {}", corr_neg);
    }
}
