//! ImGui for JUCE Integration
//!
//! FFI bindings for Dear ImGui integration with JUCE framework
//! Immediate mode GUI for audio plugin interfaces
//!
//! License: MIT (ImGui) + GPL/commercial (JUCE)
//! Repo: https://github.com/ocornut/imgui

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_float, c_int, c_void};

/// ImGui context handle
#[repr(C)]
pub struct ImGuiContext {
    _private: [u8; 0],
}

/// ImGui window handle (JUCE component wrapper)
#[repr(C)]
pub struct ImGuiJuceWindow {
    _private: [u8; 0],
}

/// ImGui error types
#[derive(Debug, Clone, PartialEq)]
pub enum ImGuiError {
    InitFailed(String),
    RenderFailed(String),
    WidgetFailed(String),
    NotAvailable,
}

impl std::fmt::Display for ImGuiError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ImGuiError::InitFailed(msg) => write!(f, "ImGui init failed: {}", msg),
            ImGuiError::RenderFailed(msg) => write!(f, "ImGui render failed: {}", msg),
            ImGuiError::WidgetFailed(msg) => write!(f, "ImGui widget error: {}", msg),
            ImGuiError::NotAvailable => write!(f, "ImGui not available"),
        }
    }
}

impl std::error::Error for ImGuiError {}

/// ImGui style configuration
#[derive(Debug, Clone, Copy)]
pub struct ImGuiStyle {
    pub alpha: f32,
    pub window_rounding: f32,
    pub frame_rounding: f32,
    pub item_spacing: (f32, f32),
    pub colors: [u32; 32],  // ImGuiCol_COUNT = 32
}

impl Default for ImGuiStyle {
    fn default() -> Self {
        Self {
            alpha: 1.0,
            window_rounding: 4.0,
            frame_rounding: 4.0,
            item_spacing: (8.0, 4.0),
            colors: [0; 32],
        }
    }
}

/// Audio plugin GUI layout
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PluginLayout {
    Small,   // ~300x200
    Medium,  // ~600x400
    Large,   // ~1000x700
    Custom(u32, u32),
}

/// ImGui JUCE wrapper for audio plugins
pub struct ImGuiJuceComponent {
    context: *mut ImGuiContext,
    window: *mut ImGuiJuceWindow,
    width: u32,
    height: u32,
    frame_count: u64,
}

/// Widget builder for common audio controls
pub struct AudioWidgetBuilder {
    x: f32,
    y: f32,
    width: f32,
    height: f32,
}

// FFI function declarations
extern "C" {
    fn imgui_juce_ffi_is_available() -> c_int;
    fn imgui_juce_ffi_get_version() -> *const c_char;
    
    // Context management
    fn imgui_juce_ffi_create_context() -> *mut ImGuiContext;
    fn imgui_juce_ffi_destroy_context(ctx: *mut ImGuiContext);
    fn imgui_juce_ffi_set_current_context(ctx: *mut ImGuiContext);
    
    // Window management
    fn imgui_juce_ffi_create_window(ctx: *mut ImGuiContext, 
                                     width: c_int, height: c_int,
                                     title: *const c_char) -> *mut ImGuiJuceWindow;
    fn imgui_juce_ffi_destroy_window(window: *mut ImGuiJuceWindow);
    fn imgui_juce_ffi_get_window_size(window: *mut ImGuiJuceWindow, 
                                       width: *mut c_int, height: *mut c_int);
    
    // Frame management
    fn imgui_juce_ffi_new_frame(ctx: *mut ImGuiContext);
    fn imgui_juce_ffi_render(ctx: *mut ImGuiContext);
    fn imgui_juce_ffi_end_frame(ctx: *mut ImGuiContext);
    
    // Widgets
    fn imgui_juce_ffi_button(label: *const c_char, width: c_float, height: c_float) -> c_int;
    fn imgui_juce_ffi_slider_float(label: *const c_char, value: *mut c_float,
                                  min: c_float, max: c_float, format: *const c_char) -> c_int;
    fn imgui_juce_ffi_knob_float(label: *const c_char, value: *mut c_float,
                                  min: c_float, max: c_float, size: c_float) -> c_int;
    fn imgui_juce_ffi_combo(label: *const c_char, current_item: *mut c_int,
                             items: *const *const c_char, item_count: c_int) -> c_int;
    fn imgui_juce_ffi_checkbox(label: *const c_char, value: *mut c_int) -> c_int;
    fn imgui_juce_ffi_begin_window(title: *const c_char, open: *mut c_int, flags: c_int) -> c_int;
    fn imgui_juce_ffi_end_window();
    fn imgui_juce_ffi_text(label: *const c_char);
    fn imgui_juce_ffi_same_line();
    fn imgui_juce_ffi_separator();
    
    // Audio-specific widgets
    fn imgui_juce_ffi_vu_meter(label: *const c_char, level: c_float, 
                                min_db: c_float, max_db: c_float,
                                width: c_float, height: c_float);
    fn imgui_juce_ffi_waveform_display(samples: *const c_float, sample_count: c_int,
                                      width: c_float, height: c_float);
    fn imgui_juce_ffi_spectrum_display(bins: *const c_float, bin_count: c_int,
                                        width: c_float, height: c_float);
    
    // Style
    fn imgui_juce_ffi_set_style(ctx: *mut ImGuiContext, style: *const ImGuiStyle);
    fn imgui_juce_ffi_get_style(ctx: *mut ImGuiContext, style: *mut ImGuiStyle);
}

impl ImGuiJuceComponent {
    /// Create new ImGui JUCE component
    pub fn new(width: u32, height: u32, title: &str) -> Result<Self, ImGuiError> {
        if !Self::is_available() {
            return Err(ImGuiError::NotAvailable);
        }

        let title_cstring = CString::new(title)
            .map_err(|e| ImGuiError::InitFailed(e.to_string()))?;

        unsafe {
            let context = imgui_juce_ffi_create_context();
            if context.is_null() {
                return Err(ImGuiError::InitFailed("Failed to create ImGui context".to_string()));
            }

            imgui_juce_ffi_set_current_context(context);

            let window = imgui_juce_ffi_create_window(
                context,
                width as c_int,
                height as c_int,
                title_cstring.as_ptr(),
            );

            if window.is_null() {
                imgui_juce_ffi_destroy_context(context);
                return Err(ImGuiError::InitFailed("Failed to create window".to_string()));
            }

            Ok(Self {
                context,
                window,
                width,
                height,
                frame_count: 0,
            })
        }
    }

    /// Create component with standard plugin layout
    pub fn with_layout(layout: PluginLayout, title: &str) -> Result<Self, ImGuiError> {
        let (w, h) = match layout {
            PluginLayout::Small => (300, 200),
            PluginLayout::Medium => (600, 400),
            PluginLayout::Large => (1000, 700),
            PluginLayout::Custom(w, h) => (w, h),
        };
        Self::new(w, h, title)
    }

    /// Check if ImGui JUCE is available
    pub fn is_available() -> bool {
        unsafe { imgui_juce_ffi_is_available() != 0 }
    }

    /// Get ImGui version
    pub fn version() -> String {
        unsafe {
            let version_ptr = imgui_juce_ffi_get_version();
            if version_ptr.is_null() {
                return "unknown".to_string();
            }
            CStr::from_ptr(version_ptr)
                .to_string_lossy()
                .into_owned()
        }
    }

    /// Begin new frame
    pub fn new_frame(&mut self) {
        unsafe {
            imgui_juce_ffi_set_current_context(self.context);
            imgui_juce_ffi_new_frame(self.context);
        }
        self.frame_count += 1;
    }

    /// End frame and render
    pub fn end_frame(&mut self) {
        unsafe {
            imgui_juce_ffi_end_frame(self.context);
        }
    }

    /// Render ImGui draw data
    pub fn render(&mut self) {
        unsafe {
            imgui_juce_ffi_render(self.context);
        }
    }

    /// Get window size
    pub fn get_size(&self) -> (i32, i32) {
        let mut width: c_int = 0;
        let mut height: c_int = 0;
        unsafe {
            imgui_juce_ffi_get_window_size(self.window, &mut width, &mut height);
        }
        (width, height)
    }

    /// Set ImGui style
    pub fn set_style(&mut self, style: &ImGuiStyle) {
        unsafe {
            imgui_juce_ffi_set_style(self.context, style as *const ImGuiStyle);
        }
    }

    /// Get current style
    pub fn get_style(&self) -> ImGuiStyle {
        let mut style = ImGuiStyle::default();
        unsafe {
            imgui_juce_ffi_get_style(self.context, &mut style);
        }
        style
    }

    /// Get frame count
    pub fn frame_count(&self) -> u64 {
        self.frame_count
    }
}

impl Drop for ImGuiJuceComponent {
    fn drop(&mut self) {
        unsafe {
            if !self.window.is_null() {
                imgui_juce_ffi_destroy_window(self.window);
            }
            if !self.context.is_null() {
                imgui_juce_ffi_destroy_context(self.context);
            }
        }
    }
}

/// Audio widget drawing functions
pub mod audio_widgets {
    use super::*;

    /// Draw a button
    pub fn button(label: &str, width: f32, height: f32) -> bool {
        let label_cstring = CString::new(label).unwrap();
        unsafe {
            imgui_juce_ffi_button(label_cstring.as_ptr(), width, height) != 0
        }
    }

    /// Draw a float slider
    pub fn slider_float(label: &str, value: &mut f32, min: f32, max: f32) -> bool {
        let label_cstring = CString::new(label).unwrap();
        let format = CString::new("%.3f").unwrap();
        unsafe {
            imgui_juce_ffi_slider_float(label_cstring.as_ptr(), value as *mut c_float,
                                         min, max, format.as_ptr()) != 0
        }
    }

    /// Draw a knob (audio-style rotary control)
    pub fn knob(label: &str, value: &mut f32, min: f32, max: f32, size: f32) -> bool {
        let label_cstring = CString::new(label).unwrap();
        unsafe {
            imgui_juce_ffi_knob_float(label_cstring.as_ptr(), value as *mut c_float,
                                       min, max, size) != 0
        }
    }

    /// Draw a combo box
    pub fn combo(label: &str, current_item: &mut i32, items: &[&str]) -> bool {
        let label_cstring = CString::new(label).unwrap();
        let item_cstrings: Vec<CString> = items.iter()
            .map(|&s| CString::new(s).unwrap())
            .collect();
        let item_ptrs: Vec<*const c_char> = item_cstrings.iter()
            .map(|cs| cs.as_ptr())
            .collect();
        
        unsafe {
            imgui_juce_ffi_combo(label_cstring.as_ptr(), current_item as *mut c_int,
                                  item_ptrs.as_ptr(), items.len() as c_int) != 0
        }
    }

    /// Draw a checkbox
    pub fn checkbox(label: &str, value: &mut bool) -> bool {
        let label_cstring = CString::new(label).unwrap();
        let mut int_val = if *value { 1 } else { 0 };
        let result = unsafe {
            imgui_juce_ffi_checkbox(label_cstring.as_ptr(), &mut int_val) != 0
        };
        *value = int_val != 0;
        result
    }

    /// Begin a window
    pub fn begin_window(title: &str, open: Option<&mut bool>, flags: i32) -> bool {
        let title_cstring = CString::new(title).unwrap();
        let mut open_int = if let Some(b) = open.as_ref() {
            if **b { 1 } else { 0 }
        } else {
            1
        };
        let open_ptr = if open.is_some() {
            &mut open_int
        } else {
            std::ptr::null_mut()
        };
        
        unsafe {
            let result = imgui_juce_ffi_begin_window(title_cstring.as_ptr(), open_ptr, flags) != 0;
            if let Some(b) = open {
                *b = open_int != 0;
            }
            result
        }
    }

    /// End a window
    pub fn end_window() {
        unsafe {
            imgui_juce_ffi_end_window();
        }
    }

    /// Draw text
    pub fn text(label: &str) {
        let label_cstring = CString::new(label).unwrap();
        unsafe {
            imgui_juce_ffi_text(label_cstring.as_ptr());
        }
    }

    /// Same line (no newline)
    pub fn same_line() {
        unsafe {
            imgui_juce_ffi_same_line();
        }
    }

    /// Separator line
    pub fn separator() {
        unsafe {
            imgui_juce_ffi_separator();
        }
    }

    /// Draw VU meter
    pub fn vu_meter(label: &str, level_db: f32, min_db: f32, max_db: f32, width: f32, height: f32) {
        let label_cstring = CString::new(label).unwrap();
        let linear_level = 10.0f32.powf(level_db / 20.0);
        unsafe {
            imgui_juce_ffi_vu_meter(label_cstring.as_ptr(), linear_level, min_db, max_db, width, height);
        }
    }

    /// Draw waveform
    pub fn waveform(samples: &[f32], width: f32, height: f32) {
        unsafe {
            imgui_juce_ffi_waveform_display(samples.as_ptr(), samples.len() as c_int, width, height);
        }
    }

    /// Draw spectrum
    pub fn spectrum(bins: &[f32], width: f32, height: f32) {
        unsafe {
            imgui_juce_ffi_spectrum_display(bins.as_ptr(), bins.len() as c_int, width, height);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use super::audio_widgets::*;

    #[test]
    fn test_imgui_module_exists() {
        let _ = ImGuiError::NotAvailable;
        let _ = PluginLayout::Medium;
        let _ = ImGuiStyle::default();
    }

    #[test]
    fn test_imgui_is_available() {
        let available = ImGuiJuceComponent::is_available();
        println!("ImGui JUCE available: {}", available);
    }

    #[test]
    fn test_imgui_version() {
        let version = ImGuiJuceComponent::version();
        println!("ImGui version: {}", version);
    }

    #[test]
    fn test_plugin_layouts() {
        let layouts = vec![
            PluginLayout::Small,
            PluginLayout::Medium,
            PluginLayout::Large,
            PluginLayout::Custom(800, 600),
        ];
        for layout in layouts {
            let (w, h) = match layout {
                PluginLayout::Small => (300, 200),
                PluginLayout::Medium => (600, 400),
                PluginLayout::Large => (1000, 700),
                PluginLayout::Custom(w, h) => (w, h),
            };
            assert!(w > 0 && h > 0);
        }
    }

    #[test]
    fn test_imgui_style_default() {
        let style = ImGuiStyle::default();
        assert_eq!(style.alpha, 1.0);
        assert_eq!(style.window_rounding, 4.0);
        assert_eq!(style.frame_rounding, 4.0);
        assert_eq!(style.item_spacing, (8.0, 4.0));
    }

    #[test]
    fn test_new_fails_gracefully() {
        let result = ImGuiJuceComponent::new(600, 400, "Test");
        match result {
            Err(ImGuiError::NotAvailable) | Err(ImGuiError::InitFailed(_)) => {
                // Expected
            }
            _ => panic!("Expected NotAvailable or InitFailed"),
        }
    }

    #[test]
    fn test_with_layout_fails_gracefully() {
        let result = ImGuiJuceComponent::with_layout(PluginLayout::Medium, "Test");
        match result {
            Err(ImGuiError::NotAvailable) | Err(ImGuiError::InitFailed(_)) => {
                // Expected
            }
            _ => panic!("Expected NotAvailable or InitFailed"),
        }
    }

    #[test]
    fn test_imgui_error_display() {
        let err = ImGuiError::NotAvailable;
        assert!(err.to_string().contains("not available"));

        let err = ImGuiError::InitFailed("test".to_string());
        assert!(err.to_string().contains("init failed"));

        let err = ImGuiError::RenderFailed("test".to_string());
        assert!(err.to_string().contains("render failed"));

        let err = ImGuiError::WidgetFailed("test".to_string());
        assert!(err.to_string().contains("widget error"));
    }

    #[test]
    fn test_audio_widget_builder() {
        let builder = AudioWidgetBuilder {
            x: 10.0,
            y: 20.0,
            width: 100.0,
            height: 30.0,
        };
        assert_eq!(builder.x, 10.0);
        assert_eq!(builder.y, 20.0);
        assert_eq!(builder.width, 100.0);
        assert_eq!(builder.height, 30.0);
    }

    #[test]
    fn test_component_accessors() {
        // Create a mock component to test accessors
        let component = ImGuiJuceComponent {
            context: std::ptr::null_mut(),
            window: std::ptr::null_mut(),
            width: 800,
            height: 600,
            frame_count: 42,
        };
        
        assert_eq!(component.frame_count(), 42);
    }
}
