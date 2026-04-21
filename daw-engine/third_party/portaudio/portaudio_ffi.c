/* PortAudio FFI Stub for OpenDAW
 * Stub implementation until PortAudio library is integrated
 * License: MIT (matches PortAudio)
 */

#include <string.h>

// Stub implementations
int portaudio_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* portaudio_ffi_get_version(void) {
    return "not-available";
}

const char* portaudio_ffi_get_version_text(void) {
    return "PortAudio not available";
}

// Initialization
int portaudio_ffi_initialize(void) {
    return -1; // paNotInitialized
}

int portaudio_ffi_terminate(void) {
    return 0;
}

// Device enumeration
int portaudio_ffi_get_device_count(void) {
    return 0;
}

int portaudio_ffi_get_default_input_device(void) {
    return -1;
}

int portaudio_ffi_get_default_output_device(void) {
    return -1;
}

void* portaudio_ffi_get_device_info(int device) {
    return 0;
}

// Stream
void* portaudio_ffi_open_stream(
    const void* input_params,
    const void* output_params,
    double sample_rate,
    int frames_per_buffer,
    unsigned long stream_flags,
    void* callback,
    void* user_data
) {
    return 0;
}

int portaudio_ffi_close_stream(void* stream) {
    return 0;
}

int portaudio_ffi_start_stream(void* stream) {
    return -1;
}

int portaudio_ffi_stop_stream(void* stream) {
    return -1;
}

int portaudio_ffi_abort_stream(void* stream) {
    return -1;
}

int portaudio_ffi_is_stream_stopped(void* stream) {
    return 1;
}

int portaudio_ffi_is_stream_active(void* stream) {
    return 0;
}
