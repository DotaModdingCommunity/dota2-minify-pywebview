#!/bin/bash
# Build script for the Linux portable release.
# Mirrors the Linux leg of .github/workflows/release.yml so releases can be
# produced locally. The GTK backend (PyGObject) is compiled from an sdist by
# `pip install "pywebview[gtk]"` — it needs the build deps from the workflow:
# libglib2.0-dev libgirepository1.0-dev libcairo2-dev python3-dev pkg-config gcc.
set -euo pipefail

cd "$(dirname "$0")"

FRONTEND_DIR="../Minify/ui/web"
SRC="../Minify"
APP="dist/Minify"

echo "Building frontend..."
(
    cd "$FRONTEND_DIR"
    npm ci
    npm run build
)

rm -rf build dist

uv run pyinstaller Minify.spec

if [ "${1:-}" = "-sym" ]; then
    ln -s "$(pwd)/../Minify/mods" "$APP/mods"
    if [ -d "$SRC/config" ]; then
        ln -s "$(pwd)/../Minify/config" "$APP/config"
    fi
    ln -s "$(pwd)/../README.md" "$APP/README.md"
    ln -s "$(pwd)/../LICENSE" "$APP/LICENSE"
    if [ -f "$SRC/Source2Viewer-CLI" ]; then
        ln -s "$(pwd)/../Minify/Source2Viewer-CLI" "$APP/Source2Viewer-CLI"
    fi
    if [ -f "$SRC/rg" ]; then
        ln -s "$(pwd)/../Minify/rg" "$APP/rg"
    fi
else
    cp -r "$SRC/mods" "$APP/mods"
    if [ -d "$SRC/config" ]; then
        cp -r "$SRC/config" "$APP/"
    fi
    cp "$SRC/README.md" "$APP/README.md"
    cp "$SRC/LICENSE" "$APP/LICENSE"
    if [ -f "$SRC/Source2Viewer-CLI" ]; then
        cp "$SRC/Source2Viewer-CLI" "$APP/"
    fi
    if [ -f "$SRC/rg" ]; then
        cp "$SRC/rg" "$APP/"
    fi
fi

chmod +x "$APP/Minify"

if [ "${1:-}" != "-sym" ]; then
    VERSION=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' "$SRC/core/base.py")
    echo "Packing Minify-$VERSION-linux.zip..."
    (
        cd "$APP"
        7z a -tzip -mm=lzma -mx=9 "../../../Minify-$VERSION-linux.zip" ./*
    )
    echo "Done: $(pwd)/../Minify-$VERSION-linux.zip"
fi