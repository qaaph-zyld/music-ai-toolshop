//! FFI exports for MIDI editing operations
//!
//! Provides C-compatible exports for quantization, transpose, duplication,
//! and note manipulation from the JUCE UI.

use std::ffi::c_int;
use std::sync::Mutex;
use crate::midi_edit::MidiEditor;
use crate::MidiNote;

/// Opaque handle for MIDI editor state
static MIDI_EDITOR: Mutex<Option<MidiEditor>> = Mutex::new(None);

/// Ensure editor is initialized
fn ensure_editor() {
    let mut guard = MIDI_EDITOR.lock().unwrap();
    if guard.is_none() {
        *guard = Some(MidiEditor::new());
    }
}

/// C-compatible MIDI note structure for FFI
#[repr(C)]
pub struct MidiNoteData {
    pub pitch: c_int,
    pub velocity: c_int,
    pub start_beat: f32,
    pub duration_beats: f32,
}

/// Initialize MIDI editor (call once at startup)
#[no_mangle]
pub extern "C" fn daw_midi_edit_init() {
    ensure_editor();
}

/// Quantize notes to a grid
/// 
/// # Arguments
/// * `notes_in` - Array of input notes
/// * `note_count` - Number of notes
/// * `grid_division` - Grid size in beats (0.25 = 1/16, 0.5 = 1/8)
/// * `notes_out` - Output buffer for quantized notes (pre-allocated)
/// 
/// # Returns
/// Number of notes written to output
#[no_mangle]
pub extern "C" fn daw_midi_quantize(
    notes_in: *const MidiNoteData,
    note_count: c_int,
    grid_division: f32,
    notes_out: *mut MidiNoteData,
) -> c_int {
    if notes_in.is_null() || notes_out.is_null() || note_count <= 0 {
        return 0;
    }
    
    ensure_editor();
    
    let input_slice = unsafe {
        std::slice::from_raw_parts(notes_in, note_count as usize)
    };
    
    let notes: Vec<MidiNote> = input_slice.iter().map(|n| {
        MidiNote::new(
            n.pitch.clamp(0, 127) as u8,
            n.velocity.clamp(0, 127) as u8,
            n.start_beat.max(0.0),
            n.duration_beats.max(0.0),
        )
    }).collect();
    
    let mut editor = MIDI_EDITOR.lock().unwrap();
    let quantized = editor.as_mut().unwrap().quantize(&notes, grid_division);
    
    let output_slice = unsafe {
        std::slice::from_raw_parts_mut(notes_out, note_count as usize)
    };
    
    for (i, note) in quantized.iter().enumerate() {
        if i < output_slice.len() {
            output_slice[i] = MidiNoteData {
                pitch: note.pitch() as c_int,
                velocity: note.velocity() as c_int,
                start_beat: note.start_beat(),
                duration_beats: note.duration_beats(),
            };
        }
    }
    
    note_count
}

/// Transpose notes by semitones
/// 
/// # Arguments
/// * `notes_in` - Array of input notes
/// * `note_count` - Number of notes
/// * `semitones` - Semitones to shift (positive = up, negative = down)
/// * `notes_out` - Output buffer for transposed notes
/// 
/// # Returns
/// Number of notes written to output
#[no_mangle]
pub extern "C" fn daw_midi_transpose(
    notes_in: *const MidiNoteData,
    note_count: c_int,
    semitones: c_int,
    notes_out: *mut MidiNoteData,
) -> c_int {
    if notes_in.is_null() || notes_out.is_null() || note_count <= 0 {
        return 0;
    }
    
    ensure_editor();
    
    let input_slice = unsafe {
        std::slice::from_raw_parts(notes_in, note_count as usize)
    };
    
    let notes: Vec<MidiNote> = input_slice.iter().map(|n| {
        MidiNote::new(
            n.pitch.clamp(0, 127) as u8,
            n.velocity.clamp(0, 127) as u8,
            n.start_beat.max(0.0),
            n.duration_beats.max(0.0),
        )
    }).collect();
    
    let mut editor = MIDI_EDITOR.lock().unwrap();
    let transposed = editor.as_mut().unwrap().transpose(&notes, semitones);
    
    let output_slice = unsafe {
        std::slice::from_raw_parts_mut(notes_out, note_count as usize)
    };
    
    for (i, note) in transposed.iter().enumerate() {
        if i < output_slice.len() {
            output_slice[i] = MidiNoteData {
                pitch: note.pitch() as c_int,
                velocity: note.velocity() as c_int,
                start_beat: note.start_beat(),
                duration_beats: note.duration_beats(),
            };
        }
    }
    
    note_count
}

/// Scale velocities by a factor
/// 
/// # Arguments
/// * `notes_in` - Array of input notes
/// * `note_count` - Number of notes
/// * `scale` - Scale factor (1.0 = no change)
/// * `notes_out` - Output buffer
/// 
/// # Returns
/// Number of notes written to output
#[no_mangle]
pub extern "C" fn daw_midi_scale_velocity(
    notes_in: *const MidiNoteData,
    note_count: c_int,
    scale: f32,
    notes_out: *mut MidiNoteData,
) -> c_int {
    if notes_in.is_null() || notes_out.is_null() || note_count <= 0 {
        return 0;
    }
    
    ensure_editor();
    
    let input_slice = unsafe {
        std::slice::from_raw_parts(notes_in, note_count as usize)
    };
    
    let notes: Vec<MidiNote> = input_slice.iter().map(|n| {
        MidiNote::new(
            n.pitch.clamp(0, 127) as u8,
            n.velocity.clamp(0, 127) as u8,
            n.start_beat.max(0.0),
            n.duration_beats.max(0.0),
        )
    }).collect();
    
    let mut editor = MIDI_EDITOR.lock().unwrap();
    let scaled = editor.as_mut().unwrap().scale_velocity(&notes, scale);
    
    let output_slice = unsafe {
        std::slice::from_raw_parts_mut(notes_out, note_count as usize)
    };
    
    for (i, note) in scaled.iter().enumerate() {
        if i < output_slice.len() {
            output_slice[i] = MidiNoteData {
                pitch: note.pitch() as c_int,
                velocity: note.velocity() as c_int,
                start_beat: note.start_beat(),
                duration_beats: note.duration_beats(),
            };
        }
    }
    
    note_count
}

/// Get the number of notes in a clip (placeholder for session-based operations)
/// 
/// In the full implementation, this would query the session for clip note count.
/// For now, this is a stub that will be implemented when session FFI is extended.
#[no_mangle]
pub extern "C" fn daw_midi_get_clip_note_count(clip_id: c_int) -> c_int {
    // Placeholder - will be implemented with full session integration
    // For now, return 0 to indicate no notes or clip not found
    if clip_id < 0 {
        return -1; // Error indicator
    }
    0 // Placeholder
}

use crate::ffi_bridge::DawEngine;
use std::ffi::c_void;

/// Duplicate a MIDI clip to another location in the session
/// 
/// # Arguments
/// * `engine_ptr` - Pointer to DawEngine instance
/// * `from_track` - Source track index
/// * `from_scene` - Source scene index  
/// * `to_track` - Target track index
/// * `to_scene` - Target scene index
/// 
/// # Returns
/// 0 on success, -1 on error
/// 
/// # Safety
/// engine_ptr must be a valid pointer to DawEngine instance
#[no_mangle]
pub unsafe extern "C" fn daw_midi_duplicate_clip(
    engine_ptr: *mut c_void,
    from_track: c_int,
    from_scene: c_int,
    to_track: c_int,
    to_scene: c_int,
) -> c_int {
    // Validate pointers and indices
    if engine_ptr.is_null() {
        return -1;
    }
    if from_track < 0 || from_scene < 0 || to_track < 0 || to_scene < 0 {
        return -1;
    }
    
    let engine = &*(engine_ptr as *mut DawEngine);
    
    // Lock session for access
    match engine.session().lock() {
        Ok(mut session) => {
            let from_track = from_track as usize;
            let from_scene = from_scene as usize;
            let to_track = to_track as usize;
            let to_scene = to_scene as usize;
            
            // Check bounds
            let track_count = session.track_count();
            let scene_count = session.scene_count();
            if from_track >= track_count || to_track >= track_count {
                return -1;
            }
            if from_scene >= scene_count || to_scene >= scene_count {
                return -1;
            }
            
            // Get source clip
            let source_notes: Vec<crate::MidiNote> = if let Some(source_clip) = session.get_clip(from_track, from_scene) {
                // Check if it's a MIDI clip (has notes)
                if !source_clip.is_midi() {
                    return -1; // Cannot duplicate audio clips via MIDI function
                }
                source_clip.midi_notes().to_vec()
            } else {
                return -1; // No clip at source location
            };
            
            // Get clip name for the duplicate
            let name: String = session.get_clip(from_track, from_scene)
                .map(|c: &crate::session::Clip| c.name().to_string())
                .unwrap_or_else(|| "Duplicated Clip".to_string());
            
            // Create duplicate clip at destination
            if session.create_midi_clip(to_track, to_scene, source_notes, &name) {
                0 // Success
            } else {
                -1 // Failed to create clip
            }
        }
        Err(_) => -1, // Failed to lock session
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ffi_quantize() {
        daw_midi_edit_init();
        
        let input = [
            MidiNoteData { pitch: 60, velocity: 100, start_beat: 0.05, duration_beats: 0.5 },
        ];
        let mut output = [MidiNoteData { pitch: 0, velocity: 0, start_beat: 0.0, duration_beats: 0.0 }];
        
        let count = daw_midi_quantize(input.as_ptr(), 1, 0.25, output.as_mut_ptr());
        
        assert_eq!(count, 1);
        assert!((output[0].start_beat - 0.0).abs() < 0.001);
    }

    #[test]
    fn test_ffi_transpose() {
        daw_midi_edit_init();
        
        let input = [
            MidiNoteData { pitch: 60, velocity: 100, start_beat: 0.0, duration_beats: 1.0 },
        ];
        let mut output = [MidiNoteData { pitch: 0, velocity: 0, start_beat: 0.0, duration_beats: 0.0 }];
        
        let count = daw_midi_transpose(input.as_ptr(), 1, 12, output.as_mut_ptr());
        
        assert_eq!(count, 1);
        assert_eq!(output[0].pitch, 72);
    }

    #[test]
    fn test_ffi_null_safety() {
        // Test that null pointers don't crash
        let result = daw_midi_quantize(std::ptr::null(), 5, 0.25, std::ptr::null_mut());
        assert_eq!(result, 0);
        
        let result = daw_midi_transpose(std::ptr::null(), 5, 12, std::ptr::null_mut());
        assert_eq!(result, 0);
    }
}
