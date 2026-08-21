# -*- mode: python ; coding: utf-8 -*-
# ruff: noqa: F821 -- PyInstaller injects spec globals.
import os
import re


root = os.path.abspath(os.path.join(SPECPATH, ".."))
with open(os.path.join(root, "Minify", "core", "base.py"), encoding="utf-8") as file:
    version = re.search(r'^VERSION = "([^"]+)"', file.read(), re.MULTILINE).group(1)

a = Analysis(
    [os.path.join(root, "Minify", "__main__.py")],
    pathex=[os.path.join(root, "Minify")],
    datas=[
        (os.path.join(root, "Minify", "ui", "web", "dist"), "ui/web/dist"),
        (os.path.join(root, "Minify", "bin"), "bin"),
    ],
    hiddenimports=["webview.platforms.cocoa"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Minify", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="Minify")
app = BUNDLE(
    coll,
    name="Minify.app",
    icon=os.path.join(root, "Minify", "bin", "images", "minify-macos.icns"),
    bundle_identifier="io.github.egezenn.dota2-minify",
    version=version,
)
