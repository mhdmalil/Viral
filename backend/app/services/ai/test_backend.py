from __future__ import annotations

from typing import Any

from app.services.ai.provider import AIProvider


class TestAIProvider(AIProvider):
    """Deterministic editor for pytest. Does not call the live AI API."""

    def editor_json(self, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        del system
        kind = str(payload.get("pass") or "")
        if kind == "discovery":
            text = str(payload.get("transcript") or payload.get("context_transcript") or "").strip()
            if not text and not payload.get("has_speech"):
                return {"candidates": []}
            start = float(payload.get("window_start") or 0)
            end = float(payload.get("window_end") or start + 12)
            return {
                "candidates": [
                    {
                        "start": start,
                        "end": end,
                        "score": 0.88,
                        "hook_score": 0.9,
                        "hook_at": start,
                        "hook_line": " ".join(text.split()[:6]) or "test hook",
                        "reason": "test discovery",
                        "topic": "test",
                        "vibe": "viral",
                    }
                ]
            }
        if kind == "expand":
            results = []
            for item in payload.get("items") or []:
                if not isinstance(item, dict):
                    continue
                results.append(
                    {
                        "id": item.get("id"),
                        "action": "keep",
                        "start": item.get("start"),
                        "end": item.get("end"),
                        "setup_start": item.get("start"),
                        "hook_at": item.get("start"),
                        "hook_line": "test hook",
                        "hook_score": 0.9,
                        "payoff_end": item.get("end"),
                        "standalone": True,
                        "reason": item.get("reason") or "test expand",
                    }
                )
            return {"results": results}
        if kind == "validate":
            results = []
            for item in payload.get("items") or []:
                if not isinstance(item, dict):
                    continue
                results.append(
                    {
                        "id": item.get("id"),
                        "verdict": "keep",
                        "quality": 0.9,
                        "reason": item.get("reason") or "test validate",
                    }
                )
            return {"results": results}
        if kind == "select":
            ids = [item.get("id") for item in payload.get("cards") or [] if isinstance(item, dict)]
            return {"keep_ids": ids}
        return {}
