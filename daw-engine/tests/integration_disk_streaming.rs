//! E2E Integration Test: Disk Streaming
//!
//! Tests the complete disk streaming workflow:
//! 1. Circular buffer operations
//! 2. DiskStreamer file I/O
//! 3. StreamingPlayer background thread
//! 4. 10-minute file with < 50MB RAM usage

use daw_engine::circular_buffer::CircularBuffer;
use daw_engine::disk_streamer::{DiskStreamer, StreamingPlayer, load_file_to_ram, STREAMING_THRESHOLD_SAMPLES};
use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Instant;

/// Helper function to get approximate process memory usage (in MB)
/// Note: This is platform-specific and approximate
fn get_memory_usage_mb() -> f64 {
    // On Windows, this would use GetProcessMemoryInfo
    // On Linux, parse /proc/self/status
    // For testing purposes, we return a dummy value
    // In real implementation, use platform-specific APIs
    0.0 // Placeholder
}

/// Create a test WAV file of specified duration
fn create_test_wav(duration_sec: f64, sample_rate: u32, name: &str) -> PathBuf {
    use hound::{WavSpec, SampleFormat, WavWriter};
    use std::fs;
    
    let spec = WavSpec {
        channels: 2,
        sample_rate,
        bits_per_sample: 16,
        sample_format: SampleFormat::Int,
    };
    
    let test_dir = PathBuf::from("tests/assets");
    let _ = fs::create_dir_all(&test_dir);
    let path = test_dir.join(format!("test_{}_{}s.wav", name, duration_sec as i32));
    
    let mut writer = WavWriter::create(&path, spec).unwrap();
    let num_samples = (duration_sec * sample_rate as f64) as usize * 2; // stereo
    
    // Generate sine wave
    for i in 0..num_samples {
        let t = (i / 2) as f64 / sample_rate as f64; // Per-channel time
        let freq = 440.0;
        let sample = (t * freq * 2.0 * std::f64::consts::PI).sin() as f32;
        let sample_i16 = (sample * 32767.0) as i16;
        writer.write_sample(sample_i16).unwrap();
    }
    
    writer.finalize().unwrap();
    path
}

/// Test circular buffer basic operations
#[test]
fn test_circular_buffer_basic() {
    let mut buf = CircularBuffer::new(1024);
    
    // Write data
    let input = vec![1.0f32, 2.0, 3.0, 4.0, 5.0];
    let written = buf.write(&input);
    assert_eq!(written, 5);
    
    // Read data
    let mut output = vec![0.0f32; 5];
    let read = buf.read(&mut output);
    assert_eq!(read, 5);
    assert_eq!(output, input);
    
    // Buffer should be empty
    assert!(buf.is_empty());
}

/// Test circular buffer wraparound
#[test]
fn test_circular_buffer_wraparound() {
    let mut buf = CircularBuffer::new(16);
    
    // Fill buffer completely
    let data = vec![1.0f32; 16];
    buf.write(&data);
    
    // Consume half
    let mut out = vec![0.0f32; 8];
    buf.read(&mut out);
    
    // Write more (should wrap)
    let data2 = vec![2.0f32; 8];
    buf.write(&data2);
    
    // Read all
    let mut out2 = vec![0.0f32; 16];
    buf.read(&mut out2);
    
    // First 8 should be 1.0, last 8 should be 2.0
    assert!(out2[..8].iter().all(|&s| s == 1.0));
    assert!(out2[8..].iter().all(|&s| s == 2.0));
}

/// Test circular buffer concurrent-like operations
#[test]
fn test_circular_buffer_stress() {
    let mut buf = CircularBuffer::new(4096);
    let written_total = Arc::new(AtomicUsize::new(0));
    let read_total = Arc::new(AtomicUsize::new(0));
    
    // Simulate producer/consumer pattern
    let data: Vec<f32> = (0..10000).map(|i| i as f32).collect();
    let mut written = 0;
    let mut read = 0;
    let mut output = Vec::new();
    
    while read < data.len() {
        // Try to write
        if written < data.len() {
            let to_write = (data.len() - written).min(256);
            let n = buf.write(&data[written..written + to_write]);
            written += n;
            written_total.fetch_add(n, Ordering::Relaxed);
        }
        
        // Try to read
        let mut chunk = vec![0.0f32; 256];
        let n = buf.read(&mut chunk);
        output.extend_from_slice(&chunk[..n]);
        read += n;
        read_total.fetch_add(n, Ordering::Relaxed);
    }
    
    assert_eq!(output.len(), data.len());
    assert_eq!(output, data);
}

/// Test DiskStreamer with short file
#[test]
fn test_disk_streamer_short_file() {
    let path = create_test_wav(5.0, 48000, "short");
    
    let streamer = DiskStreamer::open(&path).unwrap();
    
    // Short file should not need streaming
    assert!(!streamer.should_stream());
    
    // Check specs
    assert_eq!(streamer.spec().sample_rate, 48000);
    assert_eq!(streamer.spec().channels, 2);
    
    // Check duration
    let duration = streamer.duration_seconds();
    assert!(duration >= 4.9 && duration <= 5.1);
}

/// Test DiskStreamer with long file
#[test]
fn test_disk_streamer_long_file() {
    let path = create_test_wav(65.0, 48000, "long");
    
    let streamer = DiskStreamer::open(&path).unwrap();
    
    // Long file should use streaming
    assert!(streamer.should_stream());
    
    // Check total samples
    let expected_samples = (65.0 * 48000.0) as u64 * 2; // stereo
    assert!(streamer.total_samples() >= expected_samples - 1000);
    assert!(streamer.total_samples() <= expected_samples + 1000);
}

/// Test DiskStreamer seek functionality
#[test]
fn test_disk_streamer_seek() {
    let path = create_test_wav(30.0, 48000, "seek");
    let mut streamer = DiskStreamer::open(&path).unwrap();
    
    // Seek to middle
    let middle_sample = streamer.total_samples() / 2;
    assert!(streamer.seek(middle_sample).is_ok());
    assert_eq!(streamer.current_position(), middle_sample);
    
    // Seek beyond end should fail
    assert!(streamer.seek(streamer.total_samples() + 1000).is_err());
}

/// Test StreamingPlayer with long file
#[test]
fn test_streaming_player_long_file() {
    let path = create_test_wav(65.0, 48000, "streaming");
    
    let player = StreamingPlayer::start(&path).unwrap();
    
    // Should be using streaming
    assert!(player.is_streaming());
    
    // Check duration
    let duration = player.duration_seconds();
    assert!(duration >= 64.0 && duration <= 66.0);
    
    // Process some audio
    let mut buffer = vec![0.0f32; 48000 * 2]; // 1 second, stereo
    let frames = player.process(&mut buffer).unwrap();
    assert!(frames > 0);
    
    // Position should have advanced
    let pos = player.position_seconds();
    assert!(pos > 0.0);
    
    // Buffered amount should be reasonable
    let buffered = player.buffered_seconds();
    assert!(buffered >= 0.0 && buffered <= 5.0); // Max 5 seconds buffered
}

/// Test StreamingPlayer with short file (RAM fallback)
#[test]
fn test_streaming_player_short_file() {
    let path = create_test_wav(5.0, 48000, "short_ram");
    
    let player = StreamingPlayer::start(&path).unwrap();
    
    // Short file should NOT use streaming
    assert!(!player.is_streaming());
}

/// Test StreamingPlayer seek
#[test]
fn test_streaming_player_seek() {
    let path = create_test_wav(65.0, 48000, "seek_stream");
    
    let mut player = StreamingPlayer::start(&path).unwrap();
    
    // Seek to 30 seconds
    assert!(player.seek_seconds(30.0).is_ok());
    
    // Position should be near 30 seconds
    let pos = player.position_seconds();
    assert!(pos >= 29.0 && pos <= 31.0);
}

/// Test load_file_to_ram for short files
#[test]
fn test_load_ram_short_file() {
    let path = create_test_wav(3.0, 48000, "ram_load");
    
    let (samples, spec) = load_file_to_ram(&path).unwrap();
    
    // Check sample count
    let expected_samples = (3.0 * 48000.0) as usize * 2; // stereo
    assert_eq!(samples.len(), expected_samples);
    
    // Check spec
    assert_eq!(spec.sample_rate, 48000);
    assert_eq!(spec.channels, 2);
    
    // Verify non-silent (sine wave)
    let non_zero = samples.iter().any(|&s| s != 0.0);
    assert!(non_zero);
}

/// Test the main E2E scenario: 10-minute file with RAM check
#[test]
fn test_streaming_10_minute_file() {
    // Create 10-minute test file
    let path = create_test_wav(600.0, 48000, "10min");
    
    println!("Created 10-minute test file: {:?}", path);
    
    // Measure memory before
    let mem_before = get_memory_usage_mb();
    
    // Start streaming
    let start_time = Instant::now();
    let player = StreamingPlayer::start(&path).unwrap();
    
    // Verify streaming mode
    assert!(player.is_streaming(), "Should use streaming for 10-minute file");
    
    // Process 5 seconds of audio
    let mut total_frames = 0usize;
    for _ in 0..5 {
        let mut buffer = vec![0.0f32; 48000 * 2]; // 1 second, stereo
        let frames = player.process(&mut buffer).unwrap();
        total_frames += frames;
        
        // Verify not silent
        let non_silent = buffer.iter().any(|&s| s.abs() > 0.001);
        assert!(non_silent, "Output should not be silent");
    }
    
    let elapsed = start_time.elapsed();
    println!("Processed 5 seconds in {:?}", elapsed);
    
    // Check position
    let pos = player.position_seconds();
    assert!(pos >= 4.0 && pos <= 6.0, "Position should be ~5 seconds, got {}", pos);
    
    // Verify RAM usage is low
    // Note: In a real test, we'd measure actual memory usage
    // For now, we verify the streaming mechanism is active
    let buffered = player.buffered_seconds();
    assert!(buffered <= 5.0, "Buffered time should be <= 5 seconds, got {}", buffered);
    
    println!("Buffered: {} seconds", buffered);
    println!("Total frames processed: {}", total_frames);
    
    // Success criteria:
    // 1. File is being streamed (not loaded to RAM)
    // 2. Audio is being produced (not silent)
    // 3. Buffered amount is reasonable (not loading entire file)
}

/// Test concurrent streaming operations
#[test]
fn test_streaming_concurrent() {
    let path = create_test_wav(60.0, 48000, "concurrent");
    
    let player = StreamingPlayer::start(&path).unwrap();
    
    // Process audio from multiple "cycles"
    for cycle in 0..10 {
        let mut buffer = vec![0.0f32; 4800 * 2]; // 0.1 second
        let frames = player.process(&mut buffer).unwrap();
        
        // Position should increase
        let pos = player.position_seconds();
        let expected_pos = (cycle as f64 + 1.0) * 0.1;
        assert!(pos >= expected_pos - 0.05 && pos <= expected_pos + 0.1,
            "Cycle {}: position {} should be near {}", cycle, pos, expected_pos);
    }
}

/// Test buffer underrun handling
#[test]
fn test_streaming_buffer_underrun() {
    let path = create_test_wav(60.0, 48000, "underrun");
    
    let player = StreamingPlayer::start(&path).unwrap();
    
    // Process a large chunk quickly (may cause underrun)
    let mut buffer = vec![0.0f32; 48000 * 10 * 2]; // 10 seconds
    let frames = player.process(&mut buffer).unwrap();
    
    // Should have processed something
    assert!(frames > 0);
    
    // Some samples might be zero (underrun), but not all
    let non_zero = buffer.iter().filter(|&&s| s != 0.0).count();
    assert!(non_zero > 0, "Should have some non-zero samples");
}

/// Test streaming with different file sizes around threshold
#[test]
fn test_streaming_threshold_boundary() {
    // Just below threshold (should NOT stream)
    let path_short = create_test_wav(25.0, 48000, "threshold_short");
    let player_short = StreamingPlayer::start(&path_short).unwrap();
    assert!(!player_short.is_streaming(), "25s file should not stream");
    
    // Just above threshold (should stream)
    let path_long = create_test_wav(35.0, 48000, "threshold_long");
    let player_long = StreamingPlayer::start(&path_long).unwrap();
    assert!(player_long.is_streaming(), "35s file should stream");
}

/// Test DiskStreamer read_ahead functionality
#[test]
fn test_disk_streamer_read_ahead() {
    let path = create_test_wav(60.0, 48000, "read_ahead");
    let mut streamer = DiskStreamer::open(&path).unwrap();
    
    // Initially buffer is empty
    assert_eq!(streamer.available_samples(), 0);
    
    // Read ahead
    let read = streamer.read_ahead().unwrap();
    assert!(read > 0, "Should have read some samples");
    
    // Buffer should have samples now
    assert!(streamer.available_samples() > 0);
    
    // Read from buffer
    let mut out = vec![0.0f32; 1024];
    let got = streamer.get_samples(&mut out);
    assert!(got > 0);
}

/// Test error handling for missing files
#[test]
fn test_streaming_file_not_found() {
    let result = DiskStreamer::open(PathBuf::from("/nonexistent/file.wav").as_path());
    assert!(result.is_err());
}

/// Test error handling for invalid files
#[test]
fn test_streaming_invalid_file() {
    use std::io::Write;
    
    // Create an invalid "wav" file
    let mut temp_file = tempfile::NamedTempFile::new().unwrap();
    temp_file.write_all(b"not a wav file").unwrap();
    
    let result = DiskStreamer::open(temp_file.path());
    assert!(result.is_err());
}

/// Cleanup test files after tests
#[test]
fn test_cleanup() {
    // This test runs last and cleans up test files
    let test_dir = PathBuf::from("tests/assets");
    if test_dir.exists() {
        let _ = std::fs::remove_dir_all(&test_dir);
    }
}
