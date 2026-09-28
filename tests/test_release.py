from __future__ import annotations

import unittest
import socket
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

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

    def test_guard_scans_commit_and_annotated_tag_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", socket.gethostname()], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "builder@example.invalid"], cwd=root, check=True)
            (root / "sample.txt").write_text("safe tree\n", encoding="utf-8")
            subprocess.run(["git", "add", "sample.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "safe fixture"], cwd=root, check=True)
            tag_message = ".".join(("release", "internal"))
            subprocess.run(
                ["git", "tag", "-a", "v0.1.0-rc1", "-m", tag_message], cwd=root, check=True
            )

            with patch.object(release_guard, "ROOT", root):
                findings = release_guard.history_metadata()

        self.assertEqual(len(findings.get("local hostname", set())), 2)
        self.assertEqual(len(findings.get("private hostname", set())), 1)

    def test_guard_recognizes_private_hostname_patterns(self) -> None:
        private_host = ".".join(("build-host", "internal"))
        self.assertRegex(private_host, release_guard.private_hostname_rule())


if __name__ == "__main__":
    unittest.main()
