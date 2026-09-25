# ViralClipper

Local-first Windows app: long video → viral-moment detection (API AI, later) → up to N captioned vertical clips.

Cursor is only the IDE. This app runs with Python and Node on your machine.

## Phase 10 (current)

Double-click **ViralClipper** on your Desktop. That starts the local API if needed and opens the app in its own Edge window. First run builds `frontend/dist` if it is missing.

Dev still works with two terminals (Vite on 5173). The desktop window uses `http://127.0.0.1:8000` and does not need Node after the UI is built.

Put your OpenRouter key in `.env` as `AI_API_KEY`. Hermes proxy is not required. Pin `AI_MODEL` later if `openrouter/free` scores inconsistently.

## Requirements

- Windows
- Python 3.13 via `py -3` for the app (`python` may be a Microsoft Store stub)
- Python 3.12 via `py -3.12` for the Whisper sidecar
- Node.js 22+
- FFmpeg on PATH (audio extract in Phase 3; clip render in Phase 6)

## Desktop

After the venv exists:

```powershell
cd frontend
npm run build
cd ..
backend\.venv\Scripts\python.exe scripts\desktop_app.py
```

That writes `ViralClipper.lnk` on your Desktop. You can also run `scripts\ViralClipper.bat`.

Close the Edge window anytime. The API stays on port 8000 until you stop it in Task Manager (python/uvicorn). A second click only reopens the window.

## Start (two terminals, optional)

From the repo root:

```powershell
py -3 -m venv backend\.venv
backend\.venv\Scripts\pip install -r backend\requirements.txt
py -3.12 -m venv backend\.venv-whisper
backend\.venv-whisper\Scripts\pip install -r backend\requirements-whisper.txt
Copy-Item .env.example .env -ErrorAction SilentlyContinue
backend\.venv\Scripts\uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Whisper lives in the 3.12 sidecar because the app venv is Python 3.13 free-threading (`ctranslate2` has no wheel for it).

```powershell
cd frontend
npm install
npm run dev
```

UI: `http://127.0.0.1:5173`  
API health: `http://127.0.0.1:8000/health`

Or: `powershell -File scripts\dev.ps1` after the venv exists.

## Tests

```powershell
backend\.venv\Scripts\pytest
```
