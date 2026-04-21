/* MusicBERT FFI Wrapper - Stub Implementation
 * 
 * This is a stub implementation for the MusicBERT Python bridge.
 * Full implementation would link to PyTorch transformer models.
 * 
 * For now, returns "not available" status until Python environment is integrated.
 */

#include <stdlib.h>
#include <string.h>

// Model handle (opaque)
typedef struct MusicBertModel {
    char* path;
    unsigned int sample_rate;
    int is_loaded;
} MusicBertModel;

// Check if MusicBERT is available
int musicbert_ffi_is_available(void) {
    return 0; // Not available in stub
}

// Get version
const char* musicbert_ffi_get_version(void) {
    return "unavailable";
}

// Get supported sample rates (stub)
int musicbert_ffi_get_supported_sample_rates(unsigned int* rates, unsigned int max_count) {
    (void)rates;
    (void)max_count;
    return -1;
}

// Load model (stub - always fails)
MusicBertModel* musicbert_ffi_model_load(const char* path, unsigned int sample_rate) {
    (void)path;
    (void)sample_rate;
    return NULL;
}

// Free model
void musicbert_ffi_model_free(MusicBertModel* model) {
    if (model) {
        free(model->path);
        free(model);
    }
}

// Analyze chords (stub - always fails)
int musicbert_ffi_analyze_chords(
    MusicBertModel* model,
    const float* audio,
    unsigned int sample_count,
    char* chords_buffer,
    unsigned int buffer_size
) {
    (void)model;
    (void)audio;
    (void)sample_count;
    (void)chords_buffer;
    (void)buffer_size;
    return -1;
}

// Detect key (stub - always fails)
int musicbert_ffi_detect_key(
    MusicBertModel* model,
    const float* audio,
    unsigned int sample_count,
    int* tonic,
    int* mode,
    float* confidence
) {
    (void)model;
    (void)audio;
    (void)sample_count;
    (void)tonic;
    (void)mode;
    (void)confidence;
    return -1;
}

// Classify genre (stub - always fails)
int musicbert_ffi_classify_genre(
    MusicBertModel* model,
    const float* audio,
    unsigned int sample_count,
    char* genres_buffer,
    unsigned int buffer_size
) {
    (void)model;
    (void)audio;
    (void)sample_count;
    (void)genres_buffer;
    (void)buffer_size;
    return -1;
}

// Detect structure (stub - always fails)
int musicbert_ffi_detect_structure(
    MusicBertModel* model,
    const float* audio,
    unsigned int sample_count,
    char* structure_buffer,
    unsigned int buffer_size
) {
    (void)model;
    (void)audio;
    (void)sample_count;
    (void)structure_buffer;
    (void)buffer_size;
    return -1;
}

// Get embeddings (stub - always fails)
int musicbert_ffi_get_embeddings(
    MusicBertModel* model,
    const float* audio,
    unsigned int sample_count,
    float* embeddings,
    unsigned int embedding_dim
) {
    (void)model;
    (void)audio;
    (void)sample_count;
    (void)embeddings;
    (void)embedding_dim;
    return -1;
}

// Batch analyze (stub - always fails)
int musicbert_ffi_batch_analyze(
    MusicBertModel* model,
    const char* file_list,
    char* results_buffer,
    unsigned int buffer_size
) {
    (void)model;
    (void)file_list;
    (void)results_buffer;
    (void)buffer_size;
    return -1;
}
