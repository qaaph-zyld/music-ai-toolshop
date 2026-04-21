/* LADSPA FFI Stub for OpenDAW
 * Stub implementation until LADSPA library is integrated
 * License: LGPL-2.1+ (matches LADSPA)
 */

#include <string.h>
#include <stdlib.h>

// Stub implementations
int ladspa_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* ladspa_ffi_get_version(void) {
    return "not-available";
}

// Library
void* ladspa_ffi_library_init(const char* path) {
    return NULL;
}

void ladspa_ffi_library_free(void* library) {
}

int ladspa_ffi_library_get_descriptor_count(void* library) {
    return 0;
}

void* ladspa_ffi_library_get_descriptor(void* library, int index) {
    return NULL;
}

void* ladspa_ffi_library_get_descriptor_by_label(void* library, const char* label) {
    return NULL;
}

// Plugin info
unsigned int ladspa_ffi_descriptor_get_unique_id(void* descriptor) {
    return 0;
}

const char* ladspa_ffi_descriptor_get_label(void* descriptor) {
    return "";
}

const char* ladspa_ffi_descriptor_get_name(void* descriptor) {
    return "";
}

const char* ladspa_ffi_descriptor_get_maker(void* descriptor) {
    return "";
}

const char* ladspa_ffi_descriptor_get_copyright(void* descriptor) {
    return "";
}

unsigned int ladspa_ffi_descriptor_get_num_ports(void* descriptor) {
    return 0;
}

// Instance
void* ladspa_ffi_instantiate(void* descriptor, unsigned int sample_rate) {
    return NULL;
}

void ladspa_ffi_cleanup(void* descriptor, void* handle) {
}

void ladspa_ffi_activate(void* descriptor, void* handle) {
}

void ladspa_ffi_deactivate(void* descriptor, void* handle) {
}

void ladspa_ffi_run(void* descriptor, void* handle, unsigned int sample_count) {
}

// Port info
const char* ladspa_ffi_port_get_name(void* descriptor, unsigned int port_index) {
    return "";
}

int ladspa_ffi_port_is_audio(void* descriptor, unsigned int port_index) {
    return 0;
}

int ladspa_ffi_port_is_control(void* descriptor, unsigned int port_index) {
    return 0;
}

int ladspa_ffi_port_is_input(void* descriptor, unsigned int port_index) {
    return 0;
}

int ladspa_ffi_port_is_output(void* descriptor, unsigned int port_index) {
    return 0;
}

void ladspa_ffi_port_get_range(void* descriptor, unsigned int port_index, float* min, float* max, float* default_val) {
    if (min) *min = 0.0f;
    if (max) *max = 1.0f;
    if (default_val) *default_val = 0.5f;
}

// Port data
void ladspa_ffi_connect_port(void* descriptor, void* handle, unsigned int port, float* data) {
}
