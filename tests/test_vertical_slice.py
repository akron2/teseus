"""Synthetic contract tests for bootstrap, dialogue, migrations, and memory."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from harness.cli import bootstrap, run_dialogue
from harness.memory import active_items, cycle, propose, restore
from harness.storage import Store


class VerticalSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="harness-test-")
        self.data_dir = Path(self.temporary.name) / "private-state"
        bootstrap(self.data_dir)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_bootstrap_and_dialogue_persist_persona_and_conversation(self) -> None:
        bootstrap(self.data_dir)
        reply = run_dialogue(self.data_dir, "SYNTHETIC_DIALOGUE_001")
        self.assertEqual(reply.splitlines()[0], "Assistant heard: SYNTHETIC_DIALOGUE_001")
        with sqlite3.connect(self.data_dir / "harness.sqlite3") as db:
            self.assertEqual(db.execute("SELECT count(*) FROM schema_migrations").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT name FROM personas").fetchone()[0], "Assistant")
            self.assertEqual(db.execute("SELECT count(*) FROM conversations").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM messages").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT count(*) FROM memory_items").fetchone()[0], 0)

    def test_explicit_memory_selection_forgetting_and_reversal_are_journaled(self) -> None:
        store = Store(self.data_dir / "harness.sqlite3")
        try:
            weak = propose(store, "SYNTHETIC_MEMORY_WEAK", 2)
            strong = propose(store, "SYNTHETIC_MEMORY_STRONG", 9)
            result = cycle(store, limit=1)
            self.assertEqual(result, {"kept": [strong], "forgotten": [weak]})
            self.assertEqual([item["id"] for item in active_items(store)], [strong])
            restore(store, weak)
            self.assertEqual({item["id"] for item in active_items(store)}, {weak, strong})
            actions = [row[0] for row in store.connection.execute(
                "SELECT action FROM memory_events WHERE memory_id=? ORDER BY id", (weak,)
            )]
            self.assertEqual(actions, ["proposed", "forgotten", "restored"])
        finally:
            store.close()

    def test_seed_profile_is_explicit_and_contains_required_public_concepts(self) -> None:
        bootstrap(self.data_dir, seed_teseus=True)
        profile = json.loads((self.data_dir / "persona.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["name"], "Teseus")
        store = Store(self.data_dir / "harness.sqlite3")
        try:
            rows = [row[0].casefold() for row in store.connection.execute("SELECT body FROM memory_items")]
            joined = " ".join(rows)
            for concept in ("ship", "memory", "live conversation", "reversible", "trust", "initiative"):
                self.assertIn(concept, joined)
            self.assertEqual(len(rows), 6)
        finally:
            store.close()

    def test_public_seed_can_be_removed(self) -> None:
        from harness.cli import remove_seed

        bootstrap(self.data_dir, seed_teseus=True)
        remove_seed(self.data_dir)
        profile = json.loads((self.data_dir / "persona.json").read_text(encoding="utf-8"))
        self.assertEqual(profile["name"], "Assistant")
        store = Store(self.data_dir / "harness.sqlite3")
        try:
            self.assertEqual(store.connection.execute("SELECT count(*) FROM memory_items").fetchone()[0], 0)
        finally:
            store.close()

    def test_migration_failure_rolls_back_entire_new_migration(self) -> None:
        store = Store(self.data_dir / "rollback.sqlite3")
        with tempfile.TemporaryDirectory(prefix="harness-migration-") as directory:
            migration_dir = Path(directory)
            (migration_dir / "0001_initial.sql").write_text(
                "CREATE TABLE example (id INTEGER PRIMARY KEY); INVALID SQL;", encoding="utf-8"
            )
            with self.assertRaises(sqlite3.OperationalError):
                store.migrate(migration_dir)
            tables = {row[0] for row in store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            self.assertNotIn("example", tables)
            self.assertNotIn("schema_migrations", tables)
        store.close()

    def test_unknown_future_migration_version_fails_closed(self) -> None:
        store = Store(self.data_dir / "future.sqlite3")
        store.migrate()
        store.connection.execute("INSERT INTO schema_migrations VALUES (99, 'synthetic')")
        store.connection.commit()
        with self.assertRaisesRegex(RuntimeError, "newer"):
            store.migrate()
        store.close()


if __name__ == "__main__":
    unittest.main()
