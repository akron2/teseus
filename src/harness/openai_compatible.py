"""Optional OpenAI-compatible chat-completions adapter using only stdlib HTTP."""

import json
import os
from dataclasses import dataclass, field
from typing import Callable
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .engine import Engine, EngineError, EngineReply, MockEngine

Transport = Callable[[Request, float], bytes]


def _urlopen(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:
        return response.read()


@dataclass(frozen=True)
class OpenAICompatibleEngine:
    """Minimal chat-completions client; neither prompts nor responses are logged."""

    api_key: str = field(repr=False)
    model: str
    base_url: str = "https://api.openai.com/v1"
    timeout: float = 30.0
    transport: Transport = _urlopen

    def __post_init__(self) -> None:
        parsed = urlsplit(self.base_url)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("provider base URL must be an HTTPS origin/path without credentials, query, or fragment")
        if (
            not self.api_key.strip()
            or any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in self.api_key)
            or not self.model.strip()
        ):
            raise ValueError("provider key and model are required")
        if not 0.1 <= self.timeout <= 120:
            raise ValueError("provider timeout must be between 0.1 and 120 seconds")

    def generate(self, text: str, persona_name: str) -> EngineReply:
        endpoint = self.base_url.rstrip("/") + "/chat/completions"
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": f"You are {persona_name}, a personal assistant."},
                    {"role": "user", "content": text},
                ],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            endpoint,
            data=body,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            raw = self.transport(request, self.timeout)
            payload = json.loads(raw.decode("utf-8"))
            result = payload["choices"][0]["message"]["content"]
            if not isinstance(result, str) or not result.strip():
                raise ValueError
            return EngineReply(text=result)
        except (URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
            # Do not attach the transport exception or provider body: either may contain secrets or user content.
            raise EngineError("model provider request failed or returned an invalid response") from None


def engine_from_environment() -> Engine:
    """Select mock by default; configure remote engine exclusively through env."""

    selected = os.environ.get("HARNESS_ENGINE", "mock").strip().casefold()
    if selected == "mock":
        return MockEngine()
    if selected != "openai-compatible":
        raise ValueError("HARNESS_ENGINE must be 'mock' or 'openai-compatible'")
    api_key = os.environ.get("HARNESS_OPENAI_API_KEY", "")
    model = os.environ.get("HARNESS_OPENAI_MODEL", "")
    base_url = os.environ.get("HARNESS_OPENAI_BASE_URL", "https://api.openai.com/v1")
    try:
        timeout = float(os.environ.get("HARNESS_OPENAI_TIMEOUT", "30"))
    except ValueError:
        raise ValueError("HARNESS_OPENAI_TIMEOUT must be a number") from None
    return OpenAICompatibleEngine(api_key=api_key, model=model, base_url=base_url, timeout=timeout)
