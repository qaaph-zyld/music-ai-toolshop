/* peaks FFI stub
 * 
 * This is a stub implementation for the peaks.js library (BBC R&D).
 * A high-performance waveform visualization component.
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
    int zoom_level;
    double offset;
} peaks_handle_t;

/* Create a new Peaks viewer instance */
void* peaks_create(const char* container_id, int width, int height) {
    /* Stub: Return NULL to indicate not available */
    (void)container_id;
    (void)width;
    (void)height;
    return NULL;
}

/* Destroy Peaks instance */
void peaks_destroy(void* handle) {
    /* Stub: Nothing to clean up */
    (void)handle;
}

/* Check if library is available */
int peaks_available(void) {
    /* Stub: Return 0 (false) - not available */
    return 0;
}

/* Load waveform data */
int peaks_load_data(void* handle, const float* peaks_data, int length,
                    int channels, int sample_rate) {
    (void)handle;
    (void)peaks_data;
    (void)length;
    (void)channels;
    (void)sample_rate;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Set zoom level (samples per pixel) */
int peaks_set_zoom(void* handle, int samples_per_pixel) {
    (void)handle;
    (void)samples_per_pixel;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Get current zoom level */
int peaks_get_zoom(void* handle) {
    (void)handle;
    /* Stub: Return 0 */
    return 0;
}

/* Set view offset (start time) */
int peaks_set_offset(void* handle, double time) {
    (void)handle;
    (void)time;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Get current offset */
double peaks_get_offset(void* handle) {
    (void)handle;
    /* Stub: Return 0.0 */
    return 0.0;
}

/* Add a segment */
int peaks_add_segment(void* handle, const char* id, double start_time,
                     double end_time, const char* label, unsigned int color,
                     int editable) {
    (void)handle;
    (void)id;
    (void)start_time;
    (void)end_time;
    (void)label;
    (void)color;
    (void)editable;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Remove a segment */
int peaks_remove_segment(void* handle, const char* segment_id) {
    (void)handle;
    (void)segment_id;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Clear all segments */
int peaks_clear_segments(void* handle) {
    (void)handle;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Add a point marker */
int peaks_add_point(void* handle, const char* id, double time,
                   const char* label, unsigned int color, int editable) {
    (void)handle;
    (void)id;
    (void)time;
    (void)label;
    (void)color;
    (void)editable;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Remove a point marker */
int peaks_remove_point(void* handle, const char* point_id) {
    (void)handle;
    (void)point_id;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Clear all point markers */
int peaks_clear_points(void* handle) {
    (void)handle;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Set view window (start and end time) */
int peaks_set_view(void* handle, double start, double end) {
    (void)handle;
    (void)start;
    (void)end;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Get audio duration */
double peaks_get_duration(void* handle) {
    (void)handle;
    /* Stub: Return 0.0 */
    return 0.0;
}

/* Seek to time */
int peaks_seek(void* handle, double time) {
    (void)handle;
    (void)time;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Resize viewer */
int peaks_resize(void* handle, int width, int height) {
    (void)handle;
    (void)width;
    (void)height;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Clear all data */
int peaks_clear(void* handle) {
    (void)handle;
    /* Stub: Return -1 to indicate error */
    return -1;
}
