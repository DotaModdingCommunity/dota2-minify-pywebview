# ui.web_window

pywebview window launcher (replaces DearPyGui window).

## `_API()`

*No documentation available.*

<details open><summary>Source</summary>

```python
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

```

</details>

## `_rgb_to_colorref(r, g, b)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def _rgb_to_colorref(r: int, g: int, b: int) -> int:
    return (b << 16) | (g << 8) | r

```

</details>

## `_on_closing()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def _on_closing() -> bool | None:
    if actions.is_locked():
        return False
    return None

```

</details>

## `_style_window(window)`

*No documentation available.*

<details open><summary>Source</summary>

```python
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

```

</details>

## `_resolve_zoom()`

Resolve the UI zoom from config (clamped to the supported range).

<details open><summary>Source</summary>

```python
def _resolve_zoom() -> float:
    """Resolve the UI zoom from config (clamped to the supported range)."""
    try:
        v = float(_config.get("ui_zoom", 1.0))
    except (TypeError, ValueError):
        v = 1.0
    return min(actions.ZOOM_MAX, max(actions.ZOOM_MIN, v))

```

</details>

## `_window_factor(screen)`

Window auto-size factor from logical desktop width (cross-platform).

<details open><summary>Source</summary>

```python
def _window_factor(screen: Screen) -> float:
    """Window auto-size factor from logical desktop width (cross-platform)."""
    try:
        return min(1.6, max(1.0, screen.width / 1920))
    except Exception:
        return 1.0

```

</details>

## `_base_size()`

Base window size (independent of zoom), clamped to 92% of the screen.

<details open><summary>Source</summary>

```python
def _base_size() -> tuple[int, int]:
    """Base window size (independent of zoom), clamped to 92% of the screen."""
    auto = _window_factor(_screen) if _screen else 1.0
    if _screen:
        return (
            min(round(800 * auto), int(_screen.width * 0.92)),
            min(round(600 * auto), int(_screen.height * 0.92)),
        )
    return round(800 * auto), round(600 * auto)

```

</details>

## `_apply_ui_zoom(zoom)`

Persist a zoom value. The window is sized once at launch; zoom is pure CSS.

<details open><summary>Source</summary>

```python
def _apply_ui_zoom(zoom: float) -> dict[str, Any]:
    """Persist a zoom value. The window is sized once at launch; zoom is pure CSS."""
    try:
        v = min(actions.ZOOM_MAX, max(actions.ZOOM_MIN, float(zoom)))
    except (TypeError, ValueError):
        v = 1.0
    _config.set("ui_zoom", v)
    return {"ok": True, "data": None, "error": None}

```

</details>

## `create_window()`

*No documentation available.*

<details open><summary>Source</summary>

```python
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

```

</details>
