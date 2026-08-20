# ui.modal_shared

Unified modal internals.

show() blocks a daemon thread on a threading.Event
until JS calls api.modal_respond().

## `_wait_for_response(event)`

Wait for JS to respond. Indefinite — the modal is user-driven; the
thread only resumes when the user clicks (or the app exits).

<details open><summary>Source</summary>

```python
def _wait_for_response(event: threading.Event) -> None:
    """Wait for JS to respond. Indefinite — the modal is user-driven; the
    thread only resumes when the user clicks (or the app exits)."""
    event.wait()

```

</details>

## `show(title, messages, buttons)`

Push a blocking modal to the JS side and wait for the user to click.
Returns the label string of the clicked button.
MUST be called from a daemon worker thread — blocks until JS responds.

<details open><summary>Source</summary>

```python
def show(title: str, messages: list[str], buttons: list[dict[str, object] | str], **_: object) -> str | None:
    """
    Push a blocking modal to the JS side and wait for the user to click.
    Returns the label string of the clicked button.
    MUST be called from a daemon worker thread — blocks until JS responds.
    """
    assert threading.current_thread() is not threading.main_thread(), (
        "modal_shared.show() must not be called from the main thread (it blocks waiting for a JS response)."
    )
    button_labels = [b["label"] if isinstance(b, dict) else b for b in buttons]

    waiter_id = str(uuid.uuid4())
    event = threading.Event()

    with _modal_lock:
        _waiters[waiter_id] = (event, None)

    from ui import output_bridge

    payload = json.dumps({"title": title, "messages": messages, "buttons": button_labels, "id": waiter_id})
    output_bridge.send_js(f"window.__modalPush({payload})")
    _wait_for_response(event)

    with _modal_lock:
        return _waiters.pop(waiter_id, (None, None))[1]

```

</details>

## `respond(waiter_id, label)`

Called by api.modal_respond() from the JS side.

<details open><summary>Source</summary>

```python
def respond(waiter_id: str, label: str) -> None:
    """Called by api.modal_respond() from the JS side."""
    with _modal_lock:
        if waiter_id in _waiters:
            event, _ = _waiters[waiter_id]
            _waiters[waiter_id] = (event, label)
            event.set()

```

</details>

## `show_setup_flow(pending)`

Send a list of (mod_name, message) tuples to the JS setup wizard and block.

<details open><summary>Source</summary>

```python
def show_setup_flow(pending: list[tuple[str, str]]) -> str | None:
    """Send a list of (mod_name, message) tuples to the JS setup wizard and block."""
    assert threading.current_thread() is not threading.main_thread(), (
        "modal_shared.show_setup_flow() must not be called from the main thread."
    )
    waiter_id = str(uuid.uuid4())
    event = threading.Event()

    with _modal_lock:
        _waiters[waiter_id] = (event, None)

    from ui import output_bridge

    payload = json.dumps({"pending": [{"name": n, "message": m} for n, m in pending], "id": waiter_id})
    output_bridge.send_js(f"window.__setupFlowPush({payload})")
    _wait_for_response(event)

    with _modal_lock:
        result = _waiters.pop(waiter_id, (None, None))[1]
    return result

```

</details>

## `setup_flow_done(waiter_id, result)`

Called by api.setup_flow_done() from the JS side.

<details open><summary>Source</summary>

```python
def setup_flow_done(waiter_id: str, result: str) -> None:
    """Called by api.setup_flow_done() from the JS side."""
    with _modal_lock:
        if waiter_id in _waiters:
            event, _ = _waiters[waiter_id]
            _waiters[waiter_id] = (event, result)
            event.set()

```

</details>

## `show_progress(messages)`

Push a non-blocking progress HUD.

<details open><summary>Source</summary>

```python
def show_progress(messages: list[str], **_: object) -> None:
    """Push a non-blocking progress HUD."""
    from ui import output_bridge

    payload = json.dumps({"messages": messages, "value": 0, "status": ""})
    output_bridge.send_js(f"window.__hudPush({payload})")

```

</details>

## `set_progress(value, status_text)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def set_progress(value: float, status_text: str | None = None, *args: object) -> None:
    from ui import output_bridge

    payload = json.dumps({"value": value, "status": status_text or "", "args": list(args)})
    output_bridge.send_js(f"window.__hudSetProgress({payload})")

```

</details>

## `hide_progress()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def hide_progress() -> None:
    from ui import output_bridge

    output_bridge.send_js("window.__hudHide()")

```

</details>
