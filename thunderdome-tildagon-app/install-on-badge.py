#!/bin/sh
mpremote mkdir apps/thunderdome
for f in ./*; do
    [ "$f" = "./__pycache__" ] && continue
    mpremote cp "$f" :apps/thunderdome/
done
mpremote reset
