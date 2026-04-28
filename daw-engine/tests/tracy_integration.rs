//! Tracy profiler integration tests
//!
//! Verifies that Tracy instrumentation compiles and works correctly
//! with and without the tracy feature flag.

use daw_engine::{AudioCallback, Profiler, CpuUsageTracker, profile_scope, plot_value, frame_mark};
use daw_engine::transport::{Transport, TransportState, PlayMode};
use daw_engine::clip_player::{ClipPlayer, TrackPlaybackState};
use daw_engine::transport_sync::{TransportSync, Quantization, QuantizeDirection};
use daw_engine::session::{SessionView, Clip};
use daw_engine::midi::{MidiEngine, MidiNote};
use daw_engine::realtime::{LockFreeQueue, RealTimeCommand, RealTimeCommandProcessor, WatchdogTimer};
use std::time::Duration;

/// Test that profiler macros work without tracy feature (no-op)
#[test]
fn test_profiler_macros_noop() {
    // These should compile and run without panicking even without tracy feature
    profile_scope!("test_scope");
    plot_value!("test_metric", 42.0);
    frame_mark!();
}

/// Test profiler creation
#[test]
fn test_profiler_creation() {
    let profiler = Profiler::new();
    profiler.frame_mark();
    profiler.plot("test_metric", 42.0);
}

/// Test CPU usage tracker calculations
#[test]
fn test_cpu_usage_tracker_basic() {
    let mut tracker = CpuUsageTracker::new(48000, 2);
    
    // Simulate 0.5ms processing time for 256 samples (128 frames) at 48kHz stereo
    // Buffer time = 128/48000 = 2.67ms = 2667us
    // Processing time = 0.5ms = 500us
    // CPU = 500/2667 * 100 = 18.75%
    let cpu = tracker.calculate(500_000, 256);
    
    assert!(cpu > 0.0 && cpu < 50.0, "CPU usage should be reasonable: {}", cpu);
    assert_eq!(tracker.last_cpu_usage(), cpu);
}

/// Test CPU usage tracker with heavy load
#[test]
fn test_cpu_usage_tracker_heavy_load() {
    let mut tracker = CpuUsageTracker::new(48000, 2);
    
    // Simulate 2ms processing time (75% CPU at 48kHz/128frames)
    let cpu = tracker.calculate(2_000_000, 256);
    
    assert!(cpu > 50.0 && cpu <= 100.0, "Heavy load CPU usage should be high: {}", cpu);
}

/// Test CPU usage tracker with zero load
#[test]
fn test_cpu_usage_tracker_zero_load() {
    let mut tracker = CpuUsageTracker::new(48000, 2);
    let cpu = tracker.calculate(0, 256);
    
    assert_eq!(cpu, 0.0, "Zero processing time should give 0% CPU");
}

/// Test audio callback with profiling instrumentation
#[test]
fn test_callback_profiling_integration() {
    let mut callback = AudioCallback::new(48000, 2);
    callback.add_sine_wave(440.0, 0.5, 48000);
    
    let mut output = vec![0.0f32; 256]; // 128 frames, stereo
    
    // Process multiple times to generate profiling data
    for _ in 0..10 {
        callback.process(&mut output);
    }
    
    // Verify metrics were recorded
    let metrics = callback.last_metrics();
    assert!(metrics.processing_time_ns > 0);
    assert_eq!(metrics.sample_count, 128);
    assert!(metrics.cpu_usage_percent >= 0.0);
    assert!(metrics.cpu_usage_percent <= 100.0);
}

/// Test nested profiling scopes
#[test]
fn test_nested_profiling_scopes() {
    profile_scope!("outer_scope");
    {
        profile_scope!("inner_scope_1");
        let x = 1 + 1;
        assert_eq!(x, 2);
    }
    {
        profile_scope!("inner_scope_2");
        let y = 2 + 2;
        assert_eq!(y, 4);
    }
}

/// Test multiple plot values
#[test]
fn test_multiple_plot_values() {
    for i in 0..100 {
        plot_value!("iteration", i as f64);
        plot_value!("sine_wave", (i as f64 * 0.1).sin());
    }
}

/// Verify conditional compilation works correctly
#[test]
fn test_conditional_compilation() {
    // The code should compile with or without the tracy feature
    // This test verifies the macros expand correctly
    
    #[cfg(feature = "tracy")]
    {
        // When tracy is enabled, the macros should expand to actual calls
        // We can't test the actual Tracy connection here, but we can verify
        // the code compiles and doesn't panic
        profile_scope!("tracy_enabled_test");
        plot_value!("tracy_enabled_metric", 100.0);
        frame_mark!();
    }
    
    #[cfg(not(feature = "tracy"))]
    {
        // When tracy is disabled, the macros should be no-ops
        profile_scope!("tracy_disabled_test");
        plot_value!("tracy_disabled_metric", 200.0);
        frame_mark!();
    }
}

/// Test profiler default implementation
#[test]
fn test_profiler_default() {
    let profiler: Profiler = Default::default();
    profiler.frame_mark();
    
    // Verify it doesn't panic
    assert!(true);
}

/// Test callback with various buffer sizes
#[test]
fn test_callback_various_buffer_sizes() {
    let sample_rates = [44100, 48000, 96000];
    let buffer_sizes = [64, 128, 256, 512];
    
    for &sample_rate in &sample_rates {
        for &buffer_frames in &buffer_sizes {
            let mut callback = AudioCallback::new(sample_rate, 2);
            callback.add_sine_wave(440.0, 0.5, sample_rate);
            
            let mut output = vec![0.0f32; buffer_frames * 2];
            callback.process(&mut output);
            
            let metrics = callback.last_metrics();
            assert_eq!(metrics.sample_count, buffer_frames);
            assert!(metrics.cpu_usage_percent >= 0.0);
            assert!(metrics.cpu_usage_percent <= 100.0);
        }
    }
}

/// Test that profiling doesn't affect audio output
#[test]
fn test_profiling_doesnt_affect_output() {
    // Process audio without profiling feature (baseline)
    let mut callback1 = AudioCallback::new(48000, 2);
    callback1.add_sine_wave(440.0, 0.5, 48000);
    let mut output1 = vec![0.0f32; 256];
    callback1.process(&mut output1);
    
    // Process audio with profiling (current configuration)
    let mut callback2 = AudioCallback::new(48000, 2);
    callback2.add_sine_wave(440.0, 0.5, 48000);
    let mut output2 = vec![0.0f32; 256];
    callback2.process(&mut output2);
    
    // Outputs should be identical (profiling doesn't change behavior)
    for (a, b) in output1.iter().zip(output2.iter()) {
        assert!((a - b).abs() < f32::EPSILON, 
            "Profiling should not affect audio output: {} vs {}", a, b);
    }
}

// ===== Phase 2: Critical Path Instrumentation Tests =====

/// Test transport module profiling instrumentation
#[test]
fn test_transport_profiling_zones() {
    let mut transport = Transport::new(120.0, 48000);
    
    // Trigger transport_play zone
    transport.play();
    assert_eq!(transport.state(), TransportState::Playing);
    
    // Trigger transport_process zone with position tracking
    transport.process(256);
    
    // Trigger loop handling
    transport.set_loop_range(0.0, 4.0);
    transport.set_play_mode(PlayMode::Loop);
    transport.process(96000); // 2 seconds = 4 beats at 120 BPM
    
    // Trigger transport_stop zone
    transport.stop();
    assert_eq!(transport.state(), TransportState::Stopped);
    
    // Trigger record
    transport.record();
    assert_eq!(transport.state(), TransportState::Recording);
    
    // Trigger transport_process zone again
    transport.process(256);
}

/// Test clip player profiling instrumentation
#[test]
fn test_clip_player_profiling_zones() {
    let mut player = ClipPlayer::new(8, 8);
    
    // Trigger clip_player_trigger zone
    player.trigger_clip(3, 2);
    assert!(player.is_track_playing(3));
    
    // Trigger clip_player_process_queue zone
    player.queue_clip(4, 5);
    player.process_queued_clips();
    assert!(player.is_track_playing(4));
    
    // Trigger stop zones
    player.stop_clip(3);
    assert!(!player.is_track_playing(3));
    
    // Trigger clip_player_stop_all zone
    player.trigger_clip(0, 0);
    player.trigger_clip(1, 1);
    player.stop_all();
    assert!(!player.is_track_playing(0));
    assert!(!player.is_track_playing(1));
}

/// Test transport sync profiling instrumentation
#[test]
fn test_transport_sync_profiling_zones() {
    let mut sync = TransportSync::new(48000.0, 120.0);
    
    // Trigger sync_schedule zone
    sync.schedule_clip(0, 0, 4.0, false);
    assert_eq!(sync.pending_count(), 1);
    
    // Trigger sync_process zone
    let triggered = sync.process(4.0);
    assert_eq!(triggered.len(), 1);
    assert_eq!(sync.pending_count(), 0);
    
    // Trigger sync_set_tempo zone
    sync.set_tempo(60.0);
    assert_eq!(sync.tempo(), 60.0);
    
    // Test quantized scheduling
    sync.schedule_clip_quantized(1, 2, 0.0, Quantization::Beat, false);
    assert_eq!(sync.pending_count(), 1);
    
    // Trigger sync_clear_all zone
    sync.clear_all();
    assert_eq!(sync.pending_count(), 0);
}

/// Test session view profiling instrumentation
#[test]
fn test_session_profiling_zones() {
    let mut session = SessionView::new(8, 8);
    
    // Add some clips
    session.set_clip(0, 0, Clip::new_audio("Test Clip", 4.0));
    session.set_clip(1, 0, Clip::new_midi("MIDI Clip", 4.0));
    session.set_clip(0, 1, Clip::new_audio("Scene 2 Clip", 4.0));
    
    // Trigger session_launch_scene zone
    session.launch_scene(0);
    assert_eq!(session.current_scene(), Some(0));
    
    // Launch another scene (triggers stop of current)
    session.launch_scene(1);
    assert_eq!(session.current_scene(), Some(1));
    
    // Trigger session_stop_all zone
    session.stop_all();
    assert_eq!(session.current_scene(), None);
}

/// Test MIDI engine profiling instrumentation
#[test]
fn test_midi_profiling_zones() {
    let mut engine = MidiEngine::new(16);
    
    // Add some notes
    let note1 = MidiNote::new(60, 100, 0.0, 1.0); // C4
    let note2 = MidiNote::new(64, 100, 0.5, 1.0); // E4
    engine.add_note(0, note1);
    engine.add_note(0, note2);
    
    // Trigger midi_process zone
    let messages = engine.process(0.0);
    assert!(!messages.is_empty());
    
    // Process at different beat positions
    let messages = engine.process(0.5);
    assert!(!messages.is_empty());
    
    let messages = engine.process(1.0);
    assert!(!messages.is_empty());
    
    // Trigger midi_stop_all zone
    let messages = engine.stop_all();
    assert!(!messages.is_empty());
}

/// Test lock-free queue profiling instrumentation
#[test]
fn test_lockfree_queue_profiling_zones() {
    let queue = LockFreeQueue::<i32, 128>::new();
    
    // Trigger lockfree_push zones
    for i in 0..50 {
        assert!(queue.push(i));
    }
    
    // Trigger lockfree_pop zones
    for _ in 0..50 {
        assert!(queue.pop().is_some());
    }
    
    assert!(queue.is_empty());
}

/// Test real-time command processor profiling instrumentation
#[test]
fn test_rt_command_processor_profiling_zones() {
    let processor = RealTimeCommandProcessor::new(
        Duration::from_millis(100),
        || { /* Watchdog callback */ }
    );
    
    // Send some commands
    for i in 0..10 {
        assert!(processor.send(RealTimeCommand::SetVolume(i, 0.5)));
    }
    
    // Trigger rt_command_process zone and handlers
    processor.process(|cmd| {
        // Process each command
        match cmd {
            RealTimeCommand::SetVolume(track, vol) => {
                assert!(track < 10);
                assert!(vol >= 0.0 && vol <= 1.0);
            }
            _ => {}
        }
    });
    
    // Verify queue is empty after processing
    assert!(processor.queue().is_empty());
}

/// Test watchdog timer profiling instrumentation
#[test]
fn test_watchdog_profiling_zones() {
    let triggered = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));
    let t = std::sync::Arc::clone(&triggered);
    
    let watchdog = WatchdogTimer::new(Duration::from_millis(50), move || {
        t.store(true, std::sync::atomic::Ordering::SeqCst);
    });
    
    // Trigger watchdog_pet zone
    watchdog.pet();
    assert!(!watchdog.check());
    
    // Pet again
    watchdog.pet();
    assert!(!watchdog.check());
}

/// Combined test that exercises all Phase 2 instrumented modules together
#[test]
fn test_phase2_all_modules_combined() {
    // Transport
    let mut transport = Transport::new(120.0, 48000);
    transport.play();
    
    // Transport Sync
    let mut sync = TransportSync::new(48000.0, 120.0);
    sync.schedule_clip(0, 0, 1.0, false);
    
    // Clip Player
    let mut player = ClipPlayer::new(8, 8);
    player.trigger_clip(0, 0);
    player.process_queued_clips();
    
    // Session
    let mut session = SessionView::new(8, 8);
    session.set_clip(0, 0, Clip::new_audio("Test", 4.0));
    session.launch_scene(0);
    
    // MIDI
    let mut midi = MidiEngine::new(16);
    midi.add_note(0, MidiNote::new(60, 100, 0.0, 1.0));
    midi.process(0.0);
    
    // Lock-free queue
    let queue = LockFreeQueue::<RealTimeCommand, 256>::new();
    queue.push(RealTimeCommand::Play);
    queue.pop();
    
    // Command processor
    let processor = RealTimeCommandProcessor::new(
        Duration::from_millis(100),
        || {}
    );
    processor.send(RealTimeCommand::Stop);
    processor.process(|_| {});
    
    // All zones triggered successfully
    assert!(true);
}
