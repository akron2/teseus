# Changelog

## 0.1.0-rc5 — 2026-09-28

Safely replace a checkout-created local lightweight release tag with the exact
remote annotated tag object in the ephemeral release runner, and cover tag
clobbering and invalid ref names with regression tests.

## 0.1.0-rc4 — 2026-09-28

Make release jobs fetch the full Git history and annotated tag object explicitly,
and block artifact building unless the checked-out release tag is locally
available as the expected annotated tag.

## 0.1.0-rc3 — 2026-09-28

Retire the failed prior release candidate and make release-tag metadata
independent of ambient machine identity. Preflight the exact neutral annotated
tag metadata and remove a newly created local tag if the post-creation privacy
guard fails.

## 0.1.0-rc2 — 2026-09-28

Document and automate the reviewed public release process. Add a guarded
maintainer release command, reproducible artifact verification, and a
least-privilege GitHub Actions workflow for public GitHub Releases.

## 0.1.0 — 2026-09-27

Initial 0.1.0 release candidate for Teseus, based on the reviewed release
candidate. Includes local bootstrap and SQLite state, a deterministic mock
dialogue, reversible memory selection, an optional environment-configured
OpenAI-compatible adapter, and an explicitly enabled owner-only Telegram
adapter. Runtime migrations and the optional public synthetic seed are packaged
with the Python distribution.

Publication to the public GitHub repository `teseus` under Apache-2.0 is
authorized by the owner in task #210. No individual copyright holder or
attribution has been invented.
