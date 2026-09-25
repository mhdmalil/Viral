# TODO

## Deferred From Recent Work
- [x] Phase 2 — video import, hash, thumbnails
- [x] Phase 3 — job worker + transcription
- [x] Phase 4 — viral candidate engine (OpenRouter HTTP, not Ollama / not Hermes proxy)
- [x] Phase 5 — selection, overlap, quality threshold (light pass with Phase 4)
- [x] Phase 6 — FFmpeg render + first burned captions
- [x] Phase 7 — extra caption styles (classic / bold / boxed, position, optional off)
- [x] Phase 8 — real auto-reframe
- [x] Phase 9 — library search/filters/tags (no Trash)
- [x] Phase 10 — Desktop shortcut + Edge app window (not a packed .exe)

## Known Gaps / Risks Not Yet Addressed
- [x] Tight talking-head cuts: project edit note, drop ums/gaps in source order, cutaway from another shot in the same file, one grade. Music and zoom stay off.
- [ ] Zoom / Ken Burns on the picture (not in this cut)
- [ ] Music bed (not in this cut)
- [ ] Pin `AI_MODEL` to one OpenRouter id if `openrouter/free` scores jump around
- [ ] Hermes agent later for auto-post (not used for scoring)
- [x] GTX 960 4GB: auto-reframe is CPU Haar (OpenCV), not GPU tracking. Whisper stays CPU.
- [x] **Speed:** Live Groq/Gemini ids, skip 404/429 immediately, rotate inside provider, 20s timeout, skip VL OpenRouter ids.
- [x] Stream generate (chunk → edit → send → continue) instead of full-file batch
- [x] Six-pass global editorial pipeline; dynamic clip count; Pass 4 invalid-only

## Nice-to-Haves (explicitly not urgent)
- [x] Clip count N is a ceiling (quality-first; never pad)
