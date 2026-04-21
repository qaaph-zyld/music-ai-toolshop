//! Disk streaming for large audio files
//!
//! Provides background read-ahead streaming to keep RAM usage low
//! for long audio files. Uses circular buffer with double-buffering.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::{spawn, JoinHandle};

/// Circular buffer for audio streaming
pub struct CircularBuffer {
    data: Vec<f32>,
    write_pos: usize,
    read_pos: usize,
    filled: usize,
    capacity: usize,
}

/// Disk-based audio streamer with read-ahead
pub struct DiskStreamer {
    file_path: String,
    _sample_rate: u32,
    _channels: u16,
    total_samples: usize,
    current_position: Arc<Mutex<usize>>,
    buffer: Arc<Mutex<CircularBuffer>>,
    is_running: Arc<AtomicBool>,
    read_thread: Option<JoinHandle<()>>,
}

/// Streamer configuration
pub struct StreamerConfig {
    pub buffer_size: usize,
    pub read_ahead_size: usize,
}

impl Default for StreamerConfig {
    fn default() -> Self {
        Self {
            buffer_size: 8192,      // ~170ms at 48kHz
            read_ahead_size: 4096,  // Read ahead samples
        }
    }
}

impl CircularBuffer {
    /// Create a new circular buffer with the specified capacity
    pub fn new(capacity: usize) -> Self {
        Self {
            data: vec![0.0f32; capacity],
            write_pos: 0,
            read_pos: 0,
            filled: 0,
            capacity,
        }
    }

    /// Write samples to the buffer
    /// Returns the number of samples written
    pub fn write(&mut self, samples: &[f32]) -> usize {
        let available = self.capacity - self.filled;
        let to_write = samples.len().min(available);

        for i in 0..to_write {
            self.data[self.write_pos] = samples[i];
            self.write_pos = (self.write_pos + 1) % self.capacity;
        }
        self.filled += to_write;
        to_write
    }

    /// Read samples from the buffer
    /// Returns the number of samples read
    pub fn read(&mut self, output: &mut [f32]) -> usize {
        let to_read = output.len().min(self.filled);

        for i in 0..to_read {
            output[i] = self.data[self.read_pos];
            self.read_pos = (self.read_pos + 1) % self.capacity;
        }
        self.filled -= to_read;
        to_read
    }

    /// Get the number of samples available to read
    pub fn available(&self) -> usize {
        self.filled
    }

    /// Check if the buffer is empty
    pub fn is_empty(&self) -> bool {
        self.filled == 0
    }

    /// Get buffer capacity
    pub fn capacity(&self) -> usize {
        self.capacity
    }

    /// Clear the buffer
    pub fn clear(&mut self) {
        self.write_pos = 0;
        self.read_pos = 0;
        self.filled = 0;
        self.data.fill(0.0f32);
    }
}

impl DiskStreamer {
    /// Create a new disk streamer
    pub fn new(file_path: &str, _config: StreamerConfig) -> Result<Self, String> {
        // For now, simplified implementation
        // In production, would parse WAV header to get sample_rate, channels, etc.

        Ok(Self {
            file_path: file_path.to_string(),
            _sample_rate: 48000,
            _channels: 2,
            total_samples: 0,
            current_position: Arc::new(Mutex::new(0)),
            buffer: Arc::new(Mutex::new(CircularBuffer::new(8192))),
            is_running: Arc::new(AtomicBool::new(false)),
            read_thread: None,
        })
    }

    /// Start the background read thread
    pub fn start(&mut self) -> Result<(), String> {
        if self.is_running.load(Ordering::SeqCst) {
            return Err("Streamer already running".to_string());
        }

        self.is_running.store(true, Ordering::SeqCst);
        let is_running = Arc::clone(&self.is_running);
        let _buffer = Arc::clone(&self.buffer);
        let _position = Arc::clone(&self.current_position);
        let _file_path = self.file_path.clone();

        // Spawn background read thread
        let handle = spawn(move || {
            while is_running.load(Ordering::SeqCst) {
                // Read ahead logic would go here
                // For now, just yield to prevent busy-waiting
                std::thread::sleep(std::time::Duration::from_millis(10));
            }
        });

        self.read_thread = Some(handle);
        Ok(())
    }

    /// Stop the streamer
    pub fn stop(&mut self) {
        self.is_running.store(false, Ordering::SeqCst);
        if let Some(handle) = self.read_thread.take() {
            let _ = handle.join();
        }
    }

    /// Read samples from the stream
    pub fn read_samples(&mut self, output: &mut [f32]) -> usize {
        if let Ok(mut buffer) = self.buffer.lock() {
            let read = buffer.read(output);
            if let Ok(mut pos) = self.current_position.lock() {
                *pos += read;
            }
            read
        } else {
            0
        }
    }

    /// Seek to a sample position
    pub fn seek(&mut self, sample_position: usize) -> Result<(), String> {
        if sample_position >= self.total_samples && self.total_samples > 0 {
            return Err("Seek position beyond end of file".to_string());
        }

        if let Ok(mut pos) = self.current_position.lock() {
            *pos = sample_position;
        }

        if let Ok(mut buffer) = self.buffer.lock() {
            buffer.clear();
        }

        Ok(())
    }

    /// Get current position in samples
    pub fn position(&self) -> usize {
        self.current_position.lock().map(|p| *p).unwrap_or(0)
    }

    /// Get file path
    pub fn file_path(&self) -> &str {
        &self.file_path
    }

    /// Check if streamer is running
    pub fn is_running(&self) -> bool {
        self.is_running.load(Ordering::SeqCst)
    }

    /// Get buffer fill level (0.0 to 1.0)
    pub fn buffer_fill_level(&self) -> f32 {
        if let Ok(buffer) = self.buffer.lock() {
            buffer.available() as f32 / buffer.capacity() as f32
        } else {
            0.0
        }
    }
}

impl Drop for DiskStreamer {
    fn drop(&mut self) {
        self.stop();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_circular_buffer_creation() {
        let buffer = CircularBuffer::new(1024);
        assert_eq!(buffer.capacity(), 1024);
        assert_eq!(buffer.available(), 0);
        assert!(buffer.is_empty());
    }

    #[test]
    fn test_circular_buffer_write_read() {
        let mut buffer = CircularBuffer::new(1024);
        let samples = vec![1.0f32, 2.0, 3.0, 4.0, 5.0];

        let written = buffer.write(&samples);
        assert_eq!(written, 5);
        assert_eq!(buffer.available(), 5);

        let mut output = vec![0.0f32; 5];
        let read = buffer.read(&mut output);
        assert_eq!(read, 5);
        assert_eq!(output, samples);
        assert!(buffer.is_empty());
    }

    #[test]
    fn test_circular_buffer_wraparound() {
        let mut buffer = CircularBuffer::new(4);
        let samples1 = vec![1.0f32, 2.0, 3.0];
        let samples2 = vec![4.0f32, 5.0, 6.0];

        buffer.write(&samples1);
        let mut temp = vec![0.0f32; 2];
        buffer.read(&mut temp); // Read 2 samples

        buffer.write(&samples2);

        let mut output = vec![0.0f32; 4];
        let read = buffer.read(&mut output);
        assert_eq!(read, 4);
        assert_eq!(output[0], 3.0); // Remaining from first write
        assert_eq!(output[1], 4.0); // Wrapped around
        assert_eq!(output[2], 5.0);
        assert_eq!(output[3], 6.0);
    }

    #[test]
    fn test_streamer_creation() {
        let streamer = DiskStreamer::new("test.wav", StreamerConfig::default());
        assert!(streamer.is_ok());
        let streamer = streamer.unwrap();
        assert_eq!(streamer.file_path(), "test.wav");
        assert!(!streamer.is_running());
    }

    #[test]
    fn test_streamer_start_stop() {
        let mut streamer = DiskStreamer::new("test.wav", StreamerConfig::default()).unwrap();
        assert!(!streamer.is_running());

        streamer.start().unwrap();
        assert!(streamer.is_running());

        streamer.stop();
        assert!(!streamer.is_running());
    }

    #[test]
    fn test_streamer_double_start_fails() {
        let mut streamer = DiskStreamer::new("test.wav", StreamerConfig::default()).unwrap();
        streamer.start().unwrap();
        let result = streamer.start();
        assert!(result.is_err());
    }

    #[test]
    fn test_streamer_seek() {
        let mut streamer = DiskStreamer::new("test.wav", StreamerConfig::default()).unwrap();
        streamer.seek(1000).unwrap();
        assert_eq!(streamer.position(), 1000);
    }

    #[test]
    fn test_streamer_buffer_fill_level() {
        let mut streamer = DiskStreamer::new("test.wav", StreamerConfig::default()).unwrap();
        let level = streamer.buffer_fill_level();
        assert_eq!(level, 0.0); // Initially empty
    }
}
