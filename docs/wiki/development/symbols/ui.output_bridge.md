# ui.output_bridge

Bridge between core/output.py and the pywebview window.
Buffers messages that arrive before the window is ready.

## `_flush()`

Flush buffered JS to the window. Caller must hold _lock.

<details open><summary>Source</summary>

```python
def _flush() -> None:
    """Flush buffered JS to the window. Caller must hold _lock."""
    if _window_ref is None or not _frontend_ready:
        return
    while _early_queue:
        try:
            _window_ref.evaluate_js(_early_queue.popleft())
        except Exception:
            pass

```

</details>

## `set_window(w)`

Called once from webview.start(func=) when the window is created.

<details open><summary>Source</summary>

```python
def set_window(w: Any) -> None:
    """Called once from webview.start(func=) when the window is created."""
    global _window_ref
    with _lock:
        _window_ref = w
        _flush()

```

</details>

## `mark_frontend_ready()`

Flush buffered JS once the frontend has registered its handlers.

<details open><summary>Source</summary>

```python
def mark_frontend_ready() -> None:
    """Flush buffered JS once the frontend has registered its handlers."""
    global _frontend_ready
    with _lock:
        _frontend_ready = True
        _flush()

```

</details>

## `get_window()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def get_window() -> Any:
    global _window_ref
    return _window_ref

```

</details>

## `close()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def close() -> None:
    w = get_window()
    if w is not None:
        w.destroy()

```

</details>

## `send_js(js)`

Send arbitrary JS to the window, or queue it until the frontend is ready.

<details open><summary>Source</summary>

```python
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

```

</details>

## `push_line(text_or_id)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def push_line(text_or_id: str | None, *args: object, msg_type: str | None = None) -> None:
    payload = json.dumps(
        {
            "raw": text_or_id,
            "args": list(args),
            "type": msg_type,
            "prefix": output.PREFIX.get(msg_type or "", ""),
        }
    )
    send_js(f"window.__termPush({payload})")

```

</details>

## `push_separator()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def push_separator() -> None:
    send_js("window.__termSep()")

```

</details>

## `push_clear()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def push_clear() -> None:
    send_js("window.__termClear()")

```

</details>

## `register_with_output()`

Register this bridge as the output handler for core/output.py.

<details open><summary>Source</summary>

```python
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

```

</details>
