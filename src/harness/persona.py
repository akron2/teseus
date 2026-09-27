"""Persona file loading and neutral defaults."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Persona:
    name: str
    description: str
    principles: tuple[str, ...]

    @classmethod
    def neutral(cls) -> "Persona":
        return cls(
            name="Assistant",
            description="A locally configured personal assistant.",
            principles=(
                "Distinguish current context from recollection.",
                "Treat memory as optional, inspectable, and reversible.",
                "Offer suggestions without acting without consent.",
            ),
        )

    @classmethod
    def load(cls, path: Path) -> "Persona":
        raw = json.loads(path.read_text(encoding="utf-8"))
        name, description, principles = raw.get("name"), raw.get("description", ""), raw.get("principles")
        if not isinstance(name, str) or not name.strip() or not isinstance(description, str):
            raise ValueError("persona file must contain a non-empty name and text description")
        if not isinstance(principles, list) or not all(isinstance(item, str) for item in principles):
            raise ValueError("persona principles must be a list of strings")
        return cls(name=name.strip(), description=description, principles=tuple(principles))

    def as_dict(self) -> dict[str, object]:
        return {"name": self.name, "description": self.description, "principles": list(self.principles)}
