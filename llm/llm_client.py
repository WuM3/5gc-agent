from __future__ import annotations

import os
from typing import Any, Callable

from agent.schemas import LLMResult
from config import load_env_file


class LLMClient:
    def __init__(self, post: Callable[..., Any] | None = None):
        if post is None:
            import requests

            post = requests.post
        self._post = post

    def generate(self, prompt: str) -> LLMResult:
        load_env_file()
        provider = os.getenv("LLM_PROVIDER", "openai_compatible").strip().lower()
        if provider == "offline":
            return LLMResult(content="", mode="offline", error="LLM provider is offline")
        if provider != "openai_compatible":
            return LLMResult(
                content="",
                mode="offline",
                error=f"Unsupported LLM_PROVIDER: {provider}",
            )

        api_key = (os.getenv("LLM_API_KEY") or "").strip()
        if not api_key:
            return LLMResult(content="", mode="offline", error="Missing LLM_API_KEY")

        try:
            timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
        except ValueError as exc:
            return LLMResult(
                content="",
                mode="offline",
                error=f"Invalid LLM_TIMEOUT_SECONDS: {exc}",
            )

        base_url = (
            os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").strip()
            or "https://api.openai.com/v1"
        ).rstrip("/")
        model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

        try:
            response = self._post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a 5G Core troubleshooting assistant. "
                                "Generate concise, actionable diagnostic reports."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                },
                timeout=timeout,
            )
            if hasattr(response, "raise_for_status"):
                try:
                    response.raise_for_status()
                except Exception as exc:
                    body = getattr(response, "text", "")
                    detail = f"{exc}; response={body[:500]}" if body else str(exc)
                    return LLMResult(content="", mode="offline", error=detail)
            data = response.json()
            choices = data.get("choices") if isinstance(data, dict) else None
            if not choices:
                return LLMResult(
                    content="",
                    mode="offline",
                    error="LLM response has no choices; check model id, quota, or provider compatibility",
                )
            message = choices[0].get("message", {})
            content = message.get("content")
            if not content:
                return LLMResult(
                    content="",
                    mode="offline",
                    error="LLM response message has no content; check model id, quota, or provider compatibility",
                )
        except Exception as exc:
            return LLMResult(content="", mode="offline", error=str(exc))

        return LLMResult(content=content, mode="online")
