#requires -Version 5.1
# CrhymeTV — Reverse-engineering batch runner
# Runs Phase 0 environment check, then delegates to run_reverse_engineering_batch.py
# Outputs saved to: d:\Projects\Music-AI-Toolshop\results\crhymetv_re\

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$ResultsDir = "d:\Projects\Music-AI-Toolshop\results\crhymetv_re"
$InputDir = "d:\Projects\Tools\yt_extractor\downloads\CrhymeTV"
$VenvPython = "d:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { (Get-Command python).Source }

New-Item -ItemType Directory -Path $ResultsDir -Force | Out-Null
$LogFile = Join-Path $ResultsDir "batch.log"
$EnvLogFile = Join-Path $ResultsDir "env_check.log"

function Write-Log($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $msg
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue
}

Write-Log "Using Python: $Python"
Write-Log "Input: $InputDir"
Write-Log "Output: $ResultsDir"

Write-Log "Running Phase 0 environment check..."
$EnvScript = Join-Path $ResultsDir "env_check_script.py"
$EnvScriptContent = @'
import sys, json, importlib
from pathlib import Path
def check(name):
    try:
        m = importlib.import_module(name)
        ver = getattr(m, '__version__', 'unknown')
        return {'ok': True, 'version': str(ver)}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
checks = {
    'python': sys.version,
    'librosa': check('librosa'),
    'numpy': check('numpy'),
    'scipy': check('scipy'),
    'soundfile': check('soundfile'),
    'praat_parselmouth': check('parselmouth'),
    'audio_separator': check('audio_separator'),
    'wav_reverse_engineer': check('wav_reverse_engineer'),
    'torch': check('torch'),
    'tensorflow': check('tensorflow'),
    'crepe': check('crepe'),
    'demucs': check('demucs'),
    'yt_dlp': check('yt_dlp'),
    'pydub': check('pydub'),
    'pyloudnorm': check('pyloudnorm'),
    'matplotlib': check('matplotlib'),
    'yaml': check('yaml'),
}
try:
    import torch
    checks['torch']['cuda_available'] = torch.cuda.is_available()
    checks['torch']['cuda_devices'] = torch.cuda.device_count() if torch.cuda.is_available() else 0
except Exception: pass
out = Path(r'd:\Projects\Music-AI-Toolshop\results\crhymetv_re') / 'env_check.json'
out.write_text(json.dumps(checks, indent=2, default=str))
print('ENV_CHECK_OK')
'@
$EnvScriptContent | Set-Content -Path $EnvScript -Encoding utf8
$envProc = Start-Process -FilePath $Python -ArgumentList $EnvScript -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput $EnvLogFile -RedirectStandardError (Join-Path $ResultsDir "env_check.err")
if ($envProc.ExitCode -ne 0) { Write-Log "Phase 0 failed (exit code $($envProc.ExitCode))."; exit 1 }
Write-Log "Phase 0 complete. Saved env_check.json"

Write-Log "Running Phase 1 batch analysis..."
$BatchArgs = @(
    "d:\Projects\Music-AI-Toolshop\run_reverse_engineering_batch.py",
    "--input-dir", $InputDir,
    "--output-dir", $ResultsDir,
    "--chunk-size", 30
)
$batchProc = Start-Process -FilePath $Python -ArgumentList $BatchArgs -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput $LogFile -RedirectStandardError (Join-Path $ResultsDir "batch.err")
$exitCode = $batchProc.ExitCode
Write-Log "Batch script finished with exit code $exitCode."

if ($exitCode -eq 0) {
    Write-Log "Regenerating catalogue from batch_status.json..."
    $CatalogueArgs = @(
        "d:\Projects\Music-AI-Toolshop\generate_crhymetv_catalogue.py",
        "--status-file", (Join-Path $ResultsDir "batch_status.json"),
        "--output-dir", $ResultsDir
    )
    $catProc = Start-Process -FilePath $Python -ArgumentList $CatalogueArgs -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput (Join-Path $ResultsDir "catalogue.log") `
        -RedirectStandardError (Join-Path $ResultsDir "catalogue.err")
    Write-Log "Catalogue generation finished with exit code $($catProc.ExitCode)."
}

Write-Log "All done. Check these files next:"
Write-Log "  - $ResultsDir\env_check.json"
Write-Log "  - $ResultsDir\batch_status.json"
Write-Log "  - $ResultsDir\per_track\*\recipe.md"
Write-Log "  - $ResultsDir\catalogue.csv"
Write-Log "  - $ResultsDir\catalogue.md"
Write-Log "  - $LogFile"
exit $exitCode
