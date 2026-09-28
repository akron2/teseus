# Release checklist

## Local pre-release gates

- [x] Confirm package metadata, build source distribution and wheel offline.
- [x] Install the wheel into a fresh local virtual environment and smoke-test
  CLI bootstrap, mock dialogue, seed installation/removal, and memory actions.
- [x] Run unit, compile, import, release-guard, privacy, secret/path, history,
  fail-closed, and package-content checks without live credentials or network.
- [x] Verify documented local README commands in isolated temporary state.
- [x] Create reproducible local artifacts and SHA-256 checksums.
- [x] Keep release candidate and Git tag local; configure no remote.

## Publication authorization

- [x] Owner authorized public GitHub publication as repository `teseus` under
  Apache-2.0 in task #210; no individual copyright holder or attribution was
  invented.
- [x] README, license, tracked file set, and reachable Git history were checked
  locally with the repository's release guard.

## Before using live integrations

- [ ] Review provider and Telegram data flows, operational settings, and the
  owner-ID allowlist before any live integration use. This is not required for
  the default offline mock or for publication of the source.

## Live checks intentionally not performed

- Provider/Telegram requests, real credentials, external CI, and publishing were
  not used. Validate such integrations only after the owner decisions above.
