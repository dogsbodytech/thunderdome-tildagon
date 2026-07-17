#!/bin/sh
# Copy only the runtime files to the badge; dev/tooling stays on the host.
mpremote mkdir apps/thunderdome
for f in app.py __init__.py metadata.json; do
    mpremote cp "$f" :apps/thunderdome/
done
mpremote reset
