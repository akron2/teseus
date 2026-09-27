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

## Required owner decisions before public release

- [ ] Confirm copyright ownership and authority to license every included file.
- [ ] Confirm Apache-2.0 is the intended and applicable license. No personal
  copyright holder or attribution has been invented in this candidate.
- [ ] Confirm rights to use the Teseus Harness name and approve the complete
  source and generated package contents.
- [ ] Review provider and Telegram data flows, operational settings, and the
  owner-ID allowlist before any live integration use.
- [ ] Perform final legal and release review before any publication.

## Live checks intentionally not performed

- Provider/Telegram requests, real credentials, external CI, and publishing were
  not used. Validate such integrations only after the owner decisions above.
