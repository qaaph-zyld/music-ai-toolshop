#pragma once

#include <juce_gui_basics/juce_gui_basics.h>
#include <juce_audio_utils/juce_audio_utils.h>
#include "../Engine/EngineBridge.h"

namespace OpenDAW {

// FFI function type definitions (outside class)
extern "C" {
    typedef int (*process_audio_fn)(
        void* engine,
        const float* input_l, const float* input_r,
        float* output_l, float* output_r,
        size_t num_samples, double sample_rate
    );
    
    typedef int (*get_meter_fn)(
        void* engine, size_t track_index,
        float* peak, float* rms
    );
}

/**
 * AudioEngineComponent - JUCE audio device integration
 * 
 * Connects JUCE's AudioAppComponent to the Rust audio engine
 * via FFI. Handles audio callback delegation and meter level
 * communication between audio and UI threads.
 */
class AudioEngineComponent : public juce::AudioAppComponent
{
public:
    AudioEngineComponent();
    ~AudioEngineComponent() override;

    // juce::AudioAppComponent interface
    void prepareToPlay(int samplesPerBlockExpected, double sampleRate) override;
    void releaseResources() override;
    void getNextAudioBlock(const juce::AudioSourceChannelInfo& bufferToFill) override;
    void paint(juce::Graphics& g) override;
    void resized() override;

    // Transport controls
    void setEngineHandle(void* engineHandle) { engine = engineHandle; }
    
    // Meter reading (called from UI thread)
    float getMeterPeak(int trackIndex) const;
    float getMeterRms(int trackIndex) const;

private:
    void* engine = nullptr;
    double currentSampleRate = 48000.0;
    int currentBufferSize = 128;
    
    // Scratch buffers for audio processing
    std::vector<float> scratchBufferL;
    std::vector<float> scratchBufferR;
    
    // Load Rust FFI functions dynamically or link directly
    // In production, these would be linked from the Rust library
    int callProcessAudio(
        const float* input_l, const float* input_r,
        float* output_l, float* output_r,
        size_t num_samples
    );
    
    int callGetMeterLevels(size_t track_index, float* peak, float* rms);

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(AudioEngineComponent)
};

} // namespace OpenDAW
