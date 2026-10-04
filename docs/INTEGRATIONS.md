# Integrations

Discovered by inspection unless marked **specified (not wired)**.

## Apps / Plugins / Embeds
None.

## APIs (Inbound & Outbound)
| Name | Direction | Endpoint(s) | Auth method | Used by | Notes |
|---|---|---|---|---|---|
| ViralClipper HTTP | Inbound | `127.0.0.1:8000` | none (local) | React (Vite or desktop SPA) | Generate runs in a background thread after `POST /generate`. Desktop also serves `frontend/dist`. |
| OpenRouter | Outbound | `{AI_API_BASE_URL}/chat/completions` and `/models` | Bearer `AI_API_KEY` | After Groq and Gemini: GLM then other `:free` ids | Default `z-ai/glm-5.2:free` |
| Gemini | Outbound | `{GEMINI_API_BASE_URL}/chat/completions` (OpenAI-compatible) | Bearer `GEMINI_API_KEY` | After every Groq model | `gemini-flash-latest`, `gemini-flash-lite-latest`, `gemini-3.5-flash`. `gemini-2.5-flash` 404s here. |
| Groq | Outbound | `{GROQ_API_BASE_URL}/chat/completions` | Bearer `GROQ_API_KEY` | First provider: all Groq chat models, rotated per call | `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b` |
| Hermes proxy | unused | — | — | — | Dropped for scoring. Possible later for auto-post. |
| Ollama HTTP API | unused | — | — | unused | **Not used** — PC cannot host a local LLM |

## Webhooks
None.

## Analytics & Tracking
None.

## Forms & Submission Handlers
| Form | Location | Submits to | Validation | Notes |
|---|---|---|---|---|
| Create account | Accounts page | `POST /api/accounts` | Pydantic | Phase 1 |
| Create project | Projects page | `POST /api/projects` | name only | Also creates a folder under `projects/` |
| Project settings | Project workbench | `PATCH /api/projects/{id}` | clip_count, captions, style, reframe, branding (`footer`, `vibes[]`) | Empty vibes = hunt all |
| Project logo | Project workbench | `POST/DELETE /api/projects/{id}/logo` | png/jpg/webp | Picture footer (or leftover custom path). Platform marks are shipped PNGs. |
| Generate | Project workbench | `POST /api/projects/{id}/generate` | requires source video | |
| Dashboard | Dashboard page | `GET /api/dashboard` | none | Counts and recent activity |
| API usage | API page, dashboard log, project dock | `GET /api/usage`, `DELETE /api/usage` | provider, project_id, hours | Reset clears recorded calls (optional project_id) |
| Library | Library page | `GET /api/clips`, `GET /api/tags`, `PATCH /api/clips/{id}` | q, project, tag, ready, vibes | No Trash |

## Payment-Related Functionality
None.

## Metafields / Metaobjects / Custom Data
n/a (not Shopify).

## External Services
| Service | Purpose | Where configured | Notes |
|---|---|---|---|
| FFmpeg | Clip/render + per-chunk audio extract for Whisper | system PATH | 2-minute wav slices during generate; 9:16 letterbox; linear cut from hook; xfade joins; punch-in; ASS captions |
| OpenCV (headless) | Haar face detect for auto-reframe | `backend/.venv-whisper` + `scripts/haar_faces.py` | CPU only; app 3.13t venv has no wheel. Missing sidecar → center crop |
| faster-whisper | Transcription | `WHISPER_MODEL`, `WHISPER_DEVICE` | Sidecar venv `backend/.venv-whisper` on CPython 3.12; CPU `tiny`; `condition_on_previous_text=False` |

## Environment Variables / Secrets (names only — never values)
| Variable | Purpose | Required in |
|---|---|---|
| `HOST` | Bind address (default 127.0.0.1) | backend |
| `PORT` | API port (default 8000) | backend |
| `DATABASE_URL` | SQLite URL | backend |
| `TRANSCRIPTION_BACKEND` | `faster-whisper` or `test` | backend |
| `WHISPER_MODEL` | Model size (`tiny` default) | backend |
| `WHISPER_DEVICE` | `cpu` (default) or `cuda` | backend |
| `AI_PROVIDER` | `openrouter` (or `test` in pytest; `hermes`/`chat` alias `ChatAIProvider`) | backend |
| `AI_API_BASE_URL` | OpenAI-compatible root, default `https://openrouter.ai/api/v1` | backend |
| `AI_API_KEY` | OpenRouter Bearer token (never commit). If agent-started processes cannot see this `.env` line, `data/ai.token` (gitignored) is the fallback. | backend |
| `AI_MODEL` | Primary OpenRouter model (GLM). Default `z-ai/glm-5.2:free`. | backend |
| `AI_FALLBACK_MODELS` | Extra OpenRouter ids after Gemini, comma-separated. Default `openrouter/free`. | backend |
| `GEMINI_API_KEY` | Google Gemini key (never commit). | backend |
| `GEMINI_MODEL` | First Gemini model to try. Default `gemini-flash-latest` (`gemini-2.5-flash` 404s on OpenAI-compat). | backend |
| `GROQ_API_KEY` | Groq key (never commit). Project `.env` wins over a leftover process/Windows value; restart the desktop shortcut after changing it. | backend |
| `GROQ_MODEL` | First Groq model to try. | backend |

---
**Rule:** nothing on this page gets removed, disconnected, or replaced without it being an
explicit part of the user's request, and without first explaining the impact.
