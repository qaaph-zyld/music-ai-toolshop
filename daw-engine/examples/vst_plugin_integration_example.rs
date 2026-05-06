//! OpenDAW VST Plugin Integration Example
//!
//! This example demonstrates how to use the OpenDAW Rust audio engine
//! as the core audio processing engine in a VST3 plugin.
//!
//! Note: This is a conceptual example. Real VST3 plugin development
//! requires the VST3 SDK and additional boilerplate.

use daw_engine::{Mixer, Transport, SessionView, Clip};

/// VST Plugin structure using OpenDAW engine
struct OpenDAWPlugin {
    sample_rate: f64,
    mixer: Mixer,
    transport: Transport,
    session: SessionView,
}

impl OpenDAWPlugin {
    fn new(sample_rate: f64) -> Self {
        let transport = Transport::new(120.0, sample_rate as u32);
        let mixer = Mixer::new(2); // Stereo
        let session = SessionView::new(8, 8); // 8 tracks, 8 scenes

        Self {
            sample_rate,
            mixer,
            transport,
            session,
        }
    }

    /// Process audio buffer (called by VST host)
    fn process(&mut self, inputs: &[f32], outputs: &mut [f32]) {
        // Copy input to output (pass-through)
        outputs.copy_from_slice(inputs);

        // Process through OpenDAW mixer
        self.mixer.process(outputs);

        // Process transport
        self.transport.process(outputs.len() as u32);
    }

    /// Set sample rate (VST host callback)
    fn set_sample_rate(&mut self, sample_rate: f64) {
        self.sample_rate = sample_rate;
        // Recreate transport with new sample rate
        self.transport = Transport::new(120.0, sample_rate as u32);
    }

    /// Set tempo (VST host callback)
    fn set_tempo(&mut self, bpm: f64) {
        self.transport.set_tempo(bpm);
    }

    /// Start playback (VST host callback)
    fn start(&mut self) {
        self.transport.play();
    }

    /// Stop playback (VST host callback)
    fn stop(&mut self) {
        self.transport.stop();
    }

    /// Set track volume (plugin parameter)
    fn set_track_volume(&mut self, track: usize, volume: f32) {
        self.mixer.set_track_volume(track, volume);
    }

    /// Launch scene (MIDI trigger or automation)
    fn launch_scene(&mut self, scene: usize) {
        self.session.launch_scene(scene);
    }

    /// Load clip into session
    fn load_clip(&mut self, track: usize, scene: usize, clip: Clip) {
        self.session.set_clip(track, scene, clip);
    }
}

/// Example VST3 plugin adapter (conceptual)
mod vst3_adapter {
    use super::*;

    /// This would be the actual VST3 plugin entry point
    /// Requires the VST3 SDK for real implementation
    pub struct VST3Plugin {
        engine: OpenDAWPlugin,
    }

    impl VST3Plugin {
        pub fn new(sample_rate: f64) -> Self {
            Self {
                engine: OpenDAWPlugin::new(sample_rate),
            }
        }

        /// VST3 process callback
        pub fn process(&mut self, inputs: &[f32], outputs: &mut [f32]) {
            self.engine.process(inputs, outputs);
        }

        /// VST3 set sample rate callback
        pub fn set_sample_rate(&mut self, sample_rate: f64) {
            self.engine.set_sample_rate(sample_rate);
        }

        /// VST3 set tempo callback
        pub fn set_tempo(&mut self, bpm: f64) {
            self.engine.set_tempo(bpm);
        }

        /// VST3 start/stop callback
        pub fn set_playback_state(&mut self, playing: bool) {
            if playing {
                self.engine.start();
            } else {
                self.engine.stop();
            }
        }
    }
}

fn main() {
    println!("OpenDAW VST Plugin Integration Example");
    println!("========================================\n");

    println!("This example demonstrates how to integrate OpenDAW");
    println!("as the audio engine in a VST3 plugin.\n");

    println!("Key integration points:");
    println!("1. VST3 process() → OpenDAW mixer.process()");
    println!("2. VST3 setSampleRate() → OpenDAW Transport::new()");
    println!("3. VST3 setTempo() → OpenDAW transport.set_tempo()");
    println!("4. VST3 parameters → OpenDAW mixer.set_track_volume()");
    println!("5. VST3 MIDI → OpenDAW session.launch_scene()\n");

    println!("To build a real VST3 plugin:");
    println!("1. Download VST3 SDK from Steinberg");
    println!("2. Use vst-rs or raw C++ bindings");
    println!("3. Implement IAudioProcessor interface");
    println!("4. Package as .vst3 bundle\n");

    println!("See VST3 SDK documentation for full implementation details.");
}
