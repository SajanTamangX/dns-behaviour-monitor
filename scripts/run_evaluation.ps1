# Run full evaluation: generate datasets, export, run analysis, check heuristic triggers, write summary.
# Prerequisites: Pi-hole running (scripts/pihole_up.ps1), Python venv with deps.
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Join-Path $ScriptDir ".."
$DataDir = Join-Path $Root "data"
$OutputsDir = Join-Path $Root "outputs"
$EvalDir = Join-Path $OutputsDir "evaluation_tables"
$SummaryPath = Join-Path $OutputsDir "evaluation_summary.md"
$VenvPython = Join-Path $Root ".venv" "Scripts" "python.exe"
if (Test-Path $VenvPython) { $Py = $VenvPython } else { $Py = "python" }

# Ensure dirs and run from project root
Set-Location $Root
foreach ($d in $DataDir, $OutputsDir, $EvalDir) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

$profiles = @("baseline", "burst", "nxdomain", "longdomain")
$results = @()

# 1) Baseline first (for heuristic baseline)
& (Join-Path $ScriptDir "flush_pihole_log.ps1")
& (Join-Path $ScriptDir "generate_traffic.ps1") -Profile baseline
Start-Sleep -Seconds 2
& (Join-Path $ScriptDir "export_dataset.ps1") -Name baseline
& $Py (Join-Path $Root "src" "run_analysis.py") (Join-Path $DataDir "baseline.log") --name baseline --outputs $OutputsDir
$baselineSummary = Join-Path $OutputsDir "baseline" "summary.json"

# 2) Other datasets
foreach ($p in @("burst", "nxdomain", "longdomain")) {
    & (Join-Path $ScriptDir "flush_pihole_log.ps1")
    & (Join-Path $ScriptDir "generate_traffic.ps1") -Profile $p
    Start-Sleep -Seconds 2
    & (Join-Path $ScriptDir "export_dataset.ps1") -Name $p
    & $Py (Join-Path $Root "src" "run_analysis.py") (Join-Path $DataDir "$p.log") --name $p --outputs $OutputsDir --baseline-summary $baselineSummary
}

# 3) Check heuristic triggers
$burstFindings = Get-Content (Join-Path $OutputsDir "burst" "findings.json") | ConvertFrom-Json
$longFindings = Get-Content (Join-Path $OutputsDir "longdomain" "findings.json") | ConvertFrom-Json
$nxFindings = Get-Content (Join-Path $OutputsDir "nxdomain" "findings.json") | ConvertFrom-Json

$burstOk = ($burstFindings | Where-Object { $_.type -eq "burst_window" }).Count -ge 1
$longOk = ($longFindings | Where-Object { $_.type -eq "long_domain" }).Count -ge 1
$nxOk = ($nxFindings | Where-Object { $_.type -eq "nxdomain_excess" }).Count -ge 1

# 4) Copy CSVs to evaluation_tables
foreach ($p in $profiles) {
    $src = Join-Path $OutputsDir $p
    if (Test-Path $src) {
        Get-ChildItem $src -Filter "*.csv" | ForEach-Object { Copy-Item $_.FullName (Join-Path $EvalDir "$p-$($_.Name)") -Force }
    }
}

# 5) Write evaluation_summary.md
@"
# Evaluation Summary

- **Baseline**: generated, analysed, used as heuristic baseline.
- **Burst**: burst_window heuristic triggered: $burstOk
- **Long domain**: long_domain heuristic triggered: $longOk
- **NXDOMAIN**: nxdomain_excess heuristic triggered: $nxOk

## Outputs

- Summary JSON and findings: $OutputsDir\<dataset>\
- Tables: $EvalDir\*.csv
"@ | Set-Content $SummaryPath -Encoding UTF8

Write-Host "Evaluation complete. Summary: $SummaryPath"
Write-Host "Burst trigger: $burstOk  Long-domain trigger: $longOk  NXDOMAIN-like trigger: $nxOk"
