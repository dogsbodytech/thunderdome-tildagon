#!/bin/sh
# Copy the whole app tree to the badge, skipping caches.
# Everything ships except __pycache__ (and .git, which can't live on the badge
# and would make the copy hang). ponytail: assumes no spaces in paths.
set -e

prune='( -name __pycache__ -o -name .git )'

mpremote mkdir apps/thunderdome 2>/dev/null || true

# Recreate the directory tree on the badge (parents print before children).
find . \( -name __pycache__ -o -name .git \) -prune -o -type d ! -name . -print | while read -r d; do
    mpremote mkdir "apps/thunderdome/${d#./}" 2>/dev/null || true
done

# Copy every file.
find . \( -name __pycache__ -o -name .git \) -prune -o -type f -print | while read -r f; do
    mpremote cp "$f" ":apps/thunderdome/${f#./}"
done

mpremote reset
