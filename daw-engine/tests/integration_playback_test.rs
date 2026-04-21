//! Full Playback Workflow Integration Test
//!
//! Tests the complete end-to-end workflow:
//! Load project → Load sample → Start transport → Process audio → Stop → Save project

use daw_engine::{
    AudioCallback, Mixer, Sample, SamplePlayer, SineWave,
    Transport, TransportState, PlayMode,
    SessionView, Clip, Project, Track, TrackType,
};
use std::io::Write;

/// Full playback workflow test
#[test]
fn integration_full_playback_workflow() {
    // Step 1: Create a project
    let mut project = Project::new("Integration Test Project");
    project.set_tempo(120.0);
    project.set_sample_rate(48000);
    
    // Add a track
    let track = Track::new("Test Track", TrackType::Audio);
    project.add_track(track);
    assert_eq!(project.track_count(), 1);
    
    // Step 2: Create session view with clips
    let mut session = SessionView::new(1, 4);
    let clip = Clip::new_audio("test_clip", 4.0); // 4 bar clip
    session.set_clip(0, 0, clip);
    
    // Verify clip was added
    let retrieved_clip = session.get_clip(0, 0);
    assert!(retrieved_clip.is_some());
    assert_eq!(retrieved_clip.unwrap().name(), "test_clip");
    
    // Step 3: Create a sample (1 second of 1kHz sine wave at 48kHz)
    let sample_rate = 48000;
    let duration_samples = sample_rate; // 1 second
    let frequency = 1000.0;
    
    let sample_data: Vec<f32> = (0..duration_samples)
        .map(|i| {
            let t = i as f32 / sample_rate as f32;
            (2.0 * std::f32::consts::PI * frequency * t).sin() * 0.5
        })
        .collect();
    
    let sample = Sample::from_raw(sample_data, 1, sample_rate);
    assert_eq!(sample.sample_rate(), sample_rate);
    assert_eq!(sample.frame_count(), duration_samples as usize);
    
    // Step 4: Create audio callback with sample player
    let mut callback = AudioCallback::new(sample_rate, 2);
    let mut player = SamplePlayer::new(sample, 2);
    player.play(); // Start the player
    callback.add_sample_player(player);
    
    assert_eq!(callback.source_count(), 1);
    
    // Step 5: Set up transport and start playback
    let mut transport = Transport::new(120.0, sample_rate);
    transport.play();
    assert_eq!(transport.state(), TransportState::Playing);
    
    // Step 6: Simulate audio processing for 100 callbacks (~1.3 seconds at 128 samples)
    let buffer_size = 128;
    let mut output_buffer = vec![0.0f32; buffer_size * 2]; // stereo
    let mut peak_level = 0.0f32;
    
    for _ in 0..100 {
        // Process audio
        callback.process(&mut output_buffer);
        
        // Track peak level
        for &sample in &output_buffer {
            peak_level = peak_level.max(sample.abs());
        }
        
        // Advance transport
        transport.process(buffer_size as u32);
    }
    
    // Step 7: Verify audio output
    // Peak level should be non-zero (we played a sine wave)
    assert!(peak_level > 0.0, "Audio output was silent!");
    // Peak should be near 0.5 (our sine amplitude)
    assert!(peak_level <= 0.5, "Audio clipped! Peak was {}", peak_level);
    
    // Step 8: Check profiling metrics and store values
    let metrics_cpu = {
        let metrics = callback.last_metrics();
        assert!(metrics.processing_time_ns > 0);
        assert_eq!(metrics.sample_count, buffer_size);
        metrics.cpu_usage_percent
    };
    
    // Step 9: Stop playback
    transport.stop();
    assert_eq!(transport.state(), TransportState::Stopped);
    
    // Step 10: Test loop mode
    transport.set_play_mode(PlayMode::Loop);
    transport.set_loop_range(0.0, 4.0); // 4 beat loop
    transport.play();
    
    // Process for 8 beats (should loop twice at 120 BPM)
    let samples_per_beat = (60.0 / 120.0 * sample_rate as f32) as u64;
    let samples_8_beats = samples_per_beat * 8;
    let callbacks_needed = (samples_8_beats / buffer_size as u64) as usize;
    
    for _ in 0..callbacks_needed {
        callback.process(&mut output_buffer);
        transport.process(buffer_size as u32);
    }
    
    // Position should have looped back
    assert!(transport.position_beats() < 8.0, "Loop did not work correctly");
    
    transport.stop();
    
    // Step 11: Serialize and deserialize project using native methods
    let project_json = project.to_json();
    assert!(!project_json.is_empty());
    
    // Deserialize back
    let restored_project = Project::from_json(&project_json)
        .expect("Failed to deserialize project");
    
    assert_eq!(restored_project.name(), project.name());
    assert_eq!(restored_project.track_count(), project.track_count());
    
    println!("Full playback workflow completed successfully!");
    println!("  - Project created with {} tracks", project.track_count());
    println!("  - Audio processed: {} callbacks", 100 + callbacks_needed);
    println!("  - Peak output level: {:.2}", peak_level);
    println!("  - Last callback CPU usage: {:.1}%", metrics_cpu);
}

/// Test project round-trip (save → load → verify identical)
#[test]
fn integration_project_roundtrip() {
    // Create original project
    let mut original = Project::new("Roundtrip Test");
    original.set_tempo(128.0);
    original.add_track(Track::new("Drums", TrackType::Audio));
    original.add_track(Track::new("Bass", TrackType::Audio));
    original.add_track(Track::new("Synth", TrackType::Midi));
    
    // Serialize using native method
    let json = original.to_json();
    
    // Save to temp file
    let temp_path = std::env::temp_dir().join("opendaw_test_project.json");
    {
        let mut file = std::fs::File::create(&temp_path).unwrap();
        file.write_all(json.as_bytes()).unwrap();
    }
    
    // Read back and deserialize using native method
    let read_json = std::fs::read_to_string(&temp_path).unwrap();
    let restored = Project::from_json(&read_json)
        .expect("Failed to deserialize");
    
    // Verify identical
    assert_eq!(original.name(), restored.name());
    assert_eq!(original.tempo(), restored.tempo());
    assert_eq!(original.track_count(), restored.track_count());
    
    // Cleanup
    std::fs::remove_file(&temp_path).ok();
}

/// Test session view scene launch with audio playback
#[test]
fn integration_scene_launch_with_audio() {
    let mut session = SessionView::new(2, 4); // 2 tracks, 4 scenes
    
    // Create clips in scene 0
    let clip1 = Clip::new_audio("Drums", 4.0);
    let clip2 = Clip::new_midi("Bass", 4.0);
    session.set_clip(0, 0, clip1);
    session.set_clip(1, 0, clip2);
    
    // Create clips in scene 1
    let clip3 = Clip::new_audio("Break", 2.0);
    session.set_clip(0, 1, clip3);
    
    // Launch scene 0
    session.launch_scene(0);
    
    // Verify playing clips
    let playing = session.get_playing_clips();
    assert_eq!(playing.len(), 2, "Expected 2 playing clips from scene 0");
    
    // Switch to scene 1
    session.launch_scene(1);
    
    let playing_after = session.get_playing_clips();
    assert_eq!(playing_after.len(), 1, "Expected 1 playing clip from scene 1");
    
    // Stop all
    session.stop_all();
    let playing_stopped = session.get_playing_clips();
    assert!(playing_stopped.is_empty(), "Expected no playing clips after stop");
}
