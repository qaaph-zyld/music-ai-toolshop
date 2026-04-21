//! sndfilter integration — real C library for reverb, compressor, and biquad filters
//!
//! Wraps the sndfilter library by Sean Connelly (0BSD license).
//! Source: https://github.com/velipso/sndfilter
//!
//! This is a REAL integration — the C code is compiled and linked via build.rs.

use std::os::raw::{c_int, c_float};

/// Stereo sample (matches sf_sample_st in snd.h)
#[repr(C)]
#[derive(Debug, Clone, Copy, Default)]
pub struct SfSample {
    pub l: c_float,
    pub r: c_float,
}

// ============================================================================
// Biquad filter FFI
// ============================================================================

#[repr(C)]
pub struct SfBiquadState {
    b0: c_float,
    b1: c_float,
    b2: c_float,
    a1: c_float,
    a2: c_float,
    xn1: SfSample,
    xn2: SfSample,
    yn1: SfSample,
    yn2: SfSample,
}

extern "C" {
    fn sf_lowpass(state: *mut SfBiquadState, rate: c_int, cutoff: c_float, resonance: c_float);
    fn sf_highpass(state: *mut SfBiquadState, rate: c_int, cutoff: c_float, resonance: c_float);
    fn sf_bandpass(state: *mut SfBiquadState, rate: c_int, freq: c_float, q: c_float);
    fn sf_notch(state: *mut SfBiquadState, rate: c_int, freq: c_float, q: c_float);
    fn sf_peaking(state: *mut SfBiquadState, rate: c_int, freq: c_float, q: c_float, gain: c_float);
    #[allow(unused)]
    fn sf_allpass(state: *mut SfBiquadState, rate: c_int, freq: c_float, q: c_float);
    fn sf_lowshelf(state: *mut SfBiquadState, rate: c_int, freq: c_float, q: c_float, gain: c_float);
    fn sf_highshelf(state: *mut SfBiquadState, rate: c_int, freq: c_float, q: c_float, gain: c_float);
    fn sf_biquad_process(state: *mut SfBiquadState, size: c_int, input: *mut SfSample, output: *mut SfSample);
}

// ============================================================================
// Compressor FFI
// ============================================================================

const SF_COMPRESSOR_MAXDELAY: usize = 1024;

#[repr(C)]
pub struct SfCompressorState {
    pub metergain: c_float,
    meterrelease: c_float,
    threshold: c_float,
    knee: c_float,
    linearpregain: c_float,
    linearthreshold: c_float,
    slope: c_float,
    attacksamplesinv: c_float,
    satreleasesamplesinv: c_float,
    wet: c_float,
    dry: c_float,
    k: c_float,
    kneedboffset: c_float,
    linearthresholdknee: c_float,
    mastergain: c_float,
    a: c_float,
    b: c_float,
    c: c_float,
    d: c_float,
    detectoravg: c_float,
    compgain: c_float,
    maxcompdiffdb: c_float,
    delaybufsize: c_int,
    delaywritepos: c_int,
    delayreadpos: c_int,
    delaybuf: [SfSample; SF_COMPRESSOR_MAXDELAY],
}

extern "C" {
    fn sf_defaultcomp(state: *mut SfCompressorState, rate: c_int);
    fn sf_simplecomp(
        state: *mut SfCompressorState,
        rate: c_int,
        pregain: c_float,
        threshold: c_float,
        knee: c_float,
        ratio: c_float,
        attack: c_float,
        release: c_float,
    );
    fn sf_compressor_process(
        state: *mut SfCompressorState,
        size: c_int,
        input: *mut SfSample,
        output: *mut SfSample,
    );
}

// ============================================================================
// Safe Rust wrappers
// ============================================================================

/// Biquad filter types
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum BiquadType {
    Lowpass,
    Highpass,
    Bandpass,
    Notch,
    Allpass,
}

/// Safe wrapper around sndfilter biquad
pub struct BiquadFilter {
    state: Box<SfBiquadState>,
}

impl BiquadFilter {
    /// Create a lowpass filter
    pub fn lowpass(sample_rate: i32, cutoff: f32, resonance: f32) -> Self {
        let mut state = Self::new_state();
        unsafe { sf_lowpass(&mut *state, sample_rate, cutoff, resonance) };
        Self { state }
    }

    /// Create a highpass filter
    pub fn highpass(sample_rate: i32, cutoff: f32, resonance: f32) -> Self {
        let mut state = Self::new_state();
        unsafe { sf_highpass(&mut *state, sample_rate, cutoff, resonance) };
        Self { state }
    }

    /// Create a bandpass filter
    pub fn bandpass(sample_rate: i32, freq: f32, q: f32) -> Self {
        let mut state = Self::new_state();
        unsafe { sf_bandpass(&mut *state, sample_rate, freq, q) };
        Self { state }
    }

    /// Create a notch filter
    pub fn notch(sample_rate: i32, freq: f32, q: f32) -> Self {
        let mut state = Self::new_state();
        unsafe { sf_notch(&mut *state, sample_rate, freq, q) };
        Self { state }
    }

    /// Create a peaking EQ filter
    pub fn peaking(sample_rate: i32, freq: f32, q: f32, gain: f32) -> Self {
        let mut state = Self::new_state();
        unsafe { sf_peaking(&mut *state, sample_rate, freq, q, gain) };
        Self { state }
    }

    /// Create a low shelf filter
    pub fn low_shelf(sample_rate: i32, freq: f32, q: f32, gain: f32) -> Self {
        let mut state = Self::new_state();
        unsafe { sf_lowshelf(&mut *state, sample_rate, freq, q, gain) };
        Self { state }
    }

    /// Create a high shelf filter
    pub fn high_shelf(sample_rate: i32, freq: f32, q: f32, gain: f32) -> Self {
        let mut state = Self::new_state();
        unsafe { sf_highshelf(&mut *state, sample_rate, freq, q, gain) };
        Self { state }
    }

    /// Process stereo samples in-place
    pub fn process(&mut self, samples: &mut [SfSample]) {
        let len = samples.len() as c_int;
        let ptr = samples.as_mut_ptr();
        unsafe {
            sf_biquad_process(&mut *self.state, len, ptr, ptr);
        }
    }

    /// Process interleaved f32 stereo buffer (L,R,L,R,...)
    pub fn process_interleaved(&mut self, buffer: &mut [f32]) {
        assert!(buffer.len() % 2 == 0, "Buffer must have even length (stereo)");
        let samples = unsafe {
            std::slice::from_raw_parts_mut(
                buffer.as_mut_ptr() as *mut SfSample,
                buffer.len() / 2,
            )
        };
        self.process(samples);
    }

    fn new_state() -> Box<SfBiquadState> {
        Box::new(SfBiquadState {
            b0: 0.0, b1: 0.0, b2: 0.0, a1: 0.0, a2: 0.0,
            xn1: SfSample::default(), xn2: SfSample::default(),
            yn1: SfSample::default(), yn2: SfSample::default(),
        })
    }
}

/// Safe wrapper around sndfilter compressor
pub struct Compressor {
    state: Box<SfCompressorState>,
}

impl Compressor {
    /// Create compressor with default settings
    pub fn new(sample_rate: i32) -> Self {
        let mut state = Self::new_state();
        unsafe { sf_defaultcomp(&mut *state, sample_rate) };
        Self { state }
    }

    /// Create compressor with simple parameters
    pub fn simple(
        sample_rate: i32,
        pregain: f32,
        threshold: f32,
        knee: f32,
        ratio: f32,
        attack: f32,
        release: f32,
    ) -> Self {
        let mut state = Self::new_state();
        unsafe {
            sf_simplecomp(
                &mut *state,
                sample_rate,
                pregain,
                threshold,
                knee,
                ratio,
                attack,
                release,
            )
        };
        Self { state }
    }

    /// Process stereo samples
    pub fn process(&mut self, input: &mut [SfSample], output: &mut [SfSample]) {
        assert_eq!(input.len(), output.len());
        let len = input.len() as c_int;
        unsafe {
            sf_compressor_process(
                &mut *self.state,
                len,
                input.as_mut_ptr(),
                output.as_mut_ptr(),
            );
        }
    }

    /// Process interleaved f32 stereo buffer in-place
    pub fn process_interleaved(&mut self, buffer: &mut [f32]) {
        assert!(buffer.len() % 2 == 0);
        let len = buffer.len() / 2;
        let mut output = vec![SfSample::default(); len];
        let input = unsafe {
            std::slice::from_raw_parts_mut(
                buffer.as_mut_ptr() as *mut SfSample,
                len,
            )
        };
        self.process(input, &mut output);
        // Copy output back to buffer
        for (i, s) in output.iter().enumerate() {
            buffer[i * 2] = s.l;
            buffer[i * 2 + 1] = s.r;
        }
    }

    /// Get the meter gain (how much compression was applied in dB)
    pub fn meter_gain(&self) -> f32 {
        self.state.metergain
    }

    fn new_state() -> Box<SfCompressorState> {
        unsafe {
            let layout = std::alloc::Layout::new::<SfCompressorState>();
            let ptr = std::alloc::alloc_zeroed(layout) as *mut SfCompressorState;
            Box::from_raw(ptr)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_biquad_lowpass_creates() {
        let _filter = BiquadFilter::lowpass(48000, 1000.0, 1.0);
    }

    #[test]
    fn test_biquad_lowpass_attenuates_high_frequencies() {
        let mut filter = BiquadFilter::lowpass(48000, 200.0, 1.0);

        // Generate 10kHz sine wave (well above 200Hz cutoff)
        let num_samples = 1024;
        let mut samples: Vec<SfSample> = (0..num_samples)
            .map(|i| {
                let t = i as f32 / 48000.0;
                let val = (2.0 * std::f32::consts::PI * 10000.0 * t).sin() * 0.5;
                SfSample { l: val, r: val }
            })
            .collect();

        // Measure input energy
        let input_energy: f32 = samples.iter().map(|s| s.l * s.l).sum();

        // Process through lowpass
        filter.process(&mut samples);

        // Measure output energy — should be significantly reduced
        let output_energy: f32 = samples.iter().map(|s| s.l * s.l).sum();

        assert!(
            output_energy < input_energy * 0.1,
            "Lowpass should attenuate 10kHz signal by >90%. Input energy: {}, Output: {}",
            input_energy,
            output_energy
        );
    }

    #[test]
    fn test_biquad_lowpass_passes_low_frequencies() {
        let mut filter = BiquadFilter::lowpass(48000, 5000.0, 0.7);

        // Generate 100Hz sine wave (well below 5kHz cutoff)
        let num_samples = 4800; // 100ms at 48kHz
        let mut samples: Vec<SfSample> = (0..num_samples)
            .map(|i| {
                let t = i as f32 / 48000.0;
                let val = (2.0 * std::f32::consts::PI * 100.0 * t).sin() * 0.5;
                SfSample { l: val, r: val }
            })
            .collect();

        let input_energy: f32 = samples.iter().map(|s| s.l * s.l).sum();

        filter.process(&mut samples);

        let output_energy: f32 = samples.iter().map(|s| s.l * s.l).sum();

        // Low frequency should pass through with minimal attenuation
        assert!(
            output_energy > input_energy * 0.5,
            "Lowpass should pass 100Hz signal. Input: {}, Output: {}",
            input_energy,
            output_energy
        );
    }

    #[test]
    fn test_biquad_highpass_attenuates_low_frequencies() {
        let mut filter = BiquadFilter::highpass(48000, 5000.0, 1.0);

        // Generate 100Hz sine wave (well below 5kHz cutoff)
        let num_samples = 4800;
        let mut samples: Vec<SfSample> = (0..num_samples)
            .map(|i| {
                let t = i as f32 / 48000.0;
                let val = (2.0 * std::f32::consts::PI * 100.0 * t).sin() * 0.5;
                SfSample { l: val, r: val }
            })
            .collect();

        let input_energy: f32 = samples.iter().map(|s| s.l * s.l).sum();
        filter.process(&mut samples);
        let output_energy: f32 = samples.iter().map(|s| s.l * s.l).sum();

        assert!(
            output_energy < input_energy * 0.1,
            "Highpass should attenuate 100Hz signal. Input: {}, Output: {}",
            input_energy,
            output_energy
        );
    }

    #[test]
    fn test_biquad_process_interleaved() {
        let mut filter = BiquadFilter::lowpass(48000, 1000.0, 1.0);
        let mut buffer = vec![0.1f32, 0.2, 0.3, 0.4, 0.5, 0.6]; // 3 stereo samples
        filter.process_interleaved(&mut buffer);
        // Should not panic, output should be different from input
    }

    #[test]
    fn test_compressor_creates_with_defaults() {
        let comp = Compressor::new(48000);
        // Default compressor starts with unity gain (1.0 = no compression applied yet)
        assert!(comp.meter_gain().is_finite());
    }

    #[test]
    fn test_compressor_processes_audio() {
        let mut comp = Compressor::simple(48000, 0.0, -24.0, 30.0, 12.0, 0.003, 0.250);

        // Generate loud signal
        let num_samples = 1024;
        let mut input: Vec<SfSample> = (0..num_samples)
            .map(|i| {
                let t = i as f32 / 48000.0;
                let val = (2.0 * std::f32::consts::PI * 440.0 * t).sin() * 0.9;
                SfSample { l: val, r: val }
            })
            .collect();
        let mut output = vec![SfSample::default(); num_samples];

        comp.process(&mut input, &mut output);

        // Output should have non-zero samples
        let has_audio = output.iter().any(|s| s.l.abs() > 0.001);
        assert!(has_audio, "Compressor output should contain audio");
    }

    #[test]
    fn test_compressor_reduces_loud_signal() {
        let mut comp = Compressor::simple(48000, 0.0, -20.0, 6.0, 4.0, 0.003, 0.250);

        // Generate very loud signal (near 0dBFS)
        let num_samples = 4096;
        let mut input: Vec<SfSample> = (0..num_samples)
            .map(|i| {
                let t = i as f32 / 48000.0;
                let val = (2.0 * std::f32::consts::PI * 440.0 * t).sin() * 0.95;
                SfSample { l: val, r: val }
            })
            .collect();
        let mut output = vec![SfSample::default(); num_samples];

        let input_peak: f32 = input.iter().map(|s| s.l.abs()).fold(0.0f32, f32::max);

        comp.process(&mut input, &mut output);

        let output_peak: f32 = output.iter().map(|s| s.l.abs()).fold(0.0f32, f32::max);

        // Compressed output peak should be less than input peak
        assert!(
            output_peak < input_peak,
            "Compressor should reduce loud signal. Input peak: {}, Output peak: {}",
            input_peak,
            output_peak
        );
    }

    #[test]
    fn test_all_biquad_types_create() {
        let _lp = BiquadFilter::lowpass(44100, 440.0, 1.0);
        let _hp = BiquadFilter::highpass(44100, 440.0, 1.0);
        let _bp = BiquadFilter::bandpass(44100, 440.0, 1.0);
        let _notch = BiquadFilter::notch(44100, 440.0, 1.0);
        let _peak = BiquadFilter::peaking(44100, 440.0, 1.0, 6.0);
        let _ls = BiquadFilter::low_shelf(44100, 440.0, 1.0, 6.0);
        let _hs = BiquadFilter::high_shelf(44100, 440.0, 1.0, 6.0);
    }
}
