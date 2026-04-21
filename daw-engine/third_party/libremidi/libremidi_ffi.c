/**
 * libremidi FFI Stub
 * 
 * This is a stub implementation for the libremidi C library.
 * The actual library (https://github.com/celtera/libremidi) is a modern
 * C++20 library for cross-platform MIDI I/O with MIDI 2.0 support.
 * 
 * This stub returns not-available status until the real library is integrated.
 */

#include <stdlib.h>
#include <string.h>
#include <stdint.h>

// Stub configuration structure
typedef struct {
    int midi_version;
    int hotplug_enabled;
    int zero_allocation;
} libremidi_config_t;

// Stub engine handle
typedef struct {
    int dummy;
} libremidi_engine_t;

// Stub enumeration handle
typedef struct {
    int dummy;
} libremidi_enumeration_t;

// Create engine (returns NULL - not available)
void* engine_create(const libremidi_config_t* config) {
    (void)config;
    return NULL;  // Not available
}

// Destroy engine (no-op)
void engine_destroy(void* engine) {
    (void)engine;
}

// Enumerate devices (returns NULL - not available)
void* enumerate_devices(void* engine) {
    (void)engine;
    return NULL;  // Not available
}

// Free enumeration (no-op)
void free_enumeration(void* enumeration) {
    free(enumeration);
}

// Open input device (returns error)
int open_input(void* engine, uint32_t device_id) {
    (void)engine;
    (void)device_id;
    return -1;  // Error: not available
}

// Open output device (returns error)
int open_output(void* engine, uint32_t device_id) {
    (void)engine;
    (void)device_id;
    return -1;  // Error: not available
}

// Close input device (no-op)
void close_input(void* engine) {
    (void)engine;
}

// Close output device (no-op)
void close_output(void* engine) {
    (void)engine;
}

// Send message (returns error)
int send_message(void* engine, const uint8_t* data, size_t length, uint64_t timestamp) {
    (void)engine;
    (void)data;
    (void)length;
    (void)timestamp;
    return -1;  // Error: not available
}

// Enable hotplug (returns error)
int enable_hotplug(void* engine) {
    (void)engine;
    return -1;  // Error: not available
}
