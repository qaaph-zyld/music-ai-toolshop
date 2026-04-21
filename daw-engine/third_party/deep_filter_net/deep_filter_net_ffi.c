// deep_filter_net_ffi.c - Stub for DeepFilterNet noise suppression library
//
// This is a stub implementation that returns "not available" status.
// The actual DeepFilterNet library integration would require linking
// to the DeepFilterNet library (deep learning-based noise suppression).
//
// Repository: https://github.com/Rikorose/DeepFilterNet

#include <stdlib.h>
#include <string.h>

typedef struct {
    int dummy;
} DfStub;

// Create DeepFilterNet from built-in model
typedef enum {
    DF_MODEL_DF2 = 0,
    DF_MODEL_DF3 = 1,
    DF_MODEL_DFL3 = 2
} DfModel;

void* df_create(unsigned int sample_rate, int model) {
    // Return NULL to indicate library not available
    // In real implementation, this would load the ONNX model
    return NULL;
}

// Create from model file
void* df_create_from_file(const char* model_path, unsigned int sample_rate) {
    // Return NULL to indicate library not available
    return NULL;
}

// Destroy instance
void df_destroy(void* df) {
    // No-op for stub
}

// Process a frame
// Returns: 0 on success, -1 on error
int df_process_frame(
    void* df,
    const float* input,
    float* output,
    int frame_size,
    float* speech_prob,
    float* att_db,
    float* gain_db
) {
    return -1; // Error: not available
}

// Set attenuation limit in dB
// Returns: 0 on success, -1 on error
int df_set_attenuation(void* df, float limit_db) {
    return -1; // Error: not available
}

// Get current attenuation
float df_get_attenuation(void* df) {
    return 0.0f; // Library not available
}

// Set post-filter
// Returns: 0 on success, -1 on error
int df_set_post_filter(void* df, int enabled) {
    return -1; // Error: not available
}

// Get version string
const char* df_get_version(void) {
    return "stub-not-available";
}
