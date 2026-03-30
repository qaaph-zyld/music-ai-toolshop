#!/usr/bin/env python3
"""Process Kontra K - Kawasaki MP3 file to create instrumental stems"""
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def check_dependencies():
    """Check if required tools are available"""
    ffmpeg_available = False
    demucs_available = False
    cuda_available = False
    
    # Check FFmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              timeout=5,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        ffmpeg_available = result.returncode == 0
    except:
        ffmpeg_available = False
    
    # Check Demucs (as python module)
    try:
        result = subprocess.run(['python', '-m', 'demucs', '-h'], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              timeout=10)
        demucs_available = result.returncode == 0
    except:
        demucs_available = False
    
    # Check CUDA
    try:
        import torch
        cuda_available = torch.cuda.is_available()
    except ImportError:
        cuda_available = False
    
    return {
        'ffmpeg': ffmpeg_available,
        'demucs': demucs_available,
        'cuda': cuda_available
    }

def build_demucs_command(input_file, model='htdemucs_ft', device='auto', two_stems=False, shifts=1, overlap=0.25):
    """Build demucs command using python module"""
    cmd = ['python', '-m', 'demucs']
    
    cmd.extend(['-n', model])
    
    # Device selection
    if device == 'auto':
        try:
            import torch
            if torch.cuda.is_available():
                cmd.extend(['-d', 'cuda'])
            else:
                cmd.extend(['-d', 'cpu'])
        except ImportError:
            cmd.extend(['-d', 'cpu'])
    else:
        cmd.extend(['-d', device])
    
    # Two stems mode (vocals/instrumental)
    if two_stems:
        cmd.extend(['--two-stems', 'vocals'])
    
    # Quality settings
    actual_device = device
    if device == 'auto':
        try:
            import torch
            actual_device = 'cuda' if torch.cuda.is_available() else 'cpu'
        except ImportError:
            actual_device = 'cpu'
    
    if actual_device == 'cpu':
        shifts = 0  # CPU processing uses shifts=0 for speed
    
    cmd.extend(['--shifts', str(shifts)])
    cmd.extend(['--overlap', str(overlap)])
    
    # Add input file
    cmd.append(input_file)
    
    return cmd

def get_output_path(cwd, model, input_file):
    """Get expected output path after demucs run"""
    track_name = Path(input_file).stem
    output_dir = os.path.join(cwd, 'separated', model, track_name)
    return output_dir

def main():
    print("=== Kontra K - Kawasaki Stem Separator ===\n")
    
    # Check dependencies
    status = check_dependencies()
    print("Dependency Status:")
    for key, value in status.items():
        print(f"  {key}: {'✓' if value else '✗'}")
    
    if not status['demucs']:
        print("\nERROR: Demucs not found. Please install: pip install -U demucs")
        return False
    
    if not status['ffmpeg']:
        print("\nERROR: FFmpeg not found. Please install FFmpeg")
        return False
    
    # Input file
    input_file = "Kontra K - Kawasaki (Official Video) (1).mp3"
    
    if not os.path.exists(input_file):
        print(f"\nERROR: Input file not found: {input_file}")
        return False
    
    print(f"\nProcessing: {input_file}")
    print("Model: htdemucs_ft (4-stem separation)")
    print("Device: " + ('cuda' if status['cuda'] else 'cpu'))
    print("Starting stem separation...\n")
    
    # Build command
    cmd = build_demucs_command(
        input_file=input_file,
        model='htdemucs_ft',
        device='auto',
        two_stems=False,  # Get all 4 stems (vocals, drums, bass, other)
        shifts=1,
        overlap=0.25
    )
    
    print("Command:", ' '.join(cmd))
    print()
    
    # Run demucs
    start_time = datetime.now()
    
    try:
        print("Running demucs...")
        result = subprocess.run(
            cmd,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if result.returncode == 0:
            print("\n✓ Stem separation completed successfully!")
            print(f"Processing time: {duration:.1f} seconds")
            
            # Get output path
            output_dir = get_output_path(os.getcwd(), 'htdemucs_ft', input_file)
            print(f"\nOutput directory: {output_dir}")
            
            # List output files
            if os.path.exists(output_dir):
                print("\nGenerated stems:")
                for file in sorted(os.listdir(output_dir)):
                    if file.endswith('.wav'):
                        file_path = os.path.join(output_dir, file)
                        size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        print(f"  {file} ({size_mb:.1f} MB)")
                
                print(f"\n✓ Instrumental stem available at: {output_dir}/other.wav")
                print("✓ Vocals stem available at: {output_dir}/vocals.wav")
                print("✓ Drums stem available at: {output_dir}/drums.wav")
                print("✓ Bass stem available at: {output_dir}/bass.wav")
            else:
                print("Warning: Output directory not found")
            
            return True
            
        else:
            print("\n✗ Stem separation failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"\n✗ Error during processing: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
