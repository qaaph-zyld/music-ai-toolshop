/* MusePack FFI Stub for OpenDAW
 * Stub implementation until MusePack is integrated
 * License: BSD-3-Clause (matches MusePack)
 */

#include <string.h>

// Stub implementations
int mpc_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* mpc_ffi_get_version(void) {
    return "not-available";
}

const char* mpc_ffi_get_encoder_version(void) {
    return "not-available";
}

// Encoder
void* mpc_ffi_encoder_new(void) {
    return 0;
}

void mpc_ffi_encoder_delete(void* encoder) {
    // No-op
}

int mpc_ffi_encoder_init(void* encoder, int sample_rate, int channels, int profile) {
    return -1;
}

int mpc_ffi_encoder_encode(void* encoder, const float* pcm_buffer, int samples) {
    return -1;
}

int mpc_ffi_encoder_finish(void* encoder) {
    return -1;
}

int mpc_ffi_encoder_get_buffer(void* encoder, char* buffer, int buffer_size) {
    return -1;
}

// Decoder
void* mpc_ffi_decoder_new(void) {
    return 0;
}

void mpc_ffi_decoder_delete(void* decoder) {
    // No-op
}

// MPC info structure - match Rust layout
struct MpcInfo {
    unsigned int sample_rate;
    unsigned short channels;
    unsigned int bitrate;
    double duration_seconds;
    unsigned int profile;
    int is_sv8;
};

int mpc_ffi_decoder_init_file(void* decoder, const char* path) {
    return -1;
}

int mpc_ffi_decoder_get_info(void* decoder, struct MpcInfo* info) {
    if (info) {
        memset(info, 0, sizeof(struct MpcInfo));
    }
    return -1;
}

int mpc_ffi_decoder_decode(void* decoder, float* pcm_buffer, int samples) {
    return -1;
}

int mpc_ffi_decoder_seek_sample(void* decoder, int sample) {
    return -1;
}

int mpc_ffi_decoder_get_state(void* decoder) {
    return -1;
}
