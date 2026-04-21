#pragma once

#include <string>
#include <functional>

namespace OpenDAW {

/// Export format constants
enum class ExportFormat {
    Wav16 = 0,
    Wav24 = 1,
    Wav32 = 2
};

/// Export result codes
enum class ExportResult {
    InProgress = 0,
    Success = 1,
    Cancelled = 2,
    Error = 3
};

/// Export configuration
struct ExportConfig {
    std::string filePath;
    ExportFormat format = ExportFormat::Wav24;
    int sampleRate = 48000;
    bool stemExport = false;
};

/// Progress callback type
using ExportProgressCallback = std::function<void(double progress)>;

/// C++ wrapper for Rust export FFI
class ExportFFI {
public:
    /// Create a new export handle
    static void* createExport();
    
    /// Configure export parameters
    /// Returns true on success, false on error
    static bool configure(void* handle, const ExportConfig& config);
    
    /// Start the export process
    /// Returns true on success, false on error
    static bool start(void* handle);
    
    /// Get export progress (0.0 to 1.0)
    static double getProgress(void* handle);
    
    /// Check if export is complete
    static bool isComplete(void* handle);
    
    /// Get export result
    static ExportResult getResult(void* handle);
    
    /// Cancel ongoing export
    static bool cancel(void* handle);
    
    /// Destroy export handle and free resources
    static void destroy(void* handle);

private:
    // Prevent instantiation
    ExportFFI() = delete;
};

} // namespace OpenDAW
