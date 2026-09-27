"""Safe-by-default behavior tests."""

import tempfile
import unittest
from pathlib import Path

from harness.cli import bootstrap
from harness.engine import MockEngine
from harness.memory import propose
from harness.storage import Store


class DefaultTests(unittest.TestCase):
    def test_mock_is_stable_and_initiative_is_only_a_suggestion(self) -> None:
        engine = MockEngine()
        first = engine.generate("SYNTHETIC_INPUT", "Assistant")
        second = engine.generate("SYNTHETIC_INPUT", "Assistant")
        self.assertEqual(first, second)
        self.assertIn("Would you like", first.initiative)

    def test_empty_memory_proposals_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="harness-default-") as directory:
            data_dir = Path(directory)
            bootstrap(data_dir)
            store = Store(data_dir / "harness.sqlite3")
            try:
                with self.assertRaises(ValueError):
                    propose(store, "   ")
                self.assertEqual(store.connection.execute("SELECT count(*) FROM memory_items").fetchone()[0], 0)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
