"""High-level bridge for MusicGen integration."""
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any, Callable


class MusicGenBridge:
    """Bridge to MusicGen Python subprocess."""
    
    def __init__(self, python_executable: Optional[str] = None):
        self.python = python_executable or "python"
        self.module_path = Path(__file__).parent
        
    def check(self) -> Dict[str, Any]:
        """Check if MusicGen is available."""
        result = subprocess.run(
            [self.python, "-m", "ai_modules.musicgen", "check"],
            capture_output=True,
            text=True,
            cwd=self.module_path.parent.parent
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"available": False, "error": result.stderr}
    
    def generate(
        self,
        prompt: str,
        duration_seconds: int = 10,
        model_size: str = "small",
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """Generate music from prompt."""
        request = {
            "prompt": prompt,
            "duration_seconds": duration_seconds,
            "model_size": model_size,
            "output_path": output_path
        }
        
        result = subprocess.run(
            [self.python, "-m", "ai_modules.musicgen", "generate"],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            cwd=self.module_path.parent.parent
        )
        
        if result.returncode != 0:
            return {"success": False, "error": result.stderr}
        
        return json.loads(result.stdout)
