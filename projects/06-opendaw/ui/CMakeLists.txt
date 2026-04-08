cmake_minimum_required(VERSION 3.15)
project(OpenDAW VERSION 0.1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Add JUCE from git submodule or FetchContent
include(FetchContent)
FetchContent_Declare(
    JUCE
    GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
    GIT_TAG 7.0.9
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(JUCE)

# Create the main application
juce_add_gui_app(OpenDAW
    PRODUCT_NAME "OpenDAW"
    COMPANY_NAME "OpenDAW Project"
    BUNDLE_ID com.opendaw.app
    ICON_BIG ""
    MICROPHONE_PERMISSION_ENABLED TRUE
    NEEDS_STORE_KIT TRUE
)

# Source files
target_sources(OpenDAW PRIVATE
    src/Main.cpp
    src/MainComponent.cpp
    src/Audio/AudioEngineComponent.cpp
    src/Project/ProjectManager.cpp
    src/SessionView/ClipSlotComponent.cpp
    src/SessionView/TrackHeaderComponent.cpp
    src/SessionView/SceneLaunchComponent.cpp
    src/SessionView/SessionGridComponent.cpp
    src/Transport/TransportBar.cpp
    src/Mixer/ChannelStrip.cpp
    src/Mixer/LevelMeterComponent.cpp
    src/Mixer/MixerPanel.cpp
    src/Engine/EngineBridge.cpp
    src/SunoBrowser/SunoBrowserComponent.cpp
    src/Export/ExportDialog.cpp
    src/Export/ExportFFI.cpp
    src/Recording/RecordingPanel.cpp
    src/StemExtraction/StemExtractionDialog.cpp
    src/PatternGen/MmmFFI.cpp
    src/PatternGen/PatternGeneratorDialog.cpp
)

# Include directories
target_include_directories(OpenDAW PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${CMAKE_CURRENT_SOURCE_DIR}/../daw-engine/include
)

# Compile definitions
target_compile_definitions(OpenDAW PRIVATE
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_VST3_HOSTING=0
    JUCE_APPLICATION_NAME_STRING="OpenDAW"
    JUCE_APPLICATION_VERSION_STRING="0.1.0"
)

# Link JUCE modules
target_link_libraries(OpenDAW PRIVATE
    juce::juce_core
    juce::juce_data_structures
    juce::juce_events
    juce::juce_graphics
    juce::juce_gui_basics
    juce::juce_gui_extra
    juce::juce_audio_basics
    juce::juce_audio_devices
    juce::juce_audio_formats
    juce::juce_audio_processors
    juce::juce_audio_utils
)

# Link Rust DAW Engine library
# The Rust library is built separately with: cargo build --release
# On Windows, cdylib produces daw_engine.dll.lib (import library for the DLL)
set(DAW_ENGINE_LIB "${CMAKE_CURRENT_SOURCE_DIR}/../daw-engine/target/release/daw_engine.dll.lib")
if(EXISTS ${DAW_ENGINE_LIB})
    target_link_libraries(OpenDAW PRIVATE ${DAW_ENGINE_LIB})
    message(STATUS "Linked Rust DAW Engine: ${DAW_ENGINE_LIB}")
else()
    message(WARNING "Rust DAW Engine library not found. Build with: cd ../daw-engine && cargo build --release")
endif()

# Windows system libraries (required for PropVariantToInt64, VariantToDouble, etc.)
if(WIN32)
    target_link_libraries(OpenDAW PRIVATE
        Propsys.lib
        Ole32.lib
        OleAut32.lib
    )
    message(STATUS "Linked Windows system libraries for FFI compatibility")
endif()

# Recommended JUCE build flags
target_link_libraries(OpenDAW PRIVATE
    juce::juce_recommended_config_flags
    juce::juce_recommended_lto_flags
    juce::juce_recommended_warning_flags
)
