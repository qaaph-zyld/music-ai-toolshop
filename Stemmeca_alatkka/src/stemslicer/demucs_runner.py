"""Demucs command builder and runner"""
import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime


class DemucsRunner:
    """Builds and validates Demucs command line arguments"""
    
    MODELS = ['htdemucs_ft', 'htdemucs', 'htdemucs_6s']
    DEVICES = ['auto', 'cpu', 'cuda']
    
    def __init__(self):
        self.ffmpeg_available = False
        self.demucs_available = False
        self.cuda_available = False
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """Check if ffmpeg and demucs are available"""
        self.ffmpeg_available = self._command_exists('ffmpeg', ['-version'])
        
        # Check for demucs in virtual environment Scripts folder first
        venv_demucs = os.path.join(os.path.dirname(sys.executable), 'demucs.exe')
        if os.path.exists(venv_demucs):
            self.demucs_available = self._command_exists(venv_demucs, ['-h'])
        else:
            self.demucs_available = self._command_exists('demucs', ['-h'])
        
        try:
            import torch
            self.cuda_available = torch.cuda.is_available()
        except ImportError:
            self.cuda_available = False
    
    def _command_exists(self, command: str, args: List[str]) -> bool:
        """Check if a command exists and can be executed"""
        try:
            result = subprocess.run(
                [command] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    def get_dependency_status(self) -> Dict[str, bool]:
        """Return status of all dependencies"""
        return {
            'ffmpeg': self.ffmpeg_available,
            'demucs': self.demucs_available,
            'cuda': self.cuda_available
        }
    
    def build_command(
        self,
        input_file: str,
        model: str = 'htdemucs_ft',
        device: str = 'auto',
        two_stems: bool = False,
        shifts: int = 1,
        overlap: float = 0.25,
        segment: Optional[int] = None,
        jobs: int = 1
    ) -> List[str]:
        """Build demucs command line arguments"""
        # Use virtual environment demucs if available
        venv_demucs = os.path.join(os.path.dirname(sys.executable), 'demucs.exe')
        cmd = [venv_demucs] if os.path.exists(venv_demucs) else ['demucs']
        
        cmd.extend(['-n', model])
        
        if device == 'auto':
            if self.cuda_available:
                cmd.extend(['-d', 'cuda'])
            else:
                cmd.extend(['-d', 'cpu'])
        else:
            cmd.extend(['-d', device])
        
        if two_stems:
            cmd.extend(['--two-stems', 'vocals'])
        
        actual_device = device
        if device == 'auto':
            actual_device = 'cuda' if self.cuda_available else 'cpu'
        
        if actual_device == 'cpu':
            shifts = 0
        
        cmd.extend(['--shifts', str(shifts)])
        cmd.extend(['--overlap', str(overlap)])
        
        if segment is not None:
            cmd.extend(['--segment', str(segment)])
        
        cmd.extend(['-j', str(jobs)])
        
        cmd.append(input_file)
        
        return cmd
    
    def get_output_path(self, cwd: str, model: str, input_file: str) -> str:
        """Get expected output path after demucs run"""
        track_name = Path(input_file).stem
        output_dir = os.path.join(cwd, 'separated', model, track_name)
        return output_dir
    
    def create_run_manifest(
        self,
        output_dir: str,
        input_file: str,
        model: str,
        settings: Dict,
        status: str,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> None:
        """Create run.json manifest with processing details"""
        manifest = {
            'input_file': input_file,
            'model': model,
            'settings': settings,
            'status': status,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat() if end_time else None,
            'duration_seconds': (end_time - start_time).total_seconds() if end_time else None
        }
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            manifest_path = os.path.join(output_dir, 'run.json')
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            print(f"Failed to write manifest: {e}")
