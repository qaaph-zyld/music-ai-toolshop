//! Spectral Analysis Module
//!
//! FFT-based audio feature extraction for production analysis.
//! Extracts spectral features used for fingerprinting and delta comparison.

use rustfft::{FftPlanner, num_complex::Complex32};
use ndarray::Array1;

/// Spectral features extracted from audio frame
#[derive(Debug, Clone, Copy, PartialEq, Default)]
pub struct SpectralFeatures {
    /// Center of spectral mass (brightness indicator)
    pub spectral_centroid: f32,
    /// Frequency below which 85% of energy resides
    pub spectral_rolloff: f32,
    /// Rate of spectral change between frames
    pub spectral_flux: f32,
    /// Noisiness vs tonal quality (0=noisy, 1=pure tone)
    pub spectral_flatness: f32,
    /// Peak to RMS ratio in dB (compression indicator)
    pub crest_factor: f32,
    /// RMS energy level in dB
    pub rms_db: f32,
    /// Peak level in dB
    pub peak_db: f32,
    /// Perceived loudness (LUFS estimate)
    pub lufs_estimate: f32,
    /// Transient density (zero crossings per sample)
    pub zero_crossing_rate: f32,
    /// Signal bandwidth in Hz
    pub bandwidth: f32,
}

/// FFT-based spectral analyzer
pub struct SpectralAnalyzer {
    fft_size: usize,
    hop_size: usize,
    sample_rate: f32,
    fft: std::sync::Arc<dyn rustfft::Fft<f32>>,
    window: Vec<f32>,
    prev_magnitude: Vec<f32>,
}

impl SpectralAnalyzer {
    /// Create new analyzer with given FFT size and sample rate
    /// 
    /// # Arguments
    /// * `fft_size` - FFT window size (must be power of 2, typically 2048)
    /// * `sample_rate` - Audio sample rate in Hz
    pub fn new(fft_size: usize, sample_rate: f32) -> Self {
        assert!(fft_size.is_power_of_two(), "FFT size must be power of 2");
        
        let mut planner = FftPlanner::new();
        let fft = planner.plan_fft_forward(fft_size);
        
        // Hann window
        let window: Vec<f32> = (0..fft_size)
            .map(|i| {
                let phase = 2.0 * std::f32::consts::PI * i as f32 / (fft_size - 1) as f32;
                0.5 * (1.0 - phase.cos())
            })
            .collect();
        
        Self {
            fft_size,
            hop_size: fft_size / 2, // 50% overlap
            sample_rate,
            fft,
            window,
            prev_magnitude: vec![0.0; fft_size / 2 + 1],
        }
    }
    
    /// Extract spectral features from mono audio buffer
    pub fn analyze(&mut self, buffer: &[f32]) -> SpectralFeatures {
        if buffer.is_empty() {
            return SpectralFeatures::default();
        }
        
        // Compute FFT
        let mut input: Vec<Complex32> = buffer.iter()
            .zip(self.window.iter())
            .map(|(&s, &w)| Complex32::new(s * w, 0.0))
            .chain(std::iter::repeat(Complex32::new(0.0, 0.0)))
            .take(self.fft_size)
            .collect();
        
        self.fft.process(&mut input);
        
        // Compute magnitude spectrum (only positive frequencies)
        let magnitude: Vec<f32> = input[..self.fft_size / 2 + 1]
            .iter()
            .map(|c| c.norm())
            .collect();
        
        // Extract features
        let features = self.extract_features(&magnitude, buffer);
        
        // Store magnitude for flux calculation
        self.prev_magnitude.clone_from(&magnitude);
        
        features
    }
    
    /// Extract features from magnitude spectrum
    fn extract_features(&self, magnitude: &[f32], time_domain: &[f32]) -> SpectralFeatures {
        let _bin_count = magnitude.len();
        let freq_resolution = self.sample_rate / self.fft_size as f32;
        
        // Compute total spectral energy
        let total_energy: f32 = magnitude.iter().map(|&m| m * m).sum();
        
        // Spectral centroid (center of mass)
        let centroid = if total_energy > 0.0 {
            magnitude.iter()
                .enumerate()
                .map(|(i, &m)| {
                    let freq = i as f32 * freq_resolution;
                    freq * m * m
                })
                .sum::<f32>() / total_energy
        } else {
            0.0
        };
        
        // Spectral rolloff (85% energy threshold)
        let rolloff = if total_energy > 0.0 {
            let threshold = total_energy * 0.85;
            let mut cumulative = 0.0;
            let mut rolloff_bin = 0;
            for (i, &m) in magnitude.iter().enumerate() {
                cumulative += m * m;
                if cumulative >= threshold {
                    rolloff_bin = i;
                    break;
                }
            }
            rolloff_bin as f32 * freq_resolution
        } else {
            0.0
        };
        
        // Spectral flatness (geometric / arithmetic mean)
        let flatness = if total_energy > 0.0 {
            let log_sum: f32 = magnitude.iter()
                .filter(|&&m| m > 0.0)
                .map(|&m| m.ln())
                .sum();
            let geo_mean = (log_sum / magnitude.len() as f32).exp();
            let arith_mean = magnitude.iter().sum::<f32>() / magnitude.len() as f32;
            if arith_mean > 0.0 {
                geo_mean / arith_mean
            } else {
                0.0
            }
        } else {
            0.0
        };
        
        // Spectral flux (difference from previous frame)
        let flux = if self.prev_magnitude.len() == magnitude.len() {
            magnitude.iter()
                .zip(self.prev_magnitude.iter())
                .map(|(&curr, &prev)| (curr - prev).max(0.0))
                .sum::<f32>()
        } else {
            0.0
        };
        
        // Time-domain features
        let rms = (time_domain.iter().map(|&s| s * s).sum::<f32>() / time_domain.len() as f32).sqrt();
        let peak = time_domain.iter().map(|&s| s.abs()).fold(0.0, f32::max);
        let zero_crossings = time_domain.windows(2)
            .filter(|w| w[0].signum() != w[1].signum())
            .count();
        
        // Bandwidth (variance around centroid)
        let bandwidth = if total_energy > 0.0 {
            magnitude.iter()
                .enumerate()
                .map(|(i, &m)| {
                    let freq = i as f32 * freq_resolution;
                    let diff = freq - centroid;
                    diff * diff * m * m
                })
                .sum::<f32>() / total_energy
        } else {
            0.0
        };
        
        // Convert to dB scale
        let rms_db = if rms > 0.0 { 20.0 * rms.log10() } else { -100.0 };
        let peak_db = if peak > 0.0 { 20.0 * peak.log10() } else { -100.0 };
        let crest_factor = peak_db - rms_db;
        
        // Simple LUFS estimate (K-weighting approximation)
        let lufs_estimate = rms_db - 14.0; // Rough approximation
        
        SpectralFeatures {
            spectral_centroid: centroid,
            spectral_rolloff: rolloff,
            spectral_flux: flux,
            spectral_flatness: flatness.clamp(0.0, 1.0),
            crest_factor,
            rms_db,
            peak_db,
            lufs_estimate,
            zero_crossing_rate: zero_crossings as f32 / time_domain.len() as f32,
            bandwidth: bandwidth.sqrt(),
        }
    }
    
    /// Analyze full audio file, returning per-frame features
    pub fn analyze_file(&mut self, buffer: &[f32]) -> Vec<SpectralFeatures> {
        let mut features = Vec::new();
        
        for chunk in buffer.chunks(self.hop_size) {
            if chunk.len() >= self.fft_size / 2 {
                features.push(self.analyze(chunk));
            }
        }
        
        features
    }
    
    /// Convert features to feature vector for ML (ndarray)
    pub fn to_feature_vector(features: &SpectralFeatures) -> Array1<f32> {
        Array1::from(vec![
            features.spectral_centroid,
            features.spectral_rolloff,
            features.spectral_flux,
            features.spectral_flatness,
            features.crest_factor,
            features.rms_db,
            features.peak_db,
            features.lufs_estimate,
            features.zero_crossing_rate,
            features.bandwidth,
        ])
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_analyzer_creation() {
        let analyzer = SpectralAnalyzer::new(2048, 44100.0);
        assert_eq!(analyzer.fft_size, 2048);
        assert_eq!(analyzer.sample_rate, 44100.0);
    }
    
    #[test]
    fn test_silence_analysis() {
        let mut analyzer = SpectralAnalyzer::new(2048, 44100.0);
        let silence = vec![0.0f32; 2048];
        let features = analyzer.analyze(&silence);
        
        assert_eq!(features.rms_db, -100.0);
        assert_eq!(features.peak_db, -100.0);
        assert_eq!(features.spectral_centroid, 0.0);
    }
    
    #[test]
    fn test_sine_wave_detection() {
        let mut analyzer = SpectralAnalyzer::new(2048, 44100.0);
        
        // Generate 1000 Hz sine wave
        let freq = 1000.0;
        let samples: Vec<f32> = (0..2048)
            .map(|i| {
                let phase = 2.0 * std::f32::consts::PI * freq * i as f32 / 44100.0;
                phase.sin() * 0.5
            })
            .collect();
        
        let features = analyzer.analyze(&samples);
        
        // Sine wave should have high spectral flatness (pure tone - energy concentrated)
        // Actually: sine has low flatness (concentrated energy = more tonal)
        assert!(features.spectral_flatness < 0.3, 
            "Sine wave should have low flatness (concentrated energy), got {}", 
            features.spectral_flatness);
        // Centroid should be near 1000 Hz
        assert!((features.spectral_centroid - 1000.0).abs() < 200.0, 
            "Centroid {} should be near 1000 Hz", features.spectral_centroid);
        // Should have low zero crossing rate for low frequency
        assert!(features.zero_crossing_rate < 0.1, "Low freq sine should have low ZCR");
    }
    
    #[test]
    fn test_white_noise_detection() {
        let mut analyzer = SpectralAnalyzer::new(2048, 44100.0);
        
        // Generate white noise (deterministic for tests)
        let noise: Vec<f32> = (0..2048)
            .enumerate()
            .map(|(i, _)| {
                // Simple pseudo-random using index
                let x = (i as f32 * 1.61803398875) % 1.0;
                (x - 0.5) * 2.0
            })
            .collect();
        
        let features = analyzer.analyze(&noise);
        
        // Noise should have high spectral flatness (energy spread across spectrum)
        assert!(features.spectral_flatness > 0.4, 
            "Noise should have high flatness (spread energy), got {}", 
            features.spectral_flatness);
        // High zero crossing rate
        assert!(features.zero_crossing_rate > 0.3, "Noise should have high ZCR");
    }
    
    #[test]
    fn test_feature_vector_conversion() {
        let features = SpectralFeatures {
            spectral_centroid: 1000.0,
            spectral_rolloff: 5000.0,
            spectral_flux: 0.5,
            spectral_flatness: 0.8,
            crest_factor: 12.0,
            rms_db: -12.0,
            peak_db: -6.0,
            lufs_estimate: -14.0,
            zero_crossing_rate: 0.05,
            bandwidth: 500.0,
        };
        
        let vector = SpectralAnalyzer::to_feature_vector(&features);
        assert_eq!(vector.len(), 10);
        assert_eq!(vector[0], 1000.0);
        assert_eq!(vector[4], 12.0);
    }
    
    #[test]
    fn test_crest_factor_calculation() {
        let mut analyzer = SpectralAnalyzer::new(2048, 44100.0);
        
        // Create signal with known crest factor
        let mut signal = vec![0.0f32; 2048];
        // Square wave: peak = 1.0, RMS = 1.0 (crest factor = 0 dB difference)
        for i in 0..2048 {
            signal[i] = if i % 2 == 0 { 1.0 } else { -1.0 };
        }
        
        let features = analyzer.analyze(&signal);
        // Square wave has crest factor around 0 dB (peak == RMS in theory, actually 3dB)
        assert!(features.crest_factor >= 0.0 && features.crest_factor < 6.0,
            "Square wave crest factor should be low, got {}", features.crest_factor);
    }
}
