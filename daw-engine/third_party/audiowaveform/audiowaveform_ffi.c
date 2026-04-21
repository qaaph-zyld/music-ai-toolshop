/* audiowaveform FFI stub
 * 
 * This is a stub implementation for the audiowaveform library (BBC).
 * Command-line tool for generating waveform data from audio files.
 * 
 * For now, all functions return "not available" status.
 */

#include <stdlib.h>
#include <string.h>

/* Opaque handle type */
typedef struct {
    int initialized;
    int has_data;
    int samples_per_pixel;
    int bits;
    int length;
} audiowaveform_handle_t;

/* Create a new waveform generator */
void* audiowaveform_create(void) {
    /* Stub: Return NULL to indicate not available */
    return NULL;
}

/* Destroy waveform generator */
void audiowaveform_destroy(void* handle) {
    /* Stub: Nothing to clean up */
    (void)handle;
}

/* Check if library is available */
int audiowaveform_available(void) {
    /* Stub: Return 0 (false) - not available */
    return 0;
}

/* Generate waveform from audio file */
int audiowaveform_generate(void* handle, const char* input_path,
                          const char* output_path, int format,
                          int samples_per_pixel, int bits) {
    (void)handle;
    (void)input_path;
    (void)output_path;
    (void)format;
    (void)samples_per_pixel;
    (void)bits;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Generate waveform for a time range */
int audiowaveform_generate_partial(void* handle, const char* input_path,
                                   const char* output_path, int format,
                                   int samples_per_pixel, int bits,
                                   double start_time, double end_time) {
    (void)handle;
    (void)input_path;
    (void)output_path;
    (void)format;
    (void)samples_per_pixel;
    (void)bits;
    (void)start_time;
    (void)end_time;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Analyze audio file */
int audiowaveform_analyze(void* handle, const char* input_path,
                         float* peak_amp, float* rms_amp, float* dc_offset,
                         float* true_peak, float* loudness) {
    (void)handle;
    (void)input_path;
    (void)peak_amp;
    (void)rms_amp;
    (void)dc_offset;
    (void)true_peak;
    (void)loudness;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Load existing waveform data */
int audiowaveform_load_data(void* handle, const char* data_path,
                           int* samples_per_pixel, int* bits, int* length) {
    (void)handle;
    (void)data_path;
    (void)samples_per_pixel;
    (void)bits;
    (void)length;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Get peak data */
int audiowaveform_get_peak_data(void* handle, short* min_data, short* max_data,
                               int offset, int count) {
    (void)handle;
    (void)min_data;
    (void)max_data;
    (void)offset;
    (void)count;
    /* Stub: Return -1 to indicate error */
    return -1;
}

/* Clear generator state */
int audiowaveform_clear(void* handle) {
    (void)handle;
    /* Stub: Return -1 to indicate error */
    return -1;
}
