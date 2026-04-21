/* JACK2 FFI Stub for OpenDAW
 * Stub implementation until JACK2 library is integrated
 * License: LGPL-2.1+ (matches JACK2)
 */

#include <string.h>

// Stub implementations
int jack_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* jack_ffi_get_version(void) {
    return "not-available";
}

// Client
void* jack_ffi_client_open(const char* name, const char* server) {
    return 0;
}

int jack_ffi_client_close(void* client) {
    return 0;
}

int jack_ffi_activate(void* client) {
    return -1;
}

int jack_ffi_deactivate(void* client) {
    return 0;
}

// Ports
void* jack_ffi_port_register(void* client, const char* name, const char* port_type, int flags, int buffer_size) {
    return 0;
}

int jack_ffi_port_unregister(void* client, void* port) {
    return 0;
}

void* jack_ffi_port_get_buffer(void* port, int nframes) {
    return 0;
}

int jack_ffi_port_connect(void* client, const char* source, const char* dest) {
    return -1;
}

int jack_ffi_port_disconnect(void* client, const char* source, const char* dest) {
    return -1;
}

// Server info
int jack_ffi_get_sample_rate(void* client) {
    return 44100;
}

int jack_ffi_get_buffer_size(void* client) {
    return 512;
}

// Transport
void jack_ffi_transport_start(void* client) {
}

void jack_ffi_transport_stop(void* client) {
}

void jack_ffi_transport_locate(void* client, int frame) {
}

int jack_ffi_get_transport_state(void* client) {
    return 0; // Stopped
}
