/* RtAudio FFI Stub for OpenDAW
 * Stub implementation until RtAudio library is integrated
 * License: MIT (matches RtAudio)
 */

#include <string.h>

// Stub implementations
int rtaudio_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* rtaudio_ffi_get_version(void) {
    return "not-available";
}

// Instance creation/destruction
void* rtaudio_ffi_create(unsigned int api) {
    return 0;
}

void rtaudio_ffi_destroy(void* rt) {
}

// Device enumeration
int rtaudio_ffi_get_device_count(void* rt) {
    return 0;
}

struct RtAudioDeviceInfo {
    int probed;
    char name[256];
    unsigned int output_channels;
    unsigned int input_channels;
    unsigned int duplex_channels;
    int is_default_output;
    int is_default_input;
    unsigned int sample_rates[16];
    unsigned int num_sample_rates;
    unsigned int preferred_sample_rate;
    unsigned int native_formats;
};

struct RtAudioDeviceInfo rtaudio_ffi_get_device_info(void* rt, unsigned int device) {
    struct RtAudioDeviceInfo info;
    memset(&info, 0, sizeof(info));
    return info;
}

unsigned int rtaudio_ffi_get_default_output_device(void* rt) {
    return 0;
}

unsigned int rtaudio_ffi_get_default_input_device(void* rt) {
    return 0;
}

// Stream
int rtaudio_ffi_open_stream(
    void* rt,
    const void* output_params,
    const void* input_params,
    unsigned int format,
    unsigned int sample_rate,
    unsigned int* buffer_frames,
    void* callback,
    void* user_data,
    const void* options
) {
    return -1;
}

void rtaudio_ffi_close_stream(void* rt) {
}

int rtaudio_ffi_start_stream(void* rt) {
    return -1;
}

int rtaudio_ffi_stop_stream(void* rt) {
    return -1;
}

int rtaudio_ffi_abort_stream(void* rt) {
    return -1;
}

int rtaudio_ffi_is_stream_running(void* rt) {
    return 0;
}

int rtaudio_ffi_is_stream_open(void* rt) {
    return 0;
}

// Error handling
const char* rtaudio_ffi_get_error_text(void* rt) {
    return "RtAudio not available";
}
