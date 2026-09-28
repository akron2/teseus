#!/usr/bin/env bash
set -euo pipefail

test -n "${RELEASE_TAG:-}"
test "${RELEASE_REF:-}" = "refs/tags/$RELEASE_TAG"

tag_ref="refs/tags/$RELEASE_TAG"
git check-ref-format "$tag_ref"

# checkout may have installed the peeled commit as a lightweight tag. Remove
# only that runner-local ref before fetching the authoritative remote tag object.
if git show-ref --verify --quiet "$tag_ref"; then
  git update-ref -d "$tag_ref"
fi

git fetch --no-tags origin "+$tag_ref:$tag_ref"
