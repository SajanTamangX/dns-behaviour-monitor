# Start Pi-hole via Docker Compose (admin 8081, DNS 5354, logs in pihole/logs)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$PiholeDir = Join-Path $Root "pihole"
Set-Location $PiholeDir
docker compose up -d
Write-Host "Pi-hole started. Admin: http://localhost:8081  DNS: 127.0.0.1:5354"
