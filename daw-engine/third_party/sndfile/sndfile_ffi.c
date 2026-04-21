/* Libsndfile FFI Stub for OpenDAW
 * Stub implementation until libsndfile is integrated
 * License: LGPL-2.1+ (matches libsndfile)
 */

#include <string.h>

// Stub implementations
int sndfile_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* sndfile_ffi_get_version(void) {
    return "not-available";
}

// File operations
void* sndfile_ffi_open(const char* path, int mode, void* info) {
    return 0;
}

int sndfile_ffi_close(void* file) {
    return 0;
}

// Read operations
long long sndfile_ffi_read_short(void* file, short* ptr, long long frames) {
    return 0;
}

long long sndfile_ffi_read_int(void* file, int* ptr, long long frames) {
    return 0;
}

long long sndfile_ffi_read_float(void* file, float* ptr, long long frames) {
    return 0;
}

// Write operations
long long sndfile_ffi_write_short(void* file, const short* ptr, long long frames) {
    return 0;
}

long long sndfile_ffi_write_float(void* file, const float* ptr, long long frames) {
    return 0;
}

// Seek
long long sndfile_ffi_seek(void* file, long long frames, int whence) {
    return 0;
}

// Error handling
const char* sndfile_ffi_error(void* file) {
    return "libsndfile not available";
}

const char* sndfile_ffi_strerror(void* file) {
    return "libsndfile not available";
}
