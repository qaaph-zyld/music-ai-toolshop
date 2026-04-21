/* Invada Studio Plugins FFI Stub for OpenDAW
 * Stub implementation until Invada library is integrated
 * License: GPL-2.0+ (matches Invada)
 */

#include <string.h>
#include <stdlib.h>

// Stub implementations
int invada_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* invada_ffi_get_version(void) {
    return "not-available";
}

// Library
void* invada_ffi_library_init(const char* path) {
    return NULL;
}

void invada_ffi_library_free(void* library) {
}

int invada_ffi_get_plugin_count(void* library) {
    return 0;
}

int invada_ffi_get_plugin_info(void* library, int index, void* info) {
    return -1;
}

// Instance
void* invada_ffi_instantiate(void* library, unsigned int plugin_id, float sample_rate) {
    return NULL;
}

void invada_ffi_cleanup(void* plugin) {
}

void invada_ffi_activate(void* plugin) {
}

void invada_ffi_deactivate(void* plugin) {
}

void invada_ffi_process(void* plugin, const float** inputs, float** outputs, unsigned int sample_count) {
}

// Parameters
unsigned int invada_ffi_get_param_count(void* plugin) {
    return 0;
}

int invada_ffi_get_param_info(void* plugin, unsigned int index, void* info) {
    return -1;
}

void invada_ffi_set_param(void* plugin, unsigned int index, float value) {
}

float invada_ffi_get_param(void* plugin, unsigned int index) {
    return 0.0f;
}
