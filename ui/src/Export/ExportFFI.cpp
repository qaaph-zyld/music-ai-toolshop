#include "ExportFFI.h"

namespace OpenDAW {

void* ExportFFI::createExport() {
    // TODO: Implement when Rust export FFI is available
    return nullptr;
}

bool ExportFFI::configure(void* handle, const ExportConfig& config) {
    (void)handle;
    (void)config;
    // TODO: Implement when Rust export FFI is available
    return false;
}

bool ExportFFI::start(void* handle) {
    (void)handle;
    // TODO: Implement when Rust export FFI is available
    return false;
}

double ExportFFI::getProgress(void* handle) {
    (void)handle;
    // TODO: Implement when Rust export FFI is available
    return 0.0;
}

bool ExportFFI::isComplete(void* handle) {
    (void)handle;
    // TODO: Implement when Rust export FFI is available
    return false;
}

ExportResult ExportFFI::getResult(void* handle) {
    (void)handle;
    // TODO: Implement when Rust export FFI is available
    return ExportResult::Error;
}

bool ExportFFI::cancel(void* handle) {
    (void)handle;
    // TODO: Implement when Rust export FFI is available
    return false;
}

void ExportFFI::destroy(void* handle) {
    (void)handle;
    // TODO: Implement when Rust export FFI is available
}

} // namespace OpenDAW
