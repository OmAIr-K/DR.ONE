# Start DR.ONE web stack (backend :8000 + frontend :5173)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "Starting API on http://127.0.0.1:8000 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root'; uvicorn server:app --host 127.0.0.1 --port 8000"

Write-Host "Starting frontend on http://127.0.0.1:5173 ..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\frontend'; npm run dev"

Write-Host ""
Write-Host "Open http://127.0.0.1:5173/ in your browser."
Write-Host "Optional: set DRONE_BLENDER_PATH if Blender is not in the default 4.2 install path."
