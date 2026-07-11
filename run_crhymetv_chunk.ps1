#requires -Version 5.1
# CrhymeTV — Run a single chunk of the reverse-engineering batch.
# Useful for parallelizing across terminals or resuming a specific chunk.
# Example:  .\run_crhymetv_chunk.ps1 -Chunk 1
#           .\run_crhymetv_chunk.ps1 -Chunk 2
#           .\run_crhymetv_chunk.ps1 -Chunk 1 -ChunkSize 30

param(
    [Parameter(Mandatory = $true)]
    [int]$Chunk,

    [int]$ChunkSize = 30,

    [switch]$NoResume
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

$ResultsDir = "d:\Projects\Music-AI-Toolshop\results\crhymetv_re"
$InputDir = "d:\Projects\Tools\yt_extractor\downloads\CrhymeTV"
$VenvPython = "d:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { (Get-Command python).Source }

$Offset = ($Chunk - 1) * $ChunkSize
$LogFile = Join-Path $ResultsDir "batch_chunk_$Chunk.log"

function Write-Log($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $msg
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue
}

Write-Log "Chunk $Chunk (offset=$Offset, limit=$ChunkSize)"
Write-Log "Using Python: $Python"

$BatchArgs = @(
    "d:\Projects\Music-AI-Toolshop\run_reverse_engineering_batch.py",
    "--input-dir", $InputDir,
    "--output-dir", $ResultsDir,
    "--offset", $Offset,
    "--limit", $ChunkSize,
    "--chunk-size", $ChunkSize
)
if ($NoResume) { $BatchArgs += "--no-resume" }

$batchProc = Start-Process -FilePath $Python -ArgumentList $BatchArgs -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput $LogFile -RedirectStandardError (Join-Path $ResultsDir "batch_chunk_$Chunk.err")
$exitCode = $batchProc.ExitCode
Write-Log "Chunk $Chunk finished with exit code $exitCode."
exit $exitCode
