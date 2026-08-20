# ui.localization

Dynamic localization handling

## `_load()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def _load() -> dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    try:
        with utils.open_utf8(base.localization_file_dir) as f:
            _cache = jsonc.load(f)
    except (FileNotFoundError, jsonc.JSONDecodeError, OSError):
        _cache = {}
    assert _cache is not None
    return _cache

```

</details>

## `load_headless(lang)`

*No documentation available.*

<details open><summary>Source</summary>

```python
def load_headless(lang: str = "EN") -> None:
    global localization_dict
    data = _load()
    new_dict = {key: values.get(lang, values.get("EN", key)) for key, values in data.items()}
    with _localization_lock:
        localization_dict = new_dict

```

</details>

## `get_available()`

*No documentation available.*

<details open><summary>Source</summary>

```python
def get_available() -> list[str]:
    localization_data = _load()
    sub_headers = set()
    for header in localization_data.values():
        if isinstance(header, dict):
            sub_headers.update(header.keys())
    sorted_langs = sorted(lang for lang in sub_headers if lang != "EN")
    return ["EN"] + sorted_langs

```

</details>
