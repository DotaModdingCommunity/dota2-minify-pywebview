# -*- mode: python ; coding: utf-8 -*-
import glob
import os
import platform
import sys
import sysconfig


# Import version utility to generate metadata files
sys.path.append(os.path.abspath(SPECPATH))
try:
    import version_util

    if platform.system() == "Windows":
        version_util.generate_metadata()
except ImportError:
    print("Warning: version_util not found, skipping metadata generation")
except Exception as e:
    print(f"Error generating metadata: {e}")

# pywebview loads its platform backend dynamically (see webview.guilib), so it
# must be forced into the build for whichever platform this spec is built on.
# On Linux, PyInstaller's pre-safe-import hooks cover most gi.repository
# modules but NOT WebKit2, which webview/platforms/gtk.py imports directly —
# without an explicit hiddenimport the frozen app depends on a system typelib
# and can crash at startup. Also note that gi bindings bundle the typelibs, so
# end users still need the runtime libraries (libwebkit2gtk-4.1-0 etc.).
if platform.system() == "Windows":
    hiddenimports = ["webview.platforms.winforms"]
elif platform.system() == "Linux":
    hiddenimports = ["webview.platforms.gtk"] + [
        "gi.repository." + name
        for name in ("Gtk", "Gdk", "GLib", "Gio", "GObject", "Pango", "cairo", "WebKit2")
    ]
else:
    hiddenimports = ["webview.platforms.cocoa"]

# Runtime assets are resolved against sys._MEIPASS (PyInstaller 6 onedir:
# dist/Minify/_internal/) — see ui/web_window.py (_base) and core/base.py (bin_dir).
datas = [
    ("../Minify/ui/web/dist", "ui/web/dist"),
    ("../Minify/bin", "bin"),
]

a = Analysis(
    ["../Minify/__main__.py"],
    pathex=["../Minify"],
    datas=datas,
    hiddenimports=hiddenimports,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Minify",
    console=False,
    icon=[os.path.join(SPECPATH, "..", "Minify", "bin", "images", "favicon.ico")] if platform.system() == "Windows" else None,
    version="ffi_main.txt" if os.path.exists("ffi_main.txt") else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="Minify",
)

try:
    os.remove("ffi_main.txt")
except:
    pass
