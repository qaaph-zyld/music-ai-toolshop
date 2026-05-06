//! Export Verification Test
//!
//! Verifies that the Rust engine can export audio to WAV format.

use daw_engine::export::{ExportEngine, ExportFormat, BitDepth};
use daw_engine::transport::Transport;
use daw_engine::mixer::Mixer;
use daw_engine::session::SessionView;
use std::path::PathBuf;
use std::fs;

#[test]
fn test_export_wav_creates_file() {
    // Setup export engine
    let transport = Transport::new(120.0, 48000);
    let mixer = Mixer::new(2);
    let session = SessionView::new(8, 8);
    let format = ExportFormat::Wav(BitDepth::Bit16);
    
    let mut engine = ExportEngine::new(48000, 2, format, transport, mixer, session);
    
    // Export to temporary file
    let output_path = PathBuf::from("test_export_output.wav");
    let result = engine.export_wav(&output_path, 0.0, 1.0);
    
    // Verify export succeeded
    assert!(result.is_ok(), "Export should succeed");
    
    // Verify file was created
    assert!(output_path.exists(), "Export file should exist");
    
    // Verify file has content
    let metadata = fs::metadata(&output_path).unwrap();
    assert!(metadata.len() > 0, "Export file should have content");
    
    // Cleanup
    let _ = fs::remove_file(&output_path);
}

#[test]
fn test_export_wav_format() {
    // Setup export engine
    let transport = Transport::new(120.0, 48000);
    let mixer = Mixer::new(2);
    let session = SessionView::new(8, 8);
    let format = ExportFormat::Wav(BitDepth::Bit16);
    
    let mut engine = ExportEngine::new(48000, 2, format, transport, mixer, session);
    
    // Export to temporary file
    let output_path = PathBuf::from("test_export_format.wav");
    let result = engine.export_wav(&output_path, 0.0, 1.0);
    
    assert!(result.is_ok(), "Export should succeed");
    
    // Verify it's a valid WAV file by reading it back
    let reader = hound::WavReader::open(&output_path).unwrap();
    assert_eq!(reader.spec().channels, 2);
    assert_eq!(reader.spec().sample_rate, 48000);
    assert_eq!(reader.spec().bits_per_sample, 16);
    
    // Cleanup
    let _ = fs::remove_file(&output_path);
}
