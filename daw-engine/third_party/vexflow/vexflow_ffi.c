/* vexflow FFI stub
 * 
 * This is a stub implementation for the VexFlow library.
 * JavaScript library for rendering musical notation in SVG.
 * 
 * For now, all functions return "not available" status.
 */

#include <stdlib.h>
#include <string.h>

/* Opaque handle type */
typedef struct {
    int width;
    int height;
    int use_svg;
    int staff_count;
    int note_count;
} vexflow_handle_t;

/* Create a new VexFlow renderer */
void* vexflow_create(int width, int height, int use_svg) {
    /* Stub: Return NULL to indicate not available */
    (void)width;
    (void)height;
    (void)use_svg;
    return NULL;
}

/* Destroy VexFlow renderer */
void vexflow_destroy(void* handle) {
    /* Stub: Nothing to clean up */
    (void)handle;
}

/* Check if library is available */
int vexflow_available(void) {
    /* Stub: Return 0 (false) - not available */
    return 0;
}

/* Add a staff */
int vexflow_add_staff(void* handle, int staff_type, int x, int y, int width) {
    (void)handle;
    (void)staff_type;
    (void)x;
    (void)y;
    (void)width;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Set clef for a staff */
int vexflow_set_clef(void* handle, int staff_id, int clef) {
    (void)handle;
    (void)staff_id;
    (void)clef;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Set key signature */
int vexflow_set_key_signature(void* handle, int staff_id, int key) {
    (void)handle;
    (void)staff_id;
    (void)key;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Set time signature */
int vexflow_set_time_signature(void* handle, int staff_id, int numerator, int denominator) {
    (void)handle;
    (void)staff_id;
    (void)numerator;
    (void)denominator;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Add a note to a staff */
int vexflow_add_note(void* handle, int staff_id, const char* note_json) {
    (void)handle;
    (void)staff_id;
    (void)note_json;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Add a chord */
int vexflow_add_chord(void* handle, int staff_id, const char* chord_json) {
    (void)handle;
    (void)staff_id;
    (void)chord_json;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Add a rest */
int vexflow_add_rest(void* handle, int staff_id, const char* duration, double position) {
    (void)handle;
    (void)staff_id;
    (void)duration;
    (void)position;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Add a tie between notes */
int vexflow_add_tie(void* handle, int from_note, int to_note) {
    (void)handle;
    (void)from_note;
    (void)to_note;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Add a beam group */
int vexflow_add_beam(void* handle, const int* note_indices, int count) {
    (void)handle;
    (void)note_indices;
    (void)count;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Render the score */
int vexflow_render(void* handle) {
    (void)handle;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Get SVG output */
int vexflow_get_svg(void* handle, char* buffer, int buffer_size) {
    (void)handle;
    (void)buffer;
    (void)buffer_size;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Clear the score */
int vexflow_clear(void* handle) {
    (void)handle;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Resize the renderer */
int vexflow_resize(void* handle, int width, int height) {
    (void)handle;
    (void)width;
    (void)height;
    /* Stub: Return -1 to indicate error */
    return -1;
}
