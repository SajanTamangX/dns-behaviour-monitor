# Start Streamlit dashboard (DNS Behaviour Monitor)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$VenvPython = Join-Path (Join-Path $Root ".venv") "Scripts\\python.exe"
$AppPath = Join-Path (Join-Path $Root "app") "streamlit_app.py"
if (Test-Path $VenvPython) { $Py = $VenvPython } else { $Py = "python" }
Set-Location $Root
$port = $null
foreach ($candidate in 8501..8510) {
    $inUse = Get-NetTCPConnection -LocalPort $candidate -State Listen -ErrorAction SilentlyContinue
    if (-not $inUse) {
        $port = $candidate
        break
    }
}
if (-not $port) {
    Write-Error "No free Streamlit port found in range 8501-8510."
    exit 1
}
if ($port -ne 8501) {
    Write-Host "Port 8501 is busy, starting Streamlit on port $port."
}
& $Py -m streamlit run $AppPath --server.port $port
