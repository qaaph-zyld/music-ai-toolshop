/**
 * Aubio FFI Stub
 * 
 * This is a stub implementation for the aubio C library.
 * The actual library (https://github.com/aubio/aubio) provides real-time
 * pitch detection, onset detection, and tempo analysis.
 * 
 * This stub returns not-available status until the real library is integrated.
 */

#include <stdlib.h>
#include <string.h>
#include <stdint.h>

// Stub pitch detector handle
typedef struct {
    int dummy;
} aubio_pitch_t;

// Stub onset detector handle
typedef struct {
    int dummy;
} aubio_onset_t;

// Stub tempo detector handle
typedef struct {
    int dummy;
} aubio_tempo_t;

// Pitch algorithms enum
enum {
    AUBIO_PITCH_YIN = 0,
    AUBIO_PITCH_YIN_FAST,
    AUBIO_PITCH_YIN_FFT,
    AUBIO_PITCH_SPEC,
    AUBIO_PITCH_SPEC_AC,
    AUBIO_PITCH_MCOMB
};

// Create pitch detector (returns NULL - not available)
void* pitch_new(int method, int buf_size, int hop_size, uint32_t sample_rate) {
    (void)method;
    (void)buf_size;
    (void)hop_size;
    (void)sample_rate;
    return NULL;  // Not available
}

// Delete pitch detector (no-op)
void pitch_del(void* pitch) {
    (void)pitch;
}

// Pitch detection (returns error)
int pitch_do(void* pitch, const float* input, float* output, float* confidence) {
    (void)pitch;
    (void)input;
    (void)output;
    (void)confidence;
    return -1;  // Error: not available
}

// Set pitch unit (no-op)
void pitch_set_unit(void* pitch, int unit) {
    (void)pitch;
    (void)unit;
}

// Set pitch tolerance (no-op)
void pitch_set_tolerance(void* pitch, float tolerance) {
    (void)pitch;
    (void)tolerance;
}

// Set pitch silence (no-op)
void pitch_set_silence(void* pitch, float silence) {
    (void)pitch;
    (void)silence;
}

// Create onset detector (returns NULL - not available)
void* onset_new(int buf_size, int hop_size, uint32_t sample_rate) {
    (void)buf_size;
    (void)hop_size;
    (void)sample_rate;
    return NULL;  // Not available
}

// Delete onset detector (no-op)
void onset_del(void* onset) {
    (void)onset;
}

// Onset detection (returns error)
int onset_do(void* onset, const float* input, int* is_onset, float* intensity) {
    (void)onset;
    (void)input;
    (void)is_onset;
    (void)intensity;
    return -1;  // Error: not available
}

// Set onset threshold (no-op)
void onset_set_threshold(void* onset, float threshold) {
    (void)onset;
    (void)threshold;
}

// Set onset min IOI (no-op)
void onset_set_min_ioi_ms(void* onset, float min_ioi) {
    (void)onset;
    (void)min_ioi;
}

// Get last onset time (returns 0)
float onset_get_last_s(void* onset) {
    (void)onset;
    return 0.0f;
}

// Create tempo detector (returns NULL - not available)
void* tempo_new(int buf_size, int hop_size, uint32_t sample_rate) {
    (void)buf_size;
    (void)hop_size;
    (void)sample_rate;
    return NULL;  // Not available
}

// Delete tempo detector (no-op)
void tempo_del(void* tempo) {
    (void)tempo;
}

// Tempo detection (returns error)
int tempo_do(void* tempo, const float* input, int* is_beat) {
    (void)tempo;
    (void)input;
    (void)is_beat;
    return -1;  // Error: not available
}

// Set tempo range (no-op)
void tempo_set_range(void* tempo, float min_bpm, float max_bpm) {
    (void)tempo;
    (void)min_bpm;
    (void)max_bpm;
}

// Get BPM (returns 0)
float tempo_get_bpm(void* tempo) {
    (void)tempo;
    return 0.0f;
}

// Get confidence (returns 0)
float tempo_get_confidence(void* tempo) {
    (void)tempo;
    return 0.0f;
}

// Get beat count (returns 0)
uint32_t tempo_get_beat(void* tempo) {
    (void)tempo;
    return 0;
}

// Get last beat time (returns 0)
float tempo_get_last_s(void* tempo) {
    (void)tempo;
    return 0.0f;
}
