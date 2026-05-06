# Generate DNS traffic via Python (port 5354). Usage: .\generate_traffic.ps1 -Profile baseline
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("baseline", "burst", "nxdomain", "longdomain")]
    [string]$Profile,
    [double]$Timeout = 1.0,
    [switch]$QuietTimeouts
)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$PythonScript = Join-Path $ScriptDir "generate_dns.py"
# Prefer project venv if present
$VenvPython = Join-Path (Join-Path $Root ".venv") "Scripts\\python.exe"
if (Test-Path $VenvPython) { $Py = $VenvPython } else { $Py = "python" }
$Args = @($PythonScript, "--profile", $Profile, "--timeout", $Timeout)
if ($QuietTimeouts) {
    $Args += "--quiet-timeouts"
}
& $Py @Args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
