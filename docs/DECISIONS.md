# Decisions Log

### 2026-09-24 — .env API keys beat leftover process env
**Context:** Changing `GROQ_API_KEY` in `.env` still called the old Groq account because `load_dotenv(override=False)` kept a Windows/Cursor environment value, and uvicorn never reloads keys.
**Decision:** Hydrate Groq/Gemini/OpenRouter from project `.env` first. Token files are fallback only. Changing a key still requires a full desktop restart.
**Alternatives considered:** Keep process env first (previous behavior).
**Context:** After delete + re-drop, `GET /clips?in_project=true` skipped the hash filter when there was no source, and same-hash import reused the file without wiping clips.
**Decision:** No current source → empty workbench. Re-import of the same bytes wipes clips first. Delete/replace cancels a live Generate instead of blocking. User uploads/clips were cleared with `clear_uploaded_media`.
**Alternatives considered:** Keep reuse-without-wipe for speed.

### 2026-09-24 — Dead Generate jobs must not block a new cut
**Context:** Killing uvicorn left SQLite jobs in RENDERING. The next Generate returned that row and never started a thread, so the workbench kept old MP4s (old layout).
**Decision:** On boot, cancel ACTIVE jobs. Generate only reuses a job if its thread is alive. Each job stores `source_id` and cuts that file. Clip files always include the clip id in the name.
**Alternatives considered:** Keep returning the latest ACTIVE row (previous behavior).
**Context:** Generate hid old cuts in Library and could keep extra source rows. An hour-long Generate then cut or showed the previous import. Deleting a video from a project left MP4s and hook files.
**Decision:** One source per project. Import/Generate drop extras and hash-check the file on disk. Import, Generate, source delete, and project delete hard-delete clips, `.ass`, `_hook.txt`, and analysis for that video. Library is not an archive of deleted projects.
**Alternatives considered:** Keep Library as a vault (previous 2026-09-22 decision).

### 2026-09-24 — Linear clip starts on the hook
**Context:** Hook-first concat played ~1.65s of `hook_at` then jumped back to setup. That cut felt wrong.
**Decision:** One source-order take. Pass 6 and Generate pin `start` to `hook_at` when it sits in the thought, then play forward. Overlay hook text still runs the whole clip. No concat reorder.
**Alternatives considered:** Keep the three-piece HOOK/SETUP/REST concat.

### 2026-09-24 — Hook-first validation vs near-start
**Context:** `hook_first_pieces` clamped any `hook_at` into `[start, end-0.2]`, so a stamp outside the thought became a fake cut near the end. Fast FFmpeg `-ss` before `-i` could also start a slice on the wrong keyframe.
**Decision:** Keep the 8/12/13.65/20 partition. `resolve_hook_at` only accepts a stamp in `[start, end)` (or `window_start + hook` when that lands in range). Out of range → linear `[start, end]`. `HOOK_NEAR_START = 0.45` still skips a pointless reorder when the hook is already the opening; that path is logged as `hook near start` vs `hook missing/invalid`. Slices use decode `-ss` after `-i`; concat order is `part_000`, `part_001`, …
**Alternatives considered:** Treat `hook < start` as `start+hook` (rejected: `hook=5, start=8` would become 13).

### 2026-09-24 — Canvas-fixed overlays, fitted source
**Context:** Hook, socials, and captions were mixed with the source picture coordinates. Portrait forced the hook onto the video at y=150; landscape put it above the strip. Captions used PlayRes 384×288, so MarginV did not match the 1080×1920 file. Socials used a fixed x=110 tied to picture_top.
**Decision:** `fit_source()` is the only picture rectangle. Hook is always vertically centered in the 112px top bar. Captions are always MarginV=420 on PlayRes 1080×1920. Socials use `max(40, video_x+30)` and `max(150, video_y+80)`, and drop icons that would enter the bottom 420px UI band. Haar/reframe stays off at generate (`crop=None`).
**Alternatives considered:** Keep hook glued to picture_top; keep 384×288 PlayRes.

### 2026-09-23 — No footer, left socials, 1x hook-first
**Context:** The footer hid socials. The concat graph sped up speech. The picture still had a large top bar.
**Decision:** Drop the bottom bar. Shrink the hook bar to 168px. Stack socials on the far left of the picture. Captions stay on the bottom of the footage. Hook-first is cut as normal-speed slices then concatenated. Project clip lists match the current video hash.
**Alternatives considered:** Footer strip; fps=30 filter concat.

### 2026-09-23 — One source per project
**Context:** Adding a second video left the old file and the old clips on the workbench. Generate used the newest source but still listed the previous cuts, so it looked like the old video was clipped again.
**Decision:** A new upload replaces other sources on that project. Generate (and a real new import) hide in-project clips; they remain in Library.
**Alternatives considered:** Multiple sources per project with generate picking `id desc`.

### 2026-09-23 — Hook-first cut, no zoom/music yet
**Context:** Edited shorts open on the attraction line, then jump into the thought. Zoom and music were requested later, not in this pass.
**Decision:** Keep the thought start in Pass 6. Render concatenates `[hook ~1.6s][setup][rest after the open]` so that 1.6s is not heard twice. The hook line stays in the top bar the whole time. Captions are remapped ASS with a yellow last word. No Ken Burns, no bed music.
**Alternatives considered:** Starting the file on the hook (old Pass 6); repeating the hook then playing the full span; SRT + force_style (apostrophes and commas broke the filtergraph).

### 2026-09-23 — Bigger picture, captions on footage
**Context:** A 420px bottom bar wasted frame. Captions in that void looked like a lower-third on black, not on the video.
**Decision:** Keep a 280px top bar for the hook. Grow the picture down to 1544px. Captions overlay the bottom of the picture. Footer is 96px for socials (or a picture strip).
**Alternatives considered:** Captions in the footer; shrinking the top bar too.

### 2026-09-23 — Fit hooks on 1080, square generate tiles
**Context:** Impact at 76px clipped long overlays left/right. Generate tiles were skinny rectangles with cramped meta. Overlay swears showed in full.
**Decision:** Shrink then wrap the hook to two lines so it stays inside 1000px. Mask overlay profanity (`fuck` → `f*ck`); captions stay exact speech. Generate cards use a square preview (`object-fit: contain`) and a stacked details block.
**Alternatives considered:** Always shrinking to tiny one-line type; cropping 9:16 previews with `cover`.
**Context:** Overlay hooks were dumping transcript fragments with commas/slashes and cutting mid-sentence at 28 characters.
**Decision:** Pass 1/2 pick with judgment: keep exact spoken words when they already hook, rephrase to a curiosity tease when they do not. Overlay is one line, sized to fit, fully above the picture. Captions stay the real transcript — never paraphrased.
**Alternatives considered:** Always quote; always rephrase; a second LLM pass after render.

### 2026-09-23 — Editor brain + mixed vibes
**Context:** User wanted real editorial thinking and mixed kinds when several chips are ticked.
**Decision:** Six-pass prompts now instruct hook→build→payoff reasoning (JSON only). A clip stores `vibes` (max 3). Wanted chips are OR: keep if any listed vibe matches; mixed funny+informative is valid when both were ticked.
**Alternatives considered:** One vibe only; requiring every ticked vibe on each clip.

### 2026-09-23 — Multi-select vibe chips
**Context:** User wants to choose several kinds (funny + informative + financial) instead of random mixes, without a one-vibe dropdown.
**Decision:** Same chip row on Generate and Library. Empty = all. Non-empty is an include list (OR). Generate saves `branding.vibes` and filters Pass 4 keepers to those vibes. Library `?vibes=` filters existing clips. One vibe per clip.
**Alternatives considered:** Single dropdown; AND on one clip; extra topic chips.

### 2026-09-22 — Footer socials row vs picture
**Context:** Social icons stacked vertically. Sometimes a full image should replace them and sit under the captions.
**Decision:** `branding.footer` is `socials` (40px icons + handles in one row near y=1868) or `picture` (fills the empty gap under the caption; size follows the real fitted frame). Picture mode does not burn socials. Hook uses Impact (fallback Arial Black) in a white box; captions stay Arial. Hook and captions sit on the actual picture edges, not the 1220 slot.
**Alternatives considered:** Mixing a custom logo into the social stack; cropping the picture to fill.

### 2026-09-22 — Generate survives navigation
**Context:** Generate was a FastAPI background task on the HTTP request. Leaving the page could abort the client and stop the job.
**Decision:** Run `run_generate_job` on a daemon thread in production. Tests still run it inline (`transcription_backend=test`). Sidebar polls the dashboard for an in-flight job.
**Alternatives considered:** Celery; keeping Starlette BackgroundTasks.

### 2026-09-22 — Library is the archive
**Context:** Project-page delete and project delete were hard-deleting clip files, so Library lost the same clips. Dashboard also counted those files on the project card.
**Decision:** Project delete/remove only hides clips on that project (and moves files into `projects/library/clips` if the project folder is removed). `POST /api/clips/bulk-delete` from Library is the only full wipe.
**Alternatives considered:** Duplicate files in a library folder on every generate.
**Consequences:** Dashboard project “Clips N” is clips still on that project. Library lists every remaining file.

### 2026-09-22 — Same video after project delete
**Context:** SQLite reused project id 1 after delete. Leftover source rows/folders made a new project look like it already had the long video.
**Decision:** Same hash on the same project returns the existing source (200). Project delete unlinks files, usage rows, and leftover `NNNN_*` folders. New projects skip an occupied folder name.
**Alternatives considered:** Keep 409 on duplicate hash; global unique hash.
**Consequences:** Re-drop of the same file is a no-op. A new project can import a video that lived on a deleted project.

### 2026-09-22 — API monitor from usage
**Context:** Dashboard needed a live view of which APIs and models Generate actually hits, including limits, without hardcoding a catalog.
**Decision:** Persist each `complete_chat` attempt (`ApiUsageEvent`). Limits come from rate-limit response headers when present. UI is numbers + CSS bars. Full view at `/usage`; dashboard is logs + link; project Watch API is a sticky side dock, not a modal.
**Alternatives considered:** Hardcoded RPM tables; overlay modal on Generate.
**Consequences:** Empty until Generate (or any chat) has run. In-memory live line is the in-flight call only.

### 2026-09-22 — Library without trash
**Context:** Phase 9 asked for search/filters/tags/trash polish. Trash and Favorites were already removed from the product.
**Decision:** Add a Library page with search (title/project/analysis), project filter, tag filter, ready/missing files, and tagging selected clips. Removing a clip from a project or deleting a project keeps it in Library. Hard delete is Library-only.
**Alternatives considered:** Soft-delete trash; putting search only on the project workbench.
**Consequences:** `/clips` redirects to `/library`.

### 2026-09-22 — CPU Haar auto-reframe (not GPU)
**Context:** Phase 8 needed a 9:16 window on talking-head footage. The machine has a GTX 960 4GB; GPU tracking would contend with other work and is a poor fit.
**Decision:** Sample five JPEGs in the clip range, run OpenCV Haar (`haarcascade_frontalface_default`) on CPU, average the largest face center, crop the largest even 9:16 window, then `scale=1080:1920`. The app venv is Python 3.13 free-threading and has no OpenCV wheel, so Haar runs in the existing CPython 3.12 Whisper sidecar (`backend/scripts/haar_faces.py`). If OpenCV/sidecar is missing or no face is found, use a center 9:16 crop. `reframe_enabled=0` keeps the old scale-then-center filter.
**Alternatives considered:** NVIDIA tracking; YOLO; always-center crop only.
**Consequences:** Existing projects stay Center until Auto is chosen. New projects default Auto. Existing clip files are not recropped until Generate.

### 2026-09-22 — Project folders on disk
**Context:** Clips lived under `media/accounts/...` and browser downloads went to the system Downloads folder.
**Decision:** Each project gets `projects/{id}_{name}/` with `source`, `clips`, `analysis`, `thumbnails`, and `downloads`. Bulk download writes a zip there and also returns it to the browser. Existing files stay where they are until the next import/generate.
**Alternatives considered:** Only Desktop shortcuts; moving every historical clip immediately.

### 2026-09-22 — Caption styles via FFmpeg force_style
**Context:** Phase 6 burned one default SRT look. Extra styles were deferred.
**Decision:** Keep one SRT cue builder. Style/position are ASS `force_style` on `subtitles=`: classic, bold, boxed; lower/center/upper. Stored on the project. Captions can be off. Existing MP4s are not re-burned until Generate.
**Alternatives considered:** Per-word karaoke; rewriting cues per style; storing style only on the account.
**Consequences:** Generate must be restarted to pick up new columns. Unknown style names fall back to classic.

### 2026-09-21 — Models first, then providers
**Context:** Generate hammered Groq `gpt-oss-120b`, Llama 404'd, then jumped to OpenRouter. User wanted model switching inside a provider.
**Decision:** Groq list is `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`. Gemini chat uses `gemini-flash-latest`, `gemini-flash-lite-latest`, `gemini-3.5-flash` (`gemini-2.5-flash` 404s on the OpenAI-compat endpoint). Each call rotates the first model inside the provider. On 429/404, try the next model on that provider before leaving it.
**Alternatives considered:** Keep Llama ids; cool the whole Groq account on one 429.
**Consequences:** In-flight Generate still uses the old chain until it finishes. Next Generate after restart uses this order.

### 2026-09-21 — Jump on 429, do not sit on Retry-After
**Context:** Generate looked stuck: Groq/GLM 429 loops waited 8–12s per attempt, then GLM hung up to 180s.
**Decision:** On 429, immediately try the next model and cool that model for 120s. Chat HTTP timeout is 35s.
**Alternatives considered:** Honor Retry-After and retry the same model.
**Consequences:** Other models on the same provider still get a turn.

### 2026-09-21 — Pass 4 rejects only invalid clips
**Context:** Discovery already returns potential clips. Pass 4 was dropping them at editorial score 0.75, so 0.55–0.70 moments never reached ranking.
**Decision:** Pass 4 keeps every legitimate distinct candidate. Reject only duplicate same-moment, dead air, incomplete unusable fragments, no content, or invalid times. Quality is ranking input for Pass 5. `user_max` (15/30) is a distinct ceiling; uncapped runs return all legitimate clips up to the safety cap. Do not invent clips to fill N.
**Alternatives considered:** Lower the 0.75 bar; keep 0.75 as a publish gate.
**Consequences:** Asking for 15 can return every valid distinct candidate up to 15. A 0.55 clip can ship if it is real content and ranks inside the ceiling.

### 2026-09-21 — Sparse-window discovery context
**Context:** Pass 1 ran all 19 windows; windows 3–18 returned 0 seeds because tiny-Whisper text was 23–191 characters. The 15 ceiling never applied.
**Decision:** If a window has speech but short text, Pass 1 sends ±90s adjacent transcript as context and keeps `window_start`/`window_end` as the search range. Candidates must overlap that range. Whisper `condition_on_previous_text=False`. Pass 4 bar stays 0.75.
**Alternatives considered:** Lower 0.75; re-transcribe with `base` on every generate.
**Consequences:** Later quiet windows can produce seeds from sparse speech plus neighbors. Cached `tiny` transcripts stay until re-transcribed.

### 2026-09-21 — Discovery was starving later windows
**Context:** Latest generate on a ~32 min video requested max 15 and returned 5. Funnel: 19 windows, 11 seeds (windows 0–2 only), 9 expanded, 5 validated, 5 selected.
**Decision:** Pass 1 no longer sees `clip_count_max`. Prompt treats each window independently, including sparse speech. Editorial bar stays 0.75. Duration still follows the thought (platform max 180s only).
**Alternatives considered:** Lower Pass 4 bar; force-fill to 15.
**Consequences:** Later quiet-but-spoken windows can still yield seeds. Analysis JSON now has `funnel` and `pass4_rejected`.

### 2026-09-21 — Clip count is a ceiling; quality-first select
**Context:** Filling toward N and spreading across time/vibe kept weaker clips and felt like a quota.
**Decision:** `select_strongest` ranks editorial quality, then standalone, then vibe/topic only as a tie-breaker. Same-moment overlap is collapsed. `user_max` / safety cap 50 are ceilings. No min-gap, no time buckets, no fill-to-N.
**Alternatives considered:** Fill toward N from extra seeds; force early/mid/late coverage.
**Consequences:** Asking for 15 can return 7 or 15. Close distinct bits can both survive. Weaker late clips do not replace stronger early ones.

### 2026-09-21 — Cover all kinds of bits, not a random highlight pile
**Context:** User knows the source has many distinct (mostly funny) parts; Generate felt like random clips.
**Decision:** Discovery catalogs every distinct bit. Pass 5 is a coverage tour (early/mid/late, mixed kinds). Local `spread_select` round-robins time buckets and unused vibe/topic before filling by score.
**Alternatives considered:** Keep top-N by quality; trust Pass 5 keep_ids alone.
**Consequences:** Clips spread across the file. Two funny moments stay two clips when they are different bits.

### 2026-09-21 — Clip count is a fill target
**Context:** User set 15 clips and received 4. Pass 5 had no quota and one-per-cluster dropped overlapping expansions.
**Decision:** When `clip_count` is set, discovery/validate keep more seeds, Pass 5 aims for N, and leftover validated clips fill the count using seed-span overlap. No invented times. "All strong clips" stays threshold-first.
**Alternatives considered:** Keep N as a ceiling only; always emit exactly N with weak pads.
**Consequences:** Long videos can return closer to the requested count. Short/empty speech still returns fewer than N.

### 2026-09-21 — Skip failed models; do not abort Generate
**Context:** One exhausted provider or a single HTTP error was aborting the whole editorial job.
**Decision:** `complete_chat` tries the next target on any request/status/payload error. Editorial passes skip a failed window/batch and continue. Missing keys still fail the job.
**Alternatives considered:** Fail the job on first exhausted chain; pad fake clips.
**Consequences:** A Groq outage still uses Gemini/GLM. A dead window yields fewer clips, not FAILED.

### 2026-09-21 — Groq then Gemini then GLM then OpenRouter extras
**Context:** Free GLM 429s emptied Generate. User has Gemini and Groq keys as well as OpenRouter.
**Decision:** Chat fallback order is Groq (`GROQ_MODEL`, default `openai/gpt-oss-120b`) → Gemini → OpenRouter `AI_MODEL` (GLM) → other OpenRouter `:free` ids. Any error skips to the next model. Keys stay in `.env`.
**Alternatives considered:** Wait longer on GLM only; route everything through OpenRouter.
**Consequences:** Generate continues when one free pool is exhausted. Gemini/Groq must be set in `.env` to join the chain.

### 2026-09-21 — Six-pass GLM editor; dynamic clip count
**Context:** First-come 2-minute scoring and midpoint 10–20s fitting made windows into clip boundaries and capped output at UI default 10.
**Decision:** Full Whisper first. Passes: discovery (windows as search only), context expansion, global pool, validation (reject “okay”), global distinct selection, word-level bounds. `clip_count` is an optional maximum when the user sets it; otherwise safety cap 50. Duration follows the thought; platform max 180s is a hard clamp only. No Clip rows until after Pass 6.
**Alternatives considered:** Streaming render per window; keep midpoint fit; keep quota of 10.
**Consequences:** First MP4 appears after editorial selection. More GLM calls per video. Empty files still produce 0 clips.

### 2026-09-21 — Generate streams as an editor, not a batch cutter
**Context:** Waiting for a full Whisper pass then every 10-minute OpenRouter window made Generate look frozen. ClipForge-style apps read a slice, edit, emit a clip, continue.
**Decision:** 2-minute audio chunks (15s lookback into the previous slice). LLM is prompted as a hook→build→payoff editor. Each accepted clip is cut and saved before the next chunk. Clip ceiling still stops the run. Cached full transcripts skip re-Whisper and still stream windows.
**Alternatives considered:** Keep batch generate; 10-minute windows.
**Consequences:** First clip can appear after one chunk instead of the whole file. Free-model 429s still skip a chunk rather than the entire job.

### 2026-09-21 — OpenRouter direct; Hermes agent later for posting
**Context:** Scoring only needs chat completions. Hermes proxy required a second PC and port 8645. User wants a Hermes agent later for auto-post, not for clip scoring.
**Decision:** ViralClipper calls `https://openrouter.ai/api/v1/chat/completions` with Bearer `AI_API_KEY`. `AI_MODEL` defaults to `openrouter/free` and can be pinned without code changes. JSON candidate contract unchanged. Hermes proxy unused.
**Alternatives considered:** Keep Hermes proxy; call Hermes agent for scoring.
**Consequences:** Generate needs a valid OpenRouter key in `.env` and internet. Scores may vary until the model is pinned. Posting agent is a later feature.

### 2026-09-20 — Hermes proxy is the viral AI, not Ollama
**Context:** User cannot run a local LLM; GTX 960 4GB. Hermes CLI/proxy exists on this PC.
**Decision (superseded 2026-09-21):** Phase 4 originally called a local Hermes proxy. Generate now uses `ChatAIProvider` (`backend/app/services/ai/chat.py`) against Groq → Gemini → OpenRouter. `AI_PROVIDER=hermes` still aliases that client.
**Alternatives considered:** Ollama local; Hermes CLI `-z` as primary.
**Consequences:** Generate needs cloud keys in `.env`. Hermes agent remains deferred for posting only.

### 2026-09-20 — Whisper on CPU with tiny model
**Context:** GTX 960 has 4GB; Python is 3.13 free-threading; viral AI stays remote.
**Decision:** Phase 3 uses faster-whisper on CPU, `tiny` default, 16 kHz mono wav via FFmpeg. The Whisper process runs in a **CPython 3.12 sidecar venv** because this app venv is 3.13 free-threading and has no `ctranslate2` wheel. Transcript JSON is cached per file hash. Videos with no audio get an empty transcript, not a fake one.
**Alternatives considered:** CUDA Whisper; `base`/`small` as default; openai-whisper in the 3.13t venv; in-process faster-whisper.
**Consequences:** First real transcribe downloads the tiny weights. Tests use `TRANSCRIPTION_BACKEND=test` so CI/dev pytest does not download models.

### 2026-09-20 — Workbench is name → drop → count/style → progress → download
**Context:** User wanted one simple loop, not account-first setup.
**Decision:** Projects create with a name only. Clip count and style live under the dropped video. Generate shows pipeline text; clip files download when they exist.
**Alternatives considered:** Clip count on the create form; fake placeholder clips.
**Consequences:** Generate is honest until Whisper exists — FAILED with an explanation, empty clip list.

### 2026-09-20 — Remote AI API, not local LLM
**Context:** Viral moment understanding needs a capable model; this PC has a GTX 960 4GB.
**Decision:** Ollama or Hermes will be consumed as HTTP APIs. No local LLM in v1. Whisper/FFmpeg stay local.
**Alternatives considered:** Local Ollama on the 960; cloud GPU.
**Consequences:** Needs network + API credentials in env. Transcripts must be windowed for API context/cost.

### 2026-09-20 — Clip count is a ceiling with a quality bar
**Context:** User chooses N clips per run.
**Decision:** Return at most N clips that pass the threshold. If fewer qualify, report how many strong clips were found. Do not pad.
**Alternatives considered:** Always emit exactly N.
**Consequences:** UX must show a honest count.

### 2026-09-20 — Account is a social identity (data model; UI deferred)
**Context:** Easy to treat accounts as folders.
**Decision:** Account still means a destination in the database. The UI hides this until social connect. Projects attach to a default Workspace account for now.
**Alternatives considered:** Folder-only org; account picker in create flow.
**Consequences:** Publishing later maps real social accounts onto the same table.

### 2026-09-20 — FastAPI + Vite React + SQLite
**Context:** Spec asked for Python backend + React frontend, local-first.
**Decision:** FastAPI on loopback, Vite SPA, SQLite file DB. Use `py -3` because `python` is a Store stub.
**Alternatives considered:** Next.js, Electron in Phase 1, Flask.
**Consequences:** Two processes in Phase 1; Phase 10 adds a launcher.

### 2026-09-22 — Desktop is Edge app mode, not Electron or pywebview
**Context:** User wants to open ViralClipper from the Desktop.
**Decision:** FastAPI serves `frontend/dist` when present. `scripts/desktop_app.py` starts uvicorn on 127.0.0.1:8000 if needed, then Microsoft Edge `--app` with `data/desktop-profile`. Shortcut uses `pythonw.exe`.
**Alternatives considered:** Electron (extra runtime), pywebview (fragile on 3.13 free-threading).
**Consequences:** Node is only needed to build the UI. Opening the Desktop shortcut restarts uvicorn on 8000 so code changes load. The launcher keeps uvicorn running after Edge `--app` returns.

### 2026-09-22 — Letterbox hook + social watermarks
**Context:** User wanted stronger hooks, black bars, hook on top, captions on bottom, and client socials on the clip.
**Decision:** Keep 1080×1920. Fit the whole source (no face crop) so landscape gets black bars. Hook (Impact, white box) sits on the top edge of the real picture; captions (Arial) sit on the bottom edge. Picture footer fills the remaining gap under the caption. 8 seconds is a floor; clips grow with continuing speech toward ~15s (max 180).
**Alternatives considered:** Full-bleed captions; official logo assets.
**Consequences:** Generate again to rebuild old clips. Editorial starts the cut on `hook_at`.

### 2026-09-20 — Projects are the workspace; accounts deferred for publishing
**Context:** Account vs project was confusing in the UI.
**Decision:** Hidden default Workspace account in the DB. UI creates/opens/deletes only in Projects. Accounts page is an empty social-connect placeholder.
**Alternatives considered:** Keep account picker on project create.
**Consequences:** Social identity wiring comes later without blocking clipping.

### 2026-09-20 — Captions in the default generate path
**Context:** User loop is detect → N clips → captions.
**Decision:** First caption style ships with render (Phase 6), extra styles later.
**Alternatives considered:** Captions as a far-later optional extra.
**Consequences:** Phase 6 is larger; product loop is complete earlier.
