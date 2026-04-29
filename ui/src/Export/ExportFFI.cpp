#include "ExportFFI.h"

// Rust FFI function declarations
extern "C" {
    void* daw_export_create();
    int daw_export_configure(void* handle, const char* file_path, int format, int sample_rate, int stem_export);
    int daw_export_start(void* handle);
    double daw_export_get_progress(void* handle);
    int daw_export_is_complete(void* handle);
    int daw_export_cancel(void* handle);
    int daw_export_get_result(void* handle);
    void daw_export_destroy(void* handle);
}

namespace OpenDAW {

void* ExportFFI::createExport() {
    return daw_export_create();
}

bool ExportFFI::configure(void* handle, const ExportConfig& config) {
    if (!handle) return false;
    
    int format = static_cast<int>(config.format);
    int stem = config.stemExport ? 1 : 0;
    
    int result = daw_export_configure(
        handle,
        config.filePath.c_str(),
        format,
        config.sampleRate,
        stem
    );
    
    return result == 0;
}

bool ExportFFI::start(void* handle) {
    if (!handle) return false;
    return daw_export_start(handle) == 0;
}

double ExportFFI::getProgress(void* handle) {
    if (!handle) return 0.0;
    return daw_export_get_progress(handle);
}

bool ExportFFI::isComplete(void* handle) {
    if (!handle) return false;
    return daw_export_is_complete(handle) == 1;
}

ExportResult ExportFFI::getResult(void* handle) {
    if (!handle) return ExportResult::Error;
    int result = daw_export_get_result(handle);
    switch (result) {
        case 0: return ExportResult::InProgress;
        case 1: return ExportResult::Success;
        case 2: return ExportResult::Cancelled;
        default: return ExportResult::Error;
    }
}

bool ExportFFI::cancel(void* handle) {
    if (!handle) return false;
    return daw_export_cancel(handle) == 0;
}

void ExportFFI::destroy(void* handle) {
    if (handle) {
        daw_export_destroy(handle);
    }
}

} // namespace OpenDAW
