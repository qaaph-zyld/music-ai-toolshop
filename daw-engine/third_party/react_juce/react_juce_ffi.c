/* React-JUCE FFI Stub for OpenDAW
 * Stub implementation until React-JUCE is integrated
 * License: MIT (React-JUCE) + GPL/commercial (JUCE)
 */

#include <string.h>

// Stub implementations
int react_juce_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* react_juce_ffi_get_version(void) {
    return "not-available";
}

// Backend
void* react_juce_ffi_backend_new(void) {
    return 0;
}

void react_juce_ffi_backend_delete(void* backend) {
    // No-op
}

int react_juce_ffi_backend_init(void* backend, const char* bundle_path) {
    return -1;
}

int react_juce_ffi_backend_init_from_memory(void* backend,
                                            const char* bundle_data,
                                            int bundle_size) {
    return -1;
}

// Component management
void* react_juce_ffi_component_create(void* backend, const char* component_name) {
    return 0;
}

void react_juce_ffi_component_delete(void* component) {
    // No-op
}

int react_juce_ffi_component_set_props(void* component, const char* props_json) {
    return -1;
}

int react_juce_ffi_component_render(void* component) {
    return -1;
}

int react_juce_ffi_component_resize(void* component, int width, int height) {
    return -1;
}

// Native bridge
int react_juce_ffi_register_native_method(void* backend,
                                          const char* method_name,
                                          void* callback) {
    return -1;
}

const char* react_juce_ffi_call_js_method(void* backend,
                                          int component_id,
                                          const char* method_name,
                                          const char* args_json) {
    return "{}";
}

// Audio parameter bridge
int react_juce_ffi_register_parameter(void* backend,
                                       const char* param_id,
                                       int min_val, int max_val, int default_val) {
    return -1;
}

int react_juce_ffi_set_parameter_value(void* backend,
                                        const char* param_id,
                                        int value) {
    return -1;
}

int react_juce_ffi_get_parameter_value(void* backend, const char* param_id) {
    return 0;
}

// Hot reload
int react_juce_ffi_enable_hot_reload(void* backend, const char* watch_path) {
    return -1;
}

int react_juce_ffi_reload_bundle(void* backend) {
    return -1;
}
