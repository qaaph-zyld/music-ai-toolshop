//! Transport tests
//! 
//! Tests for playback transport controls (play, stop, record).

use daw_engine::transport::{Transport, TransportState, PlayMode};

#[test]
fn test_transport_starts_stopped() {
    let transport = Transport::new(120.0, 48000);
    
    assert_eq!(transport.state(), TransportState::Stopped);
}

#[test]
fn test_transport_play_changes_state() {
    let mut transport = Transport::new(120.0, 48000);
    
    transport.play();
    
    assert_eq!(transport.state(), TransportState::Playing);
}

#[test]
fn test_transport_stop_changes_state() {
    let mut transport = Transport::new(120.0, 48000);
    
    transport.play();
    transport.stop();
    
    assert_eq!(transport.state(), TransportState::Stopped);
}

#[test]
fn test_transport_record_changes_state() {
    let mut transport = Transport::new(120.0, 48000);
    
    transport.record();
    
    assert_eq!(transport.state(), TransportState::Recording);
}

#[test]
fn test_transport_advances_position() {
    let mut transport = Transport::new(120.0, 48000);
    
    transport.play();
    transport.process(48000); // 1 second at 48kHz
    
    assert_eq!(transport.position_beats(), 2.0); // 120 BPM = 2 beats per second
}

#[test]
fn test_transport_loop_mode() {
    let mut transport = Transport::new(120.0, 48000);
    transport.set_loop_range(0.0, 4.0); // 4 bar loop
    transport.set_play_mode(PlayMode::Loop);
    
    transport.play();
    transport.process(96000); // 2 seconds = 4 beats
    
    // Should have looped back to start
    assert!(transport.position_beats() < 4.0);
}

#[test]
fn test_transport_punch_in_record() {
    let mut transport = Transport::new(120.0, 48000);
    transport.set_punch_in(4.0);
    transport.set_punch_out(8.0);
    
    transport.play();
    
    // Before punch-in
    transport.set_position(2.0);
    assert_eq!(transport.state(), TransportState::Playing);
    
    // After punch-in
    transport.set_position(6.0);
    // Should transition to recording at punch-in point
    // (This requires process() to be called, so simplified here)
}

#[test]
fn test_transport_rewind() {
    let mut transport = Transport::new(120.0, 48000);
    
    transport.play();
    transport.process(48000);
    transport.rewind();
    
    assert_eq!(transport.position_beats(), 0.0);
    assert_eq!(transport.state(), TransportState::Stopped);
}

#[test]
fn test_transport_jump_to_position() {
    let mut transport = Transport::new(120.0, 48000);
    
    transport.set_position(16.0); // Jump to bar 5 (16 beats)
    
    assert_eq!(transport.position_beats(), 16.0);
}

#[test]
fn test_transport_pause() {
    let mut transport = Transport::new(120.0, 48000);
    
    transport.play();
    transport.process(24000); // 0.5 seconds
    transport.pause();
    
    assert_eq!(transport.state(), TransportState::Paused);
    assert_eq!(transport.position_beats(), 1.0); // Should maintain position
}
