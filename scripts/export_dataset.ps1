# Export pihole.log to data/<name>.log
# Usage: .\export_dataset.ps1 -Name baseline
param(
    [Parameter(Mandatory = $true)]
    [string]$Name
)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$Src = Join-Path (Join-Path $Root "pihole") "logs\\pihole.log"
$DataDir = Join-Path $Root "data"
$Dest = Join-Path $DataDir "$Name.log"
if (-not (Test-Path $DataDir)) { New-Item -ItemType Directory -Path $DataDir -Force | Out-Null }
if (-not (Test-Path $Src)) { Write-Error "Source log not found: $Src" }
Copy-Item -Path $Src -Destination $Dest -Force

$lines = Get-Content -Path $Dest -ErrorAction Stop
$queryRegex = "query\[(A|AAAA)\]\s+([^\s]+)\s+from\s+([^\s]+)"
$queryCount = 0
$nonHealthQueryCount = 0

foreach ($line in $lines) {
    if ($line -match $queryRegex) {
        $queryCount++
        $domain = $Matches[2].ToLowerInvariant()
        if ($domain -ne "pi.hole") {
            $nonHealthQueryCount++
        }
    }
}

if ($queryCount -eq 0) {
    Write-Error "Exported log contains no DNS query lines. Pi-hole may not be receiving traffic."
}

if ($nonHealthQueryCount -eq 0) {
    Write-Error "Exported log only contains pi.hole health checks. Generate traffic first with .\scripts\generate_traffic.ps1 -Profile baseline"
}

Write-Host "Exported: $Src -> $Dest"
Write-Host "Validated queries: total=$queryCount non_pi_hole=$nonHealthQueryCount"
