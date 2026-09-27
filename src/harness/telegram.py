"""Optional owner-only Telegram long-polling adapter (text messages only)."""

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen


class TelegramError(RuntimeError):
    """Sanitized Telegram transport/configuration failure."""


Transport = Callable[[Request, float], bytes]


def _urlopen(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def owner_ids_from_environment() -> frozenset[int]:
    raw = os.environ.get("HARNESS_TELEGRAM_OWNER_IDS", "")
    try:
        values = frozenset(int(item.strip()) for item in raw.split(",") if item.strip())
    except ValueError:
        raise ValueError("HARNESS_TELEGRAM_OWNER_IDS must be comma-separated numeric user IDs") from None
    if not values or any(value <= 0 for value in values):
        raise ValueError("a positive Telegram owner user ID allowlist is required")
    return values


def telegram_from_environment() -> "TelegramClient":
    if os.environ.get("HARNESS_TELEGRAM_ENABLED", "").strip().casefold() != "true":
        raise ValueError("Telegram adapter is disabled; explicitly set HARNESS_TELEGRAM_ENABLED=true")
    token = os.environ.get("HARNESS_TELEGRAM_BOT_TOKEN", "")
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", token):
        raise ValueError("HARNESS_TELEGRAM_BOT_TOKEN is missing or malformed")
    return TelegramClient(token=token)


@dataclass
class TelegramClient:
    """Bot API client; token is held only in memory and errors are redacted."""

    token: str = field(repr=False)
    transport: Transport = _urlopen
    request_timeout: float = 35.0

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", self.token):
            raise ValueError("Telegram bot token is malformed")

    def _call(self, method: str, params: dict[str, object]) -> dict[str, object]:
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        request = Request(
            url,
            data=json.dumps(params).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            payload = json.loads(self.transport(request, self.request_timeout).decode("utf-8"))
            if not isinstance(payload, dict) or payload.get("ok") is not True:
                raise ValueError
            result = payload.get("result")
            if not isinstance(result, (dict, list)):
                raise ValueError
            return {"result": result}
        except (URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
            # Telegram errors can echo request metadata; never expose them or the URL/token.
            raise TelegramError("Telegram request failed or returned an invalid response") from None

    def get_updates(self, offset: int, poll_seconds: int = 25) -> list[dict[str, object]]:
        if not 0 <= poll_seconds <= 50:
            raise ValueError("poll timeout must be between 0 and 50 seconds")
        result = self._call("getUpdates", {"offset": offset, "timeout": poll_seconds, "allowed_updates": ["message"]})["result"]
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            raise TelegramError("Telegram returned an invalid update list")
        return result

    def send_message(self, chat_id: int, text: str) -> None:
        self._call("sendMessage", {"chat_id": chat_id, "text": text})

    def poll_once(
        self,
        offset: int,
        owner_ids: frozenset[int],
        dispatch: Callable[[str], str],
        poll_seconds: int = 25,
    ) -> int:
        """Process one batch; reject non-allowlisted users before dispatch."""

        next_offset = offset
        for update in self.get_updates(offset, poll_seconds):
            update_id = update.get("update_id")
            if not isinstance(update_id, int):
                continue
            next_offset = max(next_offset, update_id + 1)
            message = update.get("message")
            if not isinstance(message, dict):
                continue
            sender = message.get("from")
            chat = message.get("chat")
            text = message.get("text")
            if not isinstance(sender, dict) or not isinstance(chat, dict) or not isinstance(text, str):
                continue
            user_id, chat_id = sender.get("id"), chat.get("id")
            if not isinstance(user_id, int) or isinstance(user_id, bool) or not isinstance(chat_id, int):
                continue
            if chat.get("type") != "private" or chat_id != user_id:
                continue
            if user_id not in owner_ids:
                self.send_message(chat_id, "Access denied.")
                continue
            try:
                response = dispatch(text)
            except Exception:
                # Avoid bubbling user text, provider bodies, or exception details into logs.
                response = "The assistant is temporarily unavailable. Please try again later."
            if isinstance(response, str) and response:
                self.send_message(chat_id, response[:4096])
        return next_offset


def poll_forever(client: TelegramClient, owner_ids: frozenset[int], dispatch: Callable[[str], str]) -> None:
    offset = 0
    while True:
        offset = client.poll_once(offset, owner_ids, dispatch)
        # Avoid a tight loop if Telegram returns immediately with an empty batch.
        time.sleep(0.1)
