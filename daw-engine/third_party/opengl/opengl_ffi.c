/* OpenGL Shaders FFI Stub for OpenDAW
 * Stub implementation until OpenGL is integrated
 * License: Various (OpenGL implementations)
 */

#include <string.h>

// Stub implementations
int gl_shader_ffi_is_available(void) {
    return 0;  // Not available until library is integrated
}

const char* gl_shader_ffi_get_version(void) {
    return "not-available";
}

const char* gl_shader_ffi_get_gl_version(void) {
    return "not-available";
}

// Context
void* gl_shader_ffi_create_context(int width, int height) {
    return 0;
}

void gl_shader_ffi_destroy_context(void* ctx) {
    // No-op
}

void gl_shader_ffi_make_current(void* ctx) {
    // No-op
}

void gl_shader_ffi_swap_buffers(void* ctx) {
    // No-op
}

const char* gl_shader_ffi_get_error(void) {
    return "";
}

void gl_shader_ffi_clear_error(void) {
    // No-op
}

// Shaders
int gl_shader_ffi_compile_shader(int shader_type, const char* source) {
    return 0;
}

void gl_shader_ffi_delete_shader(int shader_id) {
    // No-op
}

const char* gl_shader_ffi_get_shader_log(int shader_id) {
    return "";
}

// Programs
void* gl_shader_ffi_create_program(void) {
    return 0;
}

void gl_shader_ffi_delete_program(void* program) {
    // No-op
}

void gl_shader_ffi_attach_shader(void* program, int shader_id) {
    // No-op
}

int gl_shader_ffi_link_program(void* program) {
    return -1;
}

const char* gl_shader_ffi_get_program_log(void* program) {
    return "";
}

void gl_shader_ffi_use_program(void* program) {
    // No-op
}

int gl_shader_ffi_get_uniform_location(void* program, const char* name) {
    return -1;
}

void gl_shader_ffi_set_uniform_1f(int location, float value) {
    // No-op
}

void gl_shader_ffi_set_uniform_2f(int location, float x, float y) {
    // No-op
}

void gl_shader_ffi_set_uniform_3f(int location, float x, float y, float z) {
    // No-op
}

void gl_shader_ffi_set_uniform_1i(int location, int value) {
    // No-op
}

void gl_shader_ffi_set_uniform_1fv(int location, const float* values, int count) {
    // No-op
}

// Framebuffers
void* gl_shader_ffi_create_framebuffer(int width, int height, int format, int has_depth) {
    return 0;
}

void gl_shader_ffi_delete_framebuffer(void* fb) {
    // No-op
}

void gl_shader_ffi_bind_framebuffer(void* fb) {
    // No-op
}

void gl_shader_ffi_unbind_framebuffer(void) {
    // No-op
}

int gl_shader_ffi_get_framebuffer_texture(void* fb) {
    return 0;
}

void gl_shader_ffi_clear_framebuffer(float r, float g, float b, float a) {
    // No-op
}

// Textures
void* gl_shader_ffi_create_texture(int width, int height, int format) {
    return 0;
}

void gl_shader_ffi_delete_texture(void* texture) {
    // No-op
}

void gl_shader_ffi_bind_texture(void* texture, int slot) {
    // No-op
}

void gl_shader_ffi_upload_texture_data(void* texture, const void* data, int data_format) {
    // No-op
}

void gl_shader_ffi_generate_mipmaps(void* texture) {
    // No-op
}

// Geometry
void gl_shader_ffi_draw_fullscreen_quad(void) {
    // No-op
}

void gl_shader_ffi_set_viewport(int x, int y, int width, int height) {
    // No-op
}

// Audio-specific
void gl_shader_ffi_upload_audio_texture(void* texture,
                                         const float* samples,
                                         int sample_count) {
    // No-op
}

void gl_shader_ffi_upload_fft_texture(void* texture,
                                       const float* bins,
                                       int bin_count) {
    // No-op
}
