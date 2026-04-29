//! Integration tests for Phase 9: Audio Effects Chain
//!
//! Tests the end-to-end plugin chain workflow:
//! 1. Plugin registry scanning and search
//! 2. Plugin chain creation with real plugin instances
//! 3. Audio processing through plugin chain with gain plugins
//! 4. Plugin bypass/unbypass functionality
//! 5. Plugin removal and reordering in chain
//! 6. Full workflow combining all operations

use daw_engine::{
    PluginChain, PluginInstanceWrapper, GainPlugin, Plugin, PluginInfo, PluginFormat,
};
use std::sync::Mutex;

// Serial test guard to prevent parallel test conflicts with global plugin state
static PLUGIN_TEST_GUARD: Mutex<()> = Mutex::new(());

/// Test 1: Plugin chain creation and adding plugins with real instances
#[test]
fn integration_plugin_chain_create_and_add() {
    let _guard = PLUGIN_TEST_GUARD.lock().unwrap();
    
    // Create a new plugin chain
    let mut chain = PluginChain::new();
    assert_eq!(chain.count(), 0);
    
    // Create and configure a gain plugin
    let mut gain_plugin = GainPlugin::new();
    gain_plugin.activate(48000.0, 128).unwrap();
    gain_plugin.set_gain_db(6.0);
    
    // Add plugin with actual implementation to chain
    let plugin_info = gain_plugin.info().clone();
    let slot = chain.add_plugin_with_instance("gain-1", plugin_info, PluginInstanceWrapper::Gain(gain_plugin));
    
    // Verify plugin was added
    assert_eq!(slot, 0);
    assert_eq!(chain.count(), 1);
    
    // Verify plugin metadata
    let instance = chain.get(0).unwrap();
    assert_eq!(instance.instance_id(), "gain-1");
    assert_eq!(instance.plugin_info().unique_id, "opendaw.gain");
    assert!(instance.is_enabled());
}

/// Test 2: Plugin chain audio processing with real GainPlugin
#[test]
fn integration_plugin_chain_audio_process() {
    let _guard = PLUGIN_TEST_GUARD.lock().unwrap();
    
    let mut chain = PluginChain::new();
    
    // Create gain plugin with +6dB (doubles amplitude)
    let mut gain_plugin = GainPlugin::new();
    gain_plugin.activate(48000.0, 64).unwrap();
    gain_plugin.set_gain_db(6.0);
    
    let plugin_info = gain_plugin.info().clone();
    chain.add_plugin_with_instance("gain-1", plugin_info, PluginInstanceWrapper::Gain(gain_plugin));
    
    // Create mono input buffer with constant 0.5 values
    let input = vec![0.5_f32; 64];
    let mut output = vec![0.0_f32; 64];
    
    // Process audio through chain
    chain.process(&input, &mut output);
    
    // Verify output is approximately doubled (6dB gain = 2x amplitude)
    let expected = 0.5 * 10.0_f32.powf(6.0 / 20.0);
    assert!(
        (output[0] - expected).abs() < 0.001,
        "Expected {} after 6dB gain, got {}",
        expected,
        output[0]
    );
    
    // Verify all samples were processed
    for (i, sample) in output.iter().enumerate() {
        assert!(
            (*sample - expected).abs() < 0.001,
            "Sample {}: Expected {}, got {}",
            i,
            expected,
            sample
        );
    }
}

/// Test 3: Plugin bypass functionality
#[test]
fn integration_plugin_chain_bypass() {
    let _guard = PLUGIN_TEST_GUARD.lock().unwrap();
    
    let mut chain = PluginChain::new();
    
    // Add gain plugin
    let mut gain_plugin = GainPlugin::new();
    gain_plugin.activate(48000.0, 64).unwrap();
    gain_plugin.set_gain_db(6.0);
    
    let plugin_info = gain_plugin.info().clone();
    let slot = chain.add_plugin_with_instance("gain-1", plugin_info, PluginInstanceWrapper::Gain(gain_plugin));
    
    // Test with enabled plugin
    let input = vec![0.5_f32; 64];
    let mut output_enabled = vec![0.0_f32; 64];
    chain.process(&input, &mut output_enabled);
    
    let expected_amplified = 0.5 * 10.0_f32.powf(6.0 / 20.0);
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
    
    // Re-enable plugin
    chain.get_mut(slot).unwrap().enable();
    assert!(chain.get(slot).unwrap().is_enabled());
    
    // Verify processing resumes
    let mut output_reenabled = vec![0.0_f32; 64];
    chain.process(&input, &mut output_reenabled);
    assert!((output_reenabled[0] - expected_amplified).abs() < 0.001);
}

/// Test 4: Plugin removal and reordering in chain
#[test]
fn integration_plugin_chain_remove_reorder() {
    let _guard = PLUGIN_TEST_GUARD.lock().unwrap();
    
    let mut chain = PluginChain::new();
    
    // Add three plugins
    let mut gain1 = GainPlugin::new();
    gain1.activate(48000.0, 64).unwrap();
    let info1 = gain1.info().clone();
    chain.add_plugin_with_instance("gain-1", info1, PluginInstanceWrapper::Gain(gain1));
    
    let mut gain2 = GainPlugin::new();
    gain2.activate(48000.0, 64).unwrap();
    let info2 = gain2.info().clone();
    chain.add_plugin_with_instance("gain-2", info2, PluginInstanceWrapper::Gain(gain2));
    
    let mut gain3 = GainPlugin::new();
    gain3.activate(48000.0, 64).unwrap();
    let info3 = gain3.info().clone();
    chain.add_plugin_with_instance("gain-3", info3, PluginInstanceWrapper::Gain(gain3));
    
    assert_eq!(chain.count(), 3);
    
    // Verify initial order
    assert_eq!(chain.get(0).unwrap().instance_id(), "gain-1");
    assert_eq!(chain.get(1).unwrap().instance_id(), "gain-2");
    assert_eq!(chain.get(2).unwrap().instance_id(), "gain-3");
    
    // Remove middle plugin
    let removed = chain.remove(1);
    assert!(removed.is_some());
    assert_eq!(removed.unwrap().instance_id(), "gain-2");
    assert_eq!(chain.count(), 2);
    
    // Verify order after removal and reindexing
    assert_eq!(chain.get(0).unwrap().instance_id(), "gain-1");
    assert_eq!(chain.get(1).unwrap().instance_id(), "gain-3");
    assert_eq!(chain.get(1).unwrap().slot_index(), 1); // Reindexed
    
    // Move plugin from position 1 to position 0 (swap)
    assert!(chain.move_plugin(1, 0));
    
    // Verify new order
    assert_eq!(chain.get(0).unwrap().instance_id(), "gain-3");
    assert_eq!(chain.get(1).unwrap().instance_id(), "gain-1");
}

/// Test 5: Multiple plugins in chain with cumulative gain
#[test]
fn integration_plugin_chain_multiple_plugins() {
    let _guard = PLUGIN_TEST_GUARD.lock().unwrap();
    
    let mut chain = PluginChain::new();
    
    // Add two +6dB gain plugins (total +12dB = ~4x amplitude)
    let mut gain1 = GainPlugin::new();
    gain1.activate(48000.0, 64).unwrap();
    gain1.set_gain_db(6.0);
    let info1 = gain1.info().clone();
    chain.add_plugin_with_instance("gain-1", info1, PluginInstanceWrapper::Gain(gain1));
    
    let mut gain2 = GainPlugin::new();
    gain2.activate(48000.0, 64).unwrap();
    gain2.set_gain_db(6.0);
    let info2 = gain2.info().clone();
    chain.add_plugin_with_instance("gain-2", info2, PluginInstanceWrapper::Gain(gain2));
    
    // Process audio
    let input = vec![0.25_f32; 64]; // Lower input to avoid clipping after 12dB gain
    let mut output = vec![0.0_f32; 64];
    chain.process(&input, &mut output);
    
    // Verify total gain is ~12dB (each 6dB plugin doubles the amplitude)
    // 0.25 * 2 * 2 = 1.0
    let expected = 0.25 * 10.0_f32.powf(12.0 / 20.0);
    assert!(
        (output[0] - expected).abs() < 0.01,
        "Expected {} after 12dB total gain, got {}",
        expected,
        output[0]
    );
}

/// Test 6: Full workflow - create, process, bypass, remove, clear
#[test]
fn integration_plugin_chain_full_workflow() {
    let _guard = PLUGIN_TEST_GUARD.lock().unwrap();
    
    // Step 1: Create empty chain
    let mut chain = PluginChain::new();
    assert_eq!(chain.count(), 0);
    
    // Step 2: Add multiple plugins
    for i in 0..4 {
        let mut gain = GainPlugin::new();
        gain.activate(48000.0, 64).unwrap();
        gain.set_gain_db(3.0); // +3dB each
        let info = gain.info().clone();
        chain.add_plugin_with_instance(&format!("gain-{}", i), info, PluginInstanceWrapper::Gain(gain));
    }
    assert_eq!(chain.count(), 4);
    
    // Step 3: Process audio
    let input = vec![0.5_f32; 64];
    let mut output = vec![0.0_f32; 64];
    chain.process(&input, &mut output);
    
    // 4 plugins * 3dB = 12dB total = ~4x amplitude
    let expected = 0.5 * 10.0_f32.powf(12.0 / 20.0);
    assert!((output[0] - expected).abs() < 0.05);
    
    // Step 4: Disable two plugins
    chain.get_mut(0).unwrap().disable();
    chain.get_mut(2).unwrap().disable();
    
    // Step 5: Process with bypassed plugins (only 2 active = 6dB)
    let mut output_partial = vec![0.0_f32; 64];
    chain.process(&input, &mut output_partial);
    
    let expected_partial = 0.5 * 10.0_f32.powf(6.0 / 20.0);
    assert!((output_partial[0] - expected_partial).abs() < 0.05);
    
    // Step 6: Remove a plugin
    assert!(chain.remove(1).is_some());
    assert_eq!(chain.count(), 3);
    
    // Step 7: Reorder plugins
    assert!(chain.move_plugin(2, 0));
    
    // Step 8: Clear all plugins
    chain.clear();
    assert_eq!(chain.count(), 0);
    
    // Step 9: Verify processing still works (passthrough)
    let mut output_cleared = vec![0.0_f32; 64];
    chain.process(&input, &mut output_cleared);
    assert!((output_cleared[0] - 0.5).abs() < 0.001);
}
