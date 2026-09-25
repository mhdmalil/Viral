from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.core.config import settings
from app.services.ai.parse import CandidateParseError, parse_json_object
from app.services.ai.provider import AIProvider
from app.services.jobs.control import JobCancelled, raise_if_cancelled

logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    fatal = True


class AIPayloadError(AIProviderError):
    fatal = False


CHAT_TIMEOUT = 20.0
MODEL_COOLDOWN_SECONDS = 120.0
_model_cooldown_until: dict[tuple[str, str], float] = {}
_missing_models: set[tuple[str, str]] = set()
_last_ok: tuple[str, str] | None = None


def retry_after_seconds(response: httpx.Response, attempt: int) -> float:
    raw = response.headers.get("retry-after") or response.headers.get("Retry-After")
    if raw:
        try:
            return min(45.0, max(8.0, float(raw)))
        except ValueError:
            pass
    return min(45.0, 15.0 + attempt * 8.0)


def _model_cooling(provider: str, model: str) -> bool:
    until = _model_cooldown_until.get((provider, model), 0.0)
    return until > time.monotonic()


def _cool_model(provider: str, model: str) -> None:
    _model_cooldown_until[(provider, model)] = time.monotonic() + MODEL_COOLDOWN_SECONDS


def chat_completions_url(base: str) -> str:
    root = (base or "").strip().rstrip("/")
    if not root:
        raise AIProviderError("Set AI_API_BASE_URL in .env.")
    if root.endswith("/chat/completions"):
        return root
    return f"{root}/chat/completions"


def parse_response_json(raw: str) -> Any:
    text = (raw or "").strip()
    if not text:
        raise AIPayloadError("AI API returned an empty body.")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        index = 0
        last: Any = None
        while index < len(text):
            while index < len(text) and text[index].isspace():
                index += 1
            if index >= len(text):
                break
            try:
                obj, end = decoder.raw_decode(text, index)
            except json.JSONDecodeError:
                break
            last = obj
            index = end
        if last is None:
            raise AIPayloadError("AI API returned an unexpected payload.")
        return last


def _flatten_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
        return "".join(parts)
    return str(content)


def assistant_text(data: Any) -> str:
    if isinstance(data, str):
        return data
    if not isinstance(data, dict):
        raise AIPayloadError("AI API returned an unexpected payload.")
    if data.get("error"):
        raise AIProviderError("AI API rejected the scoring request.")
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0] if isinstance(choices[0], dict) else {}
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        text = _flatten_content(message.get("content"))
        if not text.strip():
            text = _flatten_content(message.get("reasoning_content"))
        if not text.strip():
            text = _flatten_content(choice.get("text"))
        if not text.strip():
            delta = choice.get("delta") if isinstance(choice.get("delta"), dict) else {}
            text = _flatten_content(delta.get("content"))
        if text.strip():
            return text
    for key in ("output_text", "output", "content", "response"):
        text = _flatten_content(data.get(key))
        if text.strip():
            return text
    logger.warning("AI API payload keys=%s", sorted(str(k) for k in data.keys()))
    raise AIPayloadError("AI API returned an unexpected payload.")


class ChatAIProvider(AIProvider):
    """OpenAI-compatible chat completions (Groq, Gemini, OpenRouter). Config is .env only."""

    def editor_json(self, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        user = "JSON object only. No markdown.\n" + json.dumps(payload, ensure_ascii=False)
        for _attempt in range(2):
            try:
                content = self.complete_chat(system, user)
                return parse_json_object(content)
            except JobCancelled:
                raise
            except AIPayloadError as exc:
                last_error = exc
                logger.info("AI payload unusable; retrying editor call once")
                continue
            except CandidateParseError as exc:
                last_error = exc
                logger.info("AI JSON invalid; retrying editor call once")
                continue
            except AIProviderError as exc:
                if str(exc).startswith("Set "):
                    raise
                last_error = exc
                logger.info("All models failed this editor call; caller continues")
                break
        if last_error is not None:
            logger.info("AI editor call dropped after retries: %s", last_error)
        return {}

    def complete_chat(self, system: str, user: str) -> str:
        global _last_ok
        from app.services.ai.routing import any_chat_key, iter_chat_targets
        from app.services.ai.usage import limits_from_headers, record, set_live

        if not any_chat_key():
            raise AIProviderError("Set AI_API_KEY, GEMINI_API_KEY, or GROQ_API_KEY in .env.")
        catalog = self._openrouter_catalog()
        headers_base = {
            "Content-Type": "application/json",
            "HTTP-Referer": "http://127.0.0.1:5173",
            "X-Title": "ViralClipper",
        }
        skip_providers: set[str] = set()
        last_error = "All editorial models failed."
        prefer = _last_ok
        for target in iter_chat_targets(catalog_ids=catalog, prefer=prefer):
            raise_if_cancelled()
            stamp = (target.provider, target.model)
            if target.provider in skip_providers or stamp in _missing_models or _model_cooling(
                target.provider, target.model
            ):
                continue
            url = chat_completions_url(target.base_url)
            body = {
                "model": target.model,
                "temperature": 0.25,
                "max_tokens": 4096,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
            headers = {**headers_base, "Authorization": f"Bearer {target.api_key}"}
            set_live(target.provider, target.model)
            t0 = time.perf_counter()
            last_status = 0
            response: httpx.Response | None = None
            try:
                response = httpx.post(url, headers=headers, json=body, timeout=CHAT_TIMEOUT)
            except JobCancelled:
                raise
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError, OSError) as exc:
                last_error = f"{target.provider} request failed."
                record(
                    provider=target.provider,
                    model=target.model,
                    outcome="timeout" if isinstance(exc, httpx.TimeoutException) else "error",
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                )
                logger.info(
                    "Chat failed for %s %s (%s); next model",
                    target.provider,
                    target.model,
                    type(exc).__name__,
                )
                continue
            except Exception as exc:
                if isinstance(exc, JobCancelled):
                    raise
                last_error = f"{target.provider} request failed."
                record(
                    provider=target.provider,
                    model=target.model,
                    outcome="error",
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                )
                logger.info(
                    "Chat failed for %s %s (%s); next model",
                    target.provider,
                    target.model,
                    type(exc).__name__,
                )
                continue
            last_status = response.status_code
            remaining, limit = limits_from_headers(response.headers)
            elapsed = int((time.perf_counter() - t0) * 1000)
            raise_if_cancelled()
            if last_status == 429:
                last_error = f"{target.provider} rate-limited {target.model}."
                record(
                    provider=target.provider,
                    model=target.model,
                    outcome="429",
                    http_status=429,
                    latency_ms=elapsed,
                    remaining=remaining,
                    limit=limit,
                )
                logger.info(
                    "HTTP 429 from %s %s; next model on this provider",
                    target.provider,
                    target.model,
                )
                _cool_model(target.provider, target.model)
                continue
            if last_status in {401, 403}:
                record(
                    provider=target.provider,
                    model=target.model,
                    outcome="auth",
                    http_status=last_status,
                    latency_ms=elapsed,
                    remaining=remaining,
                    limit=limit,
                )
                logger.info("Auth rejected for %s; skipping that provider", target.provider)
                skip_providers.add(target.provider)
                last_error = f"{target.provider} API key was rejected."
                continue
            if last_status == 404:
                record(
                    provider=target.provider,
                    model=target.model,
                    outcome="404",
                    http_status=404,
                    latency_ms=elapsed,
                    remaining=remaining,
                    limit=limit,
                )
                logger.info("No model %s on %s; next model", target.model, target.provider)
                _missing_models.add(stamp)
                last_error = f"{target.provider} has no model {target.model}."
                continue
            if last_status >= 400:
                record(
                    provider=target.provider,
                    model=target.model,
                    outcome="error",
                    http_status=last_status,
                    latency_ms=elapsed,
                    remaining=remaining,
                    limit=limit,
                )
                logger.warning("%s %s HTTP %s", target.provider, target.model, last_status)
                last_error = f"{target.provider} rejected {target.model}."
                continue
            try:
                data = parse_response_json(response.text)
                text = assistant_text(data)
            except (AIProviderError, KeyError, IndexError, TypeError, json.JSONDecodeError):
                record(
                    provider=target.provider,
                    model=target.model,
                    outcome="error",
                    http_status=last_status,
                    latency_ms=elapsed,
                    remaining=remaining,
                    limit=limit,
                )
                last_error = f"{target.provider} returned an unexpected payload."
                logger.info("Bad payload from %s %s", target.provider, target.model)
                continue
            record(
                provider=target.provider,
                model=target.model,
                outcome="ok",
                http_status=last_status,
                latency_ms=elapsed,
                remaining=remaining,
                limit=limit,
            )
            logger.info("Editor using %s %s", target.provider, target.model)
            _last_ok = stamp
            return text
        raise AIProviderError(last_error)

    def _openrouter_catalog(self) -> list[str]:
        from app.services.ai.routing import fetch_openrouter_free_ids

        cached = getattr(ChatAIProvider, "_or_free", None)
        if cached is None:
            skip = {(settings.ai_model or "").strip()}
            ChatAIProvider._or_free = fetch_openrouter_free_ids(skip)
        return list(ChatAIProvider._or_free)
