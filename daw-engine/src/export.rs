//! Audio Export Engine
//!
//! Offline audio rendering and export to WAV/MP3 formats.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::path::Path;

use crate::transport::{Transport, TransportState};
use crate::mixer::Mixer;
use crate::session::SessionView;

/// Bit depth for WAV export
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum BitDepth {
    Bit16,
    Bit24,
    Bit32Float,
}

impl BitDepth {
    /// Get hound sample format
    fn to_hound_format(&self) -> hound::SampleFormat {
        match self {
            BitDepth::Bit16 | BitDepth::Bit24 => hound::SampleFormat::Int,
            BitDepth::Bit32Float => hound::SampleFormat::Float,
        }
    }

    /// Get bits per sample
    fn bits_per_sample(&self) -> u16 {
        match self {
            BitDepth::Bit16 => 16,
            BitDepth::Bit24 => 24,
            BitDepth::Bit32Float => 32,
        }
    }
}

/// Export format
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ExportFormat {
    Wav(BitDepth),
    OggVorbis(f32), // Quality factor 0.0-1.0
}

/// Progress callback type
pub type ProgressCallback = Box<dyn Fn(f64) + Send>;

/// Export engine for offline rendering
pub struct ExportEngine {
    sample_rate: u32,
    channels: u16,
    format: ExportFormat,
    transport: Transport,
    mixer: Mixer,
    _session: SessionView,
    progress_callback: Option<ProgressCallback>,
    cancel_flag: Arc<AtomicBool>,
    total_samples: u64,
    _processed_samples: Arc<AtomicBool>, // Use AtomicU64 when stabilized
}

impl ExportEngine {
    /// Create new export engine
    pub fn new(
        sample_rate: u32,
        channels: u16,
        format: ExportFormat,
        transport: Transport,
        mixer: Mixer,
        session: SessionView,
    ) -> Self {
        Self {
            sample_rate,
            channels,
            format,
            transport,
            mixer,
            _session: session,
            progress_callback: None,
            cancel_flag: Arc::new(AtomicBool::new(false)),
            total_samples: 0,
            _processed_samples: Arc::new(AtomicBool::new(false)),
        }
    }

    /// Set progress callback
    pub fn set_progress_callback(&mut self, callback: ProgressCallback) {
        self.progress_callback = Some(callback);
    }

    /// Get cancel flag for external cancellation
    pub fn cancel_flag(&self) -> Arc<AtomicBool> {
        Arc::clone(&self.cancel_flag)
    }

    /// Calculate total samples to render
    fn calculate_total_samples(&self, start_beat: f32, end_beat: f32) -> u64 {
        let beats = (end_beat - start_beat).max(0.0);
        let seconds = beats * 60.0 / self.transport.tempo();
        (seconds * self.sample_rate as f32) as u64 * self.channels as u64
    }

    /// Export to WAV file
    pub fn export_wav(
        &mut self,
        file_path: &Path,
        start_beat: f32,
        end_beat: f32,
    ) -> Result<(), ExportError> {
        let bit_depth = match self.format {
            ExportFormat::Wav(depth) => depth,
            _ => return Err(ExportError::IoError(
                std::io::Error::new(std::io::ErrorKind::InvalidInput, "Invalid format for WAV export")
            )),
        };

        // Calculate total samples
        self.total_samples = self.calculate_total_samples(start_beat, end_beat);

        // Setup WAV writer
        let spec = hound::WavSpec {
            channels: self.channels,
            sample_rate: self.sample_rate,
            bits_per_sample: bit_depth.bits_per_sample(),
            sample_format: bit_depth.to_hound_format(),
        };

        let mut writer = hound::WavWriter::create(file_path, spec)
            .map_err(|e| ExportError::WavError(e))?;

        // Set transport to start position
        self.transport.set_position(start_beat);
        self.transport.play();

        // Render in chunks
        let chunk_size = 1024;
        let mut total_processed = 0u64;

        while self.transport.position_beats() < end_beat {
            // Check cancellation
            if self.cancel_flag.load(Ordering::Relaxed) {
                return Err(ExportError::Cancelled);
            }

            // Process transport
            self.transport.process(chunk_size as u32);

            // Process audio through mixer
            let mut buffer = vec![0.0f32; chunk_size * self.channels as usize];
            self.mixer.process(&mut buffer);

            // Write samples to WAV
            for sample in &buffer {
                match bit_depth {
                    BitDepth::Bit16 => {
                        let int_sample = (sample * 32767.0).clamp(-32768.0, 32767.0) as i16;
                        writer.write_sample(int_sample)
                            .map_err(|e| ExportError::WavError(e))?;
                    }
                    BitDepth::Bit24 => {
                        let int_sample = (sample * 8388607.0).clamp(-8388608.0, 8388607.0) as i32;
                        writer.write_sample(int_sample)
                            .map_err(|e| ExportError::WavError(e))?;
                    }
                    BitDepth::Bit32Float => {
                        writer.write_sample(*sample)
                            .map_err(|e| ExportError::WavError(e))?;
                    }
                }
            }

            total_processed += buffer.len() as u64;

            // Report progress
            if let Some(ref callback) = self.progress_callback {
                if self.total_samples > 0 {
                    let progress = (total_processed as f64 / self.total_samples as f64).min(1.0);
                    callback(progress);
                }
            }

            // Check if transport stopped (reached end)
            if self.transport.state() == TransportState::Stopped {
                break;
            }
        }

        // Finalize WAV file
        writer.finalize()
            .map_err(|e| ExportError::WavError(e))?;

        Ok(())
    }

    /// Export to OGG Vorbis file
    /// 
    /// NOTE: OGG export requires libvorbis to be installed on the system.
    /// This is a stub that returns NotImplemented until vorbis encoding is configured.
    pub fn export_ogg(
        &mut self,
        _file_path: &Path,
        _start_beat: f32,
        _end_beat: f32,
    ) -> Result<(), ExportError> {
        // OGG Vorbis encoding requires libvorbis C library
        // For now, return NotImplemented - can be enabled with vorbis-encoder crate
        Err(ExportError::IoError(
            std::io::Error::new(
                std::io::ErrorKind::NotFound, 
                "OGG Vorbis encoding requires libvorbis. Install vorbis dev libraries or enable 'ogg' feature."
            )
        ))
    }

    /// Cancel export
    pub fn cancel(&self) {
        self.cancel_flag.store(true, Ordering::Relaxed);
    }
}

/// Export error types
#[derive(Debug)]
pub enum ExportError {
    WavError(hound::Error),
    IoError(std::io::Error),
    Cancelled,
}

impl std::fmt::Display for ExportError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ExportError::WavError(e) => write!(f, "WAV error: {}", e),
            ExportError::IoError(e) => write!(f, "IO error: {}", e),
            ExportError::Cancelled => write!(f, "Export cancelled"),
        }
    }
}

impl std::error::Error for ExportError {}

impl From<hound::Error> for ExportError {
    fn from(e: hound::Error) -> Self {
        ExportError::WavError(e)
    }
}

impl From<std::io::Error> for ExportError {
    fn from(e: std::io::Error) -> Self {
        ExportError::IoError(e)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::generators::SineWave;
    use crate::mixer::AudioSource;

    #[test]
    fn test_export_engine_creation() {
        let transport = Transport::new(120.0, 48000);
        let mixer = Mixer::new(2);
        let session = SessionView::new(8, 16);

        let engine = ExportEngine::new(
            48000,
            2,
            ExportFormat::Wav(BitDepth::Bit16),
            transport,
            mixer,
            session,
        );

        assert_eq!(engine.sample_rate, 48000);
        assert_eq!(engine.channels, 2);
        assert!(!engine.cancel_flag.load(Ordering::Relaxed));
    }

    #[test]
    fn test_bit_depth_properties() {
        assert_eq!(BitDepth::Bit16.bits_per_sample(), 16);
        assert_eq!(BitDepth::Bit24.bits_per_sample(), 24);
        assert_eq!(BitDepth::Bit32Float.bits_per_sample(), 32);

        assert_eq!(BitDepth::Bit16.to_hound_format(), hound::SampleFormat::Int);
        assert_eq!(BitDepth::Bit32Float.to_hound_format(), hound::SampleFormat::Float);
    }

    #[test]
    fn test_export_wav_16bit() {
        let mut transport = Transport::new(120.0, 48000);
        let mut mixer = Mixer::new(2);
        let session = SessionView::new(8, 16);

        // Add a sine wave source
        let sine = SineWave::new(440.0, 0.5);
        mixer.add_source(Box::new(sine));

        let mut engine = ExportEngine::new(
            48000,
            2,
            ExportFormat::Wav(BitDepth::Bit16),
            transport,
            mixer,
            session,
        );

        // Create temp file
        let temp_file = tempfile::NamedTempFile::with_suffix(".wav").unwrap();
        let path = temp_file.path();

        // Export 1 beat at 120 BPM = 0.5 seconds
        let result = engine.export_wav(path, 0.0, 1.0);
        assert!(result.is_ok(), "Export failed: {:?}", result);

        // Verify file was created
        assert!(path.exists());
        assert!(path.metadata().unwrap().len() > 0);

        // Verify it's a valid WAV file
        let reader = hound::WavReader::open(path).unwrap();
        assert_eq!(reader.spec().sample_rate, 48000);
        assert_eq!(reader.spec().channels, 2);
        assert_eq!(reader.spec().bits_per_sample, 16);
    }

    #[test]
    fn test_export_wav_24bit() {
        let transport = Transport::new(120.0, 48000);
        let mut mixer = Mixer::new(2);
        let session = SessionView::new(8, 16);

        let sine = SineWave::new(440.0, 0.5);
        mixer.add_source(Box::new(sine));

        let mut engine = ExportEngine::new(
            48000,
            2,
            ExportFormat::Wav(BitDepth::Bit24),
            transport,
            mixer,
            session,
        );

        let temp_file = tempfile::NamedTempFile::with_suffix(".wav").unwrap();
        let path = temp_file.path();

        let result = engine.export_wav(path, 0.0, 0.5);
        assert!(result.is_ok());

        let reader = hound::WavReader::open(path).unwrap();
        assert_eq!(reader.spec().bits_per_sample, 24);
    }

    #[test]
    fn test_export_wav_32bit_float() {
        let transport = Transport::new(120.0, 48000);
        let mut mixer = Mixer::new(2);
        let session = SessionView::new(8, 16);

        let sine = SineWave::new(440.0, 0.5);
        mixer.add_source(Box::new(sine));

        let mut engine = ExportEngine::new(
            48000,
            2,
            ExportFormat::Wav(BitDepth::Bit32Float),
            transport,
            mixer,
            session,
        );

        let temp_file = tempfile::NamedTempFile::with_suffix(".wav").unwrap();
        let path = temp_file.path();

        let result = engine.export_wav(path, 0.0, 0.5);
        assert!(result.is_ok());

        let reader = hound::WavReader::open(path).unwrap();
        assert_eq!(reader.spec().bits_per_sample, 32);
        assert_eq!(reader.spec().sample_format, hound::SampleFormat::Float);
    }

    #[test]
    fn test_export_progress_callback() {
        let transport = Transport::new(120.0, 48000);
        let mut mixer = Mixer::new(2);
        let session = SessionView::new(8, 16);

        let sine = SineWave::new(440.0, 0.5);
        mixer.add_source(Box::new(sine));

        let mut engine = ExportEngine::new(
            48000,
            2,
            ExportFormat::Wav(BitDepth::Bit16),
            transport,
            mixer,
            session,
        );

        // Track progress
        let progress_values = Arc::new(std::sync::Mutex::new(Vec::new()));
        let progress_clone = Arc::clone(&progress_values);

        engine.set_progress_callback(Box::new(move |p| {
            progress_clone.lock().unwrap().push(p);
        }));

        let temp_file = tempfile::NamedTempFile::with_suffix(".wav").unwrap();
        let path = temp_file.path();

        // Export 4 beats to get multiple progress updates
        let result = engine.export_wav(path, 0.0, 4.0);
        assert!(result.is_ok());

        // Verify progress was reported
        let values = progress_values.lock().unwrap();
        assert!(!values.is_empty(), "Progress callback should have been called");
        // Last value should be close to 1.0 (complete)
        if let Some(&last) = values.last() {
            assert!(last > 0.9, "Final progress should be > 0.9, got {}", last);
        }
    }

    #[test]
    fn test_export_cancellation() {
        let transport = Transport::new(120.0, 48000);
        let mut mixer = Mixer::new(2);
        let session = SessionView::new(8, 16);

        let sine = SineWave::new(440.0, 0.5);
        mixer.add_source(Box::new(sine));

        let mut engine = ExportEngine::new(
            48000,
            2,
            ExportFormat::Wav(BitDepth::Bit16),
            transport,
            mixer,
            session,
        );

        // Cancel immediately
        engine.cancel();

        let temp_file = tempfile::NamedTempFile::with_suffix(".wav").unwrap();
        let path = temp_file.path();

        let result = engine.export_wav(path, 0.0, 10.0);
        assert!(result.is_err());

        match result {
            Err(ExportError::Cancelled) => (), // Expected
            _ => panic!("Expected cancellation error"),
        }
    }

    #[test]
    fn test_calculate_total_samples() {
        let transport = Transport::new(120.0, 48000);
        let mixer = Mixer::new(2);
        let session = SessionView::new(8, 16);

        let engine = ExportEngine::new(
            48000,
            2, // stereo
            ExportFormat::Wav(BitDepth::Bit16),
            transport,
            mixer,
            session,
        );

        // 1 beat at 120 BPM = 0.5 seconds
        // 0.5 seconds * 48000 samples/sec * 2 channels = 48000 samples
        let samples = engine.calculate_total_samples(0.0, 1.0);
        assert_eq!(samples, 48000);

        // 4 beats = 2 seconds = 192000 samples (stereo)
        let samples = engine.calculate_total_samples(0.0, 4.0);
        assert_eq!(samples, 192000);
    }

    #[test]
    fn test_export_error_display() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file not found");
        let err = ExportError::IoError(io_err);

        let display = format!("{}", err);
        assert!(display.contains("IO error"));
    }

    #[test]
    fn test_empty_mixer_export() {
        // Export with no sources - should create valid but silent file
        let transport = Transport::new(120.0, 48000);
        let mixer = Mixer::new(2);
        let session = SessionView::new(8, 16);

        let mut engine = ExportEngine::new(
            48000,
            2,
            ExportFormat::Wav(BitDepth::Bit16),
            transport,
            mixer,
            session,
        );

        let temp_file = tempfile::NamedTempFile::with_suffix(".wav").unwrap();
        let path = temp_file.path();

        let result = engine.export_wav(path, 0.0, 1.0);
        assert!(result.is_ok());

        // Verify file is valid
        let mut reader = hound::WavReader::open(path).unwrap();
        assert_eq!(reader.spec().sample_rate, 48000);

        // All samples should be silent (0)
        let samples: Vec<i16> = reader.samples().collect::<Result<Vec<_>, _>>().unwrap();
        assert!(samples.iter().all(|&s| s == 0));
    }

    #[test]
    fn test_ogg_export_creation() {
        let transport = Transport::new(120.0, 48000);
        let mixer = Mixer::new(2);
        let session = SessionView::new(8, 16);

        let engine = ExportEngine::new(
            48000,
            2,
            ExportFormat::OggVorbis(0.5), // Quality 0.5
            transport,
            mixer,
            session,
        );

        assert_eq!(engine.sample_rate, 48000);
        match engine.format {
            ExportFormat::OggVorbis(q) => assert_eq!(q, 0.5),
            _ => panic!("Expected OggVorbis format"),
        }
    }

    #[test]
    fn test_export_ogg_vorbis_stub() {
        let transport = Transport::new(120.0, 48000);
        let mut mixer = Mixer::new(2);
        let session = SessionView::new(8, 16);

        // Add a sine wave source
        let sine = SineWave::new(440.0, 0.5);
        mixer.add_source(Box::new(sine));

        let mut engine = ExportEngine::new(
            48000,
            2,
            ExportFormat::OggVorbis(0.7),
            transport,
            mixer,
            session,
        );

        let temp_file = tempfile::NamedTempFile::with_suffix(".ogg").unwrap();
        let path = temp_file.path();

        // Export should return NotImplemented error (stub)
        let result = engine.export_ogg(path, 0.0, 1.0);
        assert!(result.is_err());
        
        match result {
            Err(ExportError::IoError(e)) => {
                assert!(e.to_string().contains("libvorbis") || e.kind() == std::io::ErrorKind::NotFound,
                    "Expected libvorbis not found error");
            }
            _ => panic!("Expected IO error for OGG stub"),
        }
    }

    #[test]
    fn test_ogg_stub_with_progress_callback() {
        let transport = Transport::new(120.0, 48000);
        let mut mixer = Mixer::new(2);
        let session = SessionView::new(8, 16);

        let sine = SineWave::new(440.0, 0.5);
        mixer.add_source(Box::new(sine));

        let mut engine = ExportEngine::new(
            48000,
            2,
            ExportFormat::OggVorbis(0.5),
            transport,
            mixer,
            session,
        );

        // Set up progress callback (won't be called for stub)
        let progress_called = Arc::new(std::sync::Mutex::new(false));
        let progress_clone = Arc::clone(&progress_called);

        engine.set_progress_callback(Box::new(move |_p| {
            *progress_clone.lock().unwrap() = true;
        }));

        let temp_file = tempfile::NamedTempFile::with_suffix(".ogg").unwrap();
        let path = temp_file.path();

        // Export should fail immediately as stub
        let result = engine.export_ogg(path, 0.0, 4.0);
        assert!(result.is_err());
        
        // Progress callback should not have been called for stub
        assert!(!*progress_called.lock().unwrap(), "Progress should not be called for stub");
    }

    #[test]
    fn test_ogg_stub_cancellation() {
        let transport = Transport::new(120.0, 48000);
        let mut mixer = Mixer::new(2);
        let session = SessionView::new(8, 16);

        let sine = SineWave::new(440.0, 0.5);
        mixer.add_source(Box::new(sine));

        let mut engine = ExportEngine::new(
            48000,
            2,
            ExportFormat::OggVorbis(0.5),
            transport,
            mixer,
            session,
        );

        // Cancel flag set but stub returns error before checking it
        engine.cancel();

        let temp_file = tempfile::NamedTempFile::with_suffix(".ogg").unwrap();
        let path = temp_file.path();

        let result = engine.export_ogg(path, 0.0, 10.0);
        assert!(result.is_err());

        // Stub returns IO error, not Cancelled
        match result {
            Err(ExportError::IoError(_)) => (), // Expected - stub error
            _ => panic!("Expected IO error for OGG stub"),
        }
    }
}
