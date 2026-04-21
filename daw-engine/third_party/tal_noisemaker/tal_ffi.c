/* TAL-NoiseMaker FFI Stub for OpenDAW
 * Stub implementation until TAL-NoiseMaker library is integrated
 * License: GPL-3.0 (matches TAL-NoiseMaker)
 */

#include <string.h>
#include <stdlib.h>

// Stub implementations
int tal_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* tal_ffi_get_version(void) {
    return "not-available";
}

// Library
void* tal_ffi_library_init(const char* path) {
    return NULL;
}

void tal_ffi_library_free(void* library) {
}

int tal_ffi_get_info(void* library, void* info) {
    return -1;
}

unsigned int tal_ffi_get_preset_count(void* library) {
    return 0;
}

int tal_ffi_get_preset_info(void* library, unsigned int index, void* info) {
    return -1;
}

// Instance
void* tal_ffi_instantiate(void* library, float sample_rate) {
    return NULL;
}

void tal_ffi_cleanup(void* synth) {
}

void tal_ffi_midi_note_on(void* synth, int note, int velocity) {
}

void tal_ffi_midi_note_off(void* synth, int note) {
}

void tal_ffi_render(void* synth, float** outputs, unsigned int sample_count) {
}

void tal_ffi_set_preset(void* synth, unsigned int preset_index) {
}

// Parameters
unsigned int tal_ffi_get_param_count(void* synth) {
    return 0;
}

int tal_ffi_get_param_info(void* synth, unsigned int index, void* info) {
    return -1;
}

void tal_ffi_set_param(void* synth, unsigned int index, float value) {
}

float tal_ffi_get_param(void* synth, unsigned int index) {
    return 0.0f;
}
