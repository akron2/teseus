from __future__ import annotations

import unittest
from pathlib import Path

from scripts import release, release_guard


class ReleaseHelpersTests(unittest.TestCase):
    def test_semver_tag_parsing(self) -> None:
        self.assertEqual(release.parse_version("v0.1.0-rc2"), ("0.1.0", "rc2"))
        self.assertEqual(release.parse_version("v1.2.3"), ("1.2.3", None))
        for invalid in ("0.1.0", "v01.2.3", "v1.2", "v1.2.3-01"):
            with self.subTest(invalid=invalid), self.assertRaises(release.ReleaseError):
                release.parse_version(invalid)

    def test_guard_accepts_only_expected_public_origin(self) -> None:
        self.assertTrue(release_guard.public_origin_is_valid([], []))
        self.assertTrue(
            release_guard.public_origin_is_valid(["origin"], ["https://github.com/akron2/teseus.git"])
        )
        self.assertTrue(
            release_guard.public_origin_is_valid(["origin"], ["git@teseus-github:akron2/teseus.git"])
        )
        for names, urls in (
            (["origin", "backup"], ["https://github.com/akron2/teseus.git", "https://example.invalid/repo.git"]),
            (["origin"], ["https://user:secret@github.com/akron2/teseus.git"]),
            (["origin"], ["https://github.com/other/repo.git"]),
            (["origin"], ["https://github.com:444/akron2/teseus.git"]),
        ):
            with self.subTest(names=names, url_count=len(urls)):
                self.assertFalse(release_guard.public_origin_is_valid(names, urls))

    def test_readme_smoke_commands_are_documented_harness_invocations(self) -> None:
        commands = release.smoke_commands(release.ROOT)
        self.assertGreaterEqual(len(commands), 4)
        self.assertTrue(all(command[:3] == ["python", "-m", "harness"] for command in commands))
        self.assertIn("demo", [argument for command in commands for argument in command])

    def test_current_release_metadata_is_aligned(self) -> None:
        self.assertEqual(release.check_version("v0.1.0-rc2"), ("0.1.0", "rc2"))


if __name__ == "__main__":
    unittest.main()
