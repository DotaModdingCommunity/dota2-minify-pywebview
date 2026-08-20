"""
Bridge between core/output.py and the pywebview window.
Buffers messages that arrive before the window is ready.
"""

import collections
import json
import threading
from typing import Any

from core import output

_window_ref: Any = None
_frontend_ready = False
_lock = threading.RLock()
_early_queue: collections.deque[str] = collections.deque()


def _flush() -> None:
    """Flush buffered JS to the window. Caller must hold _lock."""
    if _window_ref is None or not _frontend_ready:
        return
    while _early_queue:
        try:
            _window_ref.evaluate_js(_early_queue.popleft())
        except Exception:
            pass


def set_window(w: Any) -> None:
    """Called once from webview.start(func=) when the window is created."""
    global _window_ref
    with _lock:
        _window_ref = w
        _flush()


def mark_frontend_ready() -> None:
    """Flush buffered JS once the frontend has registered its handlers."""
    global _frontend_ready
    with _lock:
        _frontend_ready = True
        _flush()


def get_window() -> Any:
    global _window_ref
    return _window_ref


def close() -> None:
    w = get_window()
    if w is not None:
        w.destroy()


def send_js(js: str) -> None:
    """Send arbitrary JS to the window, or queue it until the frontend is ready."""
    with _lock:
        if _frontend_ready and _window_ref is not None:
            try:
                _window_ref.run_js(js)
            except Exception:
                pass
        else:
            _early_queue.append(js)


def push_line(text_or_id: str | None, *args: object, msg_type: str | None = None) -> None:
    payload = json.dumps(
        {
            "raw": text_or_id,
            "args": list(args),
            "type": msg_type,
        }
    )
    send_js(f"window.__termPush({payload})")


def push_separator() -> None:
    send_js("window.__termSep()")


def push_clear() -> None:
    send_js("window.__termClear()")


def register_with_output() -> None:
    """Register this bridge as the output handler for core/output.py."""

    def _send(text_or_id: str | None, *args: object, msg_type: str | None = None) -> bool:
        if msg_type == "__sep__":
            push_separator()
            return True
        if msg_type == "__clean__":
            push_clear()
            return True
        if text_or_id is None:
            return True
        push_line(text_or_id, *args, msg_type=msg_type)
        return True

    output._send = _send
