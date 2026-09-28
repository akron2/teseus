from __future__ import annotations

import unittest
import socket
import os
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
        self.assertEqual(release.check_version("v0.1.0-rc3"), ("0.1.0", "rc3"))
        with self.assertRaisesRegex(release.ReleaseError, "retired"):
            release.check_version("v0.1.0-rc2")

    def make_git_fixture(self, root: Path) -> str:
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
        (root / ".gitignore").write_text("", encoding="utf-8")
        (root / "sample.txt").write_text("safe tree\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        env = dict(
            os.environ,
            GIT_AUTHOR_NAME="Neutral Fixture",
            GIT_AUTHOR_EMAIL="fixture@example.invalid",
            GIT_COMMITTER_NAME="Neutral Fixture",
            GIT_COMMITTER_EMAIL="fixture@example.invalid",
        )
        subprocess.run(["git", "commit", "-q", "-m", "safe fixture"], cwd=root, env=env, check=True)
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, text=True, capture_output=True
        ).stdout.strip()

    def test_tag_creation_ignores_hostile_git_identity_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            home = Path(directory) / "hostile-home"
            root.mkdir()
            home.mkdir()
            commit = self.make_git_fixture(root)
            hostile = socket.gethostname()
            (home / ".gitconfig").write_text(
                f"[user]\n\tname = {hostile}\n\temail = {hostile}@invalid\n", encoding="utf-8"
            )
            subprocess.run(["git", "config", "user.name", hostile], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", f"{hostile}@invalid"], cwd=root, check=True)
            env = release.safe_env(Path(directory) / "clean-home")
            env.update(
                {
                    "HOME": str(home),
                    "GIT_CONFIG_GLOBAL": str(home / ".gitconfig"),
                    "GIT_AUTHOR_NAME": hostile,
                    "GIT_AUTHOR_EMAIL": f"{hostile}@invalid",
                    "GIT_COMMITTER_NAME": hostile,
                    "GIT_COMMITTER_EMAIL": f"{hostile}@invalid",
                    "GIT_CONFIG_COUNT": "2",
                    "GIT_CONFIG_KEY_0": "user.name",
                    "GIT_CONFIG_VALUE_0": hostile,
                    "GIT_CONFIG_KEY_1": "user.email",
                    "GIT_CONFIG_VALUE_1": f"{hostile}@invalid",
                }
            )
            with patch.object(release, "ROOT", root), patch.object(release, "run_guard"):
                release.create_annotated_tag(
                    "v0.1.0-rc3", commit, 1_000_000_000 + 700_000_000, env
                )
            tag = subprocess.run(
                ["git", "cat-file", "tag", "refs/tags/v0.1.0-rc3"],
                cwd=root,
                check=True,
                text=True,
                capture_output=True,
            ).stdout
            self.assertIn("tagger Teseus Release <release-bot@users.noreply.github.com>", tag)
            self.assertNotIn(hostile, tag)

    def test_post_tag_guard_failure_removes_only_local_tag_ref(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            commit = self.make_git_fixture(root)
            env = release.safe_env(Path(directory) / "home")
            with (
                patch.object(release, "ROOT", root),
                patch.object(release, "run_guard", side_effect=release.ReleaseError("blocked")),
            ):
                with self.assertRaisesRegex(release.ReleaseError, "blocked"):
                    release.create_annotated_tag(
                        "v0.1.0-rc3", commit, 1_000_000_000 + 700_000_000, env
                    )
            result = subprocess.run(
                ["git", "show-ref", "--verify", "--quiet", "refs/tags/v0.1.0-rc3"], cwd=root
            )
            self.assertNotEqual(result.returncode, 0)

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

    def test_github_tag_fetch_replaces_checkout_lightweight_tag_with_remote_annotated_tag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "remote.git"
            source = root / "source"
            checkout = root / "checkout"
            remote.mkdir()
            source.mkdir()
            subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=source, check=True)
            subprocess.run(["git", "config", "user.name", "Checkout Fixture"], cwd=source, check=True)
            subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=source, check=True)
            (source / "history.txt").write_text("first\n", encoding="utf-8")
            subprocess.run(["git", "add", "history.txt"], cwd=source, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "first"], cwd=source, check=True)
            (source / "history.txt").write_text("first\nsecond\n", encoding="utf-8")
            subprocess.run(["git", "commit", "-qam", "second"], cwd=source, check=True)
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=source, check=True, text=True, capture_output=True
            ).stdout.strip()
            tag = "v0.1.0-rc-test"
            subprocess.run(["git", "tag", "-a", tag, "-m", "checkout fixture"], cwd=source, check=True)
            subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=source, check=True)
            subprocess.run(["git", "push", "-q", "origin", "main", f"refs/tags/{tag}"], cwd=source, check=True)

            # The previous shallow commit-only checkout had neither history nor the local tag ref.
            subprocess.run(
                ["git", "clone", "-q", "--depth=1", "--no-tags", "--branch", "main", remote.as_uri(), str(checkout)],
                check=True,
            )
            subprocess.run(["git", "checkout", "-q", "--detach", commit], cwd=checkout, check=True)
            # actions/checkout can leave a lightweight local tag at the target
            # commit; fetching the annotated object without force then fails.
            subprocess.run(["git", "tag", tag, commit], cwd=checkout, check=True)
            old_fetch = subprocess.run(
                ["git", "fetch", "--no-tags", "origin", f"refs/tags/{tag}:refs/tags/{tag}"],
                cwd=checkout, text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(old_fetch.returncode, 0)
            self.assertIn("would clobber existing tag", old_fetch.stderr)
            self.assertTrue((checkout / ".git/shallow").exists())

            # Model fetch-depth: 0 and run the exact helper used by the workflow.
            subprocess.run(["git", "fetch", "--unshallow", "--no-tags", "origin"], cwd=checkout, check=True)
            result = subprocess.run(
                ["bash", str(release.ROOT / "scripts/fetch_release_tag.sh")],
                cwd=checkout,
                env=dict(os.environ, RELEASE_REF=f"refs/tags/{tag}", RELEASE_TAG=tag),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            tag_type = subprocess.run(
                ["git", "cat-file", "-t", f"refs/tags/{tag}"], cwd=checkout, check=True,
                text=True, capture_output=True,
            ).stdout.strip()
            peeled_commit = subprocess.run(
                ["git", "rev-parse", f"refs/tags/{tag}^{{commit}}"], cwd=checkout, check=True,
                text=True, capture_output=True,
            ).stdout.strip()
            self.assertEqual(tag_type, "tag")
            self.assertEqual(peeled_commit, commit)
            remote_tag_object = subprocess.run(
                ["git", "rev-parse", f"refs/tags/{tag}"], cwd=source, check=True,
                text=True, capture_output=True,
            ).stdout.strip()
            fetched_tag_object = subprocess.run(
                ["git", "rev-parse", f"refs/tags/{tag}"], cwd=checkout, check=True,
                text=True, capture_output=True,
            ).stdout.strip()
            self.assertEqual(fetched_tag_object, remote_tag_object)
            self.assertFalse((checkout / ".git/shallow").exists())
            history_size = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"], cwd=checkout, check=True,
                text=True, capture_output=True,
            ).stdout.strip()
            self.assertEqual(history_size, "2")

    def test_github_tag_fetch_rejects_invalid_ref_without_shell_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "remote.git"
            source = root / "source"
            checkout = root / "checkout"
            remote.mkdir()
            source.mkdir()
            subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
            commit = self.make_git_fixture(source)
            tag = "v0.1.0-rc-test"
            subprocess.run(["git", "tag", "-a", tag, "-m", "fixture"], cwd=source, check=True)
            subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=source, check=True)
            subprocess.run(["git", "push", "-q", "origin", "main", f"refs/tags/{tag}"], cwd=source, check=True)
            subprocess.run(
                ["git", "clone", "-q", "--no-tags", "--branch", "main", remote.as_uri(), str(checkout)],
                check=True,
            )
            subprocess.run(["git", "tag", tag, commit], cwd=checkout, check=True)

            marker = root / "must-not-exist"
            invalid_tag = f"{tag};touch {marker}"
            result = subprocess.run(
                ["bash", str(release.ROOT / "scripts/fetch_release_tag.sh")],
                cwd=checkout,
                env=dict(
                    os.environ,
                    RELEASE_REF=f"refs/tags/{invalid_tag}",
                    RELEASE_TAG=invalid_tag,
                ),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())
            local_tag_type = subprocess.run(
                ["git", "cat-file", "-t", f"refs/tags/{tag}"], cwd=checkout, check=True,
                text=True, capture_output=True,
            ).stdout.strip()
            self.assertEqual(local_tag_type, "commit")


if __name__ == "__main__":
    unittest.main()
