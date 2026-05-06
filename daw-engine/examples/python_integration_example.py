"""
OpenDAW Python Integration Example

Demonstrates how to use the OpenDAW Rust audio engine from Python
via the FFI interface.
"""

import ctypes
import numpy as np
from pathlib import Path

# Load the Rust engine DLL
# Build with: cargo build --release
dll_path = Path(__file__).parent.parent / "target" / "release" / "daw_engine.dll"
engine = ctypes.CDLL(str(dll_path))

# Define FFI function signatures
engine.daw_engine_init.argtypes = [ctypes.c_int, ctypes.c_int]
engine.daw_engine_init.restype = ctypes.c_void_p

engine.daw_engine_shutdown.argtypes = [ctypes.c_void_p]
engine.daw_engine_shutdown.restype = None

engine.daw_transport_play.argtypes = [ctypes.c_void_p]
engine.daw_transport_play.restype = None

engine.daw_transport_stop.argtypes = [ctypes.c_void_p]
engine.daw_transport_stop.restype = None

engine.daw_transport_set_tempo.argtypes = [ctypes.c_void_p, ctypes.c_float]
engine.daw_transport_set_tempo.restype = None

engine.daw_mixer_set_volume.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_float]
engine.daw_mixer_set_volume.restype = None

engine.daw_session_launch_scene.argtypes = [ctypes.c_void_p, ctypes.c_int]
engine.daw_session_launch_scene.restype = None

def create_engine(sample_rate=48000, buffer_size=512):
    """Initialize the OpenDAW audio engine."""
    engine_ptr = engine.daw_engine_init(sample_rate, buffer_size)
    if not engine_ptr:
        raise RuntimeError("Failed to initialize engine")
    return engine_ptr

def shutdown_engine(engine_ptr):
    """Shutdown the audio engine."""
    engine.daw_engine_shutdown(engine_ptr)

def set_tempo(engine_ptr, bpm):
    """Set the transport tempo."""
    engine.daw_transport_set_tempo(engine_ptr, bpm)

def play(engine_ptr):
    """Start playback."""
    engine.daw_transport_play(engine_ptr)

def stop(engine_ptr):
    """Stop playback."""
    engine.daw_transport_stop(engine_ptr)

def set_track_volume(engine_ptr, track, volume):
    """Set track volume (0.0 to 1.0)."""
    engine.daw_mixer_set_volume(engine_ptr, track, volume)

def launch_scene(engine_ptr, scene):
    """Launch all clips in a scene."""
    engine.daw_session_launch_scene(engine_ptr, scene)

# Example usage
if __name__ == "__main__":
    print("OpenDAW Python Integration Example")
    print("=" * 40)
    
    # Initialize engine
    print("Initializing engine...")
    engine_ptr = create_engine(sample_rate=48000, buffer_size=512)
    print("✓ Engine initialized")
    
    try:
        # Set tempo
        print("Setting tempo to 120 BPM...")
        set_tempo(engine_ptr, 120.0)
        print("✓ Tempo set")
        
        # Set track volume
        print("Setting track 0 volume to 0.8...")
        set_track_volume(engine_ptr, 0, 0.8)
        print("✓ Volume set")
        
        # Launch scene
        print("Launching scene 0...")
        launch_scene(engine_ptr, 0)
        print("✓ Scene launched")
        
        # Start playback
        print("Starting playback...")
        play(engine_ptr)
        print("✓ Playing")
        
        # In a real application, you would process audio here
        # For this example, we just demonstrate the API
        import time
        time.sleep(1)
        
        # Stop playback
        print("Stopping playback...")
        stop(engine_ptr)
        print("✓ Stopped")
        
    finally:
        # Cleanup
        print("Shutting down engine...")
        shutdown_engine(engine_ptr)
        print("✓ Engine shutdown")
    
    print("\nExample completed successfully!")
