# Changelog

### 2026-10-05
- Changed: Timeline pieces fade together (zoom only into the hook). The hook picture punches in for two seconds and the hook title slides/fades in. Captions still use classic/bold/boxed and now reveal words as they are spoken. Face crop stays unused. Health cut `8s-edit-motion`.
- Files: `motion.py`, `timeline.py`, `ffmpeg.py`, `classic.py`, `runner.py`, `health.py`, `desktop_app.py`, tests, docs

### 2026-09-25
- Changed: Generate, clip cards, the library list, and the API monitor use the same studio surface: phone-shaped clip previews, a sticky clip bar, and an accent usage chart.
- Changed: The desktop UI is a light/dark studio. Warm paper in light, ink in dark, teal actions, cards with a soft shadow, and the project setup split so options sit beside socials. Theme is remembered in the browser. Generate, clips, and API behavior are unchanged.
- Files: `tokens.css`, `app.css`, `AppLayout.tsx`, `index.html`, `ProjectDetailPage.tsx`, `ApiMonitor.tsx`, page heads

### 2026-09-25
- Fixed: Tight cuts only remove a short um/uh, or silence of about a second. A half-second gap stays, and each kept word keeps a tenth of a second of audio on each side. Hook lines drop a dangling last word such as "and". Health cut `8s-word-safe`.
- Files: `timeline.py`, `layout.py`, `health.py`, `desktop_app.py`

### 2026-09-25
- Reverted: Groq Whisper transcription. Generate uses local faster-whisper again. Health cut `8s-hook-down`.
- Files: `factory.py`, `config.py`, `health.py`, `desktop_app.py`

### 2026-09-25
- Changed: Hook type is larger and lower (y=360). Short lines stay one line. Long lines split in two so the type does not shrink. Health cut `8s-hook-down`.
- Files: `layout.py`, `health.py`, `desktop_app.py`

### 2026-09-25
- Changed: Hook is white type with a black outline on the picture, no white box. Captions keep the phrase and turn the spoken word yellow. Health cut `8s-hook-type`.
- Files: `ffmpeg.py`, `classic.py`, `health.py`, `desktop_app.py`

### 2026-09-25
- Fixed: Removing or replacing a project video deletes its clip files, transcripts, wavs, and candidate scripts, not only the database rows. Generate stops if that video is gone. Health cut `8s-erase-cuts`.
- Files: `purge.py`, `import_video.py`, `runner.py`, `ProjectDetailPage.tsx`, `health.py`, `desktop_app.py`

### 2026-09-25
- Changed: Generate takes one project edit note, jump-cuts silence and filler inside the moment (source order), and may cover the picture for about a second with another shot from the same file. Captions follow the tight timeline. One contrast grade. No music, no zoom. Health cut `8s-tight-cut`.
- Files: `timeline.py`, `runner.py`, `ffmpeg.py`, `layout.py`, `engine.py`, `prompts.py`, `normalize.py`, `ProjectDetailPage.tsx`, `health.py`, `desktop_app.py`

### 2026-09-25
- Changed: Agents open at most four skill files (shipped-code default is architecture + protection + review). No 22nd skill. `.cursorignore` drops desktop-profile, venvs, media, and MP4s from search.
- Files: `always-use-skills.mdc`, `AGENTS.md`, `.cursorignore`

### 2026-09-25
- Changed: Separate Cursor workspaces — `Desktop\ViralClipper.code-workspace` and `Desktop\NeroCasa.code-workspace`. The combined two-folder workspace was removed. New Agent in a ViralClipper window loads this repo’s skills and `docs/`; it is not a subagent.
- Files: `ViralClipper.code-workspace`, `NeroCasa.code-workspace`, `always-use-skills.mdc`, `PROJECT_CONTEXT.md`

### 2026-09-24
- Fixed: Groq/Gemini/OpenRouter keys in project `.env` override a leftover Windows/process key, so a new key is used after a full restart. Health cut `8s-env-keys`.
- Files: `config.py`, `health.py`, `desktop_app.py`
- Verified: pytest `test_config_keys.py`

### 2026-09-24
- Fixed: Re-dropping the same video no longer keeps old cuts. Workbench lists nothing until a current source exists, and only clips whose `source_hash` matches that file. Removing/replacing a video stops Generate if it is running. All saved uploads/clips/analysis on this machine were wiped; accounts and projects stay. Health cut `8s-clear-uploads`.
- Files: `clips.py`, `import_video.py`, `purge.py`, `ProjectDetailPage.tsx`, `health.py`, `desktop_app.py`
- Verified: pytest wipe/orphan/timeline + `clear_uploaded_media` run against local SQLite.

### 2026-09-24
- Fixed: After a restart, Generate no longer resumes a zombie RENDERING job, so it was replaying old clips in the old layout. Jobs bind to the imported source; stale jobs are cancelled on boot; workbench clears then recuts. Health cut `8s-live-job`.
- Files: `jobs.py`, `runner.py`, `control.py`, `main.py`, `paths.py`, `clips.py`, `ProjectDetailPage.tsx`, `health.py`, `desktop_app.py`
- Verified: pytest wipe/orphan/timeline — 10 passed.

### 2026-09-24
- Fixed: Generate only cuts the current import (drops leftover sources, hash-checks the file). Deleting a source or project now wipes that video, its clips, hook/caption sidecars, and analysis — not parked in Library. Health cut `8s-wipe-source`.
- Files: `purge.py`, `import_video.py`, `runner.py`, `jobs.py`, `clips.py`, `health.py`, `desktop_app.py`
- Verified: pytest `test_wipe_clips.py` + `test_timeline.py` — 9 passed.

### 2026-09-24
- Changed: Left socials sit below the hook line on every aspect ratio (tall sources no longer kiss the overlay). Health cut `8s-social-down`.
- Files: `layout.py`, `health.py`, `desktop_app.py`, `test_hooks.py`, `test_layout_canvas.py`
- Verified: pytest hooks + layout_canvas — 12 passed.

### 2026-09-24
- Changed: Removed hook-first jump cuts. The file starts on `hook_at` and plays forward in source order. Overlay hook text still stays the whole clip. Health cut `8s-start-hook`.
- Files: `timeline.py`, `bounds.py`, `runner.py`, `health.py`, `desktop_app.py`
- Verified: pytest timeline/editorial/hooks/layout_canvas/phase6 — 50 passed.

### 2026-09-24
- Removed: Dead Phase-4 `select_clips`, caption/reframe stub providers, wipe-test-accounts script, unused SRT/`force_style` helpers, leftover `/favorites` `/trash` routes. Renamed live HTTP client `hermes.py` → `chat.py` (`ChatAIProvider`). Caption tests assert ASS, not SRT.
- Files: `chat.py`, `factory.py`, `provider.py`, `classic.py`, `styles.py`, `layout.py`, `App.tsx`, `ProjectDetailPage.tsx`, `test_phase4.py`, `test_phase6.py`, `test_fallback.py`
- Verified: `py -3 -m pytest` timeline/fallback/phase4/editorial/hooks/layout_canvas/phase6 — 66 passed.

### 2026-09-24
- Changed: Generated clips are numbered in order (`01 - hook.mp4`). The workbench shows `1. …` and downloads/zip copies use that prefix so Explorer sorts 1, 2, 3.
- Files: `paths.py`, `runner.py`, `clips.py`, `api.py` schema, `ProjectDetailPage.tsx`, `LibraryPage.tsx`

### 2026-09-24
- Changed: Hook dropped to y=252 so it clears LIVE / For You / search. Health cut `8s-hook-under`.
- Files: `layout.py`, `health.py`, `desktop_app.py`

### 2026-09-24
- Changed: Hook is larger (up to 88px, one line) and sits at y=168 so the phone header does not crop it. Socials shift ~12px right. Health cut `8s-hook-big`.
- Files: `layout.py`, `health.py`, `desktop_app.py`

### 2026-09-24
- Fixed: Hook-first footage — invalid `hook_at` no longer clamped into a fake middle cut; window-local stamps are shifted onto the source timeline; FFmpeg slices use accurate `-ss` after `-i` with ordered `part_000` concat. Health cut `8s-hook-tl`.
- Files: `timeline.py`, `engine.py`, `ffmpeg.py`, `health.py`, `desktop_app.py`
- Verified: timeline cases (middle / near-start / exact start / near-end / outside / none).

### 2026-09-24
- Changed: Hook in the 112px top bar is nudged down 10px toward the picture. Health cut `8s-hook-down`.
- Files: `layout.py`, `health.py`, `desktop_app.py`

### 2026-09-24
- Fixed: One layout system for every source ratio. Source is fitted (no crop/stretch) into 1080×1808 under a 112px hook bar. Hook is centered in that bar. Captions use PlayRes 1080×1920 and a fixed MarginV of 420. Socials sit on the fitted picture, clamped to TikTok safe zones. Health cut `8s-fixed-canvas`.
- Files: `layout.py`, `ffmpeg.py`, `runner.py`, `classic.py`, `styles.py`, `health.py`, `desktop_app.py`
- Verified: layout canvas tests for 7 ratios plus hook/timeline/phase6/branding.

### 2026-09-24
- Fixed: Phone TikTok safe area — socials inset so tall screens do not crop them off the left; captions sit above the username/tab bar (not the PC window bottom). Health cut `8s-phone-safe`.
- Files: `layout.py`, `classic.py`, `styles.py`, `health.py`, `desktop_app.py`
- Verified: hook/social/caption geometry tests.

### 2026-09-23
- Fixed: 9:16 TikTok canvas fits any source ratio. Small 112px hook bar. Hook hugs the real picture. Captions stay near the bottom of the phone (not the middle of a letterboxed clip). Health cut `8s-fit-tt`.
- Files: `layout.py`, `ffmpeg.py`, `health.py`, `desktop_app.py`
- Verified: wide vs tall hook/caption tests; phase6 pad.

### 2026-09-23
- Changed: Social handles sit vertically centered on the icons. Captions sit a little above TikTok's bottom chrome, slightly larger, white/yellow with a black outline, and cover the spoken words. Health cut `8s-cap-up`.
- Files: `ffmpeg.py`, `layout.py`, `classic.py`, `styles.py`, `health.py`, `desktop_app.py`
- Verified: hook/caption geometry tests; timeline punch; phase6 style.

### 2026-09-23
- Fixed: Hook-first cuts play at normal speed (slice+concat, no fps squeeze). No footer bar. Smaller top hook bar. Socials stack on the far left of the picture. Captions stay on the bottom of the video. Project clip list only shows cuts from the current video. Health cut `8s-left-stack`.
- Files: `layout.py`, `ffmpeg.py`, `runner.py`, `clips.py`, `jobs.py`, `health.py`, `desktop_app.py`
- Verified: layout/hook tests; concat render; phase6 scale.

### 2026-09-23
- Fixed: A new video on a project replaces the previous file. Generate hides the last run's clips from the workbench (they stay in Library) so old cuts are not shown as this video's clips. Health cut `8s-one-source`.
- Files: `import_video.py`, `runner.py`, `ProjectDetailPage.tsx`, `health.py`, `desktop_app.py`
- Verified: source-replace unit path; hide clips helper.

### 2026-09-23
- Changed: The hook line stays in the top bar for the whole clip. Hook-first is only the footage cut. Health cut `8s-hook-stay`.
- Files: `runner.py`, `health.py`, `desktop_app.py`
- Verified: runner no longer times out the hook overlay.

### 2026-09-23
- Changed: Clips open on ~1.6s of the hook, then hard-cut into the thought (no repeat of that open). Hook box only on the open. Captions (ASS, last word yellow) start after. Sidecar files are `clip_{id}.ass` so apostrophes do not break FFmpeg. Pass 6 keeps the thought start; `hook_at` is only for the reorder. Zoom and music still off. Health cut `8s-hook-first`.
- Files: `timeline.py`, `ffmpeg.py`, `classic.py`, `bounds.py`, `runner.py`, `health.py`, `desktop_app.py`
- Verified: timeline + editorial + hook tests; phase6 render.

### 2026-09-23
- Changed: Picture is taller (1544px). Hook stays in the top bar. Captions sit on the video. Footer is a 96px socials strip. Health cut `8s-big-frame` so the desktop shortcut loads this backend.
- Files: `layout.py`, `health.py`, `desktop_app.py`
- Verified: branding + phase6 scale tests; caption above footer.

### 2026-09-23
- Fixed: Clipping progress updates before each cut so the loader is not stuck at 0/N. N is a max; some candidates are dropped or fail to cut.
- Files: `runner.py`, `job.ts`
- Verified: label regex; runner message order.

### 2026-09-23
- Fixed: Lower captions sit on the bottom edge of the picture again (not the middle, not the footer).
- Files: `layout.py`, `styles.py`
- Verified: caption_margin_v for 9:16 ≈ 56.

### 2026-09-23
- Fixed: Captions are lower-bar again (Alignment=2). The top-pin put them in the middle of the frame.
- Files: `styles.py`, `layout.py`
- Verified: subtitle style tests.

### 2026-09-23
- Fixed: Lower captions no longer jump up into the picture when a cue is longer. The block is pinned under the video and extra words grow down.
- Files: `styles.py`, `layout.py`
- Verified: subtitle style tests.

### 2026-09-23
- Fixed: Opening a project crashed with Internal Server Error because clip listing used `json` after that import was removed.
- Files: `clips.py`
- Verified: list_projects + list_clips against the local DB.

### 2026-09-23
- Fixed: Project Download saves selected clips into that project's `downloads` folder (and opens it on Windows). Edge app mode was swallowing the fake browser zip save.
- Files: `clips.py`, `api.ts`, Project/Library pages
- Verified: downloads folder name test; frontend build.

### 2026-09-23
- Fixed: Hook overlay is one line, fully above the picture (no two-line overlap). Social tags use visible platform marks as a bottom footer; if Picture has no file, ticked socials still burn.
- Files: `layout.py`, `ffmpeg.py`, `icons.py`, `normalize.py`, `runner.py`
- Verified: hook layout + icon tests.

### 2026-09-23
- Changed: Overlay hooks shrink/wrap so they are not cut off the 1080 frame. Overlay swears are masked (`f*ck`); captions stay exact speech. Generate clip cards are square previews with a stacked details block.
- Files: `layout.py`, `ffmpeg.py`, `ProjectDetailPage.tsx`, `app.css`
- Verified: hook layout tests; frontend build.

### 2026-09-23
- Changed: Hook overlay is editorial: quote when the spoken line already hooks, rephrase when it needs a tease. Captions stay exact speech.
- Files: `prompts.py`
- Verified: prompt wording.

### 2026-09-23
- Changed: On-screen hooks are a clean catchy tease (curiosity-gap allowed, grounded in speech). No commas/periods/slashes. No 28-character mid-sentence chop.
- Files: `layout.py`, `prompts.py`
- Verified: hook cleaning tests.

### 2026-09-23
- Changed: Replaced editorial system prompts with the tighter editor brief (duration is a target not a pad, viral is not a performance guess, empty windows allowed, Pass 4/5 keep useful non-funny clips).
- Files: `prompts.py`
- Verified: prompts import.

### 2026-09-23
- Changed: Editorial prompts think like a senior short-form editor (hook → build → payoff). Clips can be mixed vibes (1–3). Ticked kinds are an include list: one of them or several of them.
- Files: `prompts.py`, `vibes.py`, `engine.py`, `clips.py`, clip tiles
- Verified: pytest editorial + library; `npm run build`.

### 2026-09-23
- Added: Multi-select vibe chips on Generate (kinds to hunt) and Library (kinds to show). None ticked means all. Stored on the project in `branding.vibes`.
- Files: `vibes.py`, `engine.py`, `prompts.py`, `clips.py`, `normalize.py`, `runner.py`, `VibeChips.tsx`, `ProjectDetailPage.tsx`, `LibraryPage.tsx`
- Verified: pytest branding + editorial + library; `npm run build`.

### 2026-09-23
- Changed: Clip vibe tags now include informative, financial, and lifestyle (plus the existing funny/sad/viral set).
- Files: `clips.py`, `prompts.py`, `hermes.py`
- Verified: pytest library.

### 2026-09-22
- Fixed: Hook and captions sit on the real video edges (not the 1220 slot). Picture footer fills the gap under the caption. Hook is Impact in a white box; captions stay Arial. 8s is a minimum — continuing speech grows toward ~15s so clips are not all 8s.
- Files: `layout.py`, `ffmpeg.py`, `styles.py`, `bounds.py`, `prompts.py`, `ProjectDetailPage.tsx`
- Verified: pytest branding + editorial + letterbox; `npm run build`.

### 2026-09-22
- Changed: Picture footer is the same size band as socials (560×72 at the bottom), not a tall 360px banner.
- Verified: overlay size in `runner.py`; pytest branding.

### 2026-09-22
- Changed: Footer is Socials (icons in a row at the bottom) or Picture (full image under the captions). Picture is fitted, not cropped. Uploading a picture sets footer to picture.
- Files: `normalize.py`, `runner.py`, `ffmpeg.py`, `projects.py`, `ProjectDetailPage.tsx`, `app.css`
- Verified: pytest branding + letterbox; `tsc --noEmit`; `npm run build`.

### 2026-09-22
- Changed: Hook is 76px, boxed, sitting just above the picture. Captions are one line and sit just under the picture. Hook is larger than captions.
- Verified: pytest caption style + letterbox.

### 2026-09-22
- Fixed: Desktop shortcut restarts the API so Generate is not stuck on an old uvicorn. Clips fit into a 1080×1220 picture with 280px top / 420px bottom bars, hook text, 8s minimum at cut.
- Verified: pytest branding + letterbox.

### 2026-09-22
- Fixed: Clips must be at least 8 seconds when cutting (not only in the prompt). Auto face crop is removed — the full frame is fitted into 1080×1920 with black bars. Hook text and social icons always burn if socials are checked.
- Verified: pytest branding + letterbox; `tsc --noEmit`.

### 2026-09-22
- Changed: Project socials are three small filter rows with the supplied YouTube/Instagram/TikTok icons (same files burned on clips). Custom logo is a fourth compact row.
- Verified: `pytest` branding; `tsc --noEmit`; `npm run build`.

### 2026-09-22
- Changed: Generate loading is bouncing dots (project page + sidebar). Reduced motion uses a fade, not a frozen ring.
- Verified: `tsc --noEmit`; `npm run build`.

### 2026-09-22
- Changed: Clip tiles and Library show the AI vibe chip (funny, sad, viral, …) from saved signals. Selection logic unchanged.
- Changed: Finished clips are at least 8 seconds. Shorter hits expand forward (then back if the file ends); sources under 8s produce no clip.
- Changed: Clips render as 9:16 with black bars. Hook text on the top bar. Existing captions on the bottom bar. Project socials (YouTube/TikTok/Instagram, optional custom logo) burn bottom-left.
- Changed: Editorial ranking prefers a strong opening hook; clips start on the hook, not a long setup.
- Verified: pytest including letterbox render + branding; `tsc --noEmit`.

### 2026-09-22
- Changed: Phase 10 desktop app — FastAPI serves the built UI; Desktop shortcut `ViralClipper.lnk` opens Edge app mode. `scripts/desktop_app.py`, `scripts/ViralClipper.bat`.
- Verified: pytest including SPA fallback; `npm run build`; shortcut on the Desktop.

### 2026-09-22
- Changed: API page filters are a compact row: All APIs, groq, gemini, openrouter. Request totals stay on the Requests card.
- Fixed: Generate keeps running after you leave the project page (own thread, not tied to the HTTP request). Sidebar shows Generating until it finishes.
- Changed: API page log starts minimized with Expand. Reset on the API page and Watch API dock clears recorded usage (`DELETE /api/usage`).
- Changed: API 1h request chart fills the card and labels ticks with the PC's local clock (`at` timestamps).
- Changed: Deleting clips on a project (or deleting the project) leaves them in Library. Library delete removes the files from ViralClipper. Project folders still hold that project's current clips.
- Verified: pytest clip-library + usage; `tsc --noEmit`.
- Fixed: Clip delete no longer 500s when Windows still has the mp4 open in the player. Preview is released first; unlink retries.
- Changed: API request graph is a 1-hour line chart. Dashboard clip counts use files on disk and refresh; deleting clips is logged in activity. Recent project cards no longer sit against the API log.
- Fixed: Whisper sidecar no longer sends audio through PyAV (that crashed with an empty error). It reads the 16 kHz WAV directly. Generate transcribes in 2-minute slices again.
- Fixed: Re-uploading the same file on a project reuses the existing source instead of “already imported”. Deleting a project removes its DB rows and `projects/{id}_*` folders so a new project can use that video again. Dummy/test projects, clips, and leftover accounts were wiped; only Workspace remains.
- Changed: API usage monitor from recorded chat calls (not a hardcoded model list). Sidebar API page has request counts, 24h bars, per-provider and per-model views, live provider/model. Dashboard shows API logs plus Monitor. Project Watch API docks a side panel. `GET /api/usage`.
- Verified: `tests/test_usage.py` + library; `tsc --noEmit`; dashboard API log, `/usage`, project Watch API dock (no overlay). Empty until Generate records calls.
- Changed: Library is a filter bar plus aligned clip rows. One-click Hook tag. Editorial `hook_at` is stored and shown.
- Changed: After a project has a video, the big choose-file box is gone. Add sits next to Delete project. Empty projects still use the dropzone.
- Changed: Phase 8 auto-reframe — sample frames, OpenCV Haar faces on CPU (3.12 Whisper sidecar; app 3.13t has no wheel), 9:16 FFmpeg crop then scale 1080×1920. No face → center crop. Project option Auto vs Center. New projects default Auto. GTX 960 is not used for tracking.
- Changed: Dashboard activity is a one-line event log; nested project cards are black.
- Changed: Creating a project makes a folder under `projects/` on disk; clips and bulk downloads are stored there. Clip tiles support multi-select plus bulk download/delete.
- Changed: Phase 7 caption looks — classic, bold, or boxed; optional burned-off. Existing clips keep their files until the next Generate.
- Changed: Clip tiles and library list show source in/out times and sort by timeline.

### 2026-09-21
- Changed: Reuse the last model that succeeded until it 429s, then the next model on that same provider.
- Changed: On 429, cool that model for 2 minutes with no wait, then try the next model on the same provider. Chat timeout is 35s. Editorial batch pauses are 0.25s.
- Changed: Pass 4 no longer rejects clips for scores below 0.75. Invalid clips only (duplicate moment, dead air, unusable fragment, no content, bad times). Pass 5 ranks by quality and applies the user ceiling.
- Changed: Sparse Pass 1 windows now send adjacent transcript as context while keeping window time bounds. Whisper sidecar sets `condition_on_previous_text=False`. Per-window discovery logging added.
- Changed: If a model errors (HTTP, timeout, bad JSON, 429), Generate jumps to the next model and later windows. The job does not abort unless no API keys are set.
- Changed: Fallback order is Groq (`openai/gpt-oss-120b`) → Gemini → GLM → other OpenRouter free models.
- Changed: Six-pass editorial pipeline (discover → expand → pool → validate → select → word bounds) with GLM 5.2. Dynamic clip count; `clip_count` is an optional max. No midpoint duration fit. No clips until after selection.
- Verified: pytest including editorial unit tests and generate-on-silent-fixture 0 clips.
- Changed: Editor prompt no longer asks the model to tile a window into many timed cuts.
- Changed: Stop button on Generate. Cancels the in-flight job instead of waiting on OpenRouter.
- Verified: pytest phase2/4/6 after the runner rewrite.


- Fixed: High-score moments shorter than the min length were discarded as 0 clips. Clip length is 10–20s; shorter hits expand to 10s.
- Changed: Project delete now removes sources/jobs/clips on disk and in SQLite. Tests use a separate database so pytest leftovers stop filling the app.
- Fixed: Hermes 200 responses that are not a plain `message.content` string no longer abort Generate. UTF-8 Whisper stdout.
- Changed: Remove or replace a project’s source video. New upload replaces the old file; generate uses the latest source.
- Fixed: Duration display includes hours. The “1 hour” YouTube file on disk is ~5.5 minutes / 63 MB — the title is not the length.

### 2026-09-20
- Changed: Phase 6 — cut scored moments to 9:16 mp4 with classic burned captions; download when `has_file`.
- Verified: pytest render writes 1080×1920 from tiny.mp4; silent generate still completes with 0 clips.

### 2026-09-20
- Fixed: Whisper sidecar was missing `requests`, so Generate failed on import. Installed it; first real transcribe may download the `tiny` model.

### 2026-09-20
- Changed: Phase 4/5 — Hermes proxy scores transcript windows; validate JSON; quality threshold + overlap; persist `pending_render` clips with no fake video files.
- Verified: pytest parse/select/windows + generate on silent fixture completes with 0 clips (not padded).

### 2026-09-20
- Changed: Phase 3 transcription — FFmpeg wav extract, faster-whisper CPU `tiny`, cached transcript JSON, empty transcript when there is no audio. Generate still does not invent clips (Phase 4 AI next).
- Verified: pytest including generate job writing an analysis transcript and failing honestly after transcription.

### 2026-09-20
- Changed: Left sidebar restored. Project list and workbench use the full remaining width; other pages stay in the 960px column.
- Changed: Project workbench — create by name only, drop video, choose clip count + style (funny etc.), show AI pipeline progress, download original and future clips.
- Changed: Generate job runner is honest: stops at transcription with no fake clips.
- Verified: pytest including generate-without-video 400 and post-import job FAILED with empty clip list.
- Follow-up: Phase 3 Whisper still in `docs/TODO.md`

### 2026-09-20
- Changed: Removed manual Phase 1 test accounts (`Test`, `Business TikTok`).
- Changed: Phase 2 video import — hash, ffprobe metadata, thumbnail, duplicate detection, drag/drop UI on project detail.
- Verified: pytest 4 passed (including import + duplicate hash + reject non-video).
- Follow-up: Phase 3 in `docs/TODO.md`

### 2026-09-20
- Changed: Installed agent OS (skills already copied), always-apply skill rule, retargeted AGENTS.md and platform-expert away from Shopify, wrote project-memory docs from spec + env inspect.
- Changed: Phase 1 foundation — FastAPI, SQLite models, account/project APIs, React dark shell.
- Verified: pytest 2 passed; API `/health` 200; UI at `http://127.0.0.1:5173` (dashboard, accounts, projects); account+project created via local API and visible in the Accounts list.
- Follow-up: Phase 2 in `docs/TODO.md`
