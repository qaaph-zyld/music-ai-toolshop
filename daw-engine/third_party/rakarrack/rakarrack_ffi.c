/* Rakarrack FFI Stub for OpenDAW
 * Stub implementation until Rakarrack library is integrated
 * License: GPL-2.0+ (matches Rakarrack)
 */

#include <string.h>
#include <stdlib.h>

// Stub implementations
int rakarrack_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* rakarrack_ffi_get_version(void) {
    return "not-available";
}

// Library
void* rakarrack_ffi_library_init(const char* path) {
    return NULL;
}

void rakarrack_ffi_library_free(void* library) {
}

int rakarrack_ffi_get_effect_count(void* library) {
    return 0;
}

int rakarrack_ffi_get_effect_info(void* library, int index, void* info) {
    return -1;
}

// Instance
void* rakarrack_ffi_instantiate(void* library, unsigned int effect_id, float sample_rate) {
    return NULL;
}

void rakarrack_ffi_cleanup(void* processor) {
}

void rakarrack_ffi_activate(void* processor) {
}

void rakarrack_ffi_deactivate(void* processor) {
}

void rakarrack_ffi_process(void* processor, const float** inputs, float** outputs, unsigned int sample_count) {
}

// Parameters
unsigned int rakarrack_ffi_get_param_count(void* processor) {
    return 0;
}

int rakarrack_ffi_get_param_info(void* processor, unsigned int index, void* info) {
    return -1;
}

void rakarrack_ffi_set_param(void* processor, unsigned int index, float value) {
}

float rakarrack_ffi_get_param(void* processor, unsigned int index) {
    return 0.0f;
}
