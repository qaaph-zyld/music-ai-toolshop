/* FAUST FFI Stub for OpenDAW
 * Stub implementation until FAUST compiler is integrated
 * License: GPL-2.0 / LGPL-2.1+ (matches FAUST)
 */

#include <string.h>

// Stub implementations that return "not available"
int faust_ffi_is_available(void) {
    return 0;  // FAUST not available until compiler is integrated
}

int faust_ffi_compile_dsp(
    const char* code,
    const char* target,
    int opt_level,
    char* output,
    int output_size
) {
    // Stub: always returns error
    const char* error_msg = "FAUST compiler not integrated";
    strncpy(output, error_msg, output_size - 1);
    output[output_size - 1] = '\0';
    return -1;
}

const char* faust_ffi_get_version(void) {
    return "not-available";
}
