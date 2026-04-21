// Helm subtractive synthesizer FFI stub
// https://github.com/mtytel/helm
#include <stdlib.h>
#include <string.h>

typedef struct HelmHandle HelmHandle;

const char* helm_get_version(void) {
    return "not-available";
}

int helm_is_available(void) {
    return 0;
}

HelmHandle* helm_create(const void* config) {
    (void)config;
    return NULL;
}

void helm_free(HelmHandle* handle) {
    (void)handle;
}

int helm_process(HelmHandle* handle, const float* input, float* output, int samples) {
    (void)handle;
    (void)input;
    (void)output;
    (void)samples;
    return -1;
}

int helm_note_on(HelmHandle* handle, int note, int velocity) {
    (void)handle;
    (void)note;
    (void)velocity;
    return -1;
}

int helm_note_off(HelmHandle* handle, int note) {
    (void)handle;
    (void)note;
    return -1;
}

int helm_set_arpeggiator(HelmHandle* handle, int enabled) {
    (void)handle;
    (void)enabled;
    return -1;
}
