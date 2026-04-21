// Dexed FM synthesizer FFI stub
// Yamaha DX7 emulator - https://github.com/asb2m10/dexed
#include <stdlib.h>
#include <string.h>

typedef struct DexedHandle DexedHandle;

const char* dexed_get_version(void) {
    return "not-available";
}

int dexed_is_available(void) {
    return 0;
}

DexedHandle* dexed_create(const void* config) {
    (void)config;
    return NULL;
}

void dexed_free(DexedHandle* handle) {
    (void)handle;
}

int dexed_process(DexedHandle* handle, const float* input, float* output, int samples) {
    (void)handle;
    (void)input;
    (void)output;
    (void)samples;
    return -1;
}

int dexed_note_on(DexedHandle* handle, int note, int velocity) {
    (void)handle;
    (void)note;
    (void)velocity;
    return -1;
}

int dexed_note_off(DexedHandle* handle, int note) {
    (void)handle;
    (void)note;
    return -1;
}

int dexed_set_algorithm(DexedHandle* handle, int algorithm) {
    (void)handle;
    (void)algorithm;
    return -1;
}
