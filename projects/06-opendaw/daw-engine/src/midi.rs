//! MIDI support
//! 
//! MIDI message handling, note processing, and channel management.

/// MIDI message types
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum MidiMessage {
    /// Note on: (note, velocity, channel)
    NoteOn { note: u8, velocity: u8, channel: u8 },
    /// Note off: (note, velocity, channel)
    NoteOff { note: u8, velocity: u8, channel: u8 },
    /// Control change: (controller, value, channel)
    ControlChange { controller: u8, value: u8, channel: u8 },
    /// Program change: (program, channel)
    ProgramChange { program: u8, channel: u8 },
    /// Pitch bend: (value - 0-16383, channel)
    PitchBend { value: u16, channel: u8 },
}

impl MidiMessage {
    /// Create note on message
    pub fn note_on(note: u8, velocity: u8, channel: u8) -> Self {
        Self::NoteOn {
            note: note & 0x7F,
            velocity: velocity & 0x7F,
            channel: channel & 0x0F,
        }
    }
    
    /// Create note off message
    pub fn note_off(note: u8, channel: u8) -> Self {
        Self::NoteOff {
            note: note & 0x7F,
            velocity: 0,
            channel: channel & 0x0F,
        }
    }
    
    /// Create control change message
    pub fn control_change(controller: u8, value: u8, channel: u8) -> Self {
        Self::ControlChange {
            controller: controller & 0x7F,
            value: value & 0x7F,
            channel: channel & 0x0F,
        }
    }
    
    /// Create program change message
    pub fn program_change(program: u8, channel: u8) -> Self {
        Self::ProgramChange {
            program: program & 0x7F,
            channel: channel & 0x0F,
        }
    }
    
    /// Create pitch bend message
    pub fn pitch_bend(value: u16, channel: u8) -> Self {
        Self::PitchBend {
            value: value.min(16383),
            channel: channel & 0x0F,
        }
    }
    
    /// Get note number (for note on/off)
    pub fn note(&self) -> u8 {
        match self {
            Self::NoteOn { note, .. } | Self::NoteOff { note, .. } => *note,
            _ => 0,
        }
    }
    
    /// Get velocity (for note on/off)
    pub fn velocity(&self) -> u8 {
        match self {
            Self::NoteOn { velocity, .. } | Self::NoteOff { velocity, .. } => *velocity,
            _ => 0,
        }
    }
    
    /// Get channel
    pub fn channel(&self) -> u8 {
        match self {
            Self::NoteOn { channel, .. } => *channel,
            Self::NoteOff { channel, .. } => *channel,
            Self::ControlChange { channel, .. } => *channel,
            Self::ProgramChange { channel, .. } => *channel,
            Self::PitchBend { channel, .. } => *channel,
        }
    }
    
    /// Check if note on
    pub fn is_note_on(&self) -> bool {
        matches!(self, Self::NoteOn { .. })
    }
    
    /// Check if note off
    pub fn is_note_off(&self) -> bool {
        matches!(self, Self::NoteOff { .. })
    }
    
    /// Check if control change
    pub fn is_control_change(&self) -> bool {
        matches!(self, Self::ControlChange { .. })
    }
    
    /// Get controller number (for control change)
    pub fn controller_number(&self) -> u8 {
        match self {
            Self::ControlChange { controller, .. } => *controller,
            _ => 0,
        }
    }
    
    /// Get controller value (for control change)
    pub fn controller_value(&self) -> u8 {
        match self {
            Self::ControlChange { value, .. } => *value,
            _ => 0,
        }
    }
    
    /// Convert MIDI note to frequency (Hz)
    pub fn pitch_to_freq(pitch: u8) -> f32 {
        // A4 (MIDI 69) = 440Hz
        // Formula: 440 * 2^((pitch - 69) / 12)
        440.0 * 2.0f32.powf((pitch as f32 - 69.0) / 12.0)
    }
}

/// MIDI note with timing
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct MidiNote {
    pitch: u8,
    velocity: u8,
    start_beat: f32,
    duration_beats: f32,
}

impl MidiNote {
    /// Create new MIDI note
    pub fn new(pitch: u8, velocity: u8, start_beat: f32, duration_beats: f32) -> Self {
        Self {
            pitch: pitch & 0x7F,
            velocity: velocity & 0x7F,
            start_beat,
            duration_beats: duration_beats.max(0.0),
        }
    }
    
    /// Get pitch
    pub fn pitch(&self) -> u8 {
        self.pitch
    }
    
    /// Get velocity
    pub fn velocity(&self) -> u8 {
        self.velocity
    }
    
    /// Get start beat
    pub fn start_beat(&self) -> f32 {
        self.start_beat
    }
    
    /// Get duration in beats
    pub fn duration_beats(&self) -> f32 {
        self.duration_beats
    }
    
    /// Get end beat
    pub fn end_beat(&self) -> f32 {
        self.start_beat + self.duration_beats
    }
    
    /// Check if note is active at given beat
    pub fn is_active_at(&self, beat: f32) -> bool {
        beat >= self.start_beat && beat < self.end_beat()
    }
}

/// MIDI channel state
#[derive(Debug, Clone)]
struct ChannelState {
    notes: Vec<MidiNote>,
    playing_notes: Vec<u8>, // Currently playing note pitches
    controller_values: [u8; 128],
}

impl Default for ChannelState {
    fn default() -> Self {
        Self {
            notes: Vec::new(),
            playing_notes: Vec::new(),
            controller_values: [0; 128],
        }
    }
}

/// MIDI engine for processing notes and generating messages
#[derive(Debug)]
pub struct MidiEngine {
    channels: Vec<ChannelState>,
    current_beat: f32,
}

impl MidiEngine {
    /// Create new MIDI engine
    pub fn new(channel_count: usize) -> Self {
        Self {
            channels: vec![ChannelState::default(); channel_count],
            current_beat: -1.0, // Start at -1 so beat 0 triggers note on
        }
    }
    
    /// Add note to channel
    pub fn add_note(&mut self, channel: usize, note: MidiNote) {
        if let Some(ch) = self.channels.get_mut(channel) {
            ch.notes.push(note);
        }
    }
    
    /// Get notes for channel
    pub fn get_notes(&self, channel: usize) -> &[MidiNote] {
        self.channels
            .get(channel)
            .map(|ch| ch.notes.as_slice())
            .unwrap_or(&[])
    }
    
    /// Process at given beat, generate MIDI messages
    pub fn process(&mut self, beat: f32) -> Vec<MidiMessage> {
        let mut messages = Vec::new();
        
        for (channel_idx, channel) in self.channels.iter_mut().enumerate() {
            // Check which notes should trigger or release
            for note in &channel.notes {
                let channel_num = channel_idx as u8;
                
                // Note on: if we just crossed the start boundary
                if beat >= note.start_beat && self.current_beat < note.start_beat {
                    messages.push(MidiMessage::note_on(
                        note.pitch,
                        note.velocity,
                        channel_num,
                    ));
                    channel.playing_notes.push(note.pitch);
                }
                
                // Note off: if we just crossed the end boundary
                if beat >= note.end_beat() && self.current_beat < note.end_beat() {
                    messages.push(MidiMessage::note_off(note.pitch, channel_num));
                    channel.playing_notes.retain(|&n| n != note.pitch);
                }
            }
        }
        
        self.current_beat = beat;
        messages
    }
    
    /// Get current beat position
    pub fn current_beat(&self) -> f32 {
        self.current_beat
    }
    
    /// Stop all notes (panic)
    pub fn stop_all(&mut self) -> Vec<MidiMessage> {
        let mut messages = Vec::new();
        
        for (channel_idx, channel) in self.channels.iter_mut().enumerate() {
            for &pitch in &channel.playing_notes {
                messages.push(MidiMessage::note_off(pitch, channel_idx as u8));
            }
            channel.playing_notes.clear();
        }
        
        messages
    }
    
    /// Set controller value
    pub fn set_controller(&mut self, channel: usize, controller: u8, value: u8) {
        if let Some(ch) = self.channels.get_mut(channel) {
            ch.controller_values[(controller & 0x7F) as usize] = value & 0x7F;
        }
    }
    
    /// Get controller value
    pub fn get_controller(&self, channel: usize, controller: u8) -> u8 {
        self.channels
            .get(channel)
            .map(|ch| ch.controller_values[(controller & 0x7F) as usize])
            .unwrap_or(0)
    }
}
