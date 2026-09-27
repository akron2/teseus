"""Private local SQLite state and ordered schema migrations."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIGRATION_DIR = Path(__file__).resolve().parents[2] / "migrations"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, database: Path):
        self.database = database
        database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.connection = sqlite3.connect(database)
        try:
            database.chmod(0o600)
        except OSError:
            pass
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")

    def close(self) -> None:
        self.connection.close()

    def migrate(self, migration_dir: Path = MIGRATION_DIR) -> list[int]:
        migrations = sorted(migration_dir.glob("[0-9][0-9][0-9][0-9]_*.sql"))
        if not migrations:
            raise RuntimeError("no numbered database migrations found")
        versions = [int(path.name[:4]) for path in migrations]
        if versions != list(range(1, len(versions) + 1)):
            raise RuntimeError("database migrations must be unique and consecutive from version 0001")
        db = self.connection
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            known = {int(row[0]) for row in db.execute("SELECT version FROM schema_migrations")}
            latest = max(int(path.name[:4]) for path in migrations)
            if known and max(known) > latest:
                raise RuntimeError("database schema is newer than this program")
            applied: list[int] = []
            for path in migrations:
                version = int(path.name[:4])
                if version in known:
                    continue
                for statement in path.read_text(encoding="utf-8").split(";"):
                    if statement.strip():
                        db.execute(statement)
                db.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (version, utc_now()),
                )
                applied.append(version)
            db.commit()
            return applied
        except Exception:
            db.rollback()
            raise

    def save_persona(self, persona_id: str, persona: object) -> None:
        payload = persona.as_dict()
        self.connection.execute(
            "INSERT INTO personas(id, name, description, principles_json, created_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
            "name=excluded.name, description=excluded.description, principles_json=excluded.principles_json",
            (persona_id, payload["name"], payload["description"], json.dumps(payload["principles"]), utc_now()),
        )
        self.connection.commit()

    def load_persona(self, persona_id: str) -> dict[str, object] | None:
        row = self.connection.execute("SELECT * FROM personas WHERE id=?", (persona_id,)).fetchone()
        if row is None:
            return None
        return {"name": row["name"], "description": row["description"], "principles": json.loads(row["principles_json"])}

    def create_conversation(self, conversation_id: str, persona_id: str) -> None:
        self.connection.execute(
            "INSERT INTO conversations(id, persona_id, created_at) VALUES (?, ?, ?)",
            (conversation_id, persona_id, utc_now()),
        )
        self.connection.commit()

    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        self.connection.execute(
            "INSERT INTO messages(conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, utc_now()),
        )
        self.connection.commit()
