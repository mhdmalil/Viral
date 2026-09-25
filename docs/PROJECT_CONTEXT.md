# Project Context

## What This Project Is
- **Project name:** ViralClipper
- **One-line description:** Local-first Windows app that finds high-potential short-form moments in long videos and turns them into captioned vertical clips.
- **Primary users / audience:** A single operator on this PC (content accounts: TikTok, Instagram, YouTube, etc.).
- **Business domain / vertical:** Short-form content production from long-form video.

## Detected Stack
- **Platform:** Local FastAPI + React SPA (Windows). **Not** a Shopify theme.
- **Language(s):** Python 3.13.3 **free-threading (cp313t)** via `py` (`python` Store alias is broken). Pydantic must use cp313t wheels. TypeScript.
- **Framework(s)/libraries in active use:** FastAPI, SQLAlchemy 2, React 18, Vite (Phase 2)
- **Package manager:** pip (venv), npm 11.11.0
- **Build/dev tooling:** Uvicorn, Vite; Node v22.18.0
- **Hosting / deployment target:** Local loopback only (`127.0.0.1`). Desktop shortcut opens Edge app mode at `http://127.0.0.1:8000`.
- **Repository layout notes:** App code under `backend/` and `frontend/`. Agent OS in `AGENTS.md` + `.cursor/`. SQLite and media under `data/` and `media/`.
- **Cursor workspace:** Open `Desktop\ViralClipper.code-workspace` (this folder only). NeroCasa has its own `Desktop\NeroCasa.code-workspace`. File → New Agent uses whichever workspace is open; it does not copy old chats. Persistence is `docs/` + skills, not a subagent.

### Environment inspection (2026-09-20)
| Tool | Result |
|---|---|
| `python` | Not on PATH (Windows Store stub) |
| `py` | Python 3.13.3 |
| Node | v22.18.0 |
| npm | 11.11.0 |
| FFmpeg | Present (gyan.dev 2025-07-01 build) — used for wav extract and 9:16 render |
| GPU | NVIDIA GeForce GTX 960, 4096 MiB, driver 582.66, CUDA 13.0 reported by nvidia-smi |

## Environments
| Environment | URL / target | Notes |
|---|---|---|
| Production | Local on this PC | Bind 127.0.0.1 |
| Staging | n/a | |
| Local dev | API `http://127.0.0.1:8000`, UI Vite `5173` | CORS/proxy to loopback |
| Desktop | `http://127.0.0.1:8000` serves API + built SPA | Shortcut `ViralClipper.lnk` |

## Key Constraints
- Cursor is IDE only; app must run with `py` + `npm`.
- No public bind. No secrets in git.
- AI for viral detection is **OpenRouter** (`POST /chat/completions`). No Hermes proxy. No local LLM on the 960.
- Whisper + FFmpeg stay local. Auto-reframe is CPU Haar (OpenCV), not GPU tracking on the 960.
- Account = social identity. Clip count N is a ceiling over legitimate distinct clips. Score ranks; it does not reject. "All strong clips" returns every legitimate distinct candidate (safety cap 50). Finished clips are at least 8 seconds and usually 12–25 when the speech continues.
- Do not claim transcription, detection, render, or tracking until those phases exist.

## Ownership / Stakeholders
- Product owner: Hadi (this machine).

## Summary of Current State
Phase 9: Library search, project/tag/file filters, and clip tags. No Trash. Generate still runs the 6-pass editorial pipeline; Pass 4 drops only invalid clips. API usage is recorded per chat call and shown on `/usage`, the dashboard log, and a project Watch API dock.
