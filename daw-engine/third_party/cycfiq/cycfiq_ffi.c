/* Cycfi Q FFI Stub for OpenDAW
 * Stub implementation until Cycfi Q library is integrated
 * License: MIT (matches Cycfi Q)
 */

#include <string.h>

// Stub implementations
int q_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* q_ffi_get_version(void) {
    return "not-available";
}

// Pitch detection stubs
void* q_ffi_pitch_detector_create(int sample_rate) {
    return 0;
}

void q_ffi_pitch_detector_destroy(void* detector) {
}

int q_ffi_pitch_detector_process(
    void* detector,
    const float* input,
    int num_samples,
    float* frequency,
    float* confidence
) {
    return 0;
}

// Filter stubs
void* q_ffi_filter_create(int filter_type, float freq, float q, float gain, int sample_rate) {
    return 0;
}

void q_ffi_filter_destroy(void* filter) {
}

float q_ffi_filter_process(void* filter, float input) {
    return input;
}

void q_ffi_filter_process_block(
    void* filter,
    const float* input,
    float* output,
    int num_samples
) {
    for (int i = 0; i < num_samples; i++) {
        output[i] = input[i];
    }
}

// Envelope stubs
void* q_ffi_envelope_create(float attack_ms, float release_ms, int sample_rate) {
    return 0;
}

void q_ffi_envelope_destroy(void* envelope) {
}

float q_ffi_envelope_process(void* envelope, float input) {
    return input;
}
