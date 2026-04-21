//! Stress Tests for Audio Engine
//!
//! Tests behavior under extreme conditions and resource limits.

use daw_engine::{
    Mixer, SineWave, SamplePlayer, Sample, TransportClock, MidiEngine, MidiNote,
    Transport, SessionView, Clip, Project, Track, TrackType,
};

/// Test mixer with 64 concurrent tracks
#[test]
fn stress_64_tracks() {
    let mut mixer = Mixer::new(2);
    
    // Add 64 sine wave sources
    for i in 0..64 {
        let freq = 100.0 + (i as f32 * 10.0);
        let sine = SineWave::new(freq, 0.01); // Low amplitude to avoid clipping
        mixer.add_source(Box::new(sine));
    }
    
    assert_eq!(mixer.source_count(), 64);
    
    // Process multiple buffers
    let mut output = vec![0.0f32; 128 * 2]; // 128 frames, stereo
    for _ in 0..100 {
        mixer.process(&mut output);
    }
    
    // Output should not be silence (all sources contributing)
    assert!(output.iter().any(|&s| s != 0.0));
}

/// Test mixer with 128 tracks (beyond typical DAW limits)
#[test]
fn stress_128_tracks() {
    let mut mixer = Mixer::new(2);
    
    for i in 0..128 {
        let freq = 50.0 + (i as f32 * 5.0);
        let sine = SineWave::new(freq, 0.005);
        mixer.add_source(Box::new(sine));
    }
    
    assert_eq!(mixer.source_count(), 128);
    
    let mut output = vec![0.0f32; 128 * 2];
    mixer.process(&mut output);
    
    // Should not panic, should produce output
    assert!(output.iter().any(|&s| s != 0.0));
}

/// Test session view with 1000 clips
#[test]
fn stress_1000_clips() {
    let mut session = SessionView::new(8, 16);
    
    // Add 1000 clips distributed across tracks using set_clip
    for i in 0..1000 {
        let track_idx = i % 8;
        let scene_idx = (i / 8) % 16;
        let clip = Clip::new_audio(&format!("clip_{}", i), 4.0);
        session.set_clip(track_idx, scene_idx, clip);
    }
    
    // Should not panic
    let _playing = session.get_playing_clips();
}

/// Test rapid transport state changes
#[test]
fn stress_rapid_transport_changes() {
    let mut transport = Transport::new(120.0, 48000);
    
    // Rapidly change states
    for i in 0..1000 {
        match i % 4 {
            0 => transport.play(),
            1 => transport.stop(),
            2 => transport.pause(),
            3 => transport.rewind(),
            _ => unreachable!(),
        }
        
        // Also test position jumps
        if i % 10 == 0 {
            transport.set_position((i * 100) as f32);
        }
    }
    
    // Final state should be valid
    assert!(transport.position_beats() >= 0.0);
}

/// Test MIDI engine with 10000 notes
#[test]
fn stress_midi_10000_notes() {
    let mut engine = MidiEngine::new(16);
    
    // Add 10000 notes distributed across channels
    for i in 0..10000 {
        let channel = i % 16;
        let note = MidiNote::new(
            48 + (i % 60) as u8, // Notes from C2 to B6
            80 + (i % 40) as u8, // Velocities 80-120
            i as f32 * 0.1,      // Spaced out
            0.5,                 // Half beat duration
        );
        engine.add_note(channel, note);
    }
    
    // Process through all notes
    for beat in 0..1000 {
        let _messages = engine.process(beat as f32 * 0.1);
    }
}

/// Test large sample (1 minute stereo at 48kHz)
#[test]
fn stress_large_sample() {
    // 1 minute, stereo, 48kHz = 48000 * 60 * 2 = 5,760,000 samples
    let sample_data = vec![0.5f32; 48000 * 60 * 2];
    let sample = Sample::from_raw(sample_data, 2, 48000);
    
    let mut player = SamplePlayer::new(sample, 2);
    player.play();
    
    // Process in chunks
    let mut output = vec![0.0f32; 1024 * 2]; // 1024 frames, stereo
    for _ in 0..100 {
        player.process(&mut output);
    }
    
    assert!(player.is_playing());
}

/// Test memory pressure with many large projects
#[test]
fn stress_many_projects() {
    let mut projects = Vec::new();
    
    // Create 100 projects
    for i in 0..100 {
        let name = format!("Project {}", i);
        let mut project = Project::new(&name);
        
        // Add tracks to each project
        for t in 0..16 {
            let track_name = format!("Track {}", t);
            project.add_track(Track::new(&track_name, TrackType::Audio));
        }
        
        projects.push(project);
    }
    
    assert_eq!(projects.len(), 100);
    
    // Verify all projects are valid
    for (i, project) in projects.iter().enumerate() {
        assert_eq!(project.track_count(), 16);
    }
}

/// Test transport clock at extreme tempos
#[test]
fn stress_extreme_tempos() {
    let mut clock = TransportClock::new(48000);
    
    // Test very slow tempo
    clock.set_tempo(1.0);
    clock.advance(48000);
    let beats = clock.beats();
    assert!(beats > 0.0);
    
    // Test very fast tempo
    clock.set_tempo(999.0);
    clock.advance(48000);
    let beats_fast = clock.beats();
    assert!(beats_fast > beats);
}

/// Test audio callback under high CPU load simulation
#[test]
fn stress_callback_high_load() {
    use daw_engine::AudioCallback;
    
    let mut callback = AudioCallback::new(48000, 2);
    
    // Add many sources
    for i in 0..32 {
        callback.add_sine_wave(200.0 + i as f32 * 20.0, 0.02, 48000);
    }
    
    // Process many buffers rapidly
    let mut output = vec![0.0f32; 128 * 2];
    for _ in 0..1000 {
        callback.process(&mut output);
    }
    
    // Check profiling metrics
    let metrics = callback.last_metrics();
    assert!(metrics.processing_time_ns > 0);
    assert!(metrics.cpu_usage_percent >= 0.0);
}
