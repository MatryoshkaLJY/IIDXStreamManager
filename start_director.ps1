param([switch]$TestMode)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path $PSScriptRoot).Path
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) { throw "Missing .venv. Run install_windows.ps1 first." }
$AppRoot = Join-Path $Root "iidx_director"
$PidFile = Join-Path $Root "iidx_director\runtime\director.pid"
New-Item -ItemType Directory -Force (Split-Path $PidFile) | Out-Null
$env:IIDX_RELAY_HOST = "127.0.0.1"
$env:IIDX_DIRECTOR_HOST = "127.0.0.1"
$env:PYTHONIOENCODING = "utf-8"
if ($TestMode) { $env:IIDX_TEST_MODE = "1" } else { Remove-Item Env:IIDX_TEST_MODE -ErrorAction SilentlyContinue }

# 若串口音频切换依赖 pyserial 缺失，自动补装（不影响已安装环境）
try {
    & $VenvPython '-c' 'import serial' | Out-Null
} catch {
    Write-Host "Installing missing pyserial dependency..." -ForegroundColor Yellow
    & $VenvPython '-m' 'pip' 'install' 'pyserial==3.5'
}
$LogDir = Join-Path $Root "iidx_director\runtime"
$StdoutLog = Join-Path $LogDir "director.stdout.log"
$StderrLog = Join-Path $LogDir "director.stderr.log"
Remove-Item $StdoutLog, $StderrLog -Force -ErrorAction SilentlyContinue
$Process = Start-Process -FilePath $VenvPython -ArgumentList @("-m", "src.app") -WorkingDirectory $AppRoot -PassThru -NoNewWindow -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog
Set-Content -Path $PidFile -Value $Process.Id -Encoding ascii
Write-Host "Director started, PID=$($Process.Id)"
Write-Host "Open http://127.0.0.1:5003/"
if ($TestMode) { Write-Host "Test mode enabled (cabinet capture disabled)" -ForegroundColor Yellow }
try {
    Wait-Process -Id $Process.Id | Out-Null
    $Process.Refresh()
    $ExitCode = $Process.ExitCode
    if ($null -eq $ExitCode) { $ExitCode = 1 }
    if ($ExitCode -ne 0) {
        Write-Host "Director exited with code $ExitCode." -ForegroundColor Red
        Write-Host "See $StderrLog for details." -ForegroundColor Yellow
        if (Test-Path $StderrLog) {
            Write-Host "--- last error lines ---" -ForegroundColor Yellow
            Get-Content $StderrLog -Tail 40
            Write-Host "------------------------" -ForegroundColor Yellow
        }
    }
}
finally {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}
exit $ExitCode
