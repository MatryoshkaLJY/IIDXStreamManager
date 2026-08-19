$ErrorActionPreference = "Continue"
$Root = (Resolve-Path $PSScriptRoot).Path
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$failed = $false
if (-not (Test-Path $VenvPython)) { Write-Host "FAIL .venv was not created" -ForegroundColor Red; $failed = $true }
else {
    & $VenvPython '-c' 'import flask, flask_socketio, pydantic, obsws_python, websockets, PIL, numpy, cv2, onnxruntime, yaml; print(1)'
    if ($LASTEXITCODE -ne 0) { $failed = $true }
}
foreach ($Relative in @("iidx_state_reco\classifier_augmented_medium.onnx", "iidx_state_reco\classifier_augmented_medium.onnx.data", "iidx_state_reco\classifier_augmented_medium.labels.txt", "iidx_score_reco\rois.csv", "iidx_score_reco\font")) {
    if (Test-Path (Join-Path $Root $Relative)) { Write-Host "OK   $Relative" -ForegroundColor Green }
    else { Write-Host "FAIL $Relative" -ForegroundColor Red; $failed = $true }
}
foreach ($Port in @(5003, 8080, 8081, 8082, 9876, 9877)) {
    $Connection = Test-NetConnection 127.0.0.1 -Port $Port -WarningAction SilentlyContinue
    if ($Connection.TcpTestSucceeded) { Write-Host "BUSY 127.0.0.1:$Port (service is listening)" -ForegroundColor Yellow }
    else { Write-Host "FREE 127.0.0.1:$Port" }
}
$Obs = Test-NetConnection 127.0.0.1 -Port 4455 -WarningAction SilentlyContinue
if ($Obs.TcpTestSucceeded) { Write-Host "OK   OBS WebSocket 127.0.0.1:4455" -ForegroundColor Green }
else { Write-Host "WARN OBS WebSocket 127.0.0.1:4455 is unreachable" -ForegroundColor Yellow }
if ($failed) { exit 1 }
