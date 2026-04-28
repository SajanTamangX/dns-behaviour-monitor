# Clear Pi-hole log for clean separation between datasets (optional)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$LogPath = Join-Path (Join-Path $Root "pihole") "logs\\pihole.log"
if (Test-Path $LogPath) {
    try {
        Clear-Content $LogPath -Force -ErrorAction Stop
        Write-Host "Pi-hole log flushed: $LogPath"
    } catch {
        # On Windows host-mounted files may be locked by the container.
        # Fallback: truncate from inside the running container.
        docker exec pihole sh -c "truncate -s 0 /var/log/pihole/pihole.log" | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw
        }
        Write-Host "Pi-hole log flushed via container fallback."
    }
} else {
    Write-Host "Log file not found: $LogPath"
}
