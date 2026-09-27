"""Mock-transport tests for the opt-in provider and owner-only Telegram adapters."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from urllib.request import Request

from harness.cli import bootstrap, run_dialogue
from harness.engine import EngineError, MockEngine
from harness.openai_compatible import OpenAICompatibleEngine, engine_from_environment
from harness.telegram import TelegramClient, TelegramError, owner_ids_from_environment, telegram_from_environment


class AdapterTests(unittest.TestCase):
    def test_openai_compatible_request_and_mocked_dialogue_path(self) -> None:
        seen: dict[str, object] = {}

        def transport(request: Request, timeout: float) -> bytes:
            seen["url"] = request.full_url
            seen["authorization"] = request.get_header("Authorization")
            seen["timeout"] = timeout
            seen["body"] = json.loads(request.data.decode("utf-8"))
            return json.dumps({"choices": [{"message": {"content": "SYNTHETIC_PROVIDER_REPLY"}}]}).encode()

        engine = OpenAICompatibleEngine(
            api_key="stub" + "-test-key", model="synthetic-model", base_url="https://provider.invalid/v1",
            timeout=7, transport=transport,
        )
        with tempfile.TemporaryDirectory(prefix="harness-provider-") as directory:
            data_dir = Path(directory) / "state"
            bootstrap(data_dir)
            self.assertEqual(run_dialogue(data_dir, "SYNTHETIC_PROMPT", engine=engine), "SYNTHETIC_PROVIDER_REPLY")
        self.assertEqual(seen["url"], "https://provider.invalid/v1/chat/completions")
        self.assertEqual(seen["authorization"], "Bearer stub-test-key")
        self.assertNotIn("stub-test-key", repr(engine))
        self.assertEqual(seen["timeout"], 7)
        self.assertEqual(seen["body"]["model"], "synthetic-model")
        self.assertEqual(seen["body"]["messages"][-1], {"role": "user", "content": "SYNTHETIC_PROMPT"})

    def test_provider_errors_are_sanitized_and_configuration_is_opt_in(self) -> None:
        marker = "synthetic-secret-marker"

        def failing_transport(request: Request, timeout: float) -> bytes:
            raise URLError(marker)

        engine = OpenAICompatibleEngine(api_key="stub" + "-test-key", model="synthetic", transport=failing_transport)
        with self.assertRaises(EngineError) as raised:
            engine.generate("synthetic prompt", "Assistant")
        self.assertNotIn(marker, str(raised.exception))
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsInstance(engine_from_environment(), MockEngine)
            with self.assertRaisesRegex(ValueError, "required"):
                with patch.dict(os.environ, {"HARNESS_ENGINE": "openai-compatible"}, clear=True):
                    engine_from_environment()
        with self.assertRaises(ValueError):
            OpenAICompatibleEngine(api_key="x", model="m", base_url="http://provider.invalid/v1")

        def timeout_transport(request: Request, timeout: float) -> bytes:
            raise TimeoutError(marker)

        timed_out = OpenAICompatibleEngine(api_key="stub", model="synthetic", transport=timeout_transport)
        with self.assertRaises(EngineError) as raised:
            timed_out.generate("synthetic prompt", "Assistant")
        self.assertNotIn(marker, str(raised.exception))

    def test_invalid_environment_and_malformed_telegram_updates_fail_closed(self) -> None:
        with patch.dict(os.environ, {"HARNESS_ENGINE": "unknown-provider"}, clear=True):
            with self.assertRaisesRegex(ValueError, "HARNESS_ENGINE"):
                engine_from_environment()
        with patch.dict(
            os.environ,
            {"HARNESS_ENGINE": "openai-compatible", "HARNESS_OPENAI_API_KEY": "stub", "HARNESS_OPENAI_MODEL": " "},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "required"):
                engine_from_environment()
        with patch.dict(
            os.environ,
            {"HARNESS_TELEGRAM_ENABLED": "true", "HARNESS_TELEGRAM_BOT_TOKEN": "malformed"},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "malformed"):
                telegram_from_environment()
        with patch.dict(os.environ, {"HARNESS_TELEGRAM_OWNER_IDS": "42,not-a-number"}, clear=True):
            with self.assertRaisesRegex(ValueError, "numeric"):
                owner_ids_from_environment()

        malformed = [
            {"update_id": "not-an-integer", "message": {}},
            {"update_id": 10, "message": "not-an-object"},
            {"update_id": 11, "message": {"from": [], "chat": {}, "text": "ignored"}},
            {"update_id": 12, "message": {"from": {"id": 42}, "chat": {"id": 42, "type": "private"}, "text": []}},
        ]
        dispatches: list[str] = []

        def malformed_transport(request: Request, timeout: float) -> bytes:
            return json.dumps({"ok": True, "result": malformed}).encode()

        client = TelegramClient(token="123:stub-token", transport=malformed_transport)
        self.assertEqual(client.poll_once(0, frozenset({42}), dispatches.append, 0), 13)
        self.assertEqual(dispatches, [])

        def malformed_batch_transport(request: Request, timeout: float) -> bytes:
            return json.dumps({"ok": True, "result": [None]}).encode()

        malformed_batch = TelegramClient(token="123:stub-token", transport=malformed_batch_transport)
        with self.assertRaises(TelegramError):
            malformed_batch.poll_once(0, frozenset({42}), dispatches.append, 0)
        self.assertEqual(dispatches, [])

        def timeout_transport(request: Request, timeout: float) -> bytes:
            raise TimeoutError("synthetic transport timeout")

        timed_out_client = TelegramClient(token="123:stub-token", transport=timeout_transport)
        with self.assertRaises(TelegramError) as raised:
            timed_out_client.get_updates(0, 0)
        self.assertNotIn("synthetic transport timeout", str(raised.exception))

    def test_telegram_allowlist_denies_before_model_dispatch(self) -> None:
        incoming = [
            {"update_id": 10, "message": {"from": {"id": 9001}, "chat": {"id": 9001, "type": "private"}, "text": "SYNTHETIC_DENIED"}},
            {"update_id": 11, "message": {"from": {"id": 42}, "chat": {"id": 42, "type": "private"}, "text": "SYNTHETIC_ALLOWED"}},
            {"update_id": 12, "message": {"from": {"id": 42}, "chat": {"id": -42, "type": "group"}, "text": "SYNTHETIC_GROUP"}},
        ]
        sent: list[dict[str, object]] = []

        def transport(request: Request, timeout: float) -> bytes:
            if request.full_url.endswith("/getUpdates"):
                return json.dumps({"ok": True, "result": incoming}).encode()
            sent.append(json.loads(request.data.decode("utf-8")))
            return json.dumps({"ok": True, "result": {}}).encode()

        dispatches: list[str] = []
        client = TelegramClient(token="123:stub" + "-test-token", transport=transport)
        self.assertNotIn("stub-test-token", repr(client))
        next_offset = client.poll_once(0, frozenset({42}), lambda text: dispatches.append(text) or f"reply to {text}", 0)
        self.assertEqual(next_offset, 13)
        self.assertEqual(dispatches, ["SYNTHETIC_ALLOWED"])
        self.assertEqual(sent, [
            {"chat_id": 9001, "text": "Access denied."},
            {"chat_id": 42, "text": "reply to SYNTHETIC_ALLOWED"},
        ])

    def test_telegram_errors_redact_token_and_environment_defaults_disabled(self) -> None:
        marker = "synthetic-token-marker"

        def failing_transport(request: Request, timeout: float) -> bytes:
            raise URLError(marker)

        with self.assertRaises(TelegramError) as raised:
            TelegramClient(token="123:stub" + "-bot-token", transport=failing_transport).get_updates(0, 0)
        self.assertNotIn(marker, str(raised.exception))
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "disabled"):
                telegram_from_environment()
            with self.assertRaisesRegex(ValueError, "allowlist"):
                owner_ids_from_environment()
        with patch.dict(os.environ, {"HARNESS_TELEGRAM_ENABLED": "true", "HARNESS_TELEGRAM_BOT_TOKEN": "123:stub-token"}, clear=True):
            self.assertEqual(telegram_from_environment().token, "123:stub-token")
            with self.assertRaisesRegex(ValueError, "allowlist"):
                owner_ids_from_environment()
        with patch.dict(os.environ, {"HARNESS_TELEGRAM_OWNER_IDS": "42, 43"}, clear=True):
            self.assertEqual(owner_ids_from_environment(), frozenset({42, 43}))


if __name__ == "__main__":
    unittest.main()
