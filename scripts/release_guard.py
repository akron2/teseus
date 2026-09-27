"""Local allowlist and low-noise secret/privacy checks; never prints matches."""

import re
import sys
from pathlib import Path

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
    unexpected, missing = sorted(actual - approved), sorted(approved - actual)
    errors = 0
    if unexpected:
        print("BLOCKED: paths outside the reviewed staging manifest:", ", ".join(unexpected))
        errors += 1
    if missing:
        print("BLOCKED: manifest entries not present:", ", ".join(missing))
        errors += 1
    hits: dict[str, set[str]] = {}
    for relative in sorted(actual & approved):
        path = ROOT / relative
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"BLOCKED: non-text artifact: {relative}")
            errors += 1
            continue
        for label, pattern in content_rules():
            if pattern.search(content):
                hits.setdefault(label, set()).add(relative)
    if hits:
        for label, paths in sorted(hits.items()):
            print(f"BLOCKED: {label} in {len(paths)} file(s): " + ", ".join(sorted(paths)))
        errors += 1
    if errors:
        print("Release guard failed; matched values were suppressed.")
        return 1
    print(f"Release guard passed: {len(actual)} allowlisted text files; no configured scan findings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
