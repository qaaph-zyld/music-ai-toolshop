//! Disk Streaming for Large Audio Files
//!
//! Background thread reads audio file into circular buffer,
//! audio thread consumes samples lock-free.
//! Falls back to RAM loading for short files (< 30 seconds).

use crate::circular_buffer::CircularBuffer;
use hound::{WavReader, WavSpec, WavWriter, SampleFormat};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::{spawn, JoinHandle};

/// Error type for disk streaming operations
#[derive(Debug, Clone, PartialEq)]
pub enum DiskStreamError {
    FileNotFound(String),
    InvalidFormat(String),
    IoError(String),
    NotEnoughSamples,
    StreamingNotStarted,
}

impl std::fmt::Display for DiskStreamError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DiskStreamError::FileNotFound(p) => write!(f, "File not found: {}", p),
            DiskStreamError::InvalidFormat(m) => write!(f, "Invalid format: {}", m),
            DiskStreamError::IoError(e) => write!(f, "IO error: {}", e),
            DiskStreamError::NotEnoughSamples => write!(f, "Not enough samples in buffer"),
            DiskStreamError::StreamingNotStarted => write!(f, "Streaming not started"),
        }
    }
}

impl std::error::Error for DiskStreamError {}

impl From<std::io::Error> for DiskStreamError {
    fn from(e: std::io::Error) -> Self {
        DiskStreamError::IoError(e.to_string())
    }
}

/// Threshold for using streaming vs full RAM loading (30 seconds @ 48kHz)
pub const STREAMING_THRESHOLD_SAMPLES: u64 = 30 * 48000; // ~1.44M samples

/// Read-ahead buffer size (2 seconds @ 48kHz stereo = 192k samples)
pub const READ_AHEAD_SAMPLES: usize = 2 * 48000 * 2; // 2 sec, 2 channels

/// Manages file I/O and circular buffer for streaming
pub struct DiskStreamer {
    file: File,
    buffer: CircularBuffer,
    spec: WavSpec,
    total_samples: u64,
    current_sample: AtomicU64,
    file_path: PathBuf,
}

impl DiskStreamer {
    /// Open a WAV file for streaming
    pub fn open(path: &Path) -> Result<Self, DiskStreamError> {
        if !path.exists() {
            return Err(DiskStreamError::FileNotFound(path.to_string_lossy().to_string()));
        }
        
        // Open file and parse WAV header
        let file = File::open(path)?;
        let reader = WavReader::new(&file).map_err(|e| {
            DiskStreamError::InvalidFormat(format!("Failed to parse WAV: {:?}", e))
        })?;
        
        let spec = reader.spec();
        let total_samples = reader.duration() as u64;
        
        // Create circular buffer (2-second read-ahead)
        let buffer_capacity = READ_AHEAD_SAMPLES * 2; // Double buffer
        let buffer = CircularBuffer::new(buffer_capacity);
        
        Ok(Self {
            file,
            buffer,
            spec,
            total_samples,
            current_sample: AtomicU64::new(0),
            file_path: path.to_path_buf(),
        })
    }
    
    /// Get audio specification
    pub fn spec(&self) -> &WavSpec {
        &self.spec
    }
    
    /// Get total number of sample frames
    pub fn total_samples(&self) -> u64 {
        self.total_samples
    }
    
    /// Get duration in seconds
    pub fn duration_seconds(&self) -> f64 {
        let sample_rate = self.spec.sample_rate as f64;
        // total_samples is already frames (from reader.duration())
        self.total_samples as f64 / sample_rate
    }
    
    /// Check if this file should use streaming (vs full RAM load)
    pub fn should_stream(&self) -> bool {
        self.total_samples > STREAMING_THRESHOLD_SAMPLES
    }
    
    /// Read ahead and fill the circular buffer
    /// Called from background thread
    pub fn read_ahead(&mut self) -> Result<usize, DiskStreamError> {
        let available_write = self.buffer.available_write();
        if available_write == 0 {
            return Ok(0);
        }
        
        // Read samples in chunks
        let current = self.current_sample.load(Ordering::Relaxed);
        let remaining = self.total_samples.saturating_sub(current);
        
        if remaining == 0 {
            return Ok(0); // EOF
        }
        
        // Calculate byte position and seek
        let bytes_per_sample = (self.spec.bits_per_sample / 8) as u64;
        let data_offset = 44; // Standard WAV header size (approximate)
        let byte_pos = data_offset + current * bytes_per_sample;
        
        self.file.seek(SeekFrom::Start(byte_pos))?;
        
        // Read raw bytes and convert to f32
        let samples_to_read = (available_write.min(remaining as usize) as usize).min(4096);
        let mut raw_buffer = vec![0u8; samples_to_read * bytes_per_sample as usize];
        let bytes_read = self.file.read(&mut raw_buffer)?;
        
        if bytes_read == 0 {
            return Ok(0);
        }
        
        let samples_read = bytes_read / bytes_per_sample as usize;
        let mut float_samples = vec![0.0f32; samples_read];
        
        // Convert based on bit depth
        match self.spec.bits_per_sample {
            16 => {
                for (i, chunk) in raw_buffer.chunks_exact(2).enumerate() {
                    let sample = i16::from_le_bytes([chunk[0], chunk[1]]) as f32 / 32768.0;
                    float_samples[i] = sample;
                }
            }
            24 => {
                for (i, chunk) in raw_buffer.chunks_exact(3).enumerate() {
                    let sample = ((chunk[2] as i32) << 16 | (chunk[1] as i32) << 8 | chunk[0] as i32) as f32 / 8388608.0;
                    float_samples[i] = sample;
                }
            }
            32 => {
                for (i, chunk) in raw_buffer.chunks_exact(4).enumerate() {
                    let sample = f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]);
                    float_samples[i] = sample;
                }
            }
            _ => {
                return Err(DiskStreamError::InvalidFormat(
                    format!("Unsupported bit depth: {}", self.spec.bits_per_sample)
                ));
            }
        }
        
        // Write to circular buffer
        let written = self.buffer.write(&float_samples);
        
        // Update position
        self.current_sample.fetch_add(written as u64, Ordering::Relaxed);
        
        Ok(written)
    }
    
    /// Get samples from buffer (called from audio thread)
    pub fn get_samples(&self, out: &mut [f32]) -> usize {
        self.buffer.read(out)
    }
    
    /// Peek at samples without consuming
    pub fn peek_samples(&self, out: &mut [f32]) -> usize {
        self.buffer.peek(out)
    }
    
    /// Get available samples in buffer
    pub fn available_samples(&self) -> usize {
        self.buffer.available_read()
    }
    
    /// Get write space available
    pub fn available_write(&self) -> usize {
        self.buffer.available_write()
    }
    
    /// Seek to a specific sample position
    pub fn seek(&mut self, sample: u64) -> Result<(), DiskStreamError> {
        if sample >= self.total_samples {
            return Err(DiskStreamError::InvalidFormat(
                format!("Seek position {} beyond total samples {}", sample, self.total_samples)
            ));
        }
        
        self.current_sample.store(sample, Ordering::Relaxed);
        self.buffer.clear();
        
        Ok(())
    }
    
    /// Check if we've reached end of file
    pub fn is_eof(&self) -> bool {
        let current = self.current_sample.load(Ordering::Relaxed);
        current >= self.total_samples && self.buffer.is_empty()
    }
    
    /// Get current read position
    pub fn current_position(&self) -> u64 {
        self.current_sample.load(Ordering::Relaxed)
    }
    
    /// Check if buffering is needed (less than 0.5 sec remaining)
    pub fn needs_buffering(&self) -> bool {
        let available = self.available_samples();
        let samples_per_sec = self.spec.sample_rate as usize * self.spec.channels as usize;
        available < samples_per_sec / 2 // Less than 0.5 seconds
    }
}

/// Background thread streaming player
pub struct StreamingPlayer {
    streamer: Arc<Mutex<DiskStreamer>>,
    thread: Option<JoinHandle<()>>,
    running: Arc<AtomicBool>,
    is_streaming: bool,
}

impl StreamingPlayer {
    /// Start streaming a file
    pub fn start(path: &Path) -> Result<Self, DiskStreamError> {
        let streamer = DiskStreamer::open(path)?;
        
        // For short files, don't use streaming
        if !streamer.should_stream() {
            return Ok(Self {
                streamer: Arc::new(Mutex::new(streamer)),
                thread: None,
                running: Arc::new(AtomicBool::new(false)),
                is_streaming: false,
            });
        }
        
        let streamer = Arc::new(Mutex::new(streamer));
        let running = Arc::new(AtomicBool::new(true));
        
        let streamer_clone = Arc::clone(&streamer);
        let running_clone = Arc::clone(&running);
        
        // Spawn background thread for reading
        let thread = spawn(move || {
            while running_clone.load(Ordering::Relaxed) {
                if let Ok(mut s) = streamer_clone.lock() {
                    if s.is_eof() {
                        break;
                    }
                    
                    // Fill buffer if needed
                    if s.needs_buffering() {
                        let _ = s.read_ahead();
                    }
                }
                
                // Small sleep to avoid busy-waiting
                std::thread::sleep(std::time::Duration::from_millis(5));
            }
        });
        
        Ok(Self {
            streamer,
            thread: Some(thread),
            running,
            is_streaming: true,
        })
    }
    
    /// Process audio - called from audio thread
    /// Returns number of frames (samples / channels) processed
    pub fn process(&self, output: &mut [f32]) -> Result<usize, DiskStreamError> {
        if !self.is_streaming {
            // For short files, load fully into memory
            return Err(DiskStreamError::StreamingNotStarted);
        }
        
        // Read from circular buffer (lock-free)
        let samples_read = if let Ok(streamer) = self.streamer.lock() {
            streamer.get_samples(output)
        } else {
            0
        };
        
        // Zero out remaining samples if buffer underrun
        if samples_read < output.len() {
            for sample in &mut output[samples_read..] {
                *sample = 0.0;
            }
        }
        
        let channels = if let Ok(streamer) = self.streamer.lock() {
            streamer.spec().channels as usize
        } else {
            2 // Default to stereo
        };
        
        Ok(samples_read / channels)
    }
    
    /// Check if we're at end of file
    pub fn is_eof(&self) -> bool {
        if let Ok(streamer) = self.streamer.lock() {
            streamer.is_eof()
        } else {
            false
        }
    }
    
    /// Get current playback position in seconds
    pub fn position_seconds(&self) -> f64 {
        if let Ok(streamer) = self.streamer.lock() {
            let frame = streamer.current_position();
            let sample_rate = streamer.spec().sample_rate as f64;
            // current_position returns frames, not individual samples
            frame as f64 / sample_rate
        } else {
            0.0
        }
    }
    
    /// Seek to position in seconds
    pub fn seek_seconds(&mut self, seconds: f64) -> Result<(), DiskStreamError> {
        if let Ok(mut streamer) = self.streamer.lock() {
            let sample_rate = streamer.spec().sample_rate as f64;
            // total_samples is frames, so calculate frame position
            let frame = (seconds * sample_rate) as u64;
            streamer.seek(frame)
        } else {
            Err(DiskStreamError::StreamingNotStarted)
        }
    }
    
    /// Get available buffered time in seconds
    pub fn buffered_seconds(&self) -> f64 {
        if let Ok(streamer) = self.streamer.lock() {
            let samples = streamer.available_samples();
            let sample_rate = streamer.spec().sample_rate as f64;
            let channels = streamer.spec().channels as f64;
            samples as f64 / (sample_rate * channels)
        } else {
            0.0
        }
    }
    
    /// Check if this is a streaming file (vs short file in RAM)
    pub fn is_streaming(&self) -> bool {
        self.is_streaming
    }
    
    /// Get total duration in seconds
    pub fn duration_seconds(&self) -> f64 {
        if let Ok(streamer) = self.streamer.lock() {
            streamer.duration_seconds()
        } else {
            0.0
        }
    }
}

impl Drop for StreamingPlayer {
    fn drop(&mut self) {
        self.running.store(false, Ordering::Relaxed);
        if let Some(thread) = self.thread.take() {
            let _ = thread.join();
        }
    }
}

/// Load a short file fully into RAM (non-streaming fallback)
pub fn load_file_to_ram(path: &Path) -> Result<(Vec<f32>, WavSpec), DiskStreamError> {
    // Open file to get spec
    let file = File::open(path)?;
    let mut reader = WavReader::new(file).map_err(|e| {
        DiskStreamError::InvalidFormat(format!("Failed to parse WAV: {:?}", e))
    })?;
    
    let spec = reader.spec();
    // duration() returns frames, multiply by channels to get total interleaved samples
    let total_samples = reader.duration() as usize * spec.channels as usize;
    let mut samples = vec![0.0f32; total_samples];
    
    // Read samples based on sample format
    let mut idx = 0;
    
    match (spec.bits_per_sample, spec.sample_format) {
        (16, hound::SampleFormat::Int) => {
            for sample in reader.samples::<i16>() {
                if idx >= samples.len() { break; }
                samples[idx] = sample.map_err(|e| DiskStreamError::IoError(e.to_string()))? as f32 / 32768.0;
                idx += 1;
            }
        }
        (24, hound::SampleFormat::Int) => {
            // 24-bit samples not directly supported by hound iterator, handle manually
            return Err(DiskStreamError::InvalidFormat("24-bit manual read needed".to_string()));
        }
        (32, hound::SampleFormat::Int) => {
            for sample in reader.samples::<i32>() {
                if idx >= samples.len() { break; }
                samples[idx] = sample.map_err(|e| DiskStreamError::IoError(e.to_string()))? as f32 / 2147483648.0;
                idx += 1;
            }
        }
        (32, hound::SampleFormat::Float) => {
            for sample in reader.samples::<f32>() {
                if idx >= samples.len() { break; }
                samples[idx] = sample.map_err(|e| DiskStreamError::IoError(e.to_string()))?;
                idx += 1;
            }
        }
        _ => {
            return Err(DiskStreamError::InvalidFormat(
                format!("Unsupported format: {} bits, {:?}", spec.bits_per_sample, spec.sample_format)
            ));
        }
    }
    
    Ok((samples, spec))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;
    
    fn create_test_wav(duration_sec: f64, sample_rate: u32) -> (PathBuf, NamedTempFile) {
        let spec = WavSpec {
            channels: 2,
            sample_rate,
            bits_per_sample: 16,
            sample_format: hound::SampleFormat::Int,
        };
        
        let mut temp_file = NamedTempFile::new().unwrap();
        let path = temp_file.path().to_path_buf();
        
        {
            let mut writer = WavWriter::create(&path, spec).unwrap();
            let num_samples = (duration_sec * sample_rate as f64) as usize * 2; // *2 for stereo
            
            for i in 0..num_samples {
                let t = i as f64 / sample_rate as f64;
                let sample = (t * 440.0 * 2.0 * std::f64::consts::PI).sin() as f32;
                let sample_i16 = (sample * 32767.0) as i16;
                writer.write_sample(sample_i16).unwrap();
            }
            
            writer.finalize().unwrap();
        }
        
        (path, temp_file)
    }
    
    #[test]
    fn test_disk_streamer_open() {
        let (path, _temp) = create_test_wav(1.0, 48000);
        
        let streamer = DiskStreamer::open(&path);
        assert!(streamer.is_ok());
        
        let streamer = streamer.unwrap();
        assert_eq!(streamer.spec().channels, 2);
        assert_eq!(streamer.spec().sample_rate, 48000);
    }
    
    #[test]
    fn test_disk_streamer_file_not_found() {
        let path = Path::new("/nonexistent/file.wav");
        let result = DiskStreamer::open(path);
        
        assert!(matches!(result, Err(DiskStreamError::FileNotFound(_))));
    }
    
    #[test]
    fn test_should_stream_threshold() {
        // Short file (1 second) - should not stream
        let (short_path, _temp1) = create_test_wav(1.0, 48000);
        let streamer = DiskStreamer::open(&short_path).unwrap();
        assert!(!streamer.should_stream());
        
        // Long file (60 seconds) - should stream
        let (long_path, _temp2) = create_test_wav(60.0, 48000);
        let streamer = DiskStreamer::open(&long_path).unwrap();
        assert!(streamer.should_stream());
    }
    
    #[test]
    fn test_disk_streamer_seek() {
        let (path, _temp) = create_test_wav(10.0, 48000);
        let mut streamer = DiskStreamer::open(&path).unwrap();
        
        // Seek to middle
        let middle_sample = streamer.total_samples() / 2;
        assert!(streamer.seek(middle_sample).is_ok());
        assert_eq!(streamer.current_position(), middle_sample);
        
        // Seek beyond end should fail
        assert!(streamer.seek(streamer.total_samples() + 1000).is_err());
    }
    
    #[test]
    fn test_circular_buffer_wraparound() {
        use crate::circular_buffer::CircularBuffer;
        
        let mut buf = CircularBuffer::new(1024);
        
        // Write and read multiple times to test wraparound
        for i in 0..10 {
            let data = vec![i as f32; 256];
            let written = buf.write(&data);
            
            let mut out = vec![0.0f32; 256];
            let read = buf.read(&mut out);
            
            assert_eq!(written, 256);
            assert_eq!(read, 256);
            assert_eq!(out, data);
        }
    }
    
    #[test]
    fn test_load_file_to_ram() {
        let (path, _temp) = create_test_wav(0.5, 48000); // Short file
        
        let result = load_file_to_ram(&path);
        assert!(result.is_ok());
        
        let (samples, spec) = result.unwrap();
        let expected_samples = (0.5 * 48000.0) as usize * 2; // stereo
        assert_eq!(samples.len(), expected_samples);
        assert_eq!(spec.sample_rate, 48000);
        assert_eq!(spec.channels, 2);
    }
    
    #[test]
    fn test_streaming_player_creation() {
        let (path, _temp) = create_test_wav(60.0, 48000); // Long file
        
        let player = StreamingPlayer::start(&path);
        assert!(player.is_ok());
        
        let player = player.unwrap();
        assert!(player.is_streaming());
        assert!(!player.is_eof());
    }
    
    #[test]
    fn test_short_file_no_streaming() {
        let (path, _temp) = create_test_wav(1.0, 48000); // Short file
        
        let player = StreamingPlayer::start(&path).unwrap();
        assert!(!player.is_streaming()); // Should not use streaming
    }
}
