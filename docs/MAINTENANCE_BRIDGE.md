# Guarded maintenance bridge

This document defines a reviewable source projection for maintenance updates.
Only exact files named by a versioned private manifest may enter a temporary
candidate. The candidate is checked before its diff is shown or any public file
is changed. New source files require an explicit manifest update.

The bridge rejects links, hard links, sensitive-content signatures,
credential-shaped values, host-specific paths, and Git metadata in candidate
content. Deletions are represented in the candidate diff and are applied only
when the explicit apply phase is requested. The default run is read-only.

The bridge does not commit, create tags, publish releases, or push. Those remain
separate reviewed actions using the repository's release tooling.
