// Build script for daw-engine
// Compiles FFI wrappers

use std::env;
use std::path::PathBuf;

fn main() {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let miniaudio_dir = manifest_dir.join("third_party").join("miniaudio");
    let faust_dir = manifest_dir.join("third_party").join("faust");
    let cycfiq_dir = manifest_dir.join("third_party").join("cycfiq");

    let maximilian_dir = manifest_dir.join("third_party").join("maximilian");
    let sndfile_dir = manifest_dir.join("third_party").join("sndfile");

    let opus_dir = manifest_dir.join("third_party").join("opus");
    let portaudio_dir = manifest_dir.join("third_party").join("portaudio");
    let rtaudio_dir = manifest_dir.join("third_party").join("rtaudio");
    let lv2_dir = manifest_dir.join("third_party").join("lv2");
    let dpf_dir = manifest_dir.join("third_party").join("dpf");
    let jack_dir = manifest_dir.join("third_party").join("jack");
    let surge_dir = manifest_dir.join("third_party").join("surge");
    let vital_dir = manifest_dir.join("third_party").join("vital");
    let dexed_dir = manifest_dir.join("third_party").join("dexed");
    let obxd_dir = manifest_dir.join("third_party").join("obxd");
    let helm_dir = manifest_dir.join("third_party").join("helm");
    let tunefish_dir = manifest_dir.join("third_party").join("tunefish");
    let odin2_dir = manifest_dir.join("third_party").join("odin2");
    let ladspa_dir = manifest_dir.join("third_party").join("ladspa");
    let caps_dir = manifest_dir.join("third_party").join("caps");
    let tap_dir = manifest_dir.join("third_party").join("tap");
    let invada_dir = manifest_dir.join("third_party").join("invada");
    let calf_dir = manifest_dir.join("third_party").join("calf");
    let guitarix_dir = manifest_dir.join("third_party").join("guitarix");
    let rakarrack_dir = manifest_dir.join("third_party").join("rakarrack");
    let tal_dir = manifest_dir.join("third_party").join("tal_noisemaker");
    let ddsp_dir = manifest_dir.join("third_party").join("ddsp");
    let magenta_dir = manifest_dir.join("third_party").join("magenta");
    let mmm_dir = manifest_dir.join("third_party").join("mmm");
    let musicbert_dir = manifest_dir.join("third_party").join("musicbert");
    let clap_dir = manifest_dir.join("third_party").join("clap");
    let flac_dir = manifest_dir.join("third_party").join("flac");
    let lame_dir = manifest_dir.join("third_party").join("lame");
    let musepack_dir = manifest_dir.join("third_party").join("musepack");
    let imgui_dir = manifest_dir.join("third_party").join("imgui");
    let react_juce_dir = manifest_dir.join("third_party").join("react_juce");
    let opengl_dir = manifest_dir.join("third_party").join("opengl");
    let webrtc_dir = manifest_dir.join("third_party").join("webrtc");
    let lofi_ml_dir = manifest_dir.join("third_party").join("lofi_ml");
    let libremidi_dir = manifest_dir.join("third_party").join("libremidi");
    let midifile_dir = manifest_dir.join("third_party").join("midifile");
    let rubber_band_dir = manifest_dir.join("third_party").join("rubber_band");
    let aubio_dir = manifest_dir.join("third_party").join("aubio");
    let autotalent_dir = manifest_dir.join("third_party").join("autotalent");
    let rnnoise_dir = manifest_dir.join("third_party").join("rnnoise");
    let deep_filter_net_dir = manifest_dir.join("third_party").join("deep_filter_net");
    let webaudio_pianoroll_dir = manifest_dir.join("third_party").join("webaudio_pianoroll");
    let wavesurfer_dir = manifest_dir.join("third_party").join("wavesurfer");
    let peaks_dir = manifest_dir.join("third_party").join("peaks");
    let audiowaveform_dir = manifest_dir.join("third_party").join("audiowaveform");
    let vexflow_dir = manifest_dir.join("third_party").join("vexflow");
    let version_control_dir = manifest_dir.join("third_party").join("version_control");

    // Compile FFI wrappers
    let mut build = cc::Build::new();
    build.file(miniaudio_dir.join("miniaudio_ffi.c"))
         .include(&miniaudio_dir)
         .flag_if_supported("-Wno-unused-parameter")
         .flag_if_supported("-Wno-unused-variable")
         .file(faust_dir.join("faust_ffi.c"))
         .file(cycfiq_dir.join("cycfiq_ffi.c"))
         .file(maximilian_dir.join("maximilian_ffi.c"))
         .file(sndfile_dir.join("sndfile_ffi.c"))
         .file(opus_dir.join("opus_ffi.c"))
         .file(portaudio_dir.join("portaudio_ffi.c"))
         .file(rtaudio_dir.join("rtaudio_ffi.c"))
         .file(lv2_dir.join("lv2_ffi.c"))
         .file(dpf_dir.join("dpf_ffi.c"))
         .file(jack_dir.join("jack_ffi.c"))
         .file(surge_dir.join("surge_ffi.c"))
         .file(vital_dir.join("vital_ffi.c"))
         .file(dexed_dir.join("dexed_ffi.c"))
         .file(obxd_dir.join("obxd_ffi.c"))
         .file(helm_dir.join("helm_ffi.c"))
         .file(tunefish_dir.join("tunefish_ffi.c"))
         .file(odin2_dir.join("odin2_ffi.c"))
         .file(ladspa_dir.join("ladspa_ffi.c"))
         .file(caps_dir.join("caps_ffi.c"))
         .file(tap_dir.join("tap_ffi.c"))
         .file(invada_dir.join("invada_ffi.c"))
         .file(calf_dir.join("calf_ffi.c"))
         .file(guitarix_dir.join("guitarix_ffi.c"))
         .file(rakarrack_dir.join("rakarrack_ffi.c"))
         .file(tal_dir.join("tal_ffi.c"))
         .file(ddsp_dir.join("ddsp_ffi.c"))
         .file(magenta_dir.join("magenta_ffi.c"))
         .file(mmm_dir.join("mmm_ffi.c"))
         .file(musicbert_dir.join("musicbert_ffi.c"))
         .file(clap_dir.join("clap_ffi.c"))
         .file(lofi_ml_dir.join("lofi_ml_ffi.c"))
         .file(flac_dir.join("flac_ffi.c"))
         .file(lame_dir.join("lame_ffi.c"))
         .file(musepack_dir.join("musepack_ffi.c"))
         .file(imgui_dir.join("imgui_ffi.c"))
         .file(react_juce_dir.join("react_juce_ffi.c"))
         .file(opengl_dir.join("opengl_ffi.c"))
         .file(webrtc_dir.join("webrtc_ffi.c"))
         .file(libremidi_dir.join("libremidi_ffi.c"))
         .file(midifile_dir.join("midifile_ffi.c"))
         .file(rubber_band_dir.join("rubber_band_ffi.c"))
         .file(aubio_dir.join("aubio_ffi.c"))
         .file(autotalent_dir.join("autotalent_ffi.c"))
         .file(rnnoise_dir.join("rnnoise_ffi.c"))
         .file(deep_filter_net_dir.join("deep_filter_net_ffi.c"))
         .file(webaudio_pianoroll_dir.join("pianoroll_ffi.c"))
         .file(wavesurfer_dir.join("wavesurfer_ffi.c"))
         .file(peaks_dir.join("peaks_ffi.c"))
         .file(audiowaveform_dir.join("audiowaveform_ffi.c"))
         .file(vexflow_dir.join("vexflow_ffi.c"))
         .file(version_control_dir.join("vc_ffi.c"));

    build.compile("daw_engine_ffi");

    // Tell cargo to link the static library
    println!("cargo:rustc-link-lib=static=daw_engine_ffi");

    // Windows: Create a .def file to export FFI symbols from the DLL
    #[cfg(target_os = "windows")]
    {
        let def_content = r#"LIBRARY daw_engine
EXPORTS
    daw_audio_device_count
    daw_audio_device_manager_create
    daw_audio_device_manager_free
    daw_audio_device_name
    daw_audio_is_streaming
    daw_delta_compare
    daw_delta_create
    daw_delta_free
    daw_dexed_create
    daw_dexed_free
    daw_dexed_free_string
    daw_dexed_get_version
    daw_dexed_is_available
    daw_dexed_note_off
    daw_dexed_note_on
    daw_dexed_process
    daw_dexed_set_algorithm
    daw_engine_init
    daw_engine_process_audio
    daw_engine_process_commands
    daw_engine_shutdown
    daw_export_cancel
    daw_export_configure
    daw_export_create
    daw_export_destroy
    daw_export_get_progress
    daw_export_get_result
    daw_export_is_complete
    daw_export_start
    daw_helm_create
    daw_helm_free
    daw_helm_free_string
    daw_helm_get_version
    daw_helm_is_available
    daw_helm_note_off
    daw_helm_note_on
    daw_helm_process
    daw_helm_set_arpeggiator
    daw_meter_get_master_levels
    daw_meter_get_master_peak
    daw_meter_get_master_rms
    daw_meter_get_track_count
    daw_meter_get_track_levels
    daw_meter_get_track_peak
    daw_meter_get_track_rms
    daw_meter_init
    daw_midi_device_count
    daw_midi_device_info
    daw_midi_free_notes
    daw_midi_is_recording
    daw_midi_start_recording
    daw_midi_stop_recording
    daw_mixer_set_mute
    daw_mixer_set_pan
    daw_mixer_set_solo
    daw_mixer_set_volume
    daw_mmm_clear_pattern
    daw_mmm_create
    daw_mmm_destroy
    daw_mmm_generate
    daw_mmm_get_duration_beats
    daw_mmm_get_note_count
    daw_mmm_get_notes
    daw_mmm_get_track_name
    daw_mmm_is_available
    daw_mmm_load_style
    daw_obxd_create
    daw_obxd_free
    daw_obxd_free_string
    daw_obxd_get_version
    daw_obxd_is_available
    daw_obxd_note_off
    daw_obxd_note_on
    daw_obxd_process
    daw_obxd_set_filter_params
    daw_odin2_create
    daw_odin2_free
    daw_odin2_free_string
    daw_odin2_get_version
    daw_odin2_is_available
    daw_odin2_note_off
    daw_odin2_note_on
    daw_odin2_process
    daw_project_last_error
    daw_project_load
    daw_project_save
    daw_project_state_clear_modified
    daw_project_state_get_path
    daw_project_state_init
    daw_project_state_is_modified
    daw_project_state_mark_modified
    daw_project_state_new
    daw_project_state_set_path
    daw_register_clip_callback
    daw_register_meter_callback
    daw_register_position_callback
    daw_register_transport_callback
    daw_session_launch_clip
    daw_session_launch_scene
    daw_session_load_clip
    daw_session_stop_all
    daw_session_stop_clip
    daw_spectral_analyze
    daw_spectral_create
    daw_spectral_free
    daw_stem_cancel
    daw_stem_get_path
    daw_stem_get_progress
    daw_stem_is_available
    daw_stem_is_complete
    daw_stem_separate
    daw_stem_separator_create
    daw_stem_separator_free
    daw_track_set_armed
    daw_transport_get_position
    daw_transport_get_tempo
    daw_transport_is_playing
    daw_transport_play
    daw_transport_record
    daw_transport_set_position
    daw_transport_set_tempo
    daw_transport_stop
    daw_tunefish_create
    daw_tunefish_free
    daw_tunefish_free_string
    daw_tunefish_get_version
    daw_tunefish_is_available
    daw_tunefish_note_off
    daw_tunefish_note_on
    daw_tunefish_process
    opendaw_clip_get_state
    opendaw_clip_play
    opendaw_clip_player_get_playing_clip
    opendaw_clip_player_get_position
    opendaw_clip_player_get_state
    opendaw_clip_player_init
    opendaw_clip_player_is_playing
    opendaw_clip_player_queue_clip
    opendaw_clip_player_shutdown
    opendaw_clip_player_stop_all
    opendaw_clip_player_stop_clip
    opendaw_clip_player_trigger_clip
    opendaw_clip_stop
    opendaw_engine_init
    opendaw_engine_shutdown
    opendaw_get_callback_count
    opendaw_get_current_beat
    opendaw_get_last_triggered_clip
    opendaw_get_meter_levels
    opendaw_get_tempo
    opendaw_midi_close_device
    opendaw_midi_device_count
    opendaw_midi_get_device_name
    opendaw_midi_inject_test_message
    opendaw_midi_open_device
    opendaw_midi_read_message
    opendaw_mixer_get_meter
    opendaw_mixer_get_track_count
    opendaw_process_audio
    opendaw_reset_callback_count
    opendaw_scene_launch
    opendaw_session_get_current_scene
    opendaw_set_tempo
    opendaw_stop_all_clips
    opendaw_transport_get_bpm
    opendaw_transport_get_position
    opendaw_transport_is_playing
    opendaw_transport_is_recording
    opendaw_transport_play
    opendaw_transport_record
    opendaw_transport_set_bpm
    opendaw_transport_set_position
    opendaw_transport_stop
    opendaw_transport_sync_beats_until_next
    opendaw_transport_sync_cancel_clip
    opendaw_transport_sync_cancel_track
    opendaw_transport_sync_clear_all
    opendaw_transport_sync_get_tempo
    opendaw_transport_sync_init
    opendaw_transport_sync_is_track_scheduled
    opendaw_transport_sync_next_scheduled_beat
    opendaw_transport_sync_pending_count
    opendaw_transport_sync_process
    opendaw_transport_sync_schedule_clip
    opendaw_transport_sync_schedule_clip_quantized
    opendaw_transport_sync_set_tempo
    opendaw_transport_sync_shutdown
"#;

        let out_dir = env::var("OUT_DIR").unwrap();
        let def_path = std::path::PathBuf::from(&out_dir).join("daw_engine.def");
        std::fs::write(&def_path, def_content).expect("Failed to write .def file");
        println!("cargo:rustc-cdylib-link-arg=/DEF:{}" , def_path.display());
    }
    println!("cargo:rerun-if-changed=third_party/miniaudio/miniaudio_ffi.c");
    println!("cargo:rerun-if-changed=third_party/faust/faust_ffi.c");
    println!("cargo:rerun-if-changed=third_party/cycfiq/cycfiq_ffi.c");
    println!("cargo:rerun-if-changed=third_party/maximilian/maximilian_ffi.c");
    println!("cargo:rerun-if-changed=third_party/sndfile/sndfile_ffi.c");
    println!("cargo:rerun-if-changed=third_party/opus/opus_ffi.c");
    println!("cargo:rerun-if-changed=third_party/portaudio/portaudio_ffi.c");
    println!("cargo:rerun-if-changed=third_party/rtaudio/rtaudio_ffi.c");
    println!("cargo:rerun-if-changed=third_party/lv2/lv2_ffi.c");
    println!("cargo:rerun-if-changed=third_party/ddsp/ddsp_ffi.c");
    println!("cargo:rerun-if-changed=third_party/magenta/magenta_ffi.c");
    println!("cargo:rerun-if-changed=third_party/mmm/mmm_ffi.c");
    println!("cargo:rerun-if-changed=third_party/musicbert/musicbert_ffi.c");
    println!("cargo:rerun-if-changed=third_party/clap/clap_ffi.c");
    println!("cargo:rerun-if-changed=third_party/lofi_ml/lofi_ml_ffi.c");
    println!("cargo:rerun-if-changed=third_party/jack/jack_ffi.c");
    println!("cargo:rerun-if-changed=third_party/surge/surge_ffi.c");
    println!("cargo:rerun-if-changed=third_party/vital/vital_ffi.c");
    println!("cargo:rerun-if-changed=third_party/dexed/dexed_ffi.c");
    println!("cargo:rerun-if-changed=third_party/obxd/obxd_ffi.c");
    println!("cargo:rerun-if-changed=third_party/helm/helm_ffi.c");
    println!("cargo:rerun-if-changed=third_party/tunefish/tunefish_ffi.c");
    println!("cargo:rerun-if-changed=third_party/odin2/odin2_ffi.c");
    println!("cargo:rerun-if-changed=third_party/ladspa/ladspa_ffi.c");
    println!("cargo:rerun-if-changed=third_party/caps/caps_ffi.c");
    println!("cargo:rerun-if-changed=third_party/tap/tap_ffi.c");
    println!("cargo:rerun-if-changed=third_party/invada/invada_ffi.c");
    println!("cargo:rerun-if-changed=third_party/calf/calf_ffi.c");
    println!("cargo:rerun-if-changed=third_party/guitarix/guitarix_ffi.c");
    println!("cargo:rerun-if-changed=third_party/rakarrack/rakarrack_ffi.c");
    println!("cargo:rerun-if-changed=third_party/tal_noisemaker/tal_ffi.c");
    println!("cargo:rerun-if-changed=third_party/flac/flac_ffi.c");
    println!("cargo:rerun-if-changed=third_party/lame/lame_ffi.c");
    println!("cargo:rerun-if-changed=third_party/musepack/musepack_ffi.c");
    println!("cargo:rerun-if-changed=third_party/imgui/imgui_ffi.c");
    println!("cargo:rerun-if-changed=third_party/react_juce/react_juce_ffi.c");
    println!("cargo:rerun-if-changed=third_party/opengl/opengl_ffi.c");
    println!("cargo:rerun-if-changed=third_party/webrtc/webrtc_ffi.c");
    println!("cargo:rerun-if-changed=third_party/libremidi/libremidi_ffi.c");
    println!("cargo:rerun-if-changed=third_party/midifile/midifile_ffi.c");
    println!("cargo:rerun-if-changed=third_party/rubber_band/rubber_band_ffi.c");
    println!("cargo:rerun-if-changed=third_party/aubio/aubio_ffi.c");
    println!("cargo:rerun-if-changed=third_party/autotalent/autotalent_ffi.c");
    println!("cargo:rerun-if-changed=third_party/rnnoise/rnnoise_ffi.c");
    println!("cargo:rerun-if-changed=third_party/deep_filter_net/deep_filter_net_ffi.c");
    println!("cargo:rerun-if-changed=third_party/webaudio_pianoroll/pianoroll_ffi.c");
    println!("cargo:rerun-if-changed=third_party/wavesurfer/wavesurfer_ffi.c");
    println!("cargo:rerun-if-changed=third_party/peaks/peaks_ffi.c");
    println!("cargo:rerun-if-changed=third_party/audiowaveform/audiowaveform_ffi.c");
    println!("cargo:rerun-if-changed=third_party/vexflow/vexflow_ffi.c");
    println!("cargo:rerun-if-changed=third_party/version_control/vc_ffi.c");
}
