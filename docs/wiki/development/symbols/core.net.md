# core.net

Network request helpers with offline simulation support

## `simulate_failure()`

Whether network requests should be simulated as failing

<details open><summary>Source</summary>

```python
def simulate_failure() -> bool:
    "Whether network requests should be simulated as failing"
    return config.get("debug_simulate_offline", False)

```

</details>

## `get(url, timeout)`

requests.get() wrapper that simulates a failure when debug_simulate_offline is set

<details open><summary>Source</summary>

```python
def get(url: str, timeout: Any = 10, **kwargs: Any) -> requests.Response:
    "requests.get() wrapper that simulates a failure when debug_simulate_offline is set"
    if simulate_failure():
        raise requests.exceptions.ConnectionError(SIMULATED_FAILURE_MSG)
    return requests.get(url, timeout=timeout, **kwargs)

```

</details>
