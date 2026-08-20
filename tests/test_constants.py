import importlib

from core import base, constants


def test_s2v_win_arm64_uses_windows_build(monkeypatch):
    monkeypatch.setattr(base, "is_win", True)
    monkeypatch.setattr(base, "MACHINE", "arm64")
    monkeypatch.setattr(base, "ARCHITECTURE", "64bit")
    importlib.reload(constants)
    try:
        assert constants.s2v_latest.endswith("cli-windows-x64.zip")
    finally:
        importlib.reload(constants)


def test_s2v_win_amd64_uses_windows_build(monkeypatch):
    monkeypatch.setattr(base, "is_win", True)
    monkeypatch.setattr(base, "MACHINE", "x86_64")
    monkeypatch.setattr(base, "ARCHITECTURE", "64bit")
    importlib.reload(constants)
    try:
        assert constants.s2v_latest.endswith("cli-windows-x64.zip")
    finally:
        importlib.reload(constants)
