// Tunefish lightweight wavetable synthesizer FFI stub
// https://github.com/paynebc/tunefish
#include <stdlib.h>
#include <string.h>

typedef struct TunefishHandle TunefishHandle;

const char* tunefish_get_version(void) {
    return "not-available";
}

int tunefish_is_available(void) {
    return 0;
}

TunefishHandle* tunefish_create(const void* config) {
    (void)config;
    return NULL;
}

void tunefish_free(TunefishHandle* handle) {
    (void)handle;
}

int tunefish_process(TunefishHandle* handle, const float* input, float* output, int samples) {
    (void)handle;
    (void)input;
    (void)output;
    (void)samples;
    return -1;
}

int tunefish_note_on(TunefishHandle* handle, int note, int velocity) {
    (void)handle;
    (void)note;
    (void)velocity;
    return -1;
}

int tunefish_note_off(TunefishHandle* handle, int note) {
    (void)handle;
    (void)note;
    return -1;
}
