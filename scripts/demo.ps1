# One-command demo: pihole_up -> generate 4 datasets -> export -> run Streamlit
# You need: Docker Desktop running, Python + pip install -r requirements.txt (see README).
# No pre-existing Pi-hole or logs required — this script creates everything.
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")

Write-Host "1. Starting Pi-hole (first run may take 1-3 min to pull image/init)..."
& (Join-Path $ScriptDir "pihole_up.ps1")
# Wait for Pi-hole container healthcheck to report "healthy".
# This is more reliable than host DNS probing in environments where localhost
# networking or upstream resolvers can be transient.
$maxWait = 180
$step = 5
$waited = 0
while ($waited -lt $maxWait) {
    Start-Sleep -Seconds $step
    $waited += $step
    try {
        $health = docker inspect pihole --format "{{.State.Health.Status}}" 2>$null
        if ($health -eq "healthy") {
            Write-Host "   Pi-hole is healthy after ${waited}s."
            break
        }
    } catch {}
    Write-Host "   Waiting for Pi-hole healthcheck... ${waited}s"
}
if ($waited -ge $maxWait) {
    Write-Error "Pi-hole did not reach healthy state within ${maxWait}s. Is Docker running? Try: .\scripts\pihole_up.ps1 then check docker logs pihole and http://localhost:8081"
    exit 1
}

Write-Host "2. Generating baseline and exporting..."
& (Join-Path $ScriptDir "flush_pihole_log.ps1")
& (Join-Path $ScriptDir "generate_traffic.ps1") -Profile baseline
Start-Sleep -Seconds 2
& (Join-Path $ScriptDir "export_dataset.ps1") -Name baseline

Write-Host "3. Generating burst and exporting..."
& (Join-Path $ScriptDir "flush_pihole_log.ps1")
& (Join-Path $ScriptDir "generate_traffic.ps1") -Profile burst
Start-Sleep -Seconds 2
& (Join-Path $ScriptDir "export_dataset.ps1") -Name burst

Write-Host "4. Generating nxdomain and exporting..."
& (Join-Path $ScriptDir "flush_pihole_log.ps1")
& (Join-Path $ScriptDir "generate_traffic.ps1") -Profile nxdomain
Start-Sleep -Seconds 2
& (Join-Path $ScriptDir "export_dataset.ps1") -Name nxdomain

Write-Host "5. Generating longdomain and exporting..."
& (Join-Path $ScriptDir "flush_pihole_log.ps1")
& (Join-Path $ScriptDir "generate_traffic.ps1") -Profile longdomain
Start-Sleep -Seconds 2
& (Join-Path $ScriptDir "export_dataset.ps1") -Name longdomain

Write-Host "6. Running analysis for all datasets (baseline first for heuristic baseline)..."
Set-Location $Root
$OutputsDir = Join-Path $Root "outputs"
$DataDir = Join-Path $Root "data"
$VenvPython = Join-Path (Join-Path $Root ".venv") "Scripts\\python.exe"
if (Test-Path $VenvPython) { $Py = $VenvPython } else { $Py = "python" }
$RunAnalysis = Join-Path (Join-Path $Root "src") "run_analysis.py"
$BaselineSummary = Join-Path (Join-Path $OutputsDir "baseline") "summary.json"
& $Py $RunAnalysis (Join-Path $DataDir "baseline.log") --name baseline --outputs $OutputsDir
& $Py $RunAnalysis (Join-Path $DataDir "burst.log") --name burst --outputs $OutputsDir --baseline-summary $BaselineSummary
& $Py $RunAnalysis (Join-Path $DataDir "nxdomain.log") --name nxdomain --outputs $OutputsDir --baseline-summary $BaselineSummary
& $Py $RunAnalysis (Join-Path $DataDir "longdomain.log") --name longdomain --outputs $OutputsDir --baseline-summary $BaselineSummary

Write-Host "7. Starting Streamlit app..."
& (Join-Path $ScriptDir "run_app.ps1")
