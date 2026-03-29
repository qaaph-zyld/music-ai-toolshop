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

pub use callback::AudioCallback;
pub use generators::SineWave;
pub use mixer::Mixer;
pub use clock::TransportClock;
