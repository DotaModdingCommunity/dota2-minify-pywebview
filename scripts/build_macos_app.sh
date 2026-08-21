#!/bin/bash
# Build native arm64 or x86_64 Minify.app on Mac!!
set -euo pipefail

if [ "$(uname -s)" != "Darwin" ]; then
    echo "This script must run on macOS." >&2
    exit 1
fi

cd "$(dirname "$0")"

ARCH=$(uname -m)
APP="dist/macos/Minify.app"
ROOT=".."
SRC="$ROOT/Minify"

(
    cd "$SRC/ui/web"
    npm ci
    npm run build
)

uv sync --group dev --frozen
[ ! -e "$APP" ] || chmod -R u+w "$APP"
uv run pyinstaller --clean --noconfirm --workpath build/macos --distpath dist/macos Minify-macos.spec

# Existing app writes generated metadata into bundled bin and preserves source
# directory modes while copying mods, so bundle data must remain owner-writable pls
cp "$SRC/bin/images/minify-macos.png" "$APP/Contents/Resources/bin/images/logo.png"
cp -R "$SRC/mods" "$APP/Contents/MacOS/mods"
cp "$ROOT/README.md" "$ROOT/LICENSE" "$APP/Contents/MacOS/"
for binary in Source2Viewer-CLI rg; do
    [ ! -f "$SRC/$binary" ] || cp "$SRC/$binary" "$APP/Contents/MacOS/"
done

codesign --force --deep --sign - "$APP"
chmod -R u+w "$APP"
plutil -lint "$APP/Contents/Info.plist"
codesign --verify --deep --strict "$APP"
test "$(lipo -archs "$APP/Contents/MacOS/Minify")" = "$ARCH"

VERSION=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' "$SRC/core/base.py")
ZIP="../Minify-$VERSION-macos-$ARCH.zip"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"
echo "Built: $(cd .. && pwd)/Minify-$VERSION-macos-$ARCH.zip"
