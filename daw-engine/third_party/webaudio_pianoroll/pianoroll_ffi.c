/* webaudio_pianoroll FFI stub
 * 
 * This is a stub implementation for the webaudio-pianoroll library.
 * The full library is a JavaScript/WebAudio component, but this stub
 * provides the C FFI interface for future integration.
 * 
 * For now, all functions return "not available" status.
 */

#include <stdlib.h>
#include <string.h>

/* Opaque handle type */
typedef struct {
    int width;
    int height;
    int note_count;
} pianoroll_handle_t;

/* Create a new piano roll instance */
void* webaudio_pianoroll_create(int width, int height) {
    /* Stub: Return NULL to indicate not available */
    (void)width;
    (void)height;
    return NULL;
}

/* Destroy piano roll instance */
void webaudio_pianoroll_destroy(void* handle) {
    /* Stub: Nothing to clean up */
    (void)handle;
}

/* Check if library is available */
int webaudio_pianoroll_available(void) {
    /* Stub: Return 0 (false) - not available */
    return 0;
}

/* Add a note to the piano roll */
int webaudio_pianoroll_add_note(void* handle, int pitch, int velocity, 
                                  double start_time, double duration) {
    (void)handle;
    (void)pitch;
    (void)velocity;
    (void)start_time;
    (void)duration;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Remove a note by index */
int webaudio_pianoroll_remove_note(void* handle, int note_index) {
    (void)handle;
    (void)note_index;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Move a note to new position */
int webaudio_pianoroll_move_note(void* handle, int note_index, int new_pitch, 
                                 double new_start) {
    (void)handle;
    (void)note_index;
    (void)new_pitch;
    (void)new_start;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Resize a note */
int webaudio_pianoroll_resize_note(void* handle, int note_index, double new_duration) {
    (void)handle;
    (void)note_index;
    (void)new_duration;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Set note velocity */
int webaudio_pianoroll_set_velocity(void* handle, int note_index, int velocity) {
    (void)handle;
    (void)note_index;
    (void)velocity;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Set time signature */
int webaudio_pianoroll_set_time_signature(void* handle, int numerator, int denominator) {
    (void)handle;
    (void)numerator;
    (void)denominator;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Set grid division for quantization */
int webaudio_pianoroll_set_grid_division(void* handle, int division) {
    (void)handle;
    (void)division;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Select or deselect a note */
int webaudio_pianoroll_select_note(void* handle, int note_index, int selected) {
    (void)handle;
    (void)note_index;
    (void)selected;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Clear all selections */
int webaudio_pianoroll_clear_selection(void* handle) {
    (void)handle;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Set playback position */
int webaudio_pianoroll_set_playback_position(void* handle, double beat) {
    (void)handle;
    (void)beat;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Get number of notes */
int webaudio_pianoroll_get_note_count(void* handle) {
    (void)handle;
    /* Stub: Return 0 notes */
    return 0;
}

/* Clear all notes */
int webaudio_pianoroll_clear(void* handle) {
    (void)handle;
    /* Stub: Return -1 to indicate error */
    return -1;
}
