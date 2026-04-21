// rnnoise_ffi.c - Stub for RNNoise noise suppression library
//
// This is a stub implementation that returns "not available" status.
// The actual RNNoise library integration would require linking
// to Mozilla's RNNoise library (recurrent neural network noise suppression).
//
// Repository: https://github.com/xiph/rnnoise

#include <stdlib.h>
#include <string.h>

typedef struct {
    int dummy;
} RnNoiseStub;

// Create RNNoise state
// model: path to model file, or NULL for default
void* rnnoise_create(const char* model) {
    // Return NULL to indicate library not available
    // In real implementation, this would load the neural network model
    return NULL;
}

// Destroy RNNoise state
void rnnoise_destroy(void* st) {
    // No-op for stub
}

// Process a single frame
// Returns: 0 on success, -1 on error
int rnnoise_process_frame(void* st, float* out, const float* input, float* vad_prob) {
    return -1; // Error: not available
}

// Set VAD threshold (0.0 to 1.0)
// Returns: 0 on success, -1 on error
int rnnoise_set_vad_threshold(void* st, float threshold) {
    return -1; // Error: not available
}

// Get current VAD threshold
float rnnoise_get_vad_threshold(void* st) {
    return 0.0f; // Default, library not available
}

// Get required state size (for pre-allocation)
size_t rnnoise_get_size(void) {
    return 0; // Library not available
}
