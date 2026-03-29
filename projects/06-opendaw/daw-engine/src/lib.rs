//! OpenDAW Audio Engine
//! 
//! Real-time audio processing engine with low-latency playback,
//! mixing, and plugin hosting capabilities.

pub mod callback;
pub mod generators;
pub mod mixer;
pub mod clock;
pub mod stream;
pub mod sample;
pub mod sample_player;
pub mod session;
pub mod midi;
pub mod project;
pub mod transport;

pub use callback::AudioCallback;
pub use generators::SineWave;
pub use mixer::Mixer;
pub use clock::TransportClock;
pub use session::{SessionView, Clip, ClipState, Scene};
pub use midi::{MidiMessage, MidiNote, MidiEngine};
pub use project::{Project, Track, TrackType};
pub use transport::{Transport, TransportState, PlayMode};
