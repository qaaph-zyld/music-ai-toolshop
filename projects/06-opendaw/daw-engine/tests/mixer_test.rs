//! Mixer tests
//! 
//! Tests for the audio mixing system.

use daw_engine::{generators::SineWave, mixer::{Mixer, AudioSource}};

#[test]
fn test_mixer_combines_two_sources() {
    let mut mixer = Mixer::new(2);
    let source1 = SineWave::new(440.0, 0.5);
    let source2 = SineWave::new(880.0, 0.3);
    
    mixer.add_source(Box::new(source1));
    mixer.add_source(Box::new(source2));
    
    let mut output = vec![0.0f32; 128];
    mixer.process(&mut output);
    
    // Output should contain both frequencies (mixed)
    assert!(output.iter().any(|&s| s != 0.0),
        "Mixer should produce combined output");
}

#[test]
fn test_mixer_silence_with_no_sources() {
    let mut mixer = Mixer::new(2);
    let mut output = vec![0.5f32; 128]; // Pre-fill with non-zero
    
    mixer.process(&mut output);
    
    // With no sources, output should be zeroed
    assert!(output.iter().all(|&s| s == 0.0),
        "Mixer with no sources should produce silence");
}

#[test]
fn test_mixer_gain_control() {
    use daw_engine::generators::SineWave;
    use daw_engine::mixer::{Mixer, AudioSource};
    
    let mut mixer = Mixer::new(2);
    let mut source = SineWave::new(440.0, 1.0);
    source.set_gain(0.5); // Reduce gain to 50%
    
    mixer.add_source(Box::new(source));
    
    let mut output = vec![0.0f32; 128];
    mixer.process(&mut output);
    
    // All samples should be <= 0.5 due to gain reduction
    assert!(output.iter().all(|&s| s.abs() <= 0.5),
        "Gain should limit output amplitude");
}
