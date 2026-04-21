/* WebRTC FFI Stub for OpenDAW
 * Stub implementation until WebRTC is integrated
 * License: BSD-3-Clause (matches WebRTC)
 */

#include <string.h>

// Stub implementations
int webrtc_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* webrtc_ffi_get_version(void) {
    return "not-available";
}

// Peer connection
void* webrtc_ffi_create_peer_connection(const char* config_json) {
    return 0;
}

void webrtc_ffi_destroy_peer_connection(void* pc) {
    // No-op
}

int webrtc_ffi_create_offer(void* pc, char* sdp_out, int sdp_size) {
    return -1;
}

int webrtc_ffi_create_answer(void* pc, char* sdp_out, int sdp_size) {
    return -1;
}

int webrtc_ffi_set_local_description(void* pc, const char* sdp_type, const char* sdp) {
    return -1;
}

int webrtc_ffi_set_remote_description(void* pc, const char* sdp_type, const char* sdp) {
    return -1;
}

int webrtc_ffi_add_ice_candidate(void* pc,
                                 const char* sdp_mid,
                                 int mline_index,
                                 const char* candidate) {
    return -1;
}

int webrtc_ffi_get_connection_state(void* pc) {
    return 0;  // New
}

int webrtc_ffi_get_signaling_state(void* pc) {
    return 0;  // Stable
}

int webrtc_ffi_get_ice_connection_state(void* pc) {
    return 0;  // New
}

// Audio
void* webrtc_ffi_create_audio_track(void* pc,
                                     const char* track_id,
                                     int sample_rate,
                                     int channels) {
    return 0;
}

void webrtc_ffi_destroy_audio_track(void* track) {
    // No-op
}

int webrtc_ffi_send_audio(void* track, const float* samples, int sample_count) {
    return -1;
}

int webrtc_ffi_set_remote_audio_callback(void* track, void* callback) {
    return -1;
}

// Data channel
void* webrtc_ffi_create_data_channel(void* pc, const char* label) {
    return 0;
}

void webrtc_ffi_destroy_data_channel(void* channel) {
    // No-op
}

int webrtc_ffi_send_data(void* channel, const char* data, int length) {
    return -1;
}

int webrtc_ffi_set_data_callback(void* channel, void* callback) {
    return -1;
}

int webrtc_ffi_get_buffered_amount(void* channel) {
    return 0;
}

// Callbacks
int webrtc_ffi_set_ice_candidate_callback(void* pc, void* callback) {
    return -1;
}

int webrtc_ffi_set_connection_state_callback(void* pc, void* callback) {
    return -1;
}
