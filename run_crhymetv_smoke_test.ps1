#requires -Version 5.1
# CrhymeTV — Smoke-test the reverse-engineering batch runner on 3 tracks.

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$ResultsDir = "d:\Projects\Music-AI-Toolshop\results\crhymetv_re"
$InputDir = "d:\Projects\Tools\yt_extractor\downloads\CrhymeTV"
$VenvPython = "d:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { (Get-Command python).Source }

New-Item -ItemType Directory -Path $ResultsDir -Force | Out-Null
$LogFile = Join-Path $ResultsDir "smoke_test.log"

function Write-Log($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $msg
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue
}

Write-Log "Smoke test: 3 tracks"
Write-Log "Using Python: $Python"

$BatchArgs = @(
    "d:\Projects\Music-AI-Toolshop\run_reverse_engineering_batch.py",
    "--input-dir", $InputDir,
    "--output-dir", $ResultsDir,
    "--limit", 3,
    "--chunk-size", 3,
    "--no-resume"
)
$batchProc = Start-Process -FilePath $Python -ArgumentList $BatchArgs -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput $LogFile -RedirectStandardError (Join-Path $ResultsDir "smoke_test.err")
$exitCode = $batchProc.ExitCode
Write-Log "Smoke test finished with exit code $exitCode."
exit $exitCode
