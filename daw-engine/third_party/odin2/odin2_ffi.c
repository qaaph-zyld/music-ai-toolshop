// Odin2 modular synthesizer FFI stub
// https://github.com/TheWaveWarden/odin2
#include <stdlib.h>
#include <string.h>

typedef struct Odin2Handle Odin2Handle;

const char* odin2_get_version(void) {
    return "not-available";
}

int odin2_is_available(void) {
    return 0;
}

Odin2Handle* odin2_create(const void* config) {
    (void)config;
    return NULL;
}

void odin2_free(Odin2Handle* handle) {
    (void)handle;
}

int odin2_process(Odin2Handle* handle, const float* input, float* output, int samples) {
    (void)handle;
    (void)input;
    (void)output;
    (void)samples;
    return -1;
}

int odin2_note_on(Odin2Handle* handle, int note, int velocity) {
    (void)handle;
    (void)note;
    (void)velocity;
    return -1;
}

int odin2_note_off(Odin2Handle* handle, int note) {
    (void)handle;
    (void)note;
    return -1;
}
