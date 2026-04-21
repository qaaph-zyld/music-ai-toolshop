/* Opus FFI Stub for OpenDAW
 * Stub implementation until Opus library is integrated
 * License: BSD-3-Clause (matches Opus)
 */

#include <string.h>

// Stub implementations
int opus_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* opus_ffi_get_version(void) {
    return "not-available";
}

// Encoder stubs
void* opus_ffi_encoder_create(int sample_rate, int channels, int application) {
    return 0;
}

void opus_ffi_encoder_destroy(void* encoder) {
}

int opus_ffi_encode_float(void* encoder, const float* pcm, int frame_size, unsigned char* data, int max_data_bytes) {
    return -1;
}

int opus_ffi_encoder_set_bitrate(void* encoder, int bitrate) {
    return 0;
}

int opus_ffi_encoder_set_complexity(void* encoder, int complexity) {
    return 0;
}

// Decoder stubs
void* opus_ffi_decoder_create(int sample_rate, int channels) {
    return 0;
}

void opus_ffi_decoder_destroy(void* decoder) {
}

int opus_ffi_decode_float(void* decoder, const unsigned char* data, int len, float* pcm, int frame_size, int decode_fec) {
    return -1;
}

// Packet info stubs
int opus_ffi_packet_get_bandwidth(const unsigned char* data) {
    return -1;
}

int opus_ffi_packet_get_samples_per_frame(const unsigned char* data, int sample_rate) {
    return -1;
}
