//! Audio export renderer
//!
//! Offline rendering engine for exporting projects to audio files.
//! Renders audio faster than realtime without audio device.

use crate::mixer::{AudioSource, Mixer};
use crate::transport::Transport;
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};

/// Export format
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ExportFormat {
    /// WAV audio format
    Wav,
    /// MP3 audio format (requires external encoder)
    Mp3 { quality: u32 },
}

/// Bit depth for export
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum BitDepth {
    /// 16-bit integer
    Bit16,
    /// 24-bit integer
    Bit24,
    /// 32-bit float
    Bit32,
}

impl BitDepth {
    /// Get bits as number
    pub fn bits(&self) -> u16 {
        match self {
            BitDepth::Bit16 => 16,
            BitDepth::Bit24 => 24,
            BitDepth::Bit32 => 32,
        }
    }
}

/// Export configuration
#[derive(Debug, Clone)]
pub struct ExportConfig {
    /// Export format
    pub format: ExportFormat,
    /// Sample rate in Hz
    pub sample_rate: u32,
    /// Bit depth
    pub bit_depth: BitDepth,
    /// Export stems (individual tracks)
    pub stem_export: bool,
    /// Output file path
    pub output_path: std::path::PathBuf,
    /// Start position in beats (None = from beginning)
    pub start_beat: Option<f32>,
    /// End position in beats (None = to end)
    pub end_beat: Option<f32>,
}

impl ExportConfig {
    /// Create default export config for WAV
    pub fn new_wav(path: impl AsRef<Path>) -> Self {
        Self {
            format: ExportFormat::Wav,
            sample_rate: 48000,
            bit_depth: BitDepth::Bit24,
            stem_export: false,
            output_path: path.as_ref().to_path_buf(),
            start_beat: None,
            end_beat: None,
        }
    }

    /// Set sample rate
    pub fn with_sample_rate(mut self, rate: u32) -> Self {
        self.sample_rate = rate;
        self
    }

    /// Set bit depth
    pub fn with_bit_depth(mut self, depth: BitDepth) -> Self {
        self.bit_depth = depth;
        self
    }

    /// Enable stem export
    pub fn with_stems(mut self) -> Self {
        self.stem_export = true;
        self
    }
}

/// Export progress callback
pub trait ExportProgress: Send + Sync {
    /// Called with progress updates
    fn on_progress(&self, current_sample: u64, total_samples: u64);
    /// Called when export completes
    fn on_complete(&self, result: &ExportResult);
    /// Return true to cancel export
    fn should_cancel(&self) -> bool;
}

/// Simple progress callback implementation
pub struct DefaultProgressCallback {
    cancel_flag: AtomicBool,
}

impl DefaultProgressCallback {
    /// Create new callback
    pub fn new() -> Self {
        Self {
            cancel_flag: AtomicBool::new(false),
        }
    }

    /// Request cancelation
    pub fn cancel(&self) {
        self.cancel_flag.store(true, Ordering::SeqCst);
    }
}

impl ExportProgress for DefaultProgressCallback {
    fn on_progress(&self, current: u64, total: u64) {
        let percent = (current as f64 / total as f64 * 100.0) as u8;
        println!("Export progress: {}% ({}/{} samples)", percent, current, total);
    }

    fn on_complete(&self, result: &ExportResult) {
        match result {
            ExportResult::Success => println!("Export completed successfully"),
            ExportResult::Cancelled => println!("Export cancelled"),
            ExportResult::Error(e) => println!("Export error: {}", e),
        }
    }

    fn should_cancel(&self) -> bool {
        self.cancel_flag.load(Ordering::SeqCst)
    }
}

/// Export result
#[derive(Debug, Clone, PartialEq)]
pub enum ExportResult {
    /// Export completed successfully
    Success,
    /// Export was cancelled
    Cancelled,
    /// Export failed with error
    Error(String),
}

/// Export renderer for offline audio rendering
pub struct ExportRenderer {
    transport: Transport,
    mixer: Mixer,
    config: ExportConfig,
}

impl ExportRenderer {
    /// Create new export renderer
    pub fn new(config: ExportConfig) -> Self {
        let transport = Transport::new(120.0, config.sample_rate);
        let mixer = Mixer::new(2); // Stereo output

        Self {
            transport,
            mixer,
            config,
        }
    }

    /// Add audio source to mixer
    pub fn add_source(&mut self, source: Box<dyn AudioSource>) {
        self.mixer.add_source(source);
    }

    /// Set tempo
    pub fn set_tempo(&mut self, tempo: f32) {
        self.transport.set_tempo(tempo);
    }

    /// Export project to audio file
    pub fn export(&mut self, progress: &dyn ExportProgress) -> ExportResult {
        match self.config.format {
            ExportFormat::Wav => self.export_wav(progress),
            ExportFormat::Mp3 { quality } => self.export_mp3(quality, progress),
        }
    }

    /// Export to WAV file
    fn export_wav(&mut self, progress: &dyn ExportProgress) -> ExportResult {
        use hound::{WavSpec, WavWriter};

        // Calculate total samples to render
        let start_beat = self.config.start_beat.unwrap_or(0.0);
        let end_beat = self.config.end_beat.unwrap_or(64.0); // Default 64 beats
        let duration_beats = end_beat - start_beat;
        let tempo = self.transport.tempo();
        let duration_seconds = duration_beats * 60.0 / tempo;
        let total_samples = (duration_seconds * self.config.sample_rate as f32) as u64;

        // Set up WAV writer
        let spec = WavSpec {
            channels: 2,
            sample_rate: self.config.sample_rate,
            bits_per_sample: self.config.bit_depth.bits(),
            sample_format: hound::SampleFormat::Int,
        };

        let mut writer = match WavWriter::create(&self.config.output_path, spec) {
            Ok(w) => w,
            Err(e) => return ExportResult::Error(format!("Failed to create WAV file: {}", e)),
        };

        // Set initial position
        self.transport.set_position(start_beat);
        self.transport.play();

        // Render in chunks
        const CHUNK_SIZE: usize = 1024;
        let mut current_sample: u64 = 0;

        while current_sample < total_samples {
            // Check for cancelation
            if progress.should_cancel() {
                return ExportResult::Cancelled;
            }

            // Calculate chunk size
            let remaining = total_samples - current_sample;
            let this_chunk = CHUNK_SIZE.min(remaining as usize);

            // Render audio
            let mut buffer = vec![0.0f32; this_chunk * 2]; // Stereo
            self.mixer.process(&mut buffer);

            // Write samples to WAV
            for sample in &buffer {
                let int_sample = self.float_to_int(*sample);
                if let Err(e) = writer.write_sample(int_sample) {
                    return ExportResult::Error(format!("Failed to write sample: {}", e));
                }
            }

            // Update transport position
            self.transport.process(this_chunk as u32 / 2); // Divide by channels

            current_sample += this_chunk as u64;
            progress.on_progress(current_sample, total_samples);
        }

        // Finalize WAV file
        if let Err(e) = writer.finalize() {
            return ExportResult::Error(format!("Failed to finalize WAV: {}", e));
        }

        ExportResult::Success
    }

    /// Export stems (individual tracks)
    pub fn export_stems(&mut self, progress: &dyn ExportProgress) -> Vec<(String, ExportResult)> {
        let mut results = Vec::new();

        // For each source, export individually
        for i in 0..self.mixer.source_count() {
            // Create stem filename
            let stem_name = format!("stem_{}.wav", i);
            let stem_path = self
                .config
                .output_path
                .parent()
                .unwrap_or(std::path::Path::new("."))
                .join(&stem_name);

            // Configure for stem export
            let mut stem_config = self.config.clone();
            stem_config.output_path = stem_path.clone();
            stem_config.stem_export = false;

            // Create renderer for this stem only
            let mut stem_renderer = ExportRenderer::new(stem_config);
            // TODO: Add only this source to stem renderer

            let result = stem_renderer.export(progress);
            results.push((stem_name, result));
        }

        results
    }

    /// Export to MP3 (placeholder - requires external encoder)
    fn export_mp3(&mut self, _quality: u32, progress: &dyn ExportProgress) -> ExportResult {
        // First export to temporary WAV
        let temp_wav = self.config.output_path.with_extension("temp.wav");
        let mut temp_config = self.config.clone();
        temp_config.format = ExportFormat::Wav;
        temp_config.output_path = temp_wav.clone();

        let mut temp_renderer = ExportRenderer::new(temp_config);
        // Copy sources
        // TODO: This needs proper implementation

        let wav_result = temp_renderer.export(progress);
        if !matches!(wav_result, ExportResult::Success) {
            return wav_result;
        }

        // Then convert to MP3 using external encoder
        // This is a placeholder - actual implementation would call lame/ffmpeg
        ExportResult::Error(
            "MP3 export requires external encoder (lame/ffmpeg). Not yet implemented.".to_string(),
        )
    }

    /// Convert float sample to integer based on bit depth
    fn float_to_int(&self, sample: f32) -> i32 {
        let clamped = sample.clamp(-1.0, 1.0);
        match self.config.bit_depth {
            BitDepth::Bit16 => (clamped * 32767.0) as i32,
            BitDepth::Bit24 => (clamped * 8388607.0) as i32,
            BitDepth::Bit32 => (clamped * 2147483647.0) as i32,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::generators::SineWave;
    use tempfile::tempdir;

    #[test]
    fn test_export_config_creation() {
        let config = ExportConfig::new_wav("test.wav");
        assert_eq!(config.format, ExportFormat::Wav);
        assert_eq!(config.sample_rate, 48000);
        assert_eq!(config.bit_depth, BitDepth::Bit24);
        assert!(!config.stem_export);
    }

    #[test]
    fn test_export_config_builder() {
        let config = ExportConfig::new_wav("test.wav")
            .with_sample_rate(44100)
            .with_bit_depth(BitDepth::Bit16)
            .with_stems();

        assert_eq!(config.sample_rate, 44100);
        assert_eq!(config.bit_depth, BitDepth::Bit16);
        assert!(config.stem_export);
    }

    #[test]
    fn test_bit_depth_bits() {
        assert_eq!(BitDepth::Bit16.bits(), 16);
        assert_eq!(BitDepth::Bit24.bits(), 24);
        assert_eq!(BitDepth::Bit32.bits(), 32);
    }

    #[test]
    fn test_export_renderer_creation() {
        let config = ExportConfig::new_wav("test.wav");
        let renderer = ExportRenderer::new(config);
        assert_eq!(renderer.transport.sample_rate(), 48000);
    }

    #[test]
    fn test_export_wav_success() {
        let dir = tempdir().unwrap();
        let output_path = dir.path().join("test_export.wav");

        let config = ExportConfig::new_wav(&output_path)
            .with_sample_rate(48000)
            .with_bit_depth(BitDepth::Bit16);

        let mut renderer = ExportRenderer::new(config);
        let sine = SineWave::new(440.0, 0.5);
        renderer.add_source(Box::new(sine));

        let progress = DefaultProgressCallback::new();
        let result = renderer.export(&progress);

        assert!(matches!(result, ExportResult::Success));
        assert!(output_path.exists());

        // Verify it's a valid WAV file
        let reader = hound::WavReader::open(&output_path).unwrap();
        assert_eq!(reader.spec().sample_rate, 48000);
        assert_eq!(reader.spec().bits_per_sample, 16);
        assert_eq!(reader.spec().channels, 2);
    }

    #[test]
    fn test_export_cancellation() {
        let dir = tempdir().unwrap();
        let output_path = dir.path().join("cancelled.wav");

        let config = ExportConfig::new_wav(&output_path);
        let mut renderer = ExportRenderer::new(config);

        let progress = DefaultProgressCallback::new();
        progress.cancel();

        let result = renderer.export(&progress);
        assert!(matches!(result, ExportResult::Cancelled));
    }

    #[test]
    fn test_export_with_custom_range() {
        let dir = tempdir().unwrap();
        let output_path = dir.path().join("range_test.wav");

        let mut config = ExportConfig::new_wav(&output_path);
        config.start_beat = Some(0.0);
        config.end_beat = Some(4.0); // 4 beats at 120 BPM = 2 seconds

        let mut renderer = ExportRenderer::new(config);
        renderer.set_tempo(120.0);
        let sine = SineWave::new(440.0, 0.5);
        renderer.add_source(Box::new(sine));

        let progress = DefaultProgressCallback::new();
        let result = renderer.export(&progress);

        assert!(matches!(result, ExportResult::Success));

        // Verify file size corresponds to ~2 seconds of audio
        let reader = hound::WavReader::open(&output_path).unwrap();
        let duration = reader.duration() as f32 / reader.spec().sample_rate as f32;
        assert!((duration - 2.0).abs() < 0.1); // Within 0.1 seconds
    }

    #[test]
    fn test_float_to_int_conversion() {
        let config = ExportConfig::new_wav("test.wav").with_bit_depth(BitDepth::Bit16);
        let renderer = ExportRenderer::new(config);

        assert_eq!(renderer.float_to_int(0.0), 0);
        assert_eq!(renderer.float_to_int(1.0), 32767);
        assert_eq!(renderer.float_to_int(-1.0), -32767);
    }

    #[test]
    fn test_export_result_variants() {
        let success = ExportResult::Success;
        let cancelled = ExportResult::Cancelled;
        let error = ExportResult::Error("test error".to_string());

        assert!(matches!(success, ExportResult::Success));
        assert!(matches!(cancelled, ExportResult::Cancelled));
        assert!(matches!(error, ExportResult::Error(_)));
    }
}
