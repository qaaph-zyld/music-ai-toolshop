//! OpenGL Shaders Integration
//!
//! FFI bindings for OpenGL shader-based visualizations and GPU-accelerated audio processing
//! High-performance graphics for audio plugins and visualizers
//!
//! License: Various (OpenGL implementations)
//!

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_void};

/// OpenGL context handle
#[repr(C)]
pub struct GlContext {
    _private: [u8; 0],
}

/// Shader program handle
#[repr(C)]
pub struct ShaderProgram {
    _private: [u8; 0],
}

/// Framebuffer handle
#[repr(C)]
pub struct Framebuffer {
    _private: [u8; 0],
}

/// Texture handle
#[repr(C)]
pub struct GlTexture {
    _private: [u8; 0],
}

/// OpenGL error types
#[derive(Debug, Clone, PartialEq)]
pub enum GlShaderError {
    ContextCreationFailed(String),
    ShaderCompileFailed(String),
    ProgramLinkFailed(String),
    TextureLoadFailed(String),
    FramebufferError(String),
    RenderFailed(String),
    NotAvailable,
}

impl std::fmt::Display for GlShaderError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            GlShaderError::ContextCreationFailed(msg) => write!(f, "GL context creation failed: {}", msg),
            GlShaderError::ShaderCompileFailed(msg) => write!(f, "Shader compile failed: {}", msg),
            GlShaderError::ProgramLinkFailed(msg) => write!(f, "Program link failed: {}", msg),
            GlShaderError::TextureLoadFailed(msg) => write!(f, "Texture load failed: {}", msg),
            GlShaderError::FramebufferError(msg) => write!(f, "Framebuffer error: {}", msg),
            GlShaderError::RenderFailed(msg) => write!(f, "Render failed: {}", msg),
            GlShaderError::NotAvailable => write!(f, "OpenGL not available"),
        }
    }
}

impl std::error::Error for GlShaderError {}

/// Shader types
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ShaderType {
    Vertex,
    Fragment,
    Geometry,
    Compute,
}

/// Texture format
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum TextureFormat {
    R8,
    RG8,
    RGB8,
    RGBA8,
    R16F,
    RG16F,
    RGBA16F,
    R32F,
    RGBA32F,
}

/// Render target configuration
#[derive(Debug, Clone)]
pub struct RenderTarget {
    pub width: u32,
    pub height: u32,
    pub format: TextureFormat,
    pub has_depth: bool,
}

impl RenderTarget {
    pub fn new(width: u32, height: u32) -> Self {
        Self {
            width,
            height,
            format: TextureFormat::RGBA8,
            has_depth: false,
        }
    }

    pub fn with_format(mut self, format: TextureFormat) -> Self {
        self.format = format;
        self
    }

    pub fn with_depth(mut self) -> Self {
        self.has_depth = true;
        self
    }
}

/// Audio visualization shader uniforms
#[derive(Debug, Clone, Default)]
pub struct AudioUniforms {
    pub time: f32,
    pub sample_rate: f32,
    pub fft_bins: Vec<f32>,
    pub waveform: Vec<f32>,
    pub bpm: f32,
    pub beat_phase: f32,
}

/// OpenGL shader engine
pub struct GlShaderEngine {
    context: *mut GlContext,
    width: u32,
    height: u32,
    frame_count: u64,
}

/// Compiled shader program
pub struct GlShaderProgram {
    program: *mut ShaderProgram,
    vertex_shader: u32,
    fragment_shader: u32,
    uniforms: Vec<(String, i32)>,
}

/// Offscreen render target
pub struct GlFramebuffer {
    framebuffer: *mut Framebuffer,
    texture: u32,
    width: u32,
    height: u32,
}

/// GPU texture
pub struct GlTextureHandle {
    texture: *mut GlTexture,
    width: u32,
    height: u32,
    format: TextureFormat,
}

// FFI function declarations
extern "C" {
    fn gl_shader_ffi_is_available() -> c_int;
    fn gl_shader_ffi_get_version() -> *const c_char;
    fn gl_shader_ffi_get_gl_version() -> *const c_char;
    
    // Context
    fn gl_shader_ffi_create_context(width: c_int, height: c_int) -> *mut GlContext;
    fn gl_shader_ffi_destroy_context(ctx: *mut GlContext);
    fn gl_shader_ffi_make_current(ctx: *mut GlContext);
    fn gl_shader_ffi_swap_buffers(ctx: *mut GlContext);
    fn gl_shader_ffi_get_error() -> *const c_char;
    fn gl_shader_ffi_clear_error();
    
    // Shaders
    fn gl_shader_ffi_compile_shader(shader_type: c_int, source: *const c_char) -> c_int;
    fn gl_shader_ffi_delete_shader(shader_id: c_int);
    fn gl_shader_ffi_get_shader_log(shader_id: c_int) -> *const c_char;
    
    // Programs
    fn gl_shader_ffi_create_program() -> *mut ShaderProgram;
    fn gl_shader_ffi_delete_program(program: *mut ShaderProgram);
    fn gl_shader_ffi_attach_shader(program: *mut ShaderProgram, shader_id: c_int);
    fn gl_shader_ffi_link_program(program: *mut ShaderProgram) -> c_int;
    fn gl_shader_ffi_get_program_log(program: *mut ShaderProgram) -> *const c_char;
    fn gl_shader_ffi_use_program(program: *mut ShaderProgram);
    fn gl_shader_ffi_get_uniform_location(program: *mut ShaderProgram, name: *const c_char) -> c_int;
    fn gl_shader_ffi_set_uniform_1f(location: c_int, value: c_float);
    fn gl_shader_ffi_set_uniform_2f(location: c_int, x: c_float, y: c_float);
    fn gl_shader_ffi_set_uniform_3f(location: c_int, x: c_float, y: c_float, z: c_float);
    fn gl_shader_ffi_set_uniform_1i(location: c_int, value: c_int);
    fn gl_shader_ffi_set_uniform_1fv(location: c_int, values: *const c_float, count: c_int);
    
    // Framebuffers
    fn gl_shader_ffi_create_framebuffer(width: c_int, height: c_int, 
                                           format: c_int, has_depth: c_int) -> *mut Framebuffer;
    fn gl_shader_ffi_delete_framebuffer(fb: *mut Framebuffer);
    fn gl_shader_ffi_bind_framebuffer(fb: *mut Framebuffer);
    fn gl_shader_ffi_unbind_framebuffer();
    fn gl_shader_ffi_get_framebuffer_texture(fb: *mut Framebuffer) -> c_int;
    fn gl_shader_ffi_clear_framebuffer(r: c_float, g: c_float, b: c_float, a: c_float);
    
    // Textures
    fn gl_shader_ffi_create_texture(width: c_int, height: c_int, format: c_int) -> *mut GlTexture;
    fn gl_shader_ffi_delete_texture(texture: *mut GlTexture);
    fn gl_shader_ffi_bind_texture(texture: *mut GlTexture, slot: c_int);
    fn gl_shader_ffi_upload_texture_data(texture: *mut GlTexture, 
                                          data: *const c_void, data_format: c_int);
    fn gl_shader_ffi_generate_mipmaps(texture: *mut GlTexture);
    
    // Geometry
    fn gl_shader_ffi_draw_fullscreen_quad();
    fn gl_shader_ffi_set_viewport(x: c_int, y: c_int, width: c_int, height: c_int);
    
    // Audio-specific
    fn gl_shader_ffi_upload_audio_texture(texture: *mut GlTexture,
                                           samples: *const c_float,
                                           sample_count: c_int);
    fn gl_shader_ffi_upload_fft_texture(texture: *mut GlTexture,
                                         bins: *const c_float,
                                         bin_count: c_int);
}

impl GlShaderEngine {
    /// Create new OpenGL shader engine
    pub fn new(width: u32, height: u32) -> Result<Self, GlShaderError> {
        if !Self::is_available() {
            return Err(GlShaderError::NotAvailable);
        }

        unsafe {
            let context = gl_shader_ffi_create_context(width as c_int, height as c_int);
            if context.is_null() {
                return Err(GlShaderError::ContextCreationFailed(
                    "Failed to create OpenGL context".to_string()
                ));
            }

            gl_shader_ffi_make_current(context);

            Ok(Self {
                context,
                width,
                height,
                frame_count: 0,
            })
        }
    }

    /// Check if OpenGL shaders are available
    pub fn is_available() -> bool {
        unsafe { gl_shader_ffi_is_available() != 0 }
    }

    /// Get shader engine version
    pub fn version() -> String {
        unsafe {
            let version_ptr = gl_shader_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Get OpenGL version
    pub fn gl_version() -> String {
        unsafe {
            let version_ptr = gl_shader_ffi_get_gl_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Create shader program from source
    pub fn create_program(&self, vertex_source: &str, fragment_source: &str) 
        -> Result<GlShaderProgram, GlShaderError> {
        let vertex_cstring = CString::new(vertex_source)
            .map_err(|e| GlShaderError::ShaderCompileFailed(e.to_string()))?;
        let fragment_cstring = CString::new(fragment_source)
            .map_err(|e| GlShaderError::ShaderCompileFailed(e.to_string()))?;

        unsafe {
            // Compile vertex shader
            let vertex_id = gl_shader_ffi_compile_shader(0, vertex_cstring.as_ptr());
            if vertex_id == 0 {
                let log = CStr::from_ptr(gl_shader_ffi_get_shader_log(vertex_id))
                    .to_string_lossy()
                    .into_owned();
                return Err(GlShaderError::ShaderCompileFailed(log));
            }

            // Compile fragment shader
            let fragment_id = gl_shader_ffi_compile_shader(1, fragment_cstring.as_ptr());
            if fragment_id == 0 {
                gl_shader_ffi_delete_shader(vertex_id);
                let log = CStr::from_ptr(gl_shader_ffi_get_shader_log(fragment_id))
                    .to_string_lossy()
                    .into_owned();
                return Err(GlShaderError::ShaderCompileFailed(log));
            }

            // Create and link program
            let program = gl_shader_ffi_create_program();
            if program.is_null() {
                gl_shader_ffi_delete_shader(vertex_id);
                gl_shader_ffi_delete_shader(fragment_id);
                return Err(GlShaderError::ProgramLinkFailed(
                    "Failed to create program".to_string()
                ));
            }

            gl_shader_ffi_attach_shader(program, vertex_id);
            gl_shader_ffi_attach_shader(program, fragment_id);

            let link_result = gl_shader_ffi_link_program(program);
            if link_result != 0 {
                let log = CStr::from_ptr(gl_shader_ffi_get_program_log(program))
                    .to_string_lossy()
                    .into_owned();
                gl_shader_ffi_delete_program(program);
                gl_shader_ffi_delete_shader(vertex_id);
                gl_shader_ffi_delete_shader(fragment_id);
                return Err(GlShaderError::ProgramLinkFailed(log));
            }

            Ok(GlShaderProgram {
                program,
                vertex_shader: vertex_id as u32,
                fragment_shader: fragment_id as u32,
                uniforms: Vec::new(),
            })
        }
    }

    /// Create framebuffer for offscreen rendering
    pub fn create_framebuffer(&self, target: &RenderTarget) -> Result<GlFramebuffer, GlShaderError> {
        unsafe {
            let format_val = target.format as c_int;
            let has_depth = if target.has_depth { 1 } else { 0 };

            let framebuffer = gl_shader_ffi_create_framebuffer(
                target.width as c_int,
                target.height as c_int,
                format_val,
                has_depth,
            );

            if framebuffer.is_null() {
                return Err(GlShaderError::FramebufferError(
                    "Failed to create framebuffer".to_string()
                ));
            }

            let texture = gl_shader_ffi_get_framebuffer_texture(framebuffer) as u32;

            Ok(GlFramebuffer {
                framebuffer,
                texture,
                width: target.width,
                height: target.height,
            })
        }
    }

    /// Create texture
    pub fn create_texture(&self, width: u32, height: u32, format: TextureFormat) 
        -> Result<GlTextureHandle, GlShaderError> {
        unsafe {
            let texture = gl_shader_ffi_create_texture(width as c_int, height as c_int, format as c_int);
            if texture.is_null() {
                return Err(GlShaderError::TextureLoadFailed(
                    "Failed to create texture".to_string()
                ));
            }

            Ok(GlTextureHandle {
                texture,
                width,
                height,
                format,
            })
        }
    }

    /// Set viewport
    pub fn set_viewport(&self, x: i32, y: i32, width: i32, height: i32) {
        unsafe {
            gl_shader_ffi_set_viewport(x, y, width, height);
        }
    }

    /// Clear screen/framebuffer
    pub fn clear(&self, r: f32, g: f32, b: f32, a: f32) {
        unsafe {
            gl_shader_ffi_clear_framebuffer(r, g, b, a);
        }
    }

    /// Render fullscreen quad with current shader
    pub fn draw_fullscreen(&self) {
        unsafe {
            gl_shader_ffi_draw_fullscreen_quad();
        }
    }

    /// Swap buffers (for onscreen rendering)
    pub fn swap_buffers(&self) {
        unsafe {
            gl_shader_ffi_swap_buffers(self.context);
        }
    }

    /// Get last error
    pub fn get_error(&self) -> Option<String> {
        unsafe {
            let error_ptr = gl_shader_ffi_get_error();
            if error_ptr.is_null() {
                return None;
            }
            let error = CStr::from_ptr(error_ptr)
                .to_string_lossy()
                .into_owned();
            if error.is_empty() {
                None
            } else {
                Some(error)
            }
        }
    }

    /// Clear error state
    pub fn clear_error(&self) {
        unsafe {
            gl_shader_ffi_clear_error();
        }
    }

    /// Get frame count
    pub fn frame_count(&self) -> u64 {
        self.frame_count
    }

    /// Increment frame count
    pub fn next_frame(&mut self) {
        self.frame_count += 1;
    }
}

impl Drop for GlShaderEngine {
    fn drop(&mut self) {
        unsafe {
            if !self.context.is_null() {
                gl_shader_ffi_destroy_context(self.context);
            }
        }
    }
}

impl GlShaderProgram {
    /// Use this program for rendering
    pub fn bind(&self) {
        unsafe {
            gl_shader_ffi_use_program(self.program);
        }
    }

    /// Find uniform location
    pub fn get_uniform_location(&mut self, name: &str) -> Option<i32> {
        // Check cache
        for (n, loc) in &self.uniforms {
            if n == name {
                return Some(*loc);
            }
        }

        // Query from GL
        let name_cstring = CString::new(name).ok()?;
        unsafe {
            let loc = gl_shader_ffi_get_uniform_location(self.program, name_cstring.as_ptr());
            if loc >= 0 {
                self.uniforms.push((name.to_string(), loc));
                Some(loc)
            } else {
                None
            }
        }
    }

    /// Set float uniform
    pub fn set_float(&self, location: i32, value: f32) {
        unsafe {
            gl_shader_ffi_set_uniform_1f(location, value);
        }
    }

    /// Set vec2 uniform
    pub fn set_vec2(&self, location: i32, x: f32, y: f32) {
        unsafe {
            gl_shader_ffi_set_uniform_2f(location, x, y);
        }
    }

    /// Set vec3 uniform
    pub fn set_vec3(&self, location: i32, x: f32, y: f32, z: f32) {
        unsafe {
            gl_shader_ffi_set_uniform_3f(location, x, y, z);
        }
    }

    /// Set int uniform
    pub fn set_int(&self, location: i32, value: i32) {
        unsafe {
            gl_shader_ffi_set_uniform_1i(location, value);
        }
    }

    /// Set float array uniform
    pub fn set_float_array(&self, location: i32, values: &[f32]) {
        unsafe {
            gl_shader_ffi_set_uniform_1fv(location, values.as_ptr(), values.len() as c_int);
        }
    }
}

impl Drop for GlShaderProgram {
    fn drop(&mut self) {
        unsafe {
            if !self.program.is_null() {
                gl_shader_ffi_delete_program(self.program);
            }
            gl_shader_ffi_delete_shader(self.vertex_shader as c_int);
            gl_shader_ffi_delete_shader(self.fragment_shader as c_int);
        }
    }
}

impl GlFramebuffer {
    /// Bind framebuffer for rendering
    pub fn bind(&self) {
        unsafe {
            gl_shader_ffi_bind_framebuffer(self.framebuffer);
        }
    }

    /// Unbind framebuffer (render to screen)
    pub fn unbind() {
        unsafe {
            gl_shader_ffi_unbind_framebuffer();
        }
    }

    /// Get texture ID for sampling
    pub fn texture(&self) -> u32 {
        self.texture
    }

    /// Get dimensions
    pub fn dimensions(&self) -> (u32, u32) {
        (self.width, self.height)
    }
}

impl Drop for GlFramebuffer {
    fn drop(&mut self) {
        unsafe {
            if !self.framebuffer.is_null() {
                gl_shader_ffi_delete_framebuffer(self.framebuffer);
            }
        }
    }
}

impl GlTextureHandle {
    /// Bind texture to slot
    pub fn bind(&self, slot: i32) {
        unsafe {
            gl_shader_ffi_bind_texture(self.texture, slot);
        }
    }

    /// Upload audio data as texture
    pub fn upload_audio(&mut self, samples: &[f32]) {
        unsafe {
            gl_shader_ffi_upload_audio_texture(self.texture, samples.as_ptr(), samples.len() as c_int);
        }
    }

    /// Upload FFT bins as texture
    pub fn upload_fft(&mut self, bins: &[f32]) {
        unsafe {
            gl_shader_ffi_upload_fft_texture(self.texture, bins.as_ptr(), bins.len() as c_int);
        }
    }

    /// Generate mipmaps
    pub fn generate_mipmaps(&self) {
        unsafe {
            gl_shader_ffi_generate_mipmaps(self.texture);
        }
    }

    /// Get dimensions
    pub fn dimensions(&self) -> (u32, u32) {
        (self.width, self.height)
    }

    /// Get format
    pub fn format(&self) -> TextureFormat {
        self.format
    }
}

impl Drop for GlTextureHandle {
    fn drop(&mut self) {
        unsafe {
            if !self.texture.is_null() {
                gl_shader_ffi_delete_texture(self.texture);
            }
        }
    }
}

/// Preset shaders for audio visualization
pub mod preset_shaders {
    /// Vertex shader for fullscreen quad
    pub const FULLSCREEN_VERTEX: &str = r#"
        #version 330 core
        layout(location = 0) in vec2 position;
        layout(location = 1) in vec2 texCoord;
        out vec2 vTexCoord;
        void main() {
            gl_Position = vec4(position, 0.0, 1.0);
            vTexCoord = texCoord;
        }
    "#;

    /// Fragment shader for waveform display
    pub const WAVEFORM_FRAGMENT: &str = r#"
        #version 330 core
        in vec2 vTexCoord;
        out vec4 fragColor;
        uniform sampler2D waveformTex;
        uniform vec3 color;
        uniform float intensity;
        void main() {
            float sample = texture(waveformTex, vec2(vTexCoord.x, 0.5)).r;
            float dist = abs(vTexCoord.y - 0.5 - sample * 0.5);
            float alpha = smoothstep(0.02 * intensity, 0.0, dist);
            fragColor = vec4(color, alpha);
        }
    "#;

    /// Fragment shader for spectrum analyzer
    pub const SPECTRUM_FRAGMENT: &str = r#"
        #version 330 core
        in vec2 vTexCoord;
        out vec4 fragColor;
        uniform sampler2D spectrumTex;
        uniform vec3 barColor;
        uniform vec3 peakColor;
        uniform float time;
        void main() {
            float magnitude = texture(spectrumTex, vec2(vTexCoord.x, 0.5)).r;
            float height = magnitude * 2.0;
            float dist = vTexCoord.y - (1.0 - height);
            vec3 color = mix(barColor, peakColor, magnitude);
            float alpha = smoothstep(0.0, 0.02, -dist);
            fragColor = vec4(color, alpha);
        }
    "#;

    /// Fragment shader for oscilloscope
    pub const OSCILLOSCOPE_FRAGMENT: &str = r#"
        #version 330 core
        in vec2 vTexCoord;
        out vec4 fragColor;
        uniform sampler2D audioTex;
        uniform vec2 resolution;
        uniform float time;
        uniform vec3 traceColor;
        void main() {
            float sample = texture(audioTex, vec2(vTexCoord.x, 0.5)).r;
            float pixelSize = 2.0 / resolution.y;
            float dist = abs(vTexCoord.y - 0.5 - sample * 0.4);
            float alpha = smoothstep(pixelSize * 2.0, 0.0, dist);
            fragColor = vec4(traceColor, alpha);
        }
    "#;
}

#[cfg(test)]
mod tests {
    use super::*;
    use super::preset_shaders::*;

    #[test]
    fn test_gl_shader_module_exists() {
        let _ = GlShaderError::NotAvailable;
        let _ = ShaderType::Fragment;
        let _ = TextureFormat::RGBA8;
        let _ = RenderTarget::new(800, 600);
    }

    #[test]
    fn test_gl_shader_is_available() {
        let available = GlShaderEngine::is_available();
        println!("OpenGL shaders available: {}", available);
    }

    #[test]
    fn test_gl_shader_version() {
        let version = GlShaderEngine::version();
        println!("Shader engine version: {}", version);
        
        let gl_ver = GlShaderEngine::gl_version();
        println!("OpenGL version: {}", gl_ver);
    }

    #[test]
    fn test_shader_types() {
        let types = vec![
            ShaderType::Vertex,
            ShaderType::Fragment,
            ShaderType::Geometry,
            ShaderType::Compute,
        ];
        for t in types {
            let s = format!("{:?}", t);
            assert!(!s.is_empty());
        }
    }

    #[test]
    fn test_texture_formats() {
        let formats = vec![
            TextureFormat::R8,
            TextureFormat::RGBA8,
            TextureFormat::R16F,
            TextureFormat::RGBA16F,
            TextureFormat::R32F,
            TextureFormat::RGBA32F,
        ];
        for f in formats {
            let s = format!("{:?}", f);
            assert!(!s.is_empty());
        }
    }

    #[test]
    fn test_render_target_builder() {
        let target = RenderTarget::new(800, 600)
            .with_format(TextureFormat::RGBA16F)
            .with_depth();
        
        assert_eq!(target.width, 800);
        assert_eq!(target.height, 600);
        assert_eq!(target.format, TextureFormat::RGBA16F);
        assert!(target.has_depth);
    }

    #[test]
    fn test_audio_uniforms_default() {
        let uniforms: AudioUniforms = Default::default();
        assert_eq!(uniforms.time, 0.0);
        assert_eq!(uniforms.sample_rate, 0.0);
        assert!(uniforms.fft_bins.is_empty());
        assert!(uniforms.waveform.is_empty());
        assert_eq!(uniforms.bpm, 0.0);
        assert_eq!(uniforms.beat_phase, 0.0);
    }

    #[test]
    fn test_new_fails_gracefully() {
        let result = GlShaderEngine::new(800, 600);
        match result {
            Err(GlShaderError::NotAvailable) | Err(GlShaderError::ContextCreationFailed(_)) => {
                // Expected
            }
            _ => panic!("Expected NotAvailable or ContextCreationFailed"),
        }
    }

    #[test]
    fn test_gl_shader_error_display() {
        let err = GlShaderError::NotAvailable;
        assert!(err.to_string().contains("not available"));

        let err = GlShaderError::ContextCreationFailed("test".to_string());
        assert!(err.to_string().contains("context creation failed"));

        let err = GlShaderError::ShaderCompileFailed("test".to_string());
        assert!(err.to_string().contains("Shader compile failed"));

        let err = GlShaderError::ProgramLinkFailed("test".to_string());
        assert!(err.to_string().contains("Program link failed"));

        let err = GlShaderError::TextureLoadFailed("test".to_string());
        assert!(err.to_string().contains("Texture load failed"));

        let err = GlShaderError::FramebufferError("test".to_string());
        assert!(err.to_string().contains("Framebuffer error"));

        let err = GlShaderError::RenderFailed("test".to_string());
        assert!(err.to_string().contains("Render failed"));
    }

    #[test]
    fn test_preset_shaders_exist() {
        assert!(!FULLSCREEN_VERTEX.is_empty());
        assert!(FULLSCREEN_VERTEX.contains("#version"));
        
        assert!(!WAVEFORM_FRAGMENT.is_empty());
        assert!(WAVEFORM_FRAGMENT.contains("waveformTex"));
        
        assert!(!SPECTRUM_FRAGMENT.is_empty());
        assert!(SPECTRUM_FRAGMENT.contains("spectrumTex"));
        
        assert!(!OSCILLOSCOPE_FRAGMENT.is_empty());
        assert!(OSCILLOSCOPE_FRAGMENT.contains("audioTex"));
    }

    #[test]
    fn test_engine_accessors() {
        let engine = GlShaderEngine {
            context: std::ptr::null_mut(),
            width: 800,
            height: 600,
            frame_count: 100,
        };
        
        assert_eq!(engine.frame_count(), 100);
    }
}
