"""
Example usage of the WAV Reverse Engineering Tool.

This script demonstrates how to use the audio analysis and reverse engineering
capabilities of the wav-reverse-engineer package.
"""

import os
import sys
import json
from pathlib import Path

# Add the parent directory to the path so we can import the package
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from audio_analyzer.audio_processor import AudioProcessor
from audio_analyzer.feature_extractor import FeatureExtractor
from audio_analyzer.visualizer import AudioVisualizer
from audio_analyzer.utils import save_analysis_results, ensure_dir

def analyze_audio_file(input_file: str, output_dir: str = 'output') -> dict:
    """
    Analyze an audio file and save the results.
    
    Args:
        input_file: Path to the input audio file
        output_dir: Directory to save the analysis results
        
    Returns:
        Dictionary containing the analysis results
    """
    print(f"Analyzing audio file: {input_file}")
    
    # Create output directories
    ensure_dir(output_dir)
    audio_basename = os.path.splitext(os.path.basename(input_file))[0]
    
    # Initialize processors
    audio_processor = AudioProcessor()
    feature_extractor = FeatureExtractor()
    visualizer = AudioVisualizer()
    
    # Load and process audio
    print("Loading audio...")
    audio, sample_rate = audio_processor.load_audio(input_file)
    
    # Get audio information
    audio_info = audio_processor.get_audio_info(audio, sample_rate)
    print("\nAudio Information:")
    for key, value in audio_info.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    
    # Extract features
    print("\nExtracting features...")
    features = feature_extractor.extract_features(audio, sample_rate)
    
    # Detect chords
    print("Detecting chords...")
    chords = feature_extractor.detect_chords(audio, sample_rate)
    features['chords'] = [{
        'root': chord.root.name,
        'quality': chord.quality,
        'confidence': chord.confidence,
        'start_time': chord.start_time,
        'duration': chord.duration
    } for chord in chords]
    
    # Detect notes
    print("Detecting notes...")
    notes = feature_extractor.detect_notes(audio, sample_rate)
    features['notes'] = notes
    
    # Save analysis results
    json_path = os.path.join(output_dir, f"{audio_basename}_analysis.json")
    save_analysis_results(features, json_path)
    print(f"\nAnalysis results saved to: {json_path}")
    
    # Generate visualizations
    print("\nGenerating visualizations...")
    vis_dir = os.path.join(output_dir, 'visualizations')
    visualizer.generate_analysis_report(
        audio, sample_rate, 
        output_dir=vis_dir,
        prefix=audio_basename
    )
    print(f"Visualizations saved to: {vis_dir}")
    
    return features

def main():
    """Main function to demonstrate the tool's capabilities."""
    # Example usage
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # Use a test file if no input is provided
        test_dir = os.path.join(os.path.dirname(__file__), '..', 'test_audio')
        input_file = os.path.join(test_dir, 'example.wav')
        
        # Create test directory if it doesn't exist
        os.makedirs(test_dir, exist_ok=True)
        
        # Generate a test audio file if it doesn't exist
        if not os.path.exists(input_file):
            print(f"No input file provided and test file not found at {input_file}")
            print("Please provide a WAV file as an argument.")
            print("Example: python example_usage.py path/to/your/audio.wav")
            return
    
    # Analyze the audio file
    output_dir = os.path.join('output', 'example_analysis')
    features = analyze_audio_file(input_file, output_dir)
    
    # Print a summary of the analysis
    print("\nAnalysis Summary:")
    print(f"- Duration: {features.get('duration', 0):.2f} seconds")
    print(f"- Estimated Tempo: {features.get('tempo', 0):.2f} BPM")
    print(f"- Estimated Key: {features.get('key', 'N/A')} {features.get('mode', '').capitalize()}")
    print(f"- Detected Chords: {len(features.get('chords', []))}")
    print(f"- Detected Notes: {len(features.get('notes', []))}")
    
    # Print the first few chords and notes as examples
    if 'chords' in features and features['chords']:
        print("\nFirst few chords:")
        for chord in features['chords'][:5]:
            print(f"  - {chord['root']} {chord['quality']} "
                  f"(start: {chord['start_time']:.2f}s, "
                  f"duration: {chord['duration']:.2f}s, "
                  f"confidence: {chord['confidence']:.2f})")
    
    if 'notes' in features and features['notes']:
        print("\nFirst few notes:")
        for note in features['notes'][:5]:
            print(f"  - {note['pitch']} (start: {note['start_time']:.2f}s, "
                  f"duration: {note['duration']:.2f}s, "
                  f"confidence: {note['confidence']:.2f})")
    
    print("\nAnalysis complete! Check the output directory for detailed results and visualizations.")

if __name__ == "__main__":
    main()
