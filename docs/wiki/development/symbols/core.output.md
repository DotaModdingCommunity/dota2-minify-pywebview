# core.output

Agnostic output interface

## `_resolve(text_or_id)`

Resolve &-prefixed localization key with format args.

<details open><summary>Source</summary>

```python
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
    return text

```

</details>

## `capture_thread(sink)`

Route only THIS thread's add_text to `sink` while the context is active.

<details open><summary>Source</summary>

```python
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

```

</details>

## `_console_line(text, msg_type)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def _console_line(text: str, msg_type: str | None) -> None:
    prefix = PREFIX.get(msg_type or "", "")
    color = _STYLE.get(msg_type or "", "")
    try:
        if sys.stdout is not None:
            print(f"{color}{prefix}{text}{RESET}")
    except UnicodeEncodeError:
        if sys.stdout is not None:
            print(f"{color}{prefix}{text.encode('ascii', 'replace').decode('ascii')}{RESET}")

```

</details>

## `add_text(text_or_id)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def add_text(text_or_id: str, *args: Any, msg_type: str | None = None) -> Any:
    local_sink = getattr(_local, "sink", None)
    if local_sink is not None:
        return local_sink(text_or_id, *args, msg_type=msg_type)
    if _send is not None:
        return _send(text_or_id, *args, msg_type=msg_type)
    _console_line(_resolve(text_or_id, *args), msg_type)
    return None

```

</details>

## `add_section(text_or_id)`

Emit a phase/section header line (styled bold in both renderers).

<details open><summary>Source</summary>

```python
def add_section(text_or_id: str, *args: Any) -> Any:
    """Emit a phase/section header line (styled bold in both renderers)."""
    return add_text(text_or_id, *args, msg_type="section")

```

</details>

## `add_detail(text_or_id)`

Emit a dimmed secondary line (paths, tracebacks, list items).

<details open><summary>Source</summary>

```python
def add_detail(text_or_id: str, *args: Any) -> Any:
    """Emit a dimmed secondary line (paths, tracebacks, list items)."""
    return add_text(text_or_id, *args, msg_type="detail")

```

</details>

## `add_separator()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def add_separator() -> None:
    if _send is not None:
        _send(None, msg_type="__sep__")
    else:
        print("-" * 50)

```

</details>

## `clean()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def clean() -> None:
    if _send is not None:
        _send(None, msg_type="__clean__")

```

</details>
