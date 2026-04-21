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

    // === Real third-party library compilation ===
    // sndfilter: reverb, compressor, biquad filters (0BSD license)
    let sndfilter_src = manifest_dir.join("third_party").join("sndfilter").join("repo").join("src");
    if sndfilter_src.exists() {
        cc::Build::new()
            .file(sndfilter_src.join("snd.c"))
            .file(sndfilter_src.join("biquad.c"))
            .file(sndfilter_src.join("compressor.c"))
            .file(sndfilter_src.join("reverb.c"))
            .file(sndfilter_src.join("mem.c"))
            .include(&sndfilter_src)
            .define("_USE_MATH_DEFINES", None) // MSVC: enable M_PI
            .flag_if_supported("-Wno-unused-parameter")
            .compile("sndfilter");
        println!("cargo:rustc-link-lib=static=sndfilter");
        println!("cargo:rerun-if-changed=third_party/sndfilter/repo/src/reverb.c");
        println!("cargo:rerun-if-changed=third_party/sndfilter/repo/src/compressor.c");
        println!("cargo:rerun-if-changed=third_party/sndfilter/repo/src/biquad.c");
    }

    // Note: When using cdylib, Rust automatically exports #[no_mangle] pub extern "C" functions
    // No manual .def file needed - the #[no_mangle] attribute ensures symbols are exported
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
