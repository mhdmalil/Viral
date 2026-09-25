$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

$uvicorn = Join-Path $root "backend\.venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uvicorn)) {
  Write-Error "Create the venv first: py -3 -m venv backend\.venv ; backend\.venv\Scripts\pip install -r backend\requirements.txt"
}

$whisperPy = Join-Path $root "backend\.venv-whisper\Scripts\python.exe"
if (-not (Test-Path $whisperPy)) {
  Write-Warning "Whisper sidecar missing. Speech transcription needs: py -3.12 -m venv backend\.venv-whisper ; backend\.venv-whisper\Scripts\pip install -r backend\requirements-whisper.txt"
}

Write-Warning "Generate scoring needs AI_API_KEY in .env (OpenRouter). Hermes proxy is not used."

Start-Process -FilePath $uvicorn -ArgumentList "app.main:app","--app-dir","backend","--host","127.0.0.1","--port","8000" -WorkingDirectory $root
Set-Location (Join-Path $root "frontend")
npm run dev
