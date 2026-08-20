"""pywebview window launcher (replaces DearPyGui window)."""

import ctypes
import json
import os
import sys
import threading
from ctypes import byref, c_int, sizeof
from pathlib import Path
from typing import Any, Callable, cast

import ui.actions as actions
import ui.modal_shared as modal_shared
import webview
from core import base
from core import config as _config
from ui import output_bridge
from webview.dom import DOMEventHandler
from webview.screen import Screen


_API_WHITELIST = {
    "modal_respond",
    "patch",
    "uninstall",
    "get_mods",
    "set_mod_enabled",
    "get_mod_preview",
    "get_mod_file_preview",
    "get_mod_notes_html",
    "refresh_mods",
    "get_settings",
    "save_settings",
    "get_mod_settings",
    "save_mod_settings",
    "run_mod_utility",
    "reset_mod_settings",
    "reset_all_mod_settings",
    "get_localization",
    "set_language",
    "get_available_langs",
    "resolve_steam_path",
    "get_steam_path_state",
    "get_steam_accounts",
    "get_app_info",
    "open_url",
    "get_setup_state",
    "save_setup",
    "get_welcome_state",
    "dismiss_welcome",
    "get_d2pfx_categories",
    "get_d2pfx_mods",
    "get_d2pfx_preview",
    "get_d2pfx_state",
    "reload_d2pfx",
    "refresh_d2pfx_catalogue",
    "clear_d2pfx_cache",
    "get_d2pfx_counts",
    "get_d2pfx_selected_variants",
    "set_d2pfx_selected_variants",
    "toggle_d2pfx_mod",
    "open_path",
    "create_debug_zip",
    "compile_assets",
    "set_all_mods",
    "wipe_language_paths",
    "extract_workshop_tools",
    "launch_steam",
    "kill_steam",
    "validate_dota2",
    "select_compile_dir",
    "compile_from_custom",
    "open_file_dialog",
    "restart_steam_and_apply",
    "get_setup_data",
    "reset_settings",
    "setup_flow_done",
    "set_ui_zoom",
}


class _API:
    def frontend_ready(self):
        output_bridge.mark_frontend_ready()

    def modal_respond(self, waiter_id: str, label: str):
        return modal_shared.respond(waiter_id, label)

    def setup_flow_done(self, waiter_id: str, result: str):
        return modal_shared.setup_flow_done(waiter_id, result)

    def set_ui_zoom(self, zoom: float):
        return _apply_ui_zoom(zoom)

    def __getattr__(self, name: str) -> Callable[..., Any]:
        if name not in _API_WHITELIST:
            raise AttributeError(f"API '{name}' not exposed")
        if not actions._init_done and name not in actions._EARLY_ALLOW:

            def _block(*_a: Any, **_kw: Any) -> dict[str, Any]:
                return {"ok": False, "data": None, "error": "Initializing"}

            return _block
        return getattr(actions, name)

    def __dir__(self) -> list[str]:
        return list(super().__dir__()) + sorted(_API_WHITELIST)


_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_BORDER_COLOR = 34
_DWMWA_CAPTION_COLOR = 35
_DWMWA_TEXT_COLOR = 36


def _rgb_to_colorref(r: int, g: int, b: int) -> int:
    return (b << 16) | (g << 8) | r


_base = Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


def _on_closing() -> bool | None:
    if actions.is_locked():
        return False
    return None


def _style_window(window: Any) -> None:
    if not base.is_win:
        return

    try:
        from ctypes import wintypes

        hwnd = wintypes.HWND(window.native.Handle.ToInt32())
    except Exception:
        return

    dwmapi = ctypes.WinDLL("dwmapi")
    dwmapi.DwmSetWindowAttribute(
        hwnd,
        _DWMWA_USE_IMMERSIVE_DARK_MODE,
        byref(c_int(1)),
        sizeof(c_int),
    )
    dwmapi.DwmSetWindowAttribute(
        hwnd,
        _DWMWA_CAPTION_COLOR,
        byref(c_int(_rgb_to_colorref(15, 15, 18))),
        sizeof(c_int),
    )
    dwmapi.DwmSetWindowAttribute(
        hwnd,
        _DWMWA_TEXT_COLOR,
        byref(c_int(_rgb_to_colorref(200, 200, 200))),
        sizeof(c_int),
    )
    dwmapi.DwmSetWindowAttribute(
        hwnd,
        _DWMWA_BORDER_COLOR,
        byref(c_int(_rgb_to_colorref(46, 46, 46))),
        sizeof(c_int),
    )


_screen: Any = None


def _resolve_zoom() -> float:
    """Resolve the UI zoom from config (clamped to the supported range)."""
    try:
        v = float(_config.get("ui_zoom", 1.0))
    except (TypeError, ValueError):
        v = 1.0
    return min(actions.ZOOM_MAX, max(actions.ZOOM_MIN, v))


def _window_factor(screen: Screen) -> float:
    """Window auto-size factor from logical desktop width (cross-platform)."""
    try:
        return min(1.6, max(1.0, screen.width / 1920))
    except Exception:
        return 1.0


def _base_size() -> tuple[int, int]:
    """Base window size (independent of zoom), clamped to 92% of the screen."""
    auto = _window_factor(_screen) if _screen else 1.0
    if _screen:
        return (
            min(round(800 * auto), int(_screen.width * 0.92)),
            min(round(600 * auto), int(_screen.height * 0.92)),
        )
    return round(800 * auto), round(600 * auto)


def _apply_ui_zoom(zoom: float) -> dict[str, Any]:
    """Persist a zoom value. The window is sized once at launch; zoom is pure CSS."""
    try:
        v = min(actions.ZOOM_MAX, max(actions.ZOOM_MIN, float(zoom)))
    except (TypeError, ValueError):
        v = 1.0
    _config.set("ui_zoom", v)
    return {"ok": True, "data": None, "error": None}


def create_window():
    global _screen
    api = _API()
    url = os.environ.get("MINIFY_DEV_URL") or str(_base / "ui" / "web" / "dist" / "index.html")

    zoom = _resolve_zoom()
    win_w, win_h = _base_size()
    try:
        _screen = webview.screens[0]
        x = (_screen.width - win_w) // 2
        y = (_screen.height - win_h) // 2
    except Exception:
        x = y = None

    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}zoom={zoom}"

    w = webview.create_window(
        "Minify",
        url,
        js_api=api,
        width=win_w,
        height=win_h,
        x=x,
        y=y,
        min_size=(win_w, win_h),
        resizable=True,
        background_color="#0d0d0d",
    )
    assert w is not None
    w.events.closing += _on_closing
    w.events.before_show += _style_window

    def _install_dropped_mod(path: str, progress_callback: Callable[[float, str], None] | None = None) -> bool:
        """Delegate to actions — avoids duplicating install logic."""
        try:
            actions._install_mod_from_drop(path, progress_callback=progress_callback)
            return True
        except Exception as e:
            from core import log, output

            error = str(e) or "Unknown error"
            log.write_warning(f"Failed to install dropped mod {path}: {error}")
            output.add_text("&drop_install_failed", os.path.basename(path), error, msg_type="error")
            return False

    _drop_warned = False

    def _on_drop_files(event: dict[str, Any]) -> None:
        """DOM drop callback — hands off to a daemon thread immediately so the
        pywebview message loop stays free to process JS/repaint calls."""
        nonlocal _drop_warned
        if actions.is_locked():
            output_bridge.send_js('window.__dropComplete({"ok": false, "error": "locked"})')
            return
        files = event.get("dataTransfer", {}).get("files", [])
        paths = [f["pywebviewFullPath"] for f in files if f.get("pywebviewFullPath")]

        def _work(paths: list[str] = paths) -> None:
            nonlocal _drop_warned
            from core import log, mods_shared

            # All send_js calls happen from this thread so the event-handler
            # returns instantly and the JS engine can repaint between updates.
            output_bridge.send_js("window.__hideDropOverlay()")
            if not paths:
                if files and not _drop_warned:
                    _drop_warned = True
                    log.write_warning(
                        "Drop event received but no file paths were resolved "
                        + "(pywebviewFullPath missing) — drag-and-drop may be limited on this platform"
                    )
                return
            modal_shared.show_progress(["&status_installing_mod"])
            n = len(paths)
            failures = []
            last_pct = -1

            def _throttle_pct(pct: float, status: str) -> None:
                # Only push when the visible percent changes so we don't flood
                # the JS bridge with run_js calls (keeps the UI snappy while
                # the bar still fills smoothly).
                nonlocal last_pct
                rounded = int(pct * 100)
                if rounded != last_pct:
                    last_pct = rounded
                    modal_shared.set_progress(pct, status)

            for i, path in enumerate(paths):
                base_frac = i / n if n > 1 else 0.0
                file_frac = 1.0 / n

                def _file_progress(frac: float, status: str, _base: float = base_frac, _inc: float = file_frac) -> None:
                    _throttle_pct(_base + frac * _inc, status)

                # Show progress *before* the heavy work so the bar moves
                # as each file starts, not after it finishes.
                _throttle_pct(base_frac, os.path.basename(path))
                if not _install_dropped_mod(path, progress_callback=_file_progress):
                    failures.append(os.path.basename(path))
            modal_shared.set_progress(100, "&status_done")
            mods_shared.scan_mods(force=True)
            modal_shared.hide_progress()
            payload = json.dumps({"ok": not failures, "error": "; ".join(failures) or None})
            output_bridge.send_js(f"window.__dropComplete({payload})")

        threading.Thread(target=_work, daemon=True).start()

    def _on_started() -> None:
        output_bridge.set_window(w)
        # Immediately hide the drop overlay in JS the moment the file lands,
        # before pywebview's IPC serialises the event and calls Python.
        # Without this the overlay stays frozen for the entire IPC round-trip.
        w.run_js(
            "window.addEventListener('drop', function(){"
            + "  if(window.__hideDropOverlay) window.__hideDropOverlay();"
            + "}, true);"
        )
        try:
            doc = w.dom.document
            events = cast(Any, doc.events)

            def _noop(_e: Any) -> None:
                pass

            events.dragover += DOMEventHandler(_noop, True, False, debounce=500)
            events.drop += DOMEventHandler(_on_drop_files, True, False)
        except Exception:
            from core import log

            log.write_warning("Could not register drop listeners — drag-and-drop disabled")

    icon_name = "favicon.ico" if base.is_win else "logo.png"
    ico = _base / "bin" / "images" / icon_name
    icon_path = str(ico) if ico.exists() else None
    webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = False
    webview.start(func=_on_started, icon=icon_path, debug=_config.get("debug_env", False))
