/* Miniaudio FFI Wrapper for OpenDAW
 * Simplified API for device enumeration and basic info
 * Public Domain / MIT-0 License (matches miniaudio)
 */

#define MINIAUDIO_IMPLEMENTATION
#include "miniaudio.h"
#include <string.h>
#include <stdlib.h>

// Opaque handle types
typedef struct ma_context* ma_context_handle;
typedef struct ma_device* ma_device_handle;

// Device info structure for FFI
typedef struct {
    char name[256];
    ma_uint32 channels;
    ma_uint32 sample_rate;
    ma_bool32 is_default;
} ma_device_info_ffi;

// Context management
ma_context_handle ma_ffi_context_create(void) {
    ma_context* context = (ma_context*)malloc(sizeof(ma_context));
    if (!context) return NULL;
    
    ma_result result = ma_context_init(NULL, 0, NULL, context);
    if (result != MA_SUCCESS) {
        free(context);
        return NULL;
    }
    return context;
}

void ma_ffi_context_destroy(ma_context_handle ctx) {
    if (!ctx) return;
    ma_context_uninit((ma_context*)ctx);
    free(ctx);
}

// Device enumeration
ma_uint32 ma_ffi_get_device_count(ma_context_handle ctx) {
    if (!ctx) return 0;
    
    ma_device_info* pPlaybackInfos;
    ma_uint32 playbackCount;
    ma_device_info* pCaptureInfos;
    ma_uint32 captureCount;
    
    ma_result result = ma_context_get_devices(
        (ma_context*)ctx,
        &pPlaybackInfos, &playbackCount,
        &pCaptureInfos, &captureCount
    );
    
    if (result != MA_SUCCESS) return 0;
    return playbackCount;
}

ma_bool32 ma_ffi_get_device_info(ma_context_handle ctx, ma_uint32 index, ma_device_info_ffi* info) {
    if (!ctx || !info) return MA_FALSE;
    
    ma_device_info* pPlaybackInfos;
    ma_uint32 playbackCount;
    ma_device_info* pCaptureInfos;
    ma_uint32 captureCount;
    
    ma_result result = ma_context_get_devices(
        (ma_context*)ctx,
        &pPlaybackInfos, &playbackCount,
        &pCaptureInfos, &captureCount
    );
    
    if (result != MA_SUCCESS || index >= playbackCount) return MA_FALSE;
    
    strncpy(info->name, pPlaybackInfos[index].name, sizeof(info->name) - 1);
    info->name[sizeof(info->name) - 1] = '\0';
    info->channels = (unsigned int)pPlaybackInfos[index].nativeDataFormats[0].channels;
    info->sample_rate = (unsigned int)pPlaybackInfos[index].nativeDataFormats[0].sampleRate;
    info->is_default = pPlaybackInfos[index].isDefault;
    
    return MA_TRUE;
}

// Version info
const char* ma_ffi_get_version(void) {
    return ma_version_string();
}

// Library availability check
ma_bool32 ma_ffi_is_available(void) {
    return MA_TRUE;  // If this code is running, miniaudio is available
}
