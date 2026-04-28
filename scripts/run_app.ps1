# Start Streamlit dashboard (DNS Behaviour Monitor)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$VenvPython = Join-Path (Join-Path $Root ".venv") "Scripts\\python.exe"
$AppPath = Join-Path (Join-Path $Root "app") "streamlit_app.py"
if (Test-Path $VenvPython) { $Py = $VenvPython } else { $Py = "python" }
Set-Location $Root
$port = 8501
$inUse = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($inUse) {
    $port = 8502
    Write-Host "Port 8501 is busy, starting Streamlit on port 8502."
}
& $Py -m streamlit run $AppPath --server.port $port
