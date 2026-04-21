/* wavesurfer FFI stub
 * 
 * This is a stub implementation for the wavesurfer.js library.
 * The full library is a JavaScript/WebAudio component for waveform
 * visualization. This stub provides the C FFI interface.
 * 
 * For now, all functions return "not available" status.
 */

#include <stdlib.h>
#include <string.h>

/* Opaque handle type */
typedef struct {
    char container_id[256];
    int width;
    int height;
    double duration;
    float zoom_level;
} wavesurfer_handle_t;

/* Create a new WaveSurfer instance */
void* wavesurfer_create(const char* container_id, int width, int height) {
    /* Stub: Return NULL to indicate not available */
    (void)container_id;
    (void)width;
    (void)height;
    return NULL;
}

/* Destroy WaveSurfer instance */
void wavesurfer_destroy(void* handle) {
    /* Stub: Nothing to clean up */
    (void)handle;
}

/* Check if library is available */
int wavesurfer_available(void) {
    /* Stub: Return 0 (false) - not available */
    return 0;
}

/* Load audio buffer */
int wavesurfer_load_buffer(void* handle, const float* buffer, int length, 
                           int channels, int sample_rate) {
    (void)handle;
    (void)buffer;
    (void)length;
    (void)channels;
    (void)sample_rate;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Set zoom level (pixels per second) */
int wavesurfer_set_zoom(void* handle, float pixels_per_second) {
    (void)handle;
    (void)pixels_per_second;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Get current zoom level */
float wavesurfer_get_zoom(void* handle) {
    (void)handle;
    /* Stub: Return 0.0 */
    return 0.0f;
}

/* Add a region */
int wavesurfer_add_region(void* handle, double start, double end, unsigned int color) {
    (void)handle;
    (void)start;
    (void)end;
    (void)color;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Remove a region */
int wavesurfer_remove_region(void* handle, int region_id) {
    (void)handle;
    (void)region_id;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Clear all regions */
int wavesurfer_clear_regions(void* handle) {
    (void)handle;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Set cursor position */
int wavesurfer_set_cursor(void* handle, double position) {
    (void)handle;
    (void)position;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Set cursor visibility */
int wavesurfer_set_cursor_visible(void* handle, int visible) {
    (void)handle;
    (void)visible;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Set waveform color */
int wavesurfer_set_wave_color(void* handle, unsigned int color) {
    (void)handle;
    (void)color;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Set progress color */
int wavesurfer_set_progress_color(void* handle, unsigned int color) {
    (void)handle;
    (void)color;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Get audio duration */
double wavesurfer_get_duration(void* handle) {
    (void)handle;
    /* Stub: Return 0.0 */
    return 0.0;
}

/* Clear waveform */
int wavesurfer_clear(void* handle) {
    (void)handle;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Resize container */
int wavesurfer_resize(void* handle, int width, int height) {
    (void)handle;
    (void)width;
    (void)height;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Zoom in */
int wavesurfer_zoom_in(void* handle, float factor) {
    (void)handle;
    (void)factor;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Zoom out */
int wavesurfer_zoom_out(void* handle, float factor) {
    (void)handle;
    (void)factor;
    /* Stub: Return -1 to indicate error */
    return -1;
}
