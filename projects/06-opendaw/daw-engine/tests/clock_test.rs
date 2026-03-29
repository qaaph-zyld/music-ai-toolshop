//! Transport clock tests
//! 
//! Tests for sample-accurate timing.

use daw_engine::clock::TransportClock;

#[test]
fn test_clock_advances_at_sample_rate() {
    let mut clock = TransportClock::new(48000);
    clock.set_tempo(120.0);
    
    clock.advance(48000); // 1 second of samples
    
    assert_eq!(clock.beats(), 2.0); // At 120 BPM, 1 sec = 2 beats
}

#[test]
fn test_clock_different_tempo() {
    let mut clock = TransportClock::new(48000);
    clock.set_tempo(60.0); // Half the tempo
    
    clock.advance(48000); // 1 second
    
    assert_eq!(clock.beats(), 1.0); // At 60 BPM, 1 sec = 1 beat
}

#[test]
fn test_clock_different_sample_rate() {
    let mut clock = TransportClock::new(44100); // CD quality
    clock.set_tempo(120.0);
    
    clock.advance(44100); // 1 second at 44.1kHz
    
    assert_eq!(clock.beats(), 2.0); // Still 2 beats per second at 120 BPM
}

#[test]
fn test_clock_multiple_advances() {
    let mut clock = TransportClock::new(48000);
    clock.set_tempo(120.0);
    
    clock.advance(24000); // 0.5 sec
    assert_eq!(clock.beats(), 1.0);
    
    clock.advance(24000); // Another 0.5 sec
    assert_eq!(clock.beats(), 2.0);
}
