/* ImGui JUCE FFI Stub for OpenDAW
 * Stub implementation until ImGui JUCE is integrated
 * License: MIT (ImGui) + GPL/commercial (JUCE)
 */

#include <string.h>

// Stub implementations
int imgui_juce_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* imgui_juce_ffi_get_version(void) {
    return "not-available";
}

// Context management
void* imgui_juce_ffi_create_context(void) {
    return 0;
}

void imgui_juce_ffi_destroy_context(void* ctx) {
    // No-op
}

void imgui_juce_ffi_set_current_context(void* ctx) {
    // No-op
}

// Window management
void* imgui_juce_ffi_create_window(void* ctx, int width, int height, const char* title) {
    return 0;
}

void imgui_juce_ffi_destroy_window(void* window) {
    // No-op
}

void imgui_juce_ffi_get_window_size(void* window, int* width, int* height) {
    if (width) *width = 0;
    if (height) *height = 0;
}

// Frame management
void imgui_juce_ffi_new_frame(void* ctx) {
    // No-op
}

void imgui_juce_ffi_render(void* ctx) {
    // No-op
}

void imgui_juce_ffi_end_frame(void* ctx) {
    // No-op
}

// Widgets
int imgui_juce_ffi_button(const char* label, float width, float height) {
    return 0;
}

int imgui_juce_ffi_slider_float(const char* label, float* value,
                               float min, float max, const char* format) {
    return 0;
}

int imgui_juce_ffi_knob_float(const char* label, float* value,
                               float min, float max, float size) {
    return 0;
}

int imgui_juce_ffi_combo(const char* label, int* current_item,
                          const char** items, int item_count) {
    return 0;
}

int imgui_juce_ffi_checkbox(const char* label, int* value) {
    return 0;
}

int imgui_juce_ffi_begin_window(const char* title, int* open, int flags) {
    return 0;
}

void imgui_juce_ffi_end_window(void) {
    // No-op
}

void imgui_juce_ffi_text(const char* label) {
    // No-op
}

void imgui_juce_ffi_same_line(void) {
    // No-op
}

void imgui_juce_ffi_separator(void) {
    // No-op
}

// Audio-specific widgets
void imgui_juce_ffi_vu_meter(const char* label, float level,
                              float min_db, float max_db,
                              float width, float height) {
    // No-op
}

void imgui_juce_ffi_waveform_display(const float* samples, int sample_count,
                                      float width, float height) {
    // No-op
}

void imgui_juce_ffi_spectrum_display(const float* bins, int bin_count,
                                      float width, float height) {
    // No-op
}

// Style structure - match Rust layout
struct ImGuiStyle {
    float alpha;
    float window_rounding;
    float frame_rounding;
    float item_spacing_x;
    float item_spacing_y;
    unsigned int colors[32];
};

void imgui_juce_ffi_set_style(void* ctx, const struct ImGuiStyle* style) {
    // No-op
}

void imgui_juce_ffi_get_style(void* ctx, struct ImGuiStyle* style) {
    if (style) {
        memset(style, 0, sizeof(struct ImGuiStyle));
    }
}
