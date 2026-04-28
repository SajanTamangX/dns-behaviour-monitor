# Stop Pi-hole containers
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$PiholeDir = Join-Path $Root "pihole"
Set-Location $PiholeDir
docker compose down
Write-Host "Pi-hole stopped."
