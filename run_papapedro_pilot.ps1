#requires -Version 5.1
# PapaPedro beats — Pilot reverse-engineering pipeline
# Runs Phase 0 env check, then delegates to run_papapedro_pilot.py
# Outputs saved to: d:\Projects\Music-AI-Toolshop\results\papapedro_re\

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
$ResultsDir = "d:\Projects\Music-AI-Toolshop\results\papapedro_re"
$VenvPython = "d:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { (Get-Command python).Source }
New-Item -ItemType Directory -Path $ResultsDir -Force | Out-Null
$LogFile = Join-Path $ResultsDir "pilot_env.log"
function Write-Log($msg) { $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $msg; Write-Host $line; Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue }
Write-Log "Using Python: $Python"

Write-Log "Running Phase 0 environment check..."
$EnvCheck = @"
import sys, json, importlib
from pathlib import Path
def check(name):
    try:
        m = importlib.import_module(name)
        ver = getattr(m, '__version__', 'unknown')
        return {'ok': True, 'version': str(ver)}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
checks = {'python': sys.version, 'librosa': check('librosa'), 'numpy': check('numpy'), 'scipy': check('scipy'), 'soundfile': check('soundfile'), 'praat_parselmouth': check('parselmouth'), 'audio_separator': check('audio_separator'), 'wav_reverse_engineer': check('wav_reverse_engineer'), 'torch': check('torch'), 'tensorflow': check('tensorflow'), 'crepe': check('crepe'), 'demucs': check('demucs'), 'yt_dlp': check('yt_dlp'), 'pydub': check('pydub'), 'pyloudnorm': check('pyloudnorm'), 'matplotlib': check('matplotlib'), 'yaml': check('yaml')}
try:
    import torch
    checks['torch']['cuda_available'] = torch.cuda.is_available()
    checks['torch']['cuda_devices'] = torch.cuda.device_count() if torch.cuda.is_available() else 0
except Exception: pass
out = Path(r'$ResultsDir') / 'env_check.json'
out.write_text(json.dumps(checks, indent=2, default=str))
print('ENV_CHECK_OK')
"@
$EnvCheck | & $Python - | Tee-Object -FilePath $LogFile -Append
if ($LASTEXITCODE -ne 0) { Write-Log "Phase 0 failed."; exit 1 }
Write-Log "Phase 0 complete. Saved env_check.json"

Write-Log "Running Phase 1 pilot analysis..."
& $Python "d:\Projects\Music-AI-Toolshop\run_papapedro_pilot.py" | Tee-Object -FilePath $LogFile -Append
$exitCode = $LASTEXITCODE
Write-Log "Pilot script finished with exit code $exitCode."
Write-Log "All done. Check these files next:"
Write-Log "  - $ResultsDir\env_check.json"
Write-Log "  - $ResultsDir\pilot_status.json"
Write-Log "  - $ResultsDir\per_beat\*\recipe.md"
Write-Log "  - $LogFile"
exit $exitCode
