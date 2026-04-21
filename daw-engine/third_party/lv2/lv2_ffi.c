/* LV2/Lilv FFI Stub for OpenDAW
 * Stub implementation until Lilv library is integrated
 * License: ISC (matches Lilv)
 */

#include <string.h>

// Stub implementations
int lv2_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* lv2_ffi_get_version(void) {
    return "not-available";
}

// World
void* lv2_ffi_world_new(void) {
    return 0;
}

void lv2_ffi_world_free(void* world) {
}

void lv2_ffi_world_load_all(void* world) {
}

void* lv2_ffi_world_get_all_plugins(void* world) {
    return 0;
}

// Plugin discovery
int lv2_ffi_plugins_get_size(void* plugins) {
    return 0;
}

void* lv2_ffi_plugins_get_plugin(void* plugins, int index) {
    return 0;
}

void* lv2_ffi_plugins_get_by_uri(void* world, const char* uri) {
    return 0;
}

// Plugin info
const char* lv2_ffi_plugin_get_uri(void* plugin) {
    return "";
}

const char* lv2_ffi_plugin_get_name(void* plugin) {
    return "";
}

const char* lv2_ffi_plugin_get_author_name(void* plugin) {
    return "";
}

const char* lv2_ffi_plugin_get_license(void* plugin) {
    return "";
}

unsigned int lv2_ffi_plugin_get_num_ports(void* plugin) {
    return 0;
}

int lv2_ffi_plugin_has_feature(void* plugin, const char* feature) {
    return 0;
}

// Port info
void* lv2_ffi_plugin_get_port_by_index(void* plugin, unsigned int index) {
    return 0;
}

void* lv2_ffi_plugin_get_port_by_symbol(void* plugin, const char* symbol) {
    return 0;
}

const char* lv2_ffi_port_get_name(void* plugin, void* port) {
    return "";
}

const char* lv2_ffi_port_get_symbol(void* plugin, void* port) {
    return "";
}

int lv2_ffi_port_is_a(void* plugin, void* port, const char* class_uri) {
    return 0;
}

void lv2_ffi_port_get_range(void* plugin, void* port, float* min, float* max, float* def) {
    if (min) *min = 0.0f;
    if (max) *max = 1.0f;
    if (def) *def = 0.5f;
}
