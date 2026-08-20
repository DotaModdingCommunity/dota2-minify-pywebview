# core.utils

## `read_mod_states()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def read_mod_states() -> dict:
    if os.path.exists(_MOD_STATES_FILE):
        try:
            with open_utf8R(_MOD_STATES_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}

```

</details>

## `write_mod_states(states)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def write_mod_states(states: dict) -> None:
    os.makedirs(base.cache_dir, exist_ok=True)
    with open_utf8R(_MOD_STATES_FILE, "w") as f:
        json.dump(states, f, indent=2)

```

</details>

## `get_mod_state(mod_name, key, default)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def get_mod_state(mod_name: str, key: str, default=None):
    states = read_mod_states()
    mod_data = states.get(mod_name, {})
    if key not in mod_data and default is not None:
        states.setdefault(mod_name, {})[key] = default
        write_mod_states(states)
    return mod_data.get(key, default)

```

</details>

## `set_mod_state(mod_name, key, value)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def set_mod_state(mod_name: str, key: str, value) -> None:
    states = read_mod_states()
    states.setdefault(mod_name, {})[key] = value
    write_mod_states(states)

```

</details>

## `try_pass()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def try_pass():
    try:
        yield
    except Exception:
        pass

```

</details>

## `open_utf8(file, mode)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def open_utf8(file: str | os.PathLike[str], mode: str = "r", *args: Any, **kwargs: Any) -> IO[Any]:
    if "b" not in mode:
        kwargs.setdefault("encoding", "utf-8")
    return _real_open(file, mode, *args, **kwargs)

```

</details>

## `open_utf8R(file, mode)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def open_utf8R(file: str | os.PathLike[str], mode: str = "r", *args: Any, **kwargs: Any) -> IO[Any]:
    if "b" not in mode:
        kwargs.setdefault("encoding", "utf-8")
        kwargs.setdefault("errors", "replace")
    return _real_open(file, mode, *args, **kwargs)

```

</details>

## `setup_system()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def setup_system():
    import conditions

    from core import fs

    fs.create_dirs(base.logs_dir)
    conditions.is_dota_running("&error_please_close_dota_terminal", "error")
    conditions.is_compiler_found()

```

</details>

## `sanitize_win_path(name)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def sanitize_win_path(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).rstrip(" .") or uuid.uuid4().hex[:8]

```

</details>
