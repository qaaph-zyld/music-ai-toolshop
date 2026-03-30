#!/usr/bin/env python3
"""Process Kontra K - Kawasaki MP3 file to create instrumental stems"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stemslicer.demucs_runner import DemucsRunner
from datetime import datetime

def main():
    # Initialize Demucs runner
    runner = DemucsRunner()
    
    # Check dependencies
    status = runner.get_dependency_status()
    print("Dependency Status:")
    for key, value in status.items():
        print(f"  {key}: {'✓' if value else '✗'}")
    
    if not status['demucs']:
        print("ERROR: Demucs not found. Please install: pip install -U demucs")
        return False
    
    if not status['ffmpeg']:
        print("ERROR: FFmpeg not found. Please install FFmpeg")
        return False
    
    # Input file
    input_file = "Kontra K - Kawasaki (Official Video) (1).mp3"
    
    if not os.path.exists(input_file):
        print(f"ERROR: Input file not found: {input_file}")
        return False
    
    print(f"\nProcessing: {input_file}")
    print("Model: htdemucs_ft (4-stem separation)")
    print("Device: " + ('cuda' if status['cuda'] else 'cpu'))
    print("Starting stem separation...\n")
    
    # Build command
    cmd = runner.build_command(
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
        import subprocess
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
            print("✓ Stem separation completed successfully!")
            print(f"Processing time: {duration:.1f} seconds")
            
            # Get output path
            output_dir = runner.get_output_path(os.getcwd(), 'htdemucs_ft', input_file)
            print(f"\nOutput directory: {output_dir}")
            
            # List output files
            if os.path.exists(output_dir):
                print("\nGenerated stems:")
                for file in sorted(os.listdir(output_dir)):
                    if file.endswith('.wav'):
                        file_path = os.path.join(output_dir, file)
                        size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        print(f"  {file} ({size_mb:.1f} MB)")
            
            # Create run manifest
            runner.create_run_manifest(
                output_dir=output_dir,
                input_file=input_file,
                model='htdemucs_ft',
                settings={'shifts': 1, 'overlap': 0.25, 'device': 'auto'},
                status='completed',
                start_time=start_time,
                end_time=end_time
            )
            
            print(f"\n✓ Instrumental stem available at: {output_dir}/other.wav")
            return True
            
        else:
            print("✗ Stem separation failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"✗ Error during processing: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
