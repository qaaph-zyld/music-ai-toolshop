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
    for (_i, project) in projects.iter().enumerate() {
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

/// Baseline measurement: Mixer with 8 tracks (typical project)
#[test]
fn baseline_mixer_8tracks() {
    use daw_engine::PerformanceAnalyzer;
    
    let mut analyzer = PerformanceAnalyzer::with_config(48000, 128);
    let mut mixer = daw_engine::Mixer::new(2);
    
    // Add 8 sine wave sources (typical track count)
    for i in 0..8 {
        let freq = 440.0 + (i as f32 * 10.0);
        let sine = daw_engine::SineWave::new(freq, 0.1);
        mixer.add_source(Box::new(sine));
    }
    
    let mut output = vec![0.0f32; 128 * 2];
    
    // Collect 1000 samples
    for _ in 0..1000 {
        analyzer.measure(|| {
            mixer.process(&mut output);
        });
    }
    
    let report = analyzer.generate_report();
    
    // Verify mixer performance is reasonable
    // In debug builds, expect avg < 500µs, max < 2000µs
    assert!(
        report.metrics.avg_us < 500.0,
        "8-track mixer avg too slow: {:.2} µs",
        report.metrics.avg_us
    );
    assert!(
        report.metrics.max_us < 2000.0,
        "8-track mixer max too slow: {:.2} µs",
        report.metrics.max_us
    );
}

/// Baseline measurement: SamplePlayer processing
#[test]
fn baseline_sample_player() {
    use daw_engine::{PerformanceAnalyzer, Sample, SamplePlayer};
    
    let mut analyzer = PerformanceAnalyzer::with_config(48000, 128);
    
    // 5-second stereo sample
    let sample_data = vec![0.5f32; 48000 * 5 * 2];
    let sample = Sample::from_raw(sample_data, 2, 48000);
    let mut player = SamplePlayer::new(sample, 2);
    player.play();
    
    let mut output = vec![0.0f32; 128 * 2];
    
    // Collect 1000 samples
    for _ in 0..1000 {
        analyzer.measure(|| {
            player.process(&mut output);
        });
    }
    
    let report = analyzer.generate_report();
    
    // Sample player should be real-time safe (large sample processing takes time)
    // Just verify it produces consistent output and is within reasonable bounds
    assert!(report.metrics.avg_us < 1000.0, "SamplePlayer avg should be < 1000 µs, got {:.2} µs", report.metrics.avg_us);
    assert!(report.metrics.max_us < 2000.0, "SamplePlayer max should be < 2000 µs, got {:.2} µs", report.metrics.max_us);
}

/// Baseline measurement: Transport clock advancement
#[test]
fn baseline_transport_clock() {
    use daw_engine::{PerformanceAnalyzer, TransportClock};
    
    let mut analyzer = PerformanceAnalyzer::with_config(48000, 128);
    let mut clock = TransportClock::new(48000);
    clock.set_tempo(120.0);
    
    // Collect 1000 samples
    for _ in 0..1000 {
        analyzer.measure(|| {
            clock.advance(128);
            clock.beats();
        });
    }
    
    let report = analyzer.generate_report();
    
    // Clock should be extremely fast
    assert!(report.metrics.avg_us < 10.0, "Clock advance should take < 10 µs, took {:.2} µs", report.metrics.avg_us);
}

/// Baseline measurement: MIDI engine processing
#[test]
fn baseline_midi_engine() {
    use daw_engine::{PerformanceAnalyzer, MidiEngine, MidiNote};
    
    let mut analyzer = PerformanceAnalyzer::with_config(48000, 128);
    let mut engine = MidiEngine::new(16);
    
    // Add 100 notes
    for i in 0..100 {
        let channel = i % 16;
        let note = MidiNote::new(
            60 + (i % 12) as u8,
            100,
            i as f32 * 0.1,
            0.5,
        );
        engine.add_note(channel, note);
    }
    
    let mut beat = 0.0f32;
    
    // Collect 1000 samples
    for _ in 0..1000 {
        analyzer.measure(|| {
            beat = (beat + 0.1) % 100.0;
            engine.process(beat);
        });
    }
    
    let report = analyzer.generate_report();
    
    // MIDI engine should be reasonably fast with 100 notes
    assert!(report.metrics.avg_us < 100.0, "MIDI engine avg too slow: {:.2} µs", report.metrics.avg_us);
    assert!(report.metrics.max_us < 500.0, "MIDI engine max too slow: {:.2} µs", report.metrics.max_us);
}

/// Performance degradation test: Linear scaling check
#[test]
fn baseline_scaling_linear() {
    use daw_engine::{Mixer, SineWave};
    
    fn measure_mixer(tracks: usize) -> f64 {
        let mut mixer = Mixer::new(2);
        
        for i in 0..tracks {
            let freq = 440.0 + (i as f32 * 10.0);
            let sine = SineWave::new(freq, 0.1);
            mixer.add_source(Box::new(sine));
        }
        
        let mut output = vec![0.0f32; 128 * 2];
        
        // Warmup
        for _ in 0..100 {
            mixer.process(&mut output);
        }
        
        // Measure
        let start = std::time::Instant::now();
        for _ in 0..1000 {
            mixer.process(&mut output);
        }
        let elapsed = start.elapsed();
        
        elapsed.as_secs_f64() * 1_000_000.0 / 1000.0 // Average µs per call
    }
    
    let time_8 = measure_mixer(8);
    let time_16 = measure_mixer(16);
    let time_32 = measure_mixer(32);
    
    // Should scale roughly linearly (within 2.5x factor)
    let ratio_16_8 = time_16 / time_8;
    let ratio_32_8 = time_32 / time_8;
    
    assert!(
        ratio_16_8 < 2.5,
        "16 tracks should take < 2.5x 8 tracks, took {:.2}x",
        ratio_16_8
    );
    assert!(
        ratio_32_8 < 5.0,
        "32 tracks should take < 5x 8 tracks, took {:.2}x",
        ratio_32_8
    );
}

/// Optimization candidate identification test
#[test]
fn baseline_identify_optimization_candidates() {
    use daw_engine::{PerformanceAnalyzer, BaselineMeasurements, Mixer, SineWave};
    
    let mut candidates = Vec::new();
    
    // Test different track counts
    for track_count in [8, 16, 32, 64].iter() {
        let mut analyzer = PerformanceAnalyzer::with_config(48000, 128);
        let mut mixer = Mixer::new(2);
        
        for i in 0..*track_count {
            let freq = 440.0 + (i as f32 * 10.0);
            let sine = SineWave::new(freq, 0.1);
            mixer.add_source(Box::new(sine));
        }
        
        let mut output = vec![0.0f32; 128 * 2];
        
        for _ in 0..1000 {
            analyzer.measure(|| {
                mixer.process(&mut output);
            });
        }
        
        let report = analyzer.generate_report();
        
        if BaselineMeasurements::is_optimization_candidate(&report.metrics, report.realtime_budget_us) {
            candidates.push((*track_count, report.score, report.metrics.avg_us));
        }
    }
    
    // Print optimization candidates for analysis
    if !candidates.is_empty() {
        println!("Optimization candidates found:");
        for (tracks, score, avg_us) in &candidates {
            println!("  {} tracks - Score: {}, Avg: {:.2} µs", tracks, score, avg_us);
        }
    }
    
    // At least 8 tracks should not be candidates (16+ may vary by build)
    assert!(
        !candidates.iter().any(|(t, _, _)| *t == 8),
        "8 tracks should not need optimization"
    );
    
    // Print all candidates for analysis
    if !candidates.is_empty() {
        println!("\nAll optimization candidates:");
        for (tracks, score, avg_us) in &candidates {
            let status = if *tracks <= 16 { "MARGINAL" } else { "EXPECTED" };
            println!("  {} tracks - Score: {}, Avg: {:.2} µs [{}]", tracks, score, avg_us, status);
        }
    }
}
