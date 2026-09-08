$ErrorActionPreference = 'Stop'

$root = Split-Path $MyInvocation.MyCommand.Path
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$logPath = Join-Path $root ".freebuff\backend-8001.log"
$errPath  = Join-Path $root ".freebuff\backend-8001.log.err"

if (-not (Test-Path $venvPython)) {
    throw "venv python not found: $venvPython"
}

Start-Process -FilePath $venvPython `
    -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8001" `
    -WorkingDirectory (Join-Path $root "backend") `
    -RedirectStandardOutput $logPath `
    -RedirectStandardError $errPath `
    -WindowStyle Hidden -PassThru | Out-Null

Write-Host "backend launching from $venvPython"
