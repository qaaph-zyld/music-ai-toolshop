/* LibFLAC FFI Stub for OpenDAW
 * Stub implementation until libFLAC is integrated
 * License: BSD-3-Clause / GPL (matches libFLAC)
 */

#include <string.h>

// Stub implementations
int flac_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* flac_ffi_get_version(void) {
    return "not-available";
}

// Encoder
void* flac_ffi_encoder_new(void) {
    return 0;
}

void flac_ffi_encoder_delete(void* encoder) {
    // No-op
}

int flac_ffi_encoder_init_file(void* encoder, const char* path,
                                int sample_rate, int channels,
                                int bits_per_sample, int compression) {
    return -1;
}

int flac_ffi_encoder_process_interleaved(void* encoder, const int* buffer, int samples) {
    return -1;
}

int flac_ffi_encoder_finish(void* encoder) {
    return -1;
}

int flac_ffi_encoder_get_state(void* encoder) {
    return -1;
}

// Decoder
void* flac_ffi_decoder_new(void) {
    return 0;
}

void flac_ffi_decoder_delete(void* decoder) {
    // No-op
}

int flac_ffi_decoder_init_file(void* decoder, const char* path) {
    return -1;
}

int flac_ffi_decoder_process_single(void* decoder) {
    return -1;
}

int flac_ffi_decoder_process_until_end_of_stream(void* decoder) {
    return -1;
}

// Metadata structure - match Rust layout
struct FlacMetadata {
    unsigned int sample_rate;
    unsigned short channels;
    unsigned short bits_per_sample;
    unsigned long long total_samples;
    float compression_ratio;
};

int flac_ffi_decoder_get_metadata(void* decoder, struct FlacMetadata* metadata) {
    if (metadata) {
        memset(metadata, 0, sizeof(struct FlacMetadata));
    }
    return -1;
}

int flac_ffi_decoder_get_state(void* decoder) {
    return -1;
}
