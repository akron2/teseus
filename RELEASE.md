# Releasing

This repository is the reviewed public source projection. Never copy files
automatically from another working tree. For each intended change, review the
diff, confirm every added/changed path belongs in `scripts/public-files.txt`,
and run `python scripts/release_guard.py`. The guard checks the allowlist,
symlinks, configured public origin, current files, every reachable Git history
blob, and reachable ref/commit/annotated-tag metadata; a finding blocks
publication and matched content is suppressed.

Update `CHANGELOG.md` with the release entry. A failed prerelease candidate is
retired permanently even if its public tag reference is later removed; every
subsequent attempt must use a fresh, incremented candidate identifier. Keep
`VERSION`, `pyproject.toml`, and `harness.__version__` aligned. A prerelease tag such as
`v0.1.0-rc3` uses the matching base package version `0.1.0` and changelog
heading `0.1.0-rc3`. Install the pinned build tools in a disposable Python 3.11
virtual environment (`build==1.2.2.post1`, `setuptools==75.8.0`,
`wheel==0.45.1`), then commit the reviewed public tree on `main`.

With the clean commit based on the fetched `origin/main`, first run the complete
safe dry run:

```sh
python scripts/release.py v0.1.0-rc3 --dry-run
```

It validates branch/status/version/changelog/tag availability, the privacy
guard and complete available history, unit/compile/import checks, two
byte-for-byte reproducible wheel+sdist builds, installation of both artifacts,
and the literal Quick start and self-contained README smoke commands. A
successful dry run leaves no tag or build output in the source tree. After it
passes, push the reviewed commit to `main` and verify the local `main` equals
`origin/main`. Run the same command without `--dry-run` to create the annotated
tag, then push only that tag using `git push origin v0.1.0-rc3`. GitHub Actions
repeats the checks in a clean runner, creates SHA-256 checksums, and publishes
a public GitHub Release with both artifacts. The workflow does not publish to
PyPI.

The release command constructs and scans the exact future tag metadata before
creating it, uses a fixed neutral project tagger, then repeats the privacy guard
after installing the local ref. A post-creation guard failure removes that new
local ref and never contacts the remote. Do not add identity variables to the
tagging environment or rely on local Git configuration.

If any gate, workflow, or privacy check fails, stop: do not force-push, move, or
reuse a tag. Review diagnostics locally without copying sensitive matches into
issues or logs, fix the public source, increment to a fresh prerelease tag, and
repeat the full process. Remove a remote ref only for an explicitly confirmed
failed tag with no release, recording its object ID privately first; leave its
orphan object untouched and request GitHub Support purge if necessary. Verify
release downloads and checksums without credentials before announcing.
