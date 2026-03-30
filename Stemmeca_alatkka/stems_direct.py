#!/usr/bin/env python3
"""Direct stem separation using demucs with manual file saving"""
import os
import sys
import torch
import soundfile as sf
import numpy as np
import librosa
from pathlib import Path
from datetime import datetime

# Import demucs
try:
    from demucs import pretrained
    from demucs.apply import apply_model
    from demucs.audio import convert_audio
except ImportError:
    print("ERROR: demucs not installed")
    sys.exit(1)

def separate_and_save_stems(input_file, output_dir=None):
    """Separate audio into stems and save manually"""
    
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "separated_stems")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading model...")
    # Load the pretrained model
    model = pretrained.get_model('htdemucs_ft')
    model.eval()
    
    if torch.cuda.is_available():
        print("Using CUDA")
        model.cuda()
    else:
        print("Using CPU")
    
    print(f"Loading audio file: {input_file}")
    # Load audio file using librosa
    waveform, sample_rate = librosa.load(input_file, sr=None, mono=False)
    
    # Convert to torch tensor
    if waveform.ndim == 1:
        waveform = waveform.reshape(1, -1)
    waveform = torch.from_numpy(waveform).float()
    
    # Convert to model's expected format
    waveform = convert_audio(waveform, sample_rate, model.samplerate, model.audio_channels)
    
    # Add batch dimension if needed
    if waveform.dim() == 2:
        waveform = waveform.unsqueeze(0)
    
    print("Separating stems...")
    # Apply model
    with torch.no_grad():
        sources = apply_model(model, waveform)
    
    # Remove batch dimension
    sources = sources.squeeze(0)
    
    # Convert to numpy and save
    stem_names = ['drums', 'bass', 'other', 'vocals']
    
    print(f"Saving stems to: {output_dir}")
    for i, stem_name in enumerate(stem_names):
        stem_audio = sources[i].cpu().numpy()
        
        # Convert to mono if stereo (take first channel)
        if stem_audio.shape[0] > 1:
            stem_audio = stem_audio[0]
        else:
            stem_audio = stem_audio[0]
        
        # Save using soundfile
        output_file = os.path.join(output_dir, f"{stem_name}.wav")
        sf.write(output_file, stem_audio, model.samplerate)
        
        size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"  ✓ {stem_name}.wav ({size_mb:.1f} MB)")
    
    print(f"\n✓ Stem separation completed!")
    print(f"✓ Instrumental stem: {output_dir}/other.wav")
    print(f"✓ Vocals stem: {output_dir}/vocals.wav")
    print(f"✓ Drums stem: {output_dir}/drums.wav")
    print(f"✓ Bass stem: {output_dir}/bass.wav")
    
    return output_dir

def main():
    print("=== Direct Stem Separator ===\n")
    
    # Input file
    input_file = "Kontra K - Kawasaki (Official Video) (1).mp3"
    
    if not os.path.exists(input_file):
        print(f"ERROR: Input file not found: {input_file}")
        return False
    
    try:
        output_dir = separate_and_save_stems(input_file)
        print(f"\nSuccess! Stems saved to: {output_dir}")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
