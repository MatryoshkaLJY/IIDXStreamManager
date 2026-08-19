$ErrorActionPreference = "Stop"
$Root = (Resolve-Path $PSScriptRoot).Path
$PidFile = Join-Path $Root "iidx_director\runtime\director.pid"
if (-not (Test-Path $PidFile)) { Write-Host "No director PID file found."; exit 0 }
$Pid = [int](Get-Content $PidFile | Select-Object -First 1)
if (Get-Process -Id $Pid -ErrorAction SilentlyContinue) {
    Write-Host "Stopping director and child services, PID=$Pid"
    & taskkill.exe /PID $Pid /T /F | Out-Host
} else { Write-Host "Process $Pid has already exited." }
Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
