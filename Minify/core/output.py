"Agnostic output interface"

import contextlib
import sys
import threading
from collections.abc import Callable
from typing import Any

Sink = Callable[..., Any]
_send: Sink | None = None  # global sink (window / cli)
_local = threading.local()  # thread-local capture sink for mod utilities

_ANSI = sys.stdout is not None and bool(getattr(sys.stdout, "isatty", lambda: False)())

RED = "\033[38;2;255;0;0m" if _ANSI else ""
YELLOW = "\033[38;2;255;255;0m" if _ANSI else ""
GREEN = "\033[38;2;0;255;0m" if _ANSI else ""
BOLD = "\033[1;4m" if _ANSI else ""  # section: bold + underline
DIM = "\033[2m" if _ANSI else ""  # detail: dimmed
RESET = "\033[0m" if _ANSI else ""

# Single source of truth for how each message type is labeled.
# Both the CLI fallback and the GUI bridge read from here, so the
# two renderers cannot drift apart.
PREFIX = {
    "error": "[ERROR] ",
    "warning": "[WARNING] ",
    "success": "[SUCCESS] ",
    "section": "",
    "detail": "",
}

_STYLE = {
    "error": BOLD + RED,
    "warning": BOLD + YELLOW,
    "success": BOLD + GREEN,
    "section": BOLD,
    "detail": DIM,
}


def _resolve(text_or_id: str, *args: Any) -> str:
    """Resolve &-prefixed localization key with format args."""
    try:
        from ui import localization
    except ImportError:
        localization = None
    text = text_or_id
    if localization is not None and text_or_id.startswith("&"):
        text = localization.localization_dict.get(text_or_id.replace("&", ""), text_or_id)
    if args:
        try:
            text = text.format(*args)
        except (IndexError, KeyError):
            pass
    return text.lstrip()


@contextlib.contextmanager
def capture_thread(sink: Sink):
    """Route only THIS thread's add_text to `sink` while the context is active."""
    previous = getattr(_local, "sink", None)
    _local.sink = sink
    try:
        yield
    finally:
        if previous is None:
            try:
                delattr(_local, "sink")
            except AttributeError:
                pass
        else:
            _local.sink = previous


def _console_line(text: str, msg_type: str | None) -> None:
    prefix = PREFIX.get(msg_type or "", "")
    color = _STYLE.get(msg_type or "", "")
    if msg_type == "detail":
        text = "   " + text
    try:
        if sys.stdout is not None:
            print(f"{color}{prefix}{text}{RESET}")
    except UnicodeEncodeError:
        if sys.stdout is not None:
            print(f"{color}{prefix}{text.encode('ascii', 'replace').decode('ascii')}{RESET}")


def add_text(text_or_id: str, *args: Any, msg_type: str | None = None) -> Any:
    local_sink = getattr(_local, "sink", None)
    if local_sink is not None:
        return local_sink(text_or_id, *args, msg_type=msg_type)
    if _send is not None:
        return _send(text_or_id, *args, msg_type=msg_type)
    _console_line(_resolve(text_or_id, *args), msg_type)
    return None


def add_section(text_or_id: str, *args: Any) -> Any:
    """Emit a phase/section header line (styled bold in both renderers)."""
    return add_text(text_or_id, *args, msg_type="section")


def add_detail(text_or_id: str, *args: Any) -> Any:
    """Emit a dimmed secondary line (paths, tracebacks, list items)."""
    return add_text(text_or_id, *args, msg_type="detail")


def add_separator() -> None:
    if _send is not None:
        _send(None, msg_type="__sep__")
    else:
        print("-" * 50)


def clean() -> None:
    if _send is not None:
        _send(None, msg_type="__clean__")
