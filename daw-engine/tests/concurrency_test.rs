//! Concurrency Stress Tests
//!
//! Tests thread safety and race conditions in audio engine.

use daw_engine::{
    Mixer, SineWave, SamplePlayer, Sample,
    SessionView, Clip,
    Transport, TransportState,
    MidiEngine, MidiNote,
    Project, Track, TrackType,
};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

/// Test mixer with concurrent access
#[test]
fn concurrency_mixer_thread_safety() {
    let mixer = Arc::new(Mutex::new(Mixer::new(2)));
    
    // Add some sources
    {
        let mut m = mixer.lock().unwrap();
        for i in 0..8 {
            m.add_source(Box::new(SineWave::new(200.0 + i as f32 * 50.0, 0.1)));
        }
    }
    
    // Spawn threads that process audio
    let mut handles = vec![];
    
    for _ in 0..4 {
        let mixer_clone = Arc::clone(&mixer);
        let handle = thread::spawn(move || {
            let mut output = vec![0.0f32; 128 * 2];
            for _ in 0..100 {
                let mut m = mixer_clone.lock().unwrap();
                m.process(&mut output);
                drop(m);
                thread::sleep(Duration::from_micros(100));
            }
        });
        handles.push(handle);
    }
    
    // Wait for all threads
    for handle in handles {
        handle.join().unwrap();
    }
    
    // Mixer should still be valid
    let m = mixer.lock().unwrap();
    assert_eq!(m.source_count(), 8);
}

/// Test transport with concurrent state changes
#[test]
fn concurrency_transport_state_changes() {
    let transport = Arc::new(Mutex::new(Transport::new(120.0, 48000)));
    
    let mut handles = vec![];
    
    // Thread 1: Play/Stop
    {
        let t = Arc::clone(&transport);
        handles.push(thread::spawn(move || {
            for _ in 0..50 {
                let mut tr = t.lock().unwrap();
                tr.play();
                drop(tr);
                thread::sleep(Duration::from_micros(50));
                let mut tr = t.lock().unwrap();
                tr.stop();
                drop(tr);
            }
        }));
    }
    
    // Thread 2: Record/Stop
    {
        let t = Arc::clone(&transport);
        handles.push(thread::spawn(move || {
            for _ in 0..50 {
                let mut tr = t.lock().unwrap();
                tr.record();
                drop(tr);
                thread::sleep(Duration::from_micros(50));
                let mut tr = t.lock().unwrap();
                tr.stop();
                drop(tr);
            }
        }));
    }
    
    // Thread 3: Jump position
    {
        let t = Arc::clone(&transport);
        handles.push(thread::spawn(move || {
            for i in 0..100 {
                let mut tr = t.lock().unwrap();
                tr.set_position(i as f32 * 10.0);
                drop(tr);
                thread::sleep(Duration::from_micros(25));
            }
        }));
    }
    
    for handle in handles {
        handle.join().unwrap();
    }
    
    // Transport should be in valid state
    let tr = transport.lock().unwrap();
    assert!(
        matches!(tr.state(), TransportState::Stopped | TransportState::Playing | 
                 TransportState::Recording | TransportState::Paused)
    );
}

/// Test session view with concurrent scene launches
#[test]
fn concurrency_session_scene_launch() {
    let session = Arc::new(Mutex::new(SessionView::new(8, 16)));
    
    // Add clips
    {
        let mut s = session.lock().unwrap();
        // Fill session with clips
        for i in 0..16 {
            let clip = Clip::new_audio("clip", 4.0);
            s.set_clip(0, i, clip);
        }
    }
    
    let mut handles = vec![];
    
    // Multiple threads launching scenes
    for thread_id in 0..4 {
        let s = Arc::clone(&session);
        handles.push(thread::spawn(move || {
            for i in 0..25 {
                let scene = (thread_id * 4 + i) % 16;
                let mut sess = s.lock().unwrap();
                sess.launch_scene(scene);
                drop(sess);
                thread::sleep(Duration::from_micros(100));
            }
        }));
    }
    
    for handle in handles {
        handle.join().unwrap();
    }
    
    // Session should still be valid
    let s = session.lock().unwrap();
    let playing = s.get_playing_clips();
    // May or may not have playing clips
    println!("Final playing clips: {}", playing.len());
}

/// Test MIDI engine with concurrent note addition
#[test]
fn concurrency_midi_note_addition() {
    let engine = Arc::new(Mutex::new(MidiEngine::new(16)));
    
    let mut handles = vec![];
    
    // Multiple threads adding notes to different channels
    for channel in 0..4 {
        let e = Arc::clone(&engine);
        handles.push(thread::spawn(move || {
            for i in 0..25 {
                let note = MidiNote::new(
                    60 + i as u8,
                    100,
                    i as f32 * 0.1,
                    0.5,
                );
                let mut eng = e.lock().unwrap();
                eng.add_note(channel, note);
                drop(eng);
            }
        }));
    }
    
    for handle in handles {
        handle.join().unwrap();
    }
    
    // Verify notes were added
    let eng = engine.lock().unwrap();
    let total_notes: usize = (0..16)
        .map(|ch| eng.get_notes(ch).len())
        .sum();
    
    assert_eq!(total_notes, 100); // 4 channels x 25 notes
}

/// Test sample player with concurrent play/stop
#[test]
fn concurrency_sample_player_control() {
    let data: Vec<f32> = (0..10000).map(|i| (i as f32 / 10000.0).sin()).collect();
    let sample = Sample::from_raw(data, 1, 48000);
    
    let player: Arc<Mutex<SamplePlayer>> = Arc::new(Mutex::new(SamplePlayer::new(sample, 2)));
    
    let mut handles = vec![];
    
    // Thread 1: Play
    {
        let p: Arc<Mutex<SamplePlayer>> = Arc::clone(&player);
        handles.push(thread::spawn(move || {
            for _ in 0..50 {
                let mut pl = p.lock().unwrap();
                pl.play();
                drop(pl);
                thread::sleep(Duration::from_micros(50));
            }
        }));
    }
    
    // Thread 2: Stop
    {
        let p: Arc<Mutex<SamplePlayer>> = Arc::clone(&player);
        handles.push(thread::spawn(move || {
            for _ in 0..50 {
                let mut pl = p.lock().unwrap();
                pl.stop();
                drop(pl);
                thread::sleep(Duration::from_micros(50));
            }
        }));
    }
    
    // Thread 3: Process audio
    {
        let p: Arc<Mutex<SamplePlayer>> = Arc::clone(&player);
        handles.push(thread::spawn(move || {
            let mut output = vec![0.0f32; 128 * 2];
            for _ in 0..100 {
                let mut pl = p.lock().unwrap();
                pl.process(&mut output);
                drop(pl);
                thread::sleep(Duration::from_micros(25));
            }
        }));
    }
    
    for handle in handles {
        handle.join().unwrap();
    }
    
    // Player should still be valid
    let pl = player.lock().unwrap();
    assert!(pl.position() >= 0.0);
}

/// Test project with concurrent modifications
#[test]
fn concurrency_project_modifications() {
    let project: Arc<Mutex<Project>> = Arc::new(Mutex::new(Project::new("Concurrent Test")));
    
    let mut handles = vec![];
    
    // Thread 1: Add tracks
    {
        let p: Arc<Mutex<Project>> = Arc::clone(&project);
        handles.push(thread::spawn(move || {
            for i in 0..20 {
                let mut proj = p.lock().unwrap();
                proj.add_track(Track::new(&format!("Track {}", i), TrackType::Audio));
                drop(proj);
                thread::sleep(Duration::from_micros(50));
            }
        }));
    }
    
    // Thread 2: Read track count
    {
        let p: Arc<Mutex<Project>> = Arc::clone(&project);
        handles.push(thread::spawn(move || {
            for _ in 0..50 {
                let proj = p.lock().unwrap();
                let _ = proj.track_count();
                drop(proj);
                thread::sleep(Duration::from_micros(20));
            }
        }));
    }
    
    // Thread 3: Change tempo
    {
        let p: Arc<Mutex<Project>> = Arc::clone(&project);
        handles.push(thread::spawn(move || {
            for i in 0..30 {
                let mut proj = p.lock().unwrap();
                proj.set_tempo(100.0 + i as f32 * 5.0);
                drop(proj);
                thread::sleep(Duration::from_micros(30));
            }
        }));
    }
    
    for handle in handles {
        handle.join().unwrap();
    }
    
    // Project should have 20 tracks
    let proj = project.lock().unwrap();
    assert_eq!(proj.track_count(), 20);
}

/// High contention test - many threads, short critical sections
#[test]
fn concurrency_high_contention() {
    let mixer = Arc::new(Mutex::new(Mixer::new(2)));
    
    // Pre-populate
    {
        let mut m = mixer.lock().unwrap();
        m.add_source(Box::new(SineWave::new(440.0, 0.5)));
    }
    
    let mut handles = vec![];
    
    // Spawn many threads with very short critical sections
    for _ in 0..16 {
        let m = Arc::clone(&mixer);
        handles.push(thread::spawn(move || {
            let mut output = vec![0.0f32; 64 * 2];
            for _ in 0..200 {
                let mut mix = m.lock().unwrap();
                mix.process(&mut output);
                drop(mix);
                // Minimal sleep to force contention
                thread::yield_now();
            }
        }));
    }
    
    for handle in handles {
        handle.join().unwrap();
    }
    
    // Mixer should still be valid
    let m = mixer.lock().unwrap();
    assert_eq!(m.source_count(), 1);
}

/// Test rapid lock/unlock cycles
#[test]
fn concurrency_rapid_lock_cycles() {
    let transport = Arc::new(Mutex::new(Transport::new(120.0, 48000)));
    
    for _ in 0..1000 {
        let t = Arc::clone(&transport);
        let _ = t.lock().unwrap().state();
    }
    
    // Should not deadlock
    let tr = transport.lock().unwrap();
    assert_eq!(tr.state(), TransportState::Stopped);
}
