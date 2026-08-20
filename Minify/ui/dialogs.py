"Native file dialog helpers for mod scripts and internal use."

import webview
from ui import output_bridge


def select_file(file_types: tuple[str, ...] | None = None, directory: str | None = None) -> str | None:
    """Open a native file picker. Returns the selected path or None if cancelled."""
    w = output_bridge.get_window()
    if w is None:
        return None
    if file_types:
        selected = w.create_file_dialog(webview.FileDialog.OPEN, file_types=(file_types,), directory=directory or "")
    else:
        selected = w.create_file_dialog(webview.FileDialog.OPEN, directory=directory or "")
    return selected[0] if selected else None
