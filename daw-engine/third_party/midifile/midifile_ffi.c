/**
 * midifile FFI Stub
 * 
 * This is a stub implementation for the midifile C++ library.
 * The actual library (https://github.com/craigsapp/midifile) is a C++ library
 * for parsing Standard MIDI Files (.mid).
 * 
 * This stub returns not-available status until the real library is integrated.
 */

#include <stdlib.h>
#include <string.h>
#include <stdint.h>

// Stub file data handle
typedef struct {
    int dummy;
} midifile_data_t;

// Stub file info handle
typedef struct {
    int dummy;
} midifile_info_t;

// Read file (returns NULL - not available)
void* read_file(const char* path, int preserve_running_status, int strict_parsing) {
    (void)path;
    (void)preserve_running_status;
    (void)strict_parsing;
    return NULL;  // Not available
}

// Read bytes (returns NULL - not available)
void* read_bytes(const uint8_t* data, size_t length, int preserve_running_status, int strict_parsing) {
    (void)data;
    (void)length;
    (void)preserve_running_status;
    (void)strict_parsing;
    return NULL;  // Not available
}

// Free file data (no-op)
void free_file_data(void* data) {
    free(data);
}

// Get file info (returns NULL - not available)
void* get_file_info(const char* path) {
    (void)path;
    return NULL;  // Not available
}

// Free file info (no-op)
void free_file_info(void* info) {
    free(info);
}

// Write file (returns error)
int write_file(const char* path, int format, uint16_t ticks_per_quarter, 
               int track_count, int use_running_status, int sort_events) {
    (void)path;
    (void)format;
    (void)ticks_per_quarter;
    (void)track_count;
    (void)use_running_status;
    (void)sort_events;
    return -1;  // Error: not available
}

// Write bytes (returns NULL - not available)
void* write_bytes(int format, uint16_t ticks_per_quarter, int track_count,
                  int use_running_status, int sort_events) {
    (void)format;
    (void)ticks_per_quarter;
    (void)track_count;
    (void)use_running_status;
    (void)sort_events;
    return NULL;  // Not available
}

// Free bytes (no-op)
void free_bytes(void* data) {
    free(data);
}
