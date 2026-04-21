/* Maximilian FFI Stub for OpenDAW
 * Stub implementation until Maximilian library is integrated
 * License: MIT (matches Maximilian)
 */

#include <string.h>

// Stub implementations
int maximilian_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* maximilian_ffi_get_version(void) {
    return "not-available";
}

// Oscillator stubs
void* maximilian_ffi_osc_create(int waveform, float freq, int sample_rate) {
    return 0;
}

void maximilian_ffi_osc_destroy(void* osc) {
}

void maximilian_ffi_osc_set_freq(void* osc, float freq) {
}

float maximilian_ffi_osc_process(void* osc) {
    return 0.0f;
}

// Envelope stubs
void* maximilian_ffi_env_create(float attack, float decay, float sustain, float release, int sample_rate) {
    return 0;
}

void maximilian_ffi_env_destroy(void* env) {
}

void maximilian_ffi_env_trigger(void* env) {
}

void maximilian_ffi_env_release(void* env) {
}

float maximilian_ffi_env_process(void* env) {
    return 0.0f;
}

int maximilian_ffi_env_is_active(void* env) {
    return 0;
}

// Filter stubs
void* maximilian_ffi_filter_create(int filter_type, float cutoff, float resonance, int sample_rate) {
    return 0;
}

void maximilian_ffi_filter_destroy(void* filter) {
}

void maximilian_ffi_filter_set_cutoff(void* filter, float cutoff) {
}

float maximilian_ffi_filter_process(void* filter, float input) {
    return input;
}

// Delay stubs
void* maximilian_ffi_delay_create(float delay_time_ms, float feedback, int sample_rate) {
    return 0;
}

void maximilian_ffi_delay_destroy(void* delay) {
}

void maximilian_ffi_delay_set_time(void* delay, float delay_time_ms) {
}

void maximilian_ffi_delay_set_feedback(void* delay, float feedback) {
}

float maximilian_ffi_delay_process(void* delay, float input) {
    return input;
}
