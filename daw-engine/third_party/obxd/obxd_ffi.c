// OB-Xd virtual analog synthesizer FFI stub
// https://github.com/reales/OB-Xd
#include <stdlib.h>
#include <string.h>

typedef struct ObxdHandle ObxdHandle;

const char* obxd_get_version(void) {
    return "not-available";
}

int obxd_is_available(void) {
    return 0;
}

ObxdHandle* obxd_create(const void* config) {
    (void)config;
    return NULL;
}

void obxd_free(ObxdHandle* handle) {
    (void)handle;
}

int obxd_process(ObxdHandle* handle, const float* input, float* output, int samples) {
    (void)handle;
    (void)input;
    (void)output;
    (void)samples;
    return -1;
}

int obxd_note_on(ObxdHandle* handle, int note, int velocity) {
    (void)handle;
    (void)note;
    (void)velocity;
    return -1;
}

int obxd_note_off(ObxdHandle* handle, int note) {
    (void)handle;
    (void)note;
    return -1;
}

int obxd_set_filter_params(ObxdHandle* handle, float cutoff, float resonance) {
    (void)handle;
    (void)cutoff;
    (void)resonance;
    return -1;
}
