#!/bin/bash
# Build script for the macOS portable release (manual — macOS is intentionally
# not part of the CI release matrix).
#
# Usage: ./build_mac.sh [-nosign]
#   -nosign  skip the ad-hoc code signature (not recommended on Apple Silicon)
#
# Produces ../Minify-<ver>-macos.zip. Upload it to the GitHub release manually,
# named exactly Minify-<ver>-macos.zip so the in-app updater finds it.
#
# Note: pywebview's cocoa backend (pyobjc) is pulled automatically on macOS via
# platform markers, so no extra backend install is needed here. For a real
# release, replace the ad-hoc signature with a Developer ID signature +
# notarization (codesign --options runtime + notarytool submit).
set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
    echo "This script must be run on macOS (pyobjc/cocoa build + codesign)." >&2
    exit 1
fi

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

echo "Installing dependencies..."
uv sync --group dev

rm -rf build dist

echo "Building with PyInstaller..."
uv run pyinstaller Minify.spec

echo "Copying project data..."
cp -r "$SRC/mods" "$APP/mods"
cp "$SRC/README.md" "$APP/README.md"
cp "$SRC/LICENSE" "$APP/LICENSE"
if [ -f "$SRC/Source2Viewer-CLI" ]; then
    cp "$SRC/Source2Viewer-CLI" "$APP/"
fi
if [ -f "$SRC/rg" ]; then
    cp "$SRC/rg" "$APP/"
fi
chmod +x "$APP/Minify"

if [ "${1:-}" != "-nosign" ]; then
    echo "Ad-hoc signing (arm64 binaries must be signed to run)..."
    find "$APP/_internal" -type f \( -name "*.so" -o -name "*.dylib" \) -exec codesign --force -s - {} \;
    codesign --force --deep -s - "$APP/Minify"
fi

VERSION=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' "$SRC/core/base.py")
ZIP="../Minify-$VERSION-macos.zip"
echo "Packing $ZIP..."
(
    cd "$APP"
    ditto -c -k --sequesterRsrc . "../../../$ZIP"
)
echo "Done: $(cd .. && pwd)/$ZIP"