/* LAME MP3 FFI Stub for OpenDAW
 * Stub implementation until LAME is integrated
 * License: LGPL (matches LAME)
 */

#include <string.h>

// Stub implementations
int lame_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* lame_ffi_get_version(void) {
    return "not-available";
}

// Encoder
void* lame_ffi_encoder_new(void) {
    return 0;
}

void lame_ffi_encoder_delete(void* encoder) {
    // No-op
}

int lame_ffi_encoder_init(void* encoder, int sample_rate, int channels,
                          int mode, int quality) {
    return -1;
}

long long lame_ffi_encoder_encode_buffer_interleaved(void* encoder,
                                                      const short* buffer,
                                                      int samples,
                                                      char* mp3_buffer,
                                                      int mp3_buffer_size) {
    return -1;
}

long long lame_ffi_encoder_encode_flush(void* encoder,
                                        char* mp3_buffer,
                                        int mp3_buffer_size) {
    return -1;
}

int lame_ffi_encoder_set_bitrate(void* encoder, int bitrate) {
    return -1;
}

int lame_ffi_encoder_set_quality(void* encoder, int quality) {
    return -1;
}

// Decoder
void* lame_ffi_decoder_new(void) {
    return 0;
}

void lame_ffi_decoder_delete(void* decoder) {
    // No-op
}

// MP3 info structure - match Rust layout
struct Mp3Info {
    unsigned int sample_rate;
    unsigned short channels;
    unsigned int bitrate;
    double duration_seconds;
    unsigned int frame_count;
};

int lame_ffi_decoder_init_file(void* decoder, const char* path) {
    return -1;
}

int lame_ffi_decoder_get_info(void* decoder, struct Mp3Info* info) {
    if (info) {
        memset(info, 0, sizeof(struct Mp3Info));
    }
    return -1;
}

int lame_ffi_decoder_decode_frame(void* decoder, short* pcm_buffer, int buffer_size) {
    return -1;
}

int lame_ffi_decoder_decode_interleaved(void* decoder, float* pcm_buffer, int samples) {
    return -1;
}
