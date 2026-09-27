"""Engine protocol and credential-free deterministic implementation."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EngineReply:
    text: str
    initiative: str | None = None


class Engine(Protocol):
    def generate(self, text: str, persona_name: str) -> EngineReply: ...


class MockEngine:
    """Stable local response; initiative is a suggestion, never an action."""

    def generate(self, text: str, persona_name: str) -> EngineReply:
        clean = " ".join(text.split())
        return EngineReply(
            text=f"{persona_name} heard: {clean}",
            initiative="Would you like to choose one detail to keep in memory?",
        )
