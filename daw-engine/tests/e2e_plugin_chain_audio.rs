//! E2E Plugin Chain Audio Processing Integration Test
//!
//! Tests end-to-end plugin chain with real audio processing.
//! Session B: E2E Integration Testing

use daw_engine::{PluginChain, PluginInstanceWrapper};
use daw_engine::plugin::{GainPlugin, Plugin, PluginInfo, PluginFormat};
use std::sync::Mutex;

// Serial test guard to prevent parallel test conflicts with global plugin state
static PLUGIN_TEST_GUARD: Mutex<()> = Mutex::new(());

/// Test: Create plugin chain, process audio, verify output is modified
#[test]
fn e2e_plugin_chain_process_audio_modified() {
    let _guard = PLUGIN_TEST_GUARD.lock().unwrap();
    
    // Create a new plugin chain
    let mut chain = PluginChain::new();
    assert_eq!(chain.count(), 0);
    
    // Create and configure a gain plugin with +6dB (doubles amplitude)
    let mut gain_plugin = GainPlugin::new();
    gain_plugin.activate(48000.0, 64).unwrap();
    gain_plugin.set_gain_db(6.0);
    
    // Add plugin to chain
    let plugin_info = gain_plugin.info().clone();
    let slot = chain.add_plugin_with_instance("gain-1", plugin_info, PluginInstanceWrapper::Gain(gain_plugin));
    assert_eq!(slot, 0);
    assert_eq!(chain.count(), 1);
    
    // Create mono input buffer with constant 0.5 values
    let input = vec![0.5_f32; 64];
    let mut output = vec![0.0_f32; 64];
    
    // Process audio through chain
    chain.process(&input, &mut output);
    
    // Verify output is approximately doubled (6dB gain = 2x amplitude)
    // 0.5 * 10^(6/20) = 0.5 * 1.995 = ~0.997
    let expected = 0.5 * 10.0_f32.powf(6.0 / 20.0);
    assert!(
        (output[0] - expected).abs() < 0.001,
        "Expected ~{} after 6dB gain, got {}",
        expected,
        output[0]
    );
    
    // Verify all samples were processed
    for (i, sample) in output.iter().enumerate() {
        assert!(
            (*sample - expected).abs() < 0.001,
            "Sample {}: Expected ~{}, got {}",
            i,
            expected,
            sample
        );
    }
    
    // Verify output is different from input (plugin actually modified the audio)
    let input_max = input.iter().fold(0.0_f32, |a, b| a.max(*b));
    let output_max = output.iter().fold(0.0_f32, |a, b| a.max(*b));
    assert!(
        (output_max - input_max).abs() > 0.1,
        "Output should be significantly different from input after gain"
    );
}

/// Test: Bypass plugin, verify output unchanged
#[test]
fn e2e_plugin_chain_bypass_unchanged() {
    let _guard = PLUGIN_TEST_GUARD.lock().unwrap();
    
    let mut chain = PluginChain::new();
    
    // Add gain plugin with significant gain
    let mut gain_plugin = GainPlugin::new();
    gain_plugin.activate(48000.0, 64).unwrap();
    gain_plugin.set_gain_db(12.0); // +12dB
    
    let plugin_info = gain_plugin.info().clone();
    let slot = chain.add_plugin_with_instance("gain-1", plugin_info, PluginInstanceWrapper::Gain(gain_plugin));
    
    // Test with enabled plugin
    let input = vec![0.5_f32; 64];
    let mut output_enabled = vec![0.0_f32; 64];
    chain.process(&input, &mut output_enabled);
    
    // Output should be amplified
    let expected_amplified = 0.5 * 10.0_f32.powf(12.0 / 20.0);
    assert!((output_enabled[0] - expected_amplified).abs() < 0.001);
    
    // Disable (bypass) the plugin
    chain.get_mut(slot).unwrap().disable();
    assert!(!chain.get(slot).unwrap().is_enabled());
    
    // Test with disabled plugin - should pass through unchanged
    let mut output_bypassed = vec![0.0_f32; 64];
    chain.process(&input, &mut output_bypassed);
    
    // Output should equal input (bypass)
    assert!(
        (output_bypassed[0] - 0.5).abs() < 0.001,
        "Bypass failed: Expected 0.5, got {}",
        output_bypassed[0]
    );
    
    // Verify all samples are unchanged
    for (i, (in_sample, out_sample)) in input.iter().zip(output_bypassed.iter()).enumerate() {
        assert!(
            (*out_sample - *in_sample).abs() < 0.001,
            "Sample {} should pass through unchanged: expected {}, got {}",
            i,
            in_sample,
            out_sample
        );
    }
    
    // Re-enable plugin
    chain.get_mut(slot).unwrap().enable();
    assert!(chain.get(slot).unwrap().is_enabled());
    
    // Verify processing resumes
    let mut output_reenabled = vec![0.0_f32; 64];
    chain.process(&input, &mut output_reenabled);
    assert!((output_reenabled[0] - expected_amplified).abs() < 0.001);
}

/// Test: Reorder plugins, verify different output
#[test]
fn e2e_plugin_chain_reorder_different_output() {
    let _guard = PLUGIN_TEST_GUARD.lock().unwrap();
    
    let mut chain = PluginChain::new();
    
    // Add two gain plugins: +3dB then +6dB
    let mut gain1 = GainPlugin::new();
    gain1.activate(48000.0, 64).unwrap();
    gain1.set_gain_db(3.0);
    let info1 = gain1.info().clone();
    chain.add_plugin_with_instance("gain-3db", info1, PluginInstanceWrapper::Gain(gain1));
    
    let mut gain2 = GainPlugin::new();
    gain2.activate(48000.0, 64).unwrap();
    gain2.set_gain_db(6.0);
    let info2 = gain2.info().clone();
    chain.add_plugin_with_instance("gain-6db", info2, PluginInstanceWrapper::Gain(gain2));
    
    assert_eq!(chain.count(), 2);
    
    // Process with original order (+3dB then +6dB = +9dB total)
    let input = vec![0.25_f32; 64];
    let mut output_original = vec![0.0_f32; 64];
    chain.process(&input, &mut output_original);
    
    // Expected: +9dB total = ~2.82x amplitude
    // 0.25 * 10^(9/20) = 0.25 * 2.818 = ~0.704
    let expected_original = 0.25 * 10.0_f32.powf(9.0 / 20.0);
    assert!(
        (output_original[0] - expected_original).abs() < 0.01,
        "Original order: Expected ~{}, got {}",
        expected_original,
        output_original[0]
    );
    
    // Reorder: swap plugins (+6dB then +3dB)
    // Since gain is commutative, output should be identical
    // But this tests the move_plugin functionality
    assert!(chain.move_plugin(1, 0), "move_plugin should succeed");
    
    // Verify new order
    assert_eq!(chain.get(0).unwrap().instance_id(), "gain-6db");
    assert_eq!(chain.get(1).unwrap().instance_id(), "gain-3db");
    
    // Process with reordered plugins
    let mut output_reordered = vec![0.0_f32; 64];
    chain.process(&input, &mut output_reordered);
    
    // For pure gain, order shouldn't matter (commutative)
    // But we verify both outputs are approximately equal
    assert!(
        (output_reordered[0] - output_original[0]).abs() < 0.001,
        "Reordered gain plugins should produce same output (commutative), original: {}, reordered: {}",
        output_original[0],
        output_reordered[0]
    );
}

/// Test: Multiple plugins in chain with cumulative effect
#[test]
fn e2e_plugin_chain_multiple_plugins_cumulative() {
    let _guard = PLUGIN_TEST_GUARD.lock().unwrap();
    
    let mut chain = PluginChain::new();
    
    // Add three gain plugins with different gains
    let gains = vec![3.0, 6.0, 9.0]; // +3dB, +6dB, +9dB
    for (i, gain_db) in gains.iter().enumerate() {
        let mut gain_plugin = GainPlugin::new();
        gain_plugin.activate(48000.0, 64).unwrap();
        gain_plugin.set_gain_db(*gain_db);
        let info = gain_plugin.info().clone();
        chain.add_plugin_with_instance(
            &format!("gain-{}", i),
            info,
            PluginInstanceWrapper::Gain(gain_plugin)
        );
    }
    
    assert_eq!(chain.count(), 3);
    
    // Process audio
    let input = vec![0.25_f32; 64];
    let mut output = vec![0.0_f32; 64];
    chain.process(&input, &mut output);
    
    // Total gain: 3 + 6 + 9 = +18dB
    // 0.25 * 10^(18/20) = 0.25 * 7.943 = ~1.986
    let expected = 0.25 * 10.0_f32.powf(18.0 / 20.0);
    assert!(
        (output[0] - expected).abs() < 0.01,
        "Expected ~{} after +18dB total gain, got {}",
        expected,
        output[0]
    );
    
    // Disable middle plugin (+6dB)
    chain.get_mut(1).unwrap().disable();
    
    // Process again
    let mut output_partial = vec![0.0_f32; 64];
    chain.process(&input, &mut output_partial);
    
    // Remaining gain: 3 + 9 = +12dB
    let expected_partial = 0.25 * 10.0_f32.powf(12.0 / 20.0);
    assert!(
        (output_partial[0] - expected_partial).abs() < 0.01,
        "Expected ~{} after +12dB partial gain, got {}",
        expected_partial,
        output_partial[0]
    );
}

/// Test: Full workflow - create chain, process, verify, remove, verify passthrough
#[test]
fn e2e_plugin_chain_full_workflow() {
    let _guard = PLUGIN_TEST_GUARD.lock().unwrap();
    
    // Step 1: Create empty chain
    let mut chain = PluginChain::new();
    assert_eq!(chain.count(), 0);
    
    // Step 2: Add multiple plugins
    for i in 0..3 {
        let mut gain = GainPlugin::new();
        gain.activate(48000.0, 64).unwrap();
        gain.set_gain_db(3.0); // +3dB each
        let info = gain.info().clone();
        chain.add_plugin_with_instance(&format!("gain-{}", i), info, PluginInstanceWrapper::Gain(gain));
    }
    assert_eq!(chain.count(), 3);
    
    // Step 3: Process audio (should have +9dB total)
    let input = vec![0.5_f32; 64];
    let mut output = vec![0.0_f32; 64];
    chain.process(&input, &mut output);
    
    let expected = 0.5 * 10.0_f32.powf(9.0 / 20.0);
    assert!((output[0] - expected).abs() < 0.05);
    
    // Step 4: Remove a plugin
    assert!(chain.remove(1).is_some());
    assert_eq!(chain.count(), 2);
    
    // Step 5: Reorder remaining plugins
    assert!(chain.move_plugin(1, 0));
    
    // Step 6: Process with modified chain (+6dB total now)
    let mut output_modified = vec![0.0_f32; 64];
    chain.process(&input, &mut output_modified);
    
    let expected_modified = 0.5 * 10.0_f32.powf(6.0 / 20.0);
    assert!((output_modified[0] - expected_modified).abs() < 0.05);
    
    // Step 7: Clear all plugins
    chain.clear();
    assert_eq!(chain.count(), 0);
    
    // Step 8: Verify processing still works (passthrough)
    let mut output_cleared = vec![0.0_f32; 64];
    chain.process(&input, &mut output_cleared);
    assert!((output_cleared[0] - 0.5).abs() < 0.001);
}
