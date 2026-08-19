$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path $PSScriptRoot).Path
$Venv = Join-Path $Root '.venv'
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue

if (-not $PythonCommand) {
    throw 'Python was not found. Install Python 3.12 x64 and enable Add Python to PATH.'
}
$PythonPath = $PythonCommand.Source
$Version = & $PythonPath '-c' 'import sys; print(sys.version_info[0], sys.version_info[1], sep=chr(46))'
if ($Version.Trim() -ne '3.12') {
    throw ('Python 3.12.x is required. Current version: ' + $Version.Trim())
}
$Arch = & $PythonPath '-c' 'import struct; print(struct.calcsize(chr(80)) * 8)'
if ($Arch.Trim() -ne '64') {
    throw ('64-bit Python is required. Current architecture: ' + $Arch.Trim())
}

if (-not (Test-Path $Venv)) {
    & $PythonPath '-m' 'venv' $Venv
}
$VenvPython = Join-Path $Venv 'Scripts\python.exe'
if (-not (Test-Path $VenvPython)) {
    throw ('Virtual environment creation failed: ' + $VenvPython)
}
& $VenvPython '-m' 'pip' 'install' '--upgrade' 'pip'
& $VenvPython '-m' 'pip' 'install' '-r' (Join-Path $Root 'requirements-windows.txt')
& $VenvPython '-c' 'import flask, flask_socketio, pydantic, obsws_python, websockets, PIL, numpy, cv2, onnxruntime, yaml, serial; print(1)'
if ($LASTEXITCODE -ne 0) {
    throw 'Dependency verification failed. Review pip output and rerun install_windows.ps1.'
}

$Required = @(
    'iidx_director\src\app.py',
    'iidx_state_reco\serve.py',
    'iidx_state_reco\classifier_augmented_medium.onnx',
    'iidx_state_reco\classifier_augmented_medium.onnx.data',
    'iidx_state_reco\classifier_augmented_medium.labels.txt',
    'iidx_score_reco\serve.py',
    'iidx_score_reco\rois.csv',
    'iidx_score_reco\font',
    'iidx_bpl_scoreboard\index.html',
    'iidx_knockout_scoreboard\index.html'
)
foreach ($Relative in $Required) {
    if (-not (Test-Path (Join-Path $Root $Relative))) {
        throw ('Required deployment file is missing: ' + $Relative)
    }
}

New-Item -ItemType Directory -Force (Join-Path $Root 'iidx_director\data') | Out-Null
New-Item -ItemType Directory -Force (Join-Path $Root 'iidx_director\runtime\screenshots') | Out-Null
$AppRoot = Join-Path $Root 'iidx_director'
Push-Location $AppRoot
try {
    & $VenvPython '-c' 'from pathlib import Path; from src.config.loader import ensure_templates; ensure_templates(Path.cwd() / Path(chr(100) + chr(97) + chr(116) + chr(97)))'
}
finally {
    Pop-Location
}
Write-Host 'Installation complete. Run start_director.bat.' -ForegroundColor Green
