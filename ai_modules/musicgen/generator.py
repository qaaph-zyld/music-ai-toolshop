"""MusicGen text-to-music generator using AudioCraft."""
import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import torch
    import numpy as np
    from audiocraft.models import MusicGen
    from audiocraft.data.audio import audio_write
    AUDIOCRAFT_AVAILABLE = True
except ImportError:
    AUDIOCRAFT_AVAILABLE = False


class MusicGenGenerator:
    """Wrapper for AudioCraft MusicGen model."""
    
    MODEL_SIZES = ['small', 'medium', 'large', 'melody']
    
    def __init__(self, model_size: str = 'small', device: Optional[str] = None):
        if not AUDIOCRAFT_AVAILABLE:
            raise ImportError("audiocraft not installed. Run: pip install audiocraft")
        
        self.model_size = model_size if model_size in self.MODEL_SIZES else 'small'
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load pretrained model."""
        print(f"Loading MusicGen {self.model_size} model...", file=sys.stderr)
        self.model = MusicGen.get_pretrained(self.model_size)
        self.model.to(self.device)
        print("Model loaded.", file=sys.stderr)
    
    def generate(
        self, 
        prompt: str, 
        duration: int = 10,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate music from text prompt."""
        if not self.model:
            return {"error": "Model not loaded"}
        
        print(f"Generating: '{prompt}' ({duration}s)", file=sys.stderr)
        
        # Set generation parameters
        self.model.set_generation_params(
            duration=duration,
            top_k=250,
            top_p=0.0,
            temperature=1.0,
        )
        
        # Generate
        descriptions = [prompt]
        wav = self.model.generate(descriptions)[0]  # First (only) sample
        
        # Save to file
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            audio_write(
                output_path.with_suffix(''),
                wav.cpu(),
                self.model.sample_rate,
                format='wav',
                strategy='loudness',
                loudness_compressor=True
            )
            actual_path = str(output_path.with_suffix('.wav'))
        else:
            actual_path = None
        
        return {
            "success": True,
            "prompt": prompt,
            "duration": duration,
            "sample_rate": self.model.sample_rate,
            "output_path": actual_path,
            "model_used": self.model_size
        }


def main():
    """CLI entry point for subprocess communication."""
    if len(sys.argv) < 2:
        print("Usage: python -m ai_modules.musicgen <command> [args]", file=sys.stderr)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "check":
        # Check dependencies
        result = {
            "available": AUDIOCRAFT_AVAILABLE,
            "torch_version": torch.__version__ if AUDIOCRAFT_AVAILABLE else None,
            "cuda_available": torch.cuda.is_available() if AUDIOCRAFT_AVAILABLE else False,
            "models_available": MusicGenGenerator.MODEL_SIZES if AUDIOCRAFT_AVAILABLE else []
        }
        print(json.dumps(result))
        
    elif command == "generate":
        # Read JSON request from stdin
        request = json.load(sys.stdin)
        
        generator = MusicGenGenerator(
            model_size=request.get('model_size', 'small')
        )
        
        result = generator.generate(
            prompt=request['prompt'],
            duration=request.get('duration_seconds', 10),
            output_path=request.get('output_path')
        )
        
        print(json.dumps(result))
    
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
