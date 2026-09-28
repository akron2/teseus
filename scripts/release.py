"""Verify a public source tree and create an annotated release tag."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(
    r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-((?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*))?$"
)


class ReleaseError(RuntimeError):
    """A release precondition or verification failed."""


def command(
    args: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    capture: bool = False,
    label: str | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            check=False,
        )
    except OSError as exc:
        raise ReleaseError(f"could not run {label or args[0]} ({type(exc).__name__})") from None
    if result.returncode:
        raise ReleaseError(f"{label or args[0]} failed (exit {result.returncode})")
    return result


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, check=False,
    )
    if check and result.returncode:
        raise ReleaseError("Git precondition failed")
    return result.stdout.strip()


def safe_env(home: Path, extra_path: Path | None = None) -> dict[str, str]:
    home.mkdir(parents=True, exist_ok=True)
    base_path = os.environ.get("PATH", "/usr/bin:/bin")
    if extra_path:
        base_path = str(extra_path) + os.pathsep + base_path
    return {
        "PATH": base_path,
        "HOME": str(home),
        "TMPDIR": str(home),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "LC_ALL": "C.UTF-8",
    }


def parse_version(tag: str) -> tuple[str, str | None]:
    match = VERSION_RE.fullmatch(tag)
    if not match:
        raise ReleaseError("tag must be a valid v-prefixed semantic version")
    core = ".".join(match.group(index) for index in (1, 2, 3))
    return core, match.group(4)


def check_version(tag: str) -> tuple[str, str | None]:
    core, prerelease = parse_version(tag)
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    source_version = metadata["project"]["version"]
    version_file = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    init = (ROOT / "src/harness/__init__.py").read_text(encoding="utf-8")
    found = re.search(r'^__version__\s*=\s*[\'"]([^\'"]+)[\'"]\s*$', init, re.MULTILINE)
    if source_version != version_file or not found or found.group(1) != version_file:
        raise ReleaseError("VERSION, package metadata, and import version do not agree")
    if core != version_file:
        raise ReleaseError("tag version does not match the package version")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if not re.search(rf"^## {re.escape(tag.removeprefix('v'))}(?:\s|—)", changelog, re.MULTILINE):
        raise ReleaseError("CHANGELOG.md has no entry for the requested tag")
    return core, prerelease


def check_repository(tag: str, ci: bool, dry_run: bool = False) -> str:
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ReleaseError("working tree is not clean")
    commit = git("rev-parse", "HEAD")
    if ci:
        ref = os.environ.get("GITHUB_REF", "")
        if ref != f"refs/tags/{tag}":
            raise ReleaseError("CI ref is not the requested release tag")
        if git("cat-file", "-t", f"refs/tags/{tag}", check=False) != "tag":
            raise ReleaseError("release ref must be an annotated tag")
        if git("rev-parse", f"refs/tags/{tag}^{{}}") != commit:
            raise ReleaseError("release tag does not point at the checked-out commit")
    else:
        if git("branch", "--show-current") != "main":
            raise ReleaseError("release preparation is allowed only on main")
        remote_main = git("rev-parse", "refs/remotes/origin/main", check=False)
        if not remote_main:
            raise ReleaseError("origin/main is not available; fetch the public main branch first")
        if dry_run:
            if git("merge-base", "refs/remotes/origin/main", "HEAD", check=False) != remote_main:
                raise ReleaseError("dry-run main must be based on the current origin/main")
        elif remote_main != commit:
            raise ReleaseError("main must be pushed and current with origin/main before release")
    if not ci:
        exists = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/tags/{tag}"],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode == 0
        if exists:
            raise ReleaseError("tag already exists locally; published history is never replaced")
        remote = subprocess.run(
            ["git", "ls-remote", "--exit-code", "origin", f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        if remote.returncode == 0 and remote.stdout.strip():
            raise ReleaseError("tag already exists on origin; published history is never replaced")
        if remote.returncode not in (0, 2):
            raise ReleaseError("could not safely check whether the requested origin tag exists")
    return commit


def run_guard(env: dict[str, str]) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/release_guard.py"], cwd=ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if result.returncode:
        raise ReleaseError("release/privacy guard blocked publication; diagnostic paths and values suppressed")
    print(result.stdout.strip())


def copy_source(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        ignore=shutil.ignore_patterns(
            ".git", ".venv", "venv", "__pycache__", "*.pyc", "build", "dist", "*.egg-info"
        ),
    )


def artifact_files(directory: Path) -> list[Path]:
    files = sorted(path for path in directory.iterdir() if path.is_file() and path.suffix in {".whl", ".gz"})
    wheels = [path for path in files if path.suffix == ".whl"]
    sdists = [path for path in files if path.name.endswith(".tar.gz")]
    if len(wheels) != 1 or len(sdists) != 1 or len(files) != 2:
        raise ReleaseError("build did not produce exactly one wheel and one sdist")
    return files


def build_once(source: Path, destination: Path, env: dict[str, str]) -> list[Path]:
    destination.mkdir(parents=True)
    command(
        [sys.executable, "-m", "build", "--no-isolation", "--wheel", "--sdist", "--outdir", str(destination)],
        cwd=source, env=env, label="package build",
    )
    raw_sdists = list(destination.glob("*.tar.gz"))
    if len(raw_sdists) != 1:
        raise ReleaseError("build did not produce exactly one source archive")
    raw = raw_sdists[0]
    normalized = destination / (raw.name + ".normalized")
    epoch = int(git("show", "-s", "--format=%ct", "HEAD"))
    command(
        [sys.executable, str(source / "scripts/normalize_sdist.py"), str(raw), str(normalized), "--epoch", str(epoch)],
        cwd=source, env=env, label="sdist normalization",
    )
    normalized.replace(raw)
    return artifact_files(destination)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def smoke_commands(source: Path) -> list[list[str]]:
    readme = (source / "README.md").read_text(encoding="utf-8")
    sections = ("## Quick start", "For a single self-contained smoke run:")
    commands: list[list[str]] = []
    for section in sections:
        start = readme.find(section)
        if start < 0:
            raise ReleaseError("README is missing a documented smoke section")
        block_start = readme.find("```sh", start)
        block_end = readme.find("```", block_start + 5)
        if block_start < 0 or block_end < 0:
            raise ReleaseError("README smoke section has no shell command block")
        block = readme[block_start + 5 : block_end]
        selected = [line.strip() for line in block.splitlines() if line.strip().startswith("PYTHONPATH=src python")]
        if not selected:
            raise ReleaseError("README smoke section has no Python harness commands")
        for line in selected:
            parts = shlex.split(line)
            if len(parts) < 4 or parts[0] != "PYTHONPATH=src" or parts[1] != "python" or parts[2:4] != ["-m", "harness"]:
                raise ReleaseError("README smoke command is outside the reviewed harness-command form")
            commands.append(parts[1:])
    return commands


def install_and_smoke(wheel: Path, sdist: Path, scratch: Path, source: Path) -> None:
    for artifact in (wheel, sdist):
        install_root = scratch / ("install-" + artifact.suffix.lstrip("."))
        venv.EnvBuilder(with_pip=True, clear=True).create(install_root)
        scripts_dir = "Scripts" if os.name == "nt" else "bin"
        python = install_root / scripts_dir / ("python.exe" if os.name == "nt" else "python")
        env = safe_env(scratch / ("home-" + artifact.suffix.lstrip(".")), install_root / scripts_dir)
        install_args = [str(python), "-m", "pip", "install", "--no-deps"]
        if artifact.suffix == ".whl":
            install_args.append("--no-index")
        else:
            install_args.extend(("--index-url", "https://pypi.org/simple"))
        command(
            [*install_args, str(artifact)],
            env=env, label=f"install {artifact.suffix.lstrip('.')}",
        )
        import_check = "import harness; assert harness.__version__ == " + repr((ROOT / "VERSION").read_text().strip())
        command([str(python), "-c", import_check], cwd=scratch, env=env, label="installed-package import")
        run_root = scratch / ("smoke-" + artifact.suffix.lstrip("."))
        run_root.mkdir()
        smoke_env = safe_env(scratch / ("smoke-home-" + artifact.suffix.lstrip(".")), install_root / scripts_dir)
        for argv in smoke_commands(source):
            smoke_env["PYTHONPATH"] = "src"
            command(argv, cwd=run_root, env=smoke_env, label="documented README smoke command")


def verify(tag: str, *, ci: bool, dry_run: bool = False) -> tuple[str, list[Path]]:
    check_version(tag)
    commit = check_repository(tag, ci, dry_run)
    print(f"Release target: {tag} at {commit}")
    with tempfile.TemporaryDirectory(prefix="teseus-release-") as temporary:
        scratch = Path(temporary)
        env = safe_env(scratch / "home")
        env["SOURCE_DATE_EPOCH"] = git("show", "-s", "--format=%ct", "HEAD")
        run_guard(env)
        test_env = dict(env, PYTHONPATH="src", PYTHONPYCACHEPREFIX=str(scratch / "pycache"))
        command(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            env=test_env, label="unit tests",
        )
        command(
            [sys.executable, "-m", "compileall", "-q", "src", "tests"],
            env=test_env, label="compile check",
        )
        command(
            [sys.executable, "-c", "import harness, harness.cli, harness.engine, harness.memory, harness.openai_compatible, harness.persona, harness.storage, harness.telegram"],
            env=test_env, label="import check",
        )
        first_source, second_source = scratch / "source-one", scratch / "source-two"
        copy_source(first_source)
        copy_source(second_source)
        first = build_once(first_source, scratch / "build-one", env)
        second = build_once(second_source, scratch / "build-two", env)
        for left, right in zip(first, second):
            if left.name != right.name or digest(left) != digest(right):
                raise ReleaseError("independent package builds are not byte-for-byte reproducible")
        wheel = next(path for path in first if path.suffix == ".whl")
        sdist = next(path for path in first if path.name.endswith(".tar.gz"))
        install_and_smoke(wheel, sdist, scratch, first_source)
        output = ROOT / "dist" if ci else scratch / "dist"
        if output.exists():
            raise ReleaseError("dist/ already exists; remove or move it before release verification")
        shutil.copytree(scratch / "build-one", output)
        checksums = output / "SHA256SUMS.txt"
        checksums.write_text(
            "".join(f"{digest(path)}  {path.name}\n" for path in artifact_files(output)),
            encoding="utf-8",
        )
        print("Reproducible artifacts built, installed, and README smoke commands passed:")
        for path in artifact_files(output):
            print(f"  {path.name}  sha256:{digest(path)}")
        print(f"  {checksums.name}")
    return commit, [ROOT / "dist" / path.name for path in artifact_files(ROOT / "dist")] if ci else []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="v-prefixed semantic version, e.g. v0.1.0-rc2")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="run every gate without creating a tag")
    mode.add_argument("--ci", action="store_true", help="verify an already-pushed annotated tag in CI")
    args = parser.parse_args()
    try:
        commit, _ = verify(args.tag, ci=args.ci, dry_run=args.dry_run)
        if args.ci:
            print("CI release verification passed; artifacts are ready in dist/.")
        elif args.dry_run:
            print(f"DRY RUN passed. Would create annotated tag {args.tag} at {commit}; no tag created.")
        else:
            command(
                ["git", "tag", "-a", args.tag, "-m", f"Release {args.tag}"],
                label="annotated tag creation",
            )
            print(f"Created annotated tag {args.tag}; push it with: git push origin {args.tag}")
        return 0
    except (ReleaseError, OSError, KeyError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
