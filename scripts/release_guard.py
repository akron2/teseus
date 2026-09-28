"""Local allowlist and low-noise secret/privacy checks; never prints matches."""

import re
import socket
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "scripts" / "public-files.txt"


def content_rules() -> list[tuple[str, re.Pattern[str]]]:
    key_word = "api" + "[_-]?" + "key"
    token_word = "access" + "[_-]?" + "token"
    sensitive_assignment = re.compile(
        r"(?i)\b(?:" + key_word + r"|" + token_word + r"|password|secret)\s*[:=]\s*['\"][^'\"]{8,}"
    )
    file_markers = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
    path_prefix = "/" + r"(?:opt|home|root|srv)/[^\s\"']+"
    absolute_host_path = re.compile(r"(?<![\w])" + path_prefix)
    blocked_person_name = "di" + "ma"
    return [
        ("credential-shaped assignment", sensitive_assignment),
        ("private-key marker", file_markers),
        ("host-specific absolute path", absolute_host_path),
        ("personal identifier", re.compile(re.escape(blocked_person_name), re.IGNORECASE)),
        ("IPv4 literal", re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")),
        ("long numeric identifier", re.compile(r"(?<![A-Za-z0-9])\d{9,}(?![A-Za-z0-9])")),
        ("provider token shape", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{24,}|[0-9]{8,}:[A-Za-z0-9_-]{20,})\b")),
    ]


def repo_files() -> set[str]:
    return {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(ROOT).parts
    }


def git_output(*args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", *args], cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
    except (OSError, subprocess.CalledProcessError):
        raise RuntimeError("Git history inspection failed") from None
    return result.stdout


def public_origin_is_valid(remote_names: list[str], remote_urls: list[str]) -> bool:
    """Accept only the one expected public origin; never expose its URL."""

    if remote_names != ["origin"] or len(remote_urls) != 1:
        return not remote_names and not remote_urls
    value = remote_urls[0]
    if "@" in value.split(":", 1)[0] and value.startswith("https://"):
        return False
    https = urlsplit(value)
    if https.scheme == "https" and https.hostname == "github.com" and not https.username:
        return (
            https.port in (None, 443)
            and https.path.rstrip("/") in {"/akron2/teseus", "/akron2/teseus.git"}
            and not https.query
            and not https.fragment
        )
    match = re.fullmatch(r"git@(github\.com|teseus-github):akron2/teseus(?:\.git)?", value)
    return match is not None


def history_blobs() -> list[tuple[str, str]]:
    """Return reachable text blobs and paths from every local ref without printing contents."""

    records: list[tuple[str, str]] = []
    for line in git_output("rev-list", "--objects", "--all").decode("utf-8", errors="replace").splitlines():
        parts = line.split(" ", 1)
        object_id = parts[0]
        if len(object_id) < 40 or any(character not in "0123456789abcdef" for character in object_id):
            continue
        object_type = git_output("cat-file", "-t", object_id).decode("ascii").strip()
        if object_type == "blob":
            path = parts[1] if len(parts) > 1 else "(path unavailable)"
            records.append((path, object_id))
    return records


def private_hostname_rule() -> re.Pattern[str]:
    return re.compile(
        r"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
        r"(?:local|internal|lan|home|corp|private)\b"
    )


def history_metadata() -> dict[str, set[str]]:
    """Return privacy findings in reachable refs and commit/tag metadata."""

    references = git_output("for-each-ref", "--format=%(refname)%09%(objectname)%09%(objecttype)")
    object_ids = set(git_output("rev-list", "--all").decode("ascii").splitlines())
    for line in references.decode("utf-8", errors="replace").splitlines():
        fields = line.split("\t")
        if len(fields) == 3 and fields[2] == "tag":
            object_ids.add(fields[1])

    hostname = socket.gethostname().strip()
    hostname_pattern = (
        re.compile(r"(?i)(?<![a-z0-9-])" + re.escape(hostname) + r"(?![a-z0-9-])")
        if hostname
        else None
    )
    findings: dict[str, set[str]] = {}
    private_hostname = private_hostname_rule()
    for object_id in sorted(object_ids):
        try:
            object_type = git_output("cat-file", "-t", object_id).decode("ascii").strip()
            if object_type not in {"commit", "tag"}:
                continue
            raw = git_output("cat-file", object_type, object_id)
        except RuntimeError:
            raise RuntimeError("Git history inspection failed") from None

        header, separator, message = raw.partition(b"\n\n")
        searchable_lines = []
        for line in header.splitlines():
            # Git identity timestamps are machine-generated metadata, not numeric identifiers.
            line = re.sub(rb"\s[0-9]+ [+-][0-9]{4}$", b"", line)
            searchable_lines.append(line)
        searchable = b"\n".join(searchable_lines)
        if separator:
            searchable += b"\n" + message
        decoded = searchable.decode("utf-8", errors="replace")
        for label, pattern in [*content_rules(), ("private hostname", private_hostname)]:
            if pattern.search(decoded):
                findings.setdefault(label, set()).add(object_id)
        if hostname_pattern and hostname_pattern.search(decoded):
            findings.setdefault("local hostname", set()).add(object_id)

    for line in references.decode("utf-8", errors="replace").splitlines():
        refname = line.split("\t", 1)[0]
        for label, pattern in [*content_rules(), ("private hostname", private_hostname)]:
            if pattern.search(refname):
                findings.setdefault(label, set()).add("ref:" + refname)
        if hostname_pattern and hostname_pattern.search(refname):
            findings.setdefault("local hostname", set()).add("ref:" + refname)
    return findings


def current_hostname_pattern() -> re.Pattern[str] | None:
    hostname = socket.gethostname().strip()
    if not hostname:
        return None
    return re.compile(r"(?i)(?<![a-z0-9-])" + re.escape(hostname) + r"(?![a-z0-9-])")


def main() -> int:
    if not MANIFEST.is_file():
        print("BLOCKED: public path manifest is missing")
        return 1
    approved = {
        line.strip()
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    actual = repo_files()
    symlinks = sorted(
        path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_symlink()
    )
    unexpected, missing = sorted(actual - approved), sorted(approved - actual)
    errors = 0
    try:
        remote_names = git_output("remote").decode("utf-8", errors="replace").splitlines()
        remote_urls = [
            git_output("remote", "get-url", "--all", name).decode("utf-8", errors="replace").strip()
            for name in remote_names
        ]
        if not public_origin_is_valid(remote_names, remote_urls):
            print("BLOCKED: Git remotes are not limited to the expected public origin")
            errors += 1
        blobs = history_blobs()
        metadata_hits = history_metadata()
    except RuntimeError as exc:
        print(f"BLOCKED: {exc}")
        return 1
    if symlinks:
        print("BLOCKED: symbolic links are not allowed in the public file set: " + ", ".join(symlinks))
        errors += 1
    if unexpected:
        print("BLOCKED: paths outside the reviewed staging manifest:", ", ".join(unexpected))
        errors += 1
    if missing:
        print("BLOCKED: manifest entries not present:", ", ".join(missing))
        errors += 1
    hits: dict[str, set[str]] = {}
    local_hostname = current_hostname_pattern()
    for relative in sorted(actual & approved):
        path = ROOT / relative
        if path.is_symlink():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"BLOCKED: non-text artifact: {relative}")
            errors += 1
            continue
        for label, pattern in content_rules():
            if pattern.search(content):
                hits.setdefault(label, set()).add(relative)
        if local_hostname and (local_hostname.search(relative) or local_hostname.search(content)):
            hits.setdefault("local hostname", set()).add(relative)
    history_hits: dict[str, set[str]] = {}
    for historical_path, object_id in blobs:
        try:
            content = git_output("cat-file", "blob", object_id).decode("utf-8")
        except UnicodeDecodeError:
            history_hits.setdefault("non-text historical blob", set()).add(historical_path)
            continue
        for label, pattern in content_rules():
            if pattern.search(historical_path) or pattern.search(content):
                history_hits.setdefault(label, set()).add(historical_path)
        if local_hostname and (
            local_hostname.search(historical_path) or local_hostname.search(content)
        ):
            history_hits.setdefault("local hostname", set()).add(historical_path)
    if history_hits:
        for label, paths in sorted(history_hits.items()):
            print(f"BLOCKED: {label} in {len(paths)} historical blob(s): " + ", ".join(sorted(paths)))
        errors += 1
    if metadata_hits:
        for label, objects in sorted(metadata_hits.items()):
            print(f"BLOCKED: {label} in {len(objects)} reachable ref/commit/tag metadata object(s)")
        errors += 1
    if hits:
        for label, paths in sorted(hits.items()):
            print(f"BLOCKED: {label} in {len(paths)} file(s): " + ", ".join(sorted(paths)))
        errors += 1
    if errors:
        print("Release guard failed; matched values were suppressed.")
        return 1
    print(
        f"Release guard passed: {len(actual)} allowlisted text files, {len(blobs)} reachable history blobs, "
        "and reachable ref/commit/tag metadata; "
        "no configured scan findings or unexpected remotes."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
