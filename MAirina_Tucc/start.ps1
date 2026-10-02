# MAirina Tucc: start the local engine (127.0.0.1:8000) and the writing screen (127.0.0.1:5174),
# warm the corpus caches, then open the browser. Close the two minimized windows to stop.
# Usage: D:\Projects\Music-AI-Toolshop\MAirina_Tucc\start.ps1
$root = "D:\Projects\Music-AI-Toolshop\MAirina_Tucc"
$engine = "http://127.0.0.1:8000"
$screen = "http://127.0.0.1:5174"

function Test-Up($url) {
    try { Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 5 | Out-Null; return $true } catch { return $false }
}

if (Test-Up "$engine/api/stats") {
    Write-Host "Engine already running on $engine"
} else {
    Write-Host "Starting engine (mt serve) ..."
    Start-Process powershell -WindowStyle Minimized -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'MAirina engine'; & '$root\mt.ps1' serve"
}

if (Test-Up $screen) {
    Write-Host "Writing screen already running on $screen"
} else {
    Write-Host "Starting writing screen (vite) ..."
    Start-Process powershell -WindowStyle Minimized -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'MAirina screen'; Set-Location '$root\rimer-ui'; & '.\node_modules\.bin\vite.cmd' --port 5174 --strictPort --host 127.0.0.1"
}

$deadline = (Get-Date).AddSeconds(90)
while (-not (Test-Up "$engine/api/stats")) {
    if ((Get-Date) -gt $deadline) { Write-Host "Engine did not answer within 90 s - check the 'MAirina engine' window."; exit 1 }
    Start-Sleep -Seconds 2
}
Write-Host "Engine up. Warming the corpus atlas (first time only, ~20 s) ..."
try { Invoke-WebRequest "$engine/api/me?lane=drill" -UseBasicParsing -TimeoutSec 120 | Out-Null } catch { Write-Host "Warm-up skipped: $($_.Exception.Message)" }

$deadline = (Get-Date).AddSeconds(60)
while (-not (Test-Up $screen)) {
    if ((Get-Date) -gt $deadline) { Write-Host "Writing screen did not answer within 60 s - check the 'MAirina screen' window."; exit 1 }
    Start-Sleep -Seconds 2
}
Start-Process $screen
Write-Host "MAirina Tucc is open at $screen"
