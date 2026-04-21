/* Vital FFI Stub for OpenDAW
 * Stub implementation until Vital library is integrated
 * License: GPL-3.0 (matches Vital)
 */

#include <string.h>

// Stub implementations
int vital_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* vital_ffi_get_version(void) {
    return "not-available";
}

// Synth creation
void* vital_ffi_create(float sample_rate) {
    return 0;
}

void vital_ffi_destroy(void* synth) {
}

// Processing
void vital_ffi_process(void* synth, float* left, float* right, int n_samples) {
}

void vital_ffi_play_note(void* synth, int note, int velocity) {
}

void vital_ffi_release_note(void* synth, int note) {
}

void vital_ffi_set_pitch_wheel(void* synth, float value) {
}

void vital_ffi_set_mod_wheel(void* synth, float value) {
}

// Parameters
int vital_ffi_set_parameter(void* synth, const char* name, float value) {
    return -1;
}

float vital_ffi_get_parameter(void* synth, const char* name) {
    return 0.0f;
}

// Presets
int vital_ffi_load_preset(void* synth, const char* path) {
    return -1;
}

int vital_ffi_get_preset_count(void* synth) {
    return 0;
}
