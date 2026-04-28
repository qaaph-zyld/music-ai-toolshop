//! OpenDAW Audio Engine
//! 
//! Real-time audio processing engine with low-latency playback,
//! mixing, and plugin hosting capabilities.
//!
//! NOTE: 53 aspirational FFI stub modules were quarantined to src/future/
//! on 2026-04-12. They contain no real integrations — only opaque handles
//! and mock tests. Re-integrate individually when actual linking is needed.

// === Core Engine ===
pub mod error;
pub mod callback;
pub mod generators;
pub mod mixer;
pub mod clock;
pub mod stream;
pub mod sample;
pub mod sample_fast;
pub mod sample_player;
pub mod sample_player_integration;
pub mod session;
pub mod midi;
pub mod midi_input;
pub mod transport;
pub mod realtime;
pub mod clip_player;
pub mod audio_processor;
pub mod audio_device;
pub mod profiler;
pub mod profiler_config;
pub mod memory_pool;
pub mod disk_stream;
pub mod loudness;
pub mod noise_suppression;
pub mod plugin;
pub mod plugin_clap;

// === Project System ===
pub mod project;
pub mod project_file;
pub mod serialization;
pub mod export;
pub mod export_renderer;

// === AI / ML Bridges ===
pub mod ai_bridge;
pub mod api_server;
pub mod musicgen;
pub mod stem_separation;
pub mod mmm;

// === FFI Layer (Rust → C++ JUCE) ===
pub mod ffi_bridge;
pub mod engine_ffi;
pub mod clip_player_ffi;
pub mod transport_sync;
pub mod transport_sync_ffi;
pub mod midi_ffi;
pub mod meter_ffi;
pub mod project_ffi;

// === Utilities ===
pub mod reverse_engineer;

// === Real Third-Party Integrations (71-component plan) ===
pub mod sndfilter;  // #35: reverb, compressor, biquad filters (0BSD)

// === Public re-exports ===
pub use error::{DAWError, DAWResult, limits, validate_sample_rate, validate_tempo, validate_buffer_size};
pub use ai_bridge::{AIBridge, AIGeneratedClip, AINote};
pub use callback::AudioCallback;
pub use generators::SineWave;
pub use sample::Sample;
pub use sample_player::SamplePlayer;
pub use mixer::{Mixer, AudioSource, PluginAudioSource};
pub use clock::TransportClock;
pub use session::{SessionView, Clip, ClipState, Scene};
pub use midi::{MidiMessage, MidiNote, MidiEngine};
pub use midi_input::{MidiInput, MidiDeviceInfo, QuantizationSettings, MidiDeviceEnumerator};
pub use project::{Project, Track, TrackType};
pub use transport::{Transport, TransportState, PlayMode};
pub use plugin::{PluginInstance, PluginChain, PluginState, PluginParameterValue, StatefulPlugin};
pub use reverse_engineer::{SpectralAnalyzer, DeltaAnalyzer, FingerprintDatabase};
pub use loudness::{LoudnessMeter, LoudnessReading};
pub use noise_suppression::{NoiseSuppressor, NoiseSuppressionResult, NoiseSuppressionError};
pub use sample_fast::{FastWavLoader, FastWavError};
pub use stem_separation::{StemSeparator, StemSeparationResult, StemSeparationError, StemType, StemProgressCallback};
pub use plugin_clap::{ClapPluginHost, ClapPluginScanner, ClapPluginInfo, ClapPluginError};
pub use export::{ExportEngine, ExportFormat, BitDepth, ExportError, ProgressCallback};
pub use musicgen::{MusicGenBridge, MusicGenStatus, GenerationRequest, GenerationResult, GenerationProgress, ModelSize};
pub use serialization::{SerializableProject, project_to_json, project_from_json, save_project_to_file, load_project_from_file, PROJECT_VERSION};
pub use audio_device::{AudioDeviceManager, AudioDeviceInfo, AudioDeviceError};
pub use api_server::start_server;
pub use profiler::{Profiler, CpuUsageTracker};
pub use profiler_config::{ProfilerConfig, init_from_env};
