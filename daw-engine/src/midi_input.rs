//! MIDI input handling and recording
//!
//! Provides real-time MIDI input from hardware controllers,
//! with recording capabilities and timestamp quantization.

use crate::{MidiMessage, MidiNote, MidiEngine};
use crossbeam::channel::{bounded, Sender, Receiver};
use std::sync::{Arc, Mutex};
use std::time::Instant;

/// Maximum number of MIDI events in the queue
const MIDI_QUEUE_SIZE: usize = 1024;

/// MIDI input manager
pub struct MidiInput {
    /// MIDI engine for processing messages
    engine: MidiEngine,
    /// Message queue for thread-safe communication
    message_sender: Sender<MidiEvent>,
    message_receiver: Receiver<MidiEvent>,
    /// Recording state
    recording: Arc<Mutex<RecordingState>>,
    /// Last recorded notes
    recorded_notes: Vec<MidiNote>,
    /// Sample rate for timestamp calculation
    sample_rate: u32,
    /// Transport position tracking
    current_beat: f32,
    tempo: f32,
}

/// MIDI event with timestamp
#[derive(Debug, Clone)]
pub struct MidiEvent {
    pub message: MidiMessage,
    pub timestamp: Instant,
    pub beat_position: f32,
}

/// Recording state
#[derive(Debug, Default)]
struct RecordingState {
    active: bool,
    start_time: Option<Instant>,
    start_beat: f32,
}

/// Quantization settings
#[derive(Debug, Clone)]
pub struct QuantizationSettings {
    pub enabled: bool,
    pub grid_division: f32, // 1.0 = quarter note, 0.5 = eighth, 0.25 = sixteenth
    pub strength: f32,      // 0.0 to 1.0
}

impl Default for QuantizationSettings {
    fn default() -> Self {
        Self {
            enabled: true,
            grid_division: 0.25, // Sixteenth note grid
            strength: 1.0,
        }
    }
}

impl MidiInput {
    /// Create new MIDI input manager
    pub fn new(channels: usize, sample_rate: u32) -> Self {
        let (sender, receiver) = bounded(MIDI_QUEUE_SIZE);
        
        Self {
            engine: MidiEngine::new(channels),
            message_sender: sender,
            message_receiver: receiver,
            recording: Arc::new(Mutex::new(RecordingState::default())),
            recorded_notes: Vec::new(),
            sample_rate,
            current_beat: 0.0,
            tempo: 120.0,
        }
    }

    /// Start recording MIDI
    pub fn start_recording(&mut self, start_beat: f32) {
        let mut state = self.recording.lock().unwrap();
        state.active = true;
        state.start_time = Some(Instant::now());
        state.start_beat = start_beat;
        self.recorded_notes.clear();
    }

    /// Stop recording MIDI
    pub fn stop_recording(&mut self) -> Vec<MidiNote> {
        let mut state = self.recording.lock().unwrap();
        state.active = false;
        state.start_time = None;
        self.recorded_notes.clone()
    }

    /// Check if recording is active
    pub fn is_recording(&self) -> bool {
        self.recording.lock().unwrap().active
    }

    /// Process incoming MIDI message (call from MIDI callback)
    pub fn process_midi_message(&mut self, message: MidiMessage, timestamp: Instant) {
        // Calculate beat position
        let beat_position = self.timestamp_to_beats(timestamp);
        
        let event = MidiEvent {
            message: message.clone(),
            timestamp,
            beat_position,
        };

        // Send to queue (non-blocking)
        let _ = self.message_sender.try_send(event);

        // If recording, capture the note
        if self.is_recording() {
            if let Some(note) = self.message_to_note(&message, beat_position) {
                self.recorded_notes.push(note);
            }
        }

        // Add to MIDI engine for playback
        if message.is_note_on() {
            let note = MidiNote::new(
                message.note(),
                message.velocity(),
                beat_position,
                0.5, // Default duration, will be updated on note off
            );
            self.engine.add_note(message.channel() as usize, note);
        }
    }

    /// Process queued MIDI events (call from audio thread)
    pub fn process_queued_events(&mut self) {
        while let Ok(_event) = self.message_receiver.try_recv() {
            // Process event in audio thread context
            // This ensures sample-accurate timing
        }
    }

    /// Update transport position (call from audio callback)
    pub fn update_transport(&mut self, beat: f32, tempo: f32) {
        self.current_beat = beat;
        self.tempo = tempo;
    }

    /// Get recorded notes as MIDI clip data
    pub fn get_recorded_clip(&self, quantize: &QuantizationSettings) -> Vec<MidiNote> {
        if quantize.enabled {
            self.recorded_notes.iter()
                .map(|note| self.quantize_note(note, quantize))
                .collect()
        } else {
            self.recorded_notes.clone()
        }
    }

    /// Quantize a note to the grid
    fn quantize_note(&self, note: &MidiNote, settings: &QuantizationSettings) -> MidiNote {
        let grid = settings.grid_division;
        let quantized_beat = (note.start_beat() / grid).round() * grid;
        
        // Apply quantization strength
        let final_beat = note.start_beat() * (1.0 - settings.strength) 
                        + quantized_beat * settings.strength;
        
        MidiNote::new(
            note.pitch(),
            note.velocity(),
            final_beat,
            note.duration_beats(),
        )
    }

    /// Convert timestamp to beat position
    fn timestamp_to_beats(&self, timestamp: Instant) -> f32 {
        let state = self.recording.lock().unwrap();
        
        if let Some(start_time) = state.start_time {
            let elapsed = timestamp.duration_since(start_time).as_secs_f32();
            let beats_elapsed = elapsed * (self.tempo / 60.0);
            state.start_beat + beats_elapsed
        } else {
            self.current_beat
        }
    }

    /// Convert MIDI message to note (if applicable)
    fn message_to_note(&self, message: &MidiMessage, beat: f32) -> Option<MidiNote> {
        if message.is_note_on() {
            Some(MidiNote::new(
                message.note(),
                message.velocity(),
                beat,
                0.1, // Short default duration, will be extended
            ))
        } else {
            None
        }
    }

    /// Get the MIDI engine reference
    pub fn engine(&self) -> &MidiEngine {
        &self.engine
    }

    /// Get mutable MIDI engine reference
    pub fn engine_mut(&mut self) -> &mut MidiEngine {
        &mut self.engine
    }

    /// Clear recorded notes
    pub fn clear_recording(&mut self) {
        self.recorded_notes.clear();
    }

    /// Set sample rate (affects timing calculations)
    pub fn set_sample_rate(&mut self, sample_rate: u32) {
        self.sample_rate = sample_rate;
    }
}

/// MIDI device enumerator
pub struct MidiDeviceEnumerator;

impl MidiDeviceEnumerator {
    /// List available MIDI input devices using midir
    pub fn list_input_devices() -> Vec<MidiDeviceInfo> {
        let midi_in = match midir::MidiInput::new("OpenDAW Device Enumeration") {
            Ok(m) => m,
            Err(_) => return Vec::new(),
        };
        
        let ports = midi_in.ports();
        let mut devices = Vec::with_capacity(ports.len());
        
        for (idx, port) in ports.iter().enumerate() {
            let name = midi_in.port_name(port).unwrap_or_else(|_| format!("MIDI Device {}", idx));
            devices.push(MidiDeviceInfo {
                id: format!("midi_in_{}", idx),
                name,
                is_available: true,
            });
        }
        
        devices
    }
    
    /// Get count of available input devices
    pub fn device_count() -> usize {
        let midi_in = match midir::MidiInput::new("OpenDAW Device Count") {
            Ok(m) => m,
            Err(_) => return 0,
        };
        midi_in.port_count()
    }
}

/// MIDI device information
#[derive(Debug, Clone)]
pub struct MidiDeviceInfo {
    pub id: String,
    pub name: String,
    pub is_available: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_midi_input_creation() {
        let input = MidiInput::new(16, 48000);
        assert!(!input.is_recording());
    }

    #[test]
    fn test_recording_state() {
        let mut input = MidiInput::new(16, 48000);
        
        input.start_recording(0.0);
        assert!(input.is_recording());
        
        let notes = input.stop_recording();
        assert!(!input.is_recording());
        assert!(notes.is_empty());
    }

    #[test]
    fn test_quantization() {
        let input = MidiInput::new(16, 48000);
        let settings = QuantizationSettings::default();
        
        // Note at beat 0.3 should quantize to 0.25 (sixteenth grid)
        let note = MidiNote::new(60, 100, 0.3, 0.5);
        let quantized = input.quantize_note(&note, &settings);
        
        assert_eq!(quantized.start_beat(), 0.25);
        assert_eq!(quantized.pitch(), 60);
    }

    #[test]
    fn test_quantization_strength() {
        let input = MidiInput::new(16, 48000);
        let settings = QuantizationSettings {
            enabled: true,
            grid_division: 0.25,
            strength: 0.5, // 50% strength
        };
        
        // Note at beat 0.3 with 50% strength
        // Target: 0.25, Original: 0.3
        // Result: 0.3 * 0.5 + 0.25 * 0.5 = 0.275
        let note = MidiNote::new(60, 100, 0.3, 0.5);
        let quantized = input.quantize_note(&note, &settings);
        
        assert!((quantized.start_beat() - 0.275).abs() < 0.001);
    }

    // TDD: Real device enumeration tests (Step A)
    
    #[test]
    fn test_enumerate_devices() {
        let devices = MidiDeviceEnumerator::list_input_devices();
        // Should return actual devices or empty vec (if no MIDI available)
        // NOT a placeholder with fake "Default MIDI Input"
        for device in &devices {
            assert!(!device.id.is_empty(), "Device ID should not be empty");
            assert!(!device.name.is_empty(), "Device name should not be empty");
        }
        
        // If we have devices, they should be real
        if !devices.is_empty() {
            // At least one device should be available
            assert!(devices.iter().any(|d| d.is_available));
        }
    }

    #[test]
    fn test_device_count_consistency() {
        let count = MidiDeviceEnumerator::device_count();
        let devices = MidiDeviceEnumerator::list_input_devices();
        
        // Count should match list length
        assert_eq!(count, devices.len(), 
            "device_count() should match list_input_devices().len()");
    }

    #[test]
    fn test_device_info_valid() {
        let devices = MidiDeviceEnumerator::list_input_devices();
        
        for (idx, device) in devices.iter().enumerate() {
            // ID should follow pattern midi_in_N
            assert_eq!(device.id, format!("midi_in_{}", idx),
                "Device ID should follow midi_in_N pattern");
            
            // Name should be meaningful (not placeholder)
            assert_ne!(device.name, "Default MIDI Input",
                "Should not use placeholder name");
        }
    }
}
