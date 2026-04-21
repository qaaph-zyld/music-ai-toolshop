#include "AudioEngineComponent.h"

// FFI declarations at namespace scope
extern "C" {
    int opendaw_process_audio(
        void* engine,
        const float* input_l, const float* input_r,
        float* output_l, float* output_r,
        size_t num_samples, double sample_rate
    );
    
    int opendaw_get_meter_levels(
        void* engine, size_t track_index,
        float* peak, float* rms
    );
}

namespace OpenDAW {

AudioEngineComponent::AudioEngineComponent()
{
    // Set up audio device manager
    setAudioChannels(2, 2); // 2 inputs, 2 outputs
    
    // Pre-allocate scratch buffers (real-time safe)
    scratchBufferL.resize(2048);
    scratchBufferR.resize(2048);
}

AudioEngineComponent::~AudioEngineComponent()
{
    shutdownAudio();
}

void AudioEngineComponent::prepareToPlay(int samplesPerBlockExpected, double sampleRate)
{
    currentSampleRate = sampleRate;
    currentBufferSize = samplesPerBlockExpected;
    
    // Initialize EngineBridge with audio settings
    auto& bridge = EngineBridge::getInstance();
    if (!bridge.isInitialized())
    {
        DBG("AudioEngineComponent: Initializing EngineBridge with SR=" + juce::String(sampleRate) + 
            ", Buffer=" + juce::String(samplesPerBlockExpected));
        bridge.initialize(static_cast<int>(sampleRate), samplesPerBlockExpected);
    }
    
    // Ensure scratch buffers are large enough
    if (scratchBufferL.size() < static_cast<size_t>(samplesPerBlockExpected))
    {
        scratchBufferL.resize(samplesPerBlockExpected);
        scratchBufferR.resize(samplesPerBlockExpected);
    }
    
    DBG("AudioEngineComponent::prepareToPlay - SR: " + juce::String(sampleRate) 
        + ", Block: " + juce::String(samplesPerBlockExpected));
}

void AudioEngineComponent::releaseResources()
{
    DBG("AudioEngineComponent::releaseResources");
}

void AudioEngineComponent::getNextAudioBlock(const juce::AudioSourceChannelInfo& bufferToFill)
{
    if (engine == nullptr)
    {
        // No engine connected - output silence
        bufferToFill.clearActiveBufferRegion();
        return;
    }
    
    const int numSamples = bufferToFill.numSamples;
    // JUCE 7: Use buffer channel counts directly instead of getNumInputChannels/getNumOutputChannels
    const int numInputChannels = (bufferToFill.buffer != nullptr) ? bufferToFill.buffer->getNumChannels() : 0;
    const int numOutputChannels = numInputChannels; // Same as input in our case
    
    // Prepare input buffers
    const float* inputL = nullptr;
    const float* inputR = nullptr;
    
    if (numInputChannels >= 1 && bufferToFill.buffer != nullptr)
    {
        inputL = bufferToFill.buffer->getReadPointer(0, bufferToFill.startSample);
        if (numInputChannels >= 2)
            inputR = bufferToFill.buffer->getReadPointer(1, bufferToFill.startSample);
        else
            inputR = inputL; // Mono to stereo
    }
    else
    {
        // No input - use silence
        if (!scratchBufferL.empty())
        {
            std::fill(scratchBufferL.begin(), scratchBufferL.begin() + numSamples, 0.0f);
            std::fill(scratchBufferR.begin(), scratchBufferR.begin() + numSamples, 0.0f);
            inputL = scratchBufferL.data();
            inputR = scratchBufferR.data();
        }
    }
    
    // Prepare output buffers
    float* outputL = nullptr;
    float* outputR = nullptr;
    
    if (bufferToFill.buffer != nullptr)
    {
        if (numOutputChannels >= 1)
            outputL = bufferToFill.buffer->getWritePointer(0, bufferToFill.startSample);
        if (numOutputChannels >= 2)
            outputR = bufferToFill.buffer->getWritePointer(1, bufferToFill.startSample);
    }
    
    // Ensure we have valid buffers
    if (outputL == nullptr || outputR == nullptr || inputL == nullptr || inputR == nullptr)
    {
        bufferToFill.clearActiveBufferRegion();
        return;
    }
    
    // Call Rust engine via FFI
    int result = callProcessAudio(inputL, inputR, outputL, outputR, 
                                   static_cast<size_t>(numSamples));
    
    if (result != 0)
    {
        // Error in processing - output silence to avoid noise
        DBG("Audio processing error: " + juce::String(result));
        bufferToFill.clearActiveBufferRegion();
    }
}

float AudioEngineComponent::getMeterPeak(int trackIndex) const
{
    if (engine == nullptr || trackIndex < 0 || trackIndex >= 32)
        return 0.0f;
    
    float peak = 0.0f;
    float rms = 0.0f;
    
    // Call Rust FFI to get meter levels
    int result = const_cast<AudioEngineComponent*>(this)->callGetMeterLevels(
        static_cast<size_t>(trackIndex), &peak, &rms);
    
    if (result == 0)
        return peak;
    
    return 0.0f;
}

float AudioEngineComponent::getMeterRms(int trackIndex) const
{
    if (engine == nullptr || trackIndex < 0 || trackIndex >= 32)
        return 0.0f;
    
    float peak = 0.0f;
    float rms = 0.0f;
    
    // Call Rust FFI to get meter levels
    int result = const_cast<AudioEngineComponent*>(this)->callGetMeterLevels(
        static_cast<size_t>(trackIndex), &peak, &rms);
    
    if (result == 0)
        return rms;
    
    return 0.0f;
}

int AudioEngineComponent::callProcessAudio(
    const float* input_l, const float* input_r,
    float* output_l, float* output_r,
    size_t num_samples)
{
    // Direct FFI call to Rust - declared at file scope
    return opendaw_process_audio(engine, input_l, input_r, output_l, output_r, 
                                num_samples, currentSampleRate);
}

int AudioEngineComponent::callGetMeterLevels(size_t track_index, float* peak, float* rms)
{
    // Direct FFI call to Rust - declared at file scope
    return opendaw_get_meter_levels(engine, track_index, peak, rms);
}

void AudioEngineComponent::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colours::black);
    
    // Draw audio engine status
    g.setColour(juce::Colours::green);
    g.setFont(14.0f);
    
    juce::String status = "Audio Engine: ";
    status += (engine != nullptr) ? "Connected" : "Not Connected";
    status += "\nSample Rate: " + juce::String(currentSampleRate);
    status += "\nBuffer Size: " + juce::String(currentBufferSize);
    
    g.drawText(status, getLocalBounds(), juce::Justification::centred);
}

void AudioEngineComponent::resized()
{
    // Layout if needed
}

} // namespace OpenDAW
